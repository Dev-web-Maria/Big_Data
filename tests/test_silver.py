import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from etl.bronze_to_silver.transform import BronzeToSilver
from minio import Minio

def get_available_dates(minio, source: str) -> list:
    """Trouve toutes les dates disponibles dans Bronze pour une source."""
    dates = set()
    objects = minio.list_objects("bronze", prefix=f"{source}/", recursive=True)
    for obj in objects:
        # Chemin : bbc/2026/05/07/batch_xxx.json → date = 2026-05-07
        parts = obj.object_name.split("/")
        if len(parts) >= 4:
            date_str = f"{parts[1]}-{parts[2]}-{parts[3]}"
            dates.add(date_str)
    return sorted(dates)

def run():
    transformer = BronzeToSilver()
    minio = Minio(
        "localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False
    )

    sources = ["bbc", "cnn", "aljazeera", "hespress", "akhbarona", "reuters"]
    print("\n PIPELINE BRONZE → SILVER\n")
    results = {}

    for source in sources:
        dates = get_available_dates(minio, source)
        if not dates:
            print(f"[SILVER]  Aucune donnée Bronze pour {source}")
            results[source] = 0
            continue

        total_source = 0
        for date in dates:
            df = transformer.run(source=source, date=date)
            total_source += len(df)
        results[source] = total_source

    print(f"\n{'='*55}")
    print("  RÉSUMÉ SILVER")
    print(f"{'='*55}")
    for source, count in results.items():
        status = "OK" if count > 0 else "NOT OK "
        print(f"  {status}  {source:<12} → {count:>3} articles propres")
    print(f"{'='*55}")
    print(f"  TOTAL : {sum(results.values())} articles dans Silver")

if __name__ == "__main__":
    run()