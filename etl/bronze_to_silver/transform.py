import pandas as pd
import json, io, os, sys
from datetime import datetime
from bs4 import BeautifulSoup
from langdetect import detect
from minio import Minio
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

class BronzeToSilver:
    """
    CONCEPT SILVER :
    On lit les fichiers JSON bruts de Bronze, on les nettoie,
    et on écrit un fichier Parquet dans Silver.
    Parquet = format colonaire compressé, 10x plus rapide que JSON
    pour les requêtes analytiques (on lit seulement les colonnes utiles).
    """

    def __init__(self):
        self.minio = Minio(
            "172.18.0.2:9000",
            access_key=os.getenv("MINIO_ROOT_USER", "minioadmin"),
            secret_key=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"),
            secure=False,
        )

    def read_bronze(self, source: str, date: str) -> pd.DataFrame:
        """
        Lit tous les fichiers JSON Bronze d'une source/date.
        date format : YYYY-MM-DD
        """
        prefix  = f"{source}/{date.replace('-', '/')}"
        objects = list(self.minio.list_objects("bronze", prefix=prefix, recursive=True))
        print(f"[SILVER] {len(objects)} fichier(s) Bronze trouvé(s) pour {source}/{date}")

        all_articles = []
        for obj in objects:
            data = self.minio.get_object("bronze", obj.object_name).read()
            all_articles.extend(json.loads(data))

        if not all_articles:
            print(f"[SILVER] Aucun article à transformer.")
            return pd.DataFrame()

        df = pd.DataFrame(all_articles)
        print(f"[SILVER] {len(df)} articles bruts chargés.")
        return df

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transformations Silver :
        1. Dédoublonnage sur l'URL
        2. Nettoyage HTML du contenu
        3. Normalisation des champs texte
        4. Gestion des valeurs nulles
        5. Calcul du nombre de mots
        6. Détection de la langue
        7. Validation de la date
        """
        if df.empty:
            return df

        initial = len(df)

        # 1. Dédoublonnage
        df = df.drop_duplicates(subset=["url"]).copy()
        print(f"[SILVER] Doublons supprimés : {initial - len(df)}")

        # 2. Nettoyage HTML
        def remove_html(text):
            if not text: return ""
            return BeautifulSoup(str(text), "lxml").get_text(separator=" ").strip()

        df["contenu"] = df["contenu"].fillna("").apply(remove_html)
        df["titre"]   = df["titre"].fillna("").str.strip()

        # 3. Normalisation texte
        df["titre"]    = df["titre"].str.replace(r'\s+', ' ', regex=True)
        df["auteur"]   = df["auteur"].fillna("Anonyme").str.strip()
        df["categorie"]= df["categorie"].fillna("general").str.lower().str.strip()
        df["source"]   = df["source"].fillna("unknown").str.lower().str.strip()

        # 4. Validation date
        df["date_publication"] = pd.to_datetime(
            df["date_publication"], errors="coerce"
        ).dt.date.astype(str)
        df["date_publication"] = df["date_publication"].replace("NaT", datetime.utcnow().date().isoformat())

        # 5. Nombre de mots
        df["nb_mots"] = df["contenu"].str.split().str.len().fillna(0).astype(int)

        # 6. Détection langue
        def safe_detect(text):
            try:
                return detect(str(text)[:400]) if len(str(text)) > 20 else "unknown"
            except:
                return "unknown"
        df["langue_detectee"] = df["contenu"].apply(safe_detect)

        # 7. Timestamp transformation
        df["silver_at"] = datetime.utcnow().isoformat()

        return df

    def filter_quality(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filtre les articles de mauvaise qualité :
        - titre trop court (< 5 chars)
        - contenu trop court (< 100 chars)
        - URL invalide
        """
        if df.empty:
            return df

        before = len(df)
        df = df[df["titre"].str.len() >= 5]
        df = df[df["contenu"].str.len() >= 100]
        df = df[df["url"].str.startswith("http", na=False)]
        print(f"[SILVER] Qualité : {before - len(df)} articles filtrés, {len(df)} retenus.")
        return df

    def write_silver(self, df: pd.DataFrame, source: str, date: str) -> str:
        """
        Écrit le DataFrame en Parquet dans MinIO /silver.

        POURQUOI PARQUET ?
        - Compression : 5x moins de place que JSON
        - Colonaire : pour lire seulement "titre" et "date",
          Parquet ne lit pas les autres colonnes → très rapide
        - Typage fort : les dates restent des dates, les entiers restent entiers
        """
        buf = io.BytesIO()
        df.to_parquet(buf, engine="pyarrow", index=False, compression="snappy")
        buf.seek(0)

        key = f"{source}/{date.replace('-', '/')}/articles.parquet"

        if not self.minio.bucket_exists("silver"):
            self.minio.make_bucket("silver")

        self.minio.put_object(
            "silver", key, buf, buf.getbuffer().nbytes,
            content_type="application/octet-stream"
        )

        size_kb = round(buf.getbuffer().nbytes / 1024, 1)
        print(f"[SILVER] ✓ Écrit → s3://silver/{key} ({size_kb} KB, {len(df)} articles)")
        return key

    def run(self, source: str, date: str) -> pd.DataFrame:
        """Pipeline complet Bronze → Silver pour une source/date."""
        print(f"\n{'='*55}")
        print(f"[SILVER] Pipeline : {source} / {date}")
        print(f"{'='*55}")

        df = self.read_bronze(source, date)
        if df.empty:
            return df

        df = self.clean(df)
        df = self.filter_quality(df)

        if not df.empty:
            self.write_silver(df, source, date)

        return df