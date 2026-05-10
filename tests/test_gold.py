import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from etl.silver_to_gold.load_gold import SilverToGold
from minio import Minio

def get_silver_dates(minio, source):
    dates = set()
    try:
        for obj in minio.list_objects("silver", prefix=f"{source}/", recursive=True):
            parts = obj.object_name.split("/")
            if len(parts) >= 4:
                dates.add(f"{parts[1]}-{parts[2]}-{parts[3]}")
    except:
        pass
    return sorted(dates)

def run():
    loader = SilverToGold()
    minio  = Minio("localhost:9000", access_key="minioadmin",
                   secret_key="minioadmin", secure=False)

    sources = ["bbc", "cnn", "aljazeera", "hespress", "akhbarona", "reuters"]
    print("\n PIPELINE SILVER → GOLD (MySQL)\n")
    results = {}

    for source in sources:
        dates = get_silver_dates(minio, source)
        total = 0
        for date in dates:
            total += loader.load(source, date)
        results[source] = total

    # Résumé
    print(f"\n{'='*55}")
    print("  RÉSUMÉ GOLD — MySQL Data Warehouse")
    print(f"{'='*55}")
    for source, count in results.items():
        status = "OK" if count > 0 else "NOT OK "
        print(f"  {status}  {source:<12} → {count:>3} articles")
    print(f"{'='*55}")
    print(f"  TOTAL : {sum(results.values())} articles dans MySQL")

    # Vérification SQL
    print("\n Vérification dans MySQL :")
    from sqlalchemy import create_engine, text
    engine = create_engine(
        "mysql+pymysql://press_user:press_pass@localhost:3306/press_warehouse?charset=utf8mb4"
    )
    with engine.connect() as conn:
        r = conn.execute(text("""
            SELECT s.nom_source, COUNT(*) as nb
            FROM fact_articles f
            JOIN dim_source s ON f.source_id = s.id
            GROUP BY s.nom_source ORDER BY nb DESC
        """))
        for row in r:
            print(f"  {row[0]:<15} → {row[1]} articles")

if __name__ == "__main__":
    run()