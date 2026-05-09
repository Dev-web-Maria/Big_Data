# etl/silver_to_gold/load_gold.py
import pandas as pd
import io, os, sys
from datetime import datetime, date
from minio import Minio
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Mapping source → métadonnées
SOURCE_META = {
    "bbc":       {"type": "international", "pays": "UK",      "langue": "en"},
    "cnn":       {"type": "international", "pays": "USA",     "langue": "en"},
    "reuters":   {"type": "agence",        "pays": "UK",      "langue": "en"},
    "aljazeera": {"type": "international", "pays": "Qatar",   "langue": "en"},
    "hespress":  {"type": "national",      "pays": "Maroc",   "langue": "ar"},
    "akhbarona": {"type": "national",      "pays": "Maroc",   "langue": "ar"},
}

MOIS_FR = {1:"Janvier",2:"Février",3:"Mars",4:"Avril",5:"Mai",6:"Juin",
           7:"Juillet",8:"Août",9:"Septembre",10:"Octobre",11:"Novembre",12:"Décembre"}
JOUR_FR = {1:"Lundi",2:"Mardi",3:"Mercredi",4:"Jeudi",5:"Vendredi",6:"Samedi",7:"Dimanche"}


class SilverToGold:
    """
    CONCEPT GOLD :
    On lit les Parquet Silver et on charge dans MySQL
    selon le modèle en étoile :
      1. Insérer la date dans dim_date
      2. Insérer la source dans dim_source
      3. Insérer la catégorie dans dim_categorie
      4. Insérer l'article dans fact_articles avec les IDs des dimensions
    """

    def __init__(self):
        self.minio = Minio(
            "172.18.0.2:9000",    
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False
        )
        db_url = "mysql+pymysql://press_user:press_pass@172.17.0.2:3306/press_warehouse?charset=utf8mb4"
        self.engine = create_engine(db_url)

    # ── Dimensions ──────────────────────────────────────────────

    def _get_or_create_date(self, conn, date_str: str) -> int:
        """Insère la date dans dim_date si elle n'existe pas, retourne son ID."""
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            d = datetime.utcnow().date()

        conn.execute(text("""
            INSERT IGNORE INTO dim_date
              (date_complete, annee, trimestre, mois, nom_mois, semaine, jour, nom_jour, est_weekend)
            VALUES
              (:date, :annee, :trim, :mois, :nom_mois, :sem, :jour, :nom_jour, :weekend)
        """), {
            "date":     d,
            "annee":    d.year,
            "trim":     (d.month - 1) // 3 + 1,
            "mois":     d.month,
            "nom_mois": MOIS_FR[d.month],
            "sem":      d.isocalendar()[1],
            "jour":     d.day,
            "nom_jour": JOUR_FR[d.weekday()],
            "weekend":  d.weekday() >= 5,
        })
        result = conn.execute(
            text("SELECT id FROM dim_date WHERE date_complete = :date"), {"date": d}
        )
        return result.fetchone()[0]

    def _get_or_create_source(self, conn, source: str) -> int:
        meta = SOURCE_META.get(source, {"type": "international", "pays": "Unknown", "langue": "unknown"})
        conn.execute(text("""
            INSERT IGNORE INTO dim_source (nom_source, type_source, pays, langue_principale)
            VALUES (:nom, :type, :pays, :lang)
        """), {"nom": source, "type": meta["type"], "pays": meta["pays"], "lang": meta["langue"]})
        result = conn.execute(
            text("SELECT id FROM dim_source WHERE nom_source = :nom"), {"nom": source}
        )
        return result.fetchone()[0]

    def _get_or_create_categorie(self, conn, categorie: str) -> int:
        cat = str(categorie).strip().lower() or "general"
        conn.execute(text("""
            INSERT IGNORE INTO dim_categorie (nom_categorie) VALUES (:cat)
        """), {"cat": cat})
        result = conn.execute(
            text("SELECT id FROM dim_categorie WHERE nom_categorie = :cat"), {"cat": cat}
        )
        return result.fetchone()[0]

    # ── Pipeline principal ───────────────────────────────────────

    def load(self, source: str, date: str) -> int:
        """Charge les articles Silver d'une source/date dans MySQL Gold."""
        print(f"\n{'='*55}")
        print(f"[GOLD] Pipeline : {source} / {date}")
        print(f"{'='*55}")

        # Lire le Parquet Silver
        key = f"{source}/{date.replace('-', '/')}/articles.parquet"
        try:
            data = self.minio.get_object("silver", key).read()
            df   = pd.read_parquet(io.BytesIO(data))
            print(f"[GOLD] {len(df)} articles Silver lus.")
        except Exception as e:
            print(f"[GOLD] ⚠️  Fichier Silver introuvable : {e}")
            return 0

        loaded = 0

        # Pré-charger source_id dans une transaction dédiée
        with self.engine.begin() as conn:
            source_id = self._get_or_create_source(conn, source)
        # ↑ commit automatique à la sortie du with

        # Insérer chaque article dans sa propre transaction
        for _, row in df.iterrows():
            try:
                with self.engine.begin() as conn:
                    date_id = self._get_or_create_date(
                        conn, str(row.get("date_publication", date))
                    )
                    cat_id = self._get_or_create_categorie(
                        conn, str(row.get("categorie", "general"))
                    )
                    conn.execute(text("""
                        INSERT IGNORE INTO fact_articles
                        (titre, auteur, date_id, source_id, categorie_id,
                        nb_mots, langue_detectee, url)
                        VALUES
                        (:titre, :auteur, :date_id, :source_id, :cat_id,
                        :nb_mots, :langue, :url)
                    """), {
                        "titre":     str(row.get("titre", ""))[:500],
                        "auteur":    str(row.get("auteur", "Anonyme"))[:200],
                        "date_id":   date_id,
                        "source_id": source_id,
                        "cat_id":    cat_id,
                        "nb_mots":   int(row.get("nb_mots", 0)),
                        "langue":    str(row.get("langue_detectee", "unknown"))[:10],
                        "url":       str(row.get("url", ""))[:1000],
                    })
                # ↑ commit automatique, rollback si exception
                loaded += 1
            except Exception as e:
                print(f"[GOLD] ⚠️ Article ignoré ({row.get('titre', '?')[:50]}) : {e}")

        print(f"[GOLD] ✓ {loaded}/{len(df)} articles chargés dans MySQL.")
        return loaded