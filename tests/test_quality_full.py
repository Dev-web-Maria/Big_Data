import sys, os, io, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
from minio import Minio
from tests.data_quality import DataQualityChecker

def load_silver_data(minio, source: str) -> pd.DataFrame:
    """Charge tous les fichiers Silver d'une source."""
    all_dfs = []
    try:
        objects = list(minio.list_objects(
            "silver", prefix=f"{source}/", recursive=True
        ))
        for obj in objects:
            if obj.object_name.endswith(".parquet"):
                data = minio.get_object("silver", obj.object_name).read()
                all_dfs.append(pd.read_parquet(io.BytesIO(data)))
    except Exception as e:
        print(f"   Erreur lecture Silver {source} : {e}")

    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()


def run():
    minio   = Minio("localhost:9000", access_key="minioadmin",
                    secret_key="minioadmin", secure=False)
    checker = DataQualityChecker()
    sources = ["bbc", "cnn", "aljazeera", "hespress", "akhbarona", "reuters"]

    print("\n AUDIT QUALITÉ — COUCHE SILVER\n")

    rapports = []
    for source in sources:
        df = load_silver_data(minio, source)
        if df.empty:
            print(f"    {source} : aucune donnée Silver trouvée")
            continue

        rapport = checker.run(df, source=source)
        checker.print_rapport(rapport)
        rapports.append(rapport)

    # Résumé global
    print(f"\n{'='*60}")
    print("  RÉSUMÉ GLOBAL")
    print(f"{'='*60}")
    for r in rapports:
        statut = "OK" if r["all_passed"] else "NOT OK"
        print(f"  {statut}  {r['source']:<12} → Score: {r['score']}% "
              f"| {r['total']} articles")

    total_articles = sum(r["total"] for r in rapports)
    avg_score      = round(sum(r["score"] for r in rapports) / len(rapports), 1) if rapports else 0
    print(f"{'─'*60}")
    print(f"  Score moyen : {avg_score}% | Total : {total_articles} articles")
    print(f"{'='*60}")


if __name__ == "__main__":
    run()