from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta
import sys, os

# Ajouter le projet au path d'Airflow
PROJECT_ROOT = "/opt/airflow/dags"
sys.path.insert(0, PROJECT_ROOT)

# ── Configuration du DAG ─────────────────────────────────────────
default_args = {
    "owner":            "data_engineer",
    "depends_on_past":  False,
    "retries":          2,
    "retry_delay":      timedelta(minutes=3),
    "execution_timeout": timedelta(minutes=30),
}

dag = DAG(
    dag_id="press_lakehouse_pipeline",
    description="Pipeline complet : Scraping → Bronze → Silver → Gold",
    schedule_interval="0 * * * *",  
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["press", "lakehouse", "medallion"],
)


# ── Tâches ───────────────────────────────────────────────────────

def task_scraping(**context):
    """Tâche 1 : Scraping toutes sources → MinIO Bronze"""
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, f"{PROJECT_ROOT}/scraper/run_all_sources.py"],
        capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise Exception(f"Scraping échoué : {result.stderr[-500:]}")
    print("[DAG] Scraping terminé.")


def task_bronze_to_silver(**context):
    """Tâche 2 : Bronze → Silver (nettoyage + Parquet)"""
    sys.path.insert(0, PROJECT_ROOT)
    from etl.bronze_to_silver.transform import BronzeToSilver
    from minio import Minio
    from datetime import datetime as dt

    minio = Minio("172.18.0.2:9000",
                  access_key="minioadmin", secret_key="minioadmin", secure=False)

    transformer = BronzeToSilver()
    today = dt.utcnow().date().isoformat()
    sources = ["bbc", "cnn", "aljazeera", "hespress", "akhbarona", "reuters"]
    total = 0

    for source in sources:
        df = transformer.run(source=source, date=today)
        total += len(df)

    print(f"[DAG] Silver : {total} articles transformés.")
    context["ti"].xcom_push(key="silver_count", value=total)


def task_silver_to_gold(**context):
    """Tâche 3 : Silver → Gold (MySQL Data Warehouse)"""
    sys.path.insert(0, PROJECT_ROOT)
    from etl.silver_to_gold.load_gold import SilverToGold
    from minio import Minio
    from datetime import datetime as dt

    minio = Minio("172.18.0.2:9000",
                  access_key="minioadmin", secret_key="minioadmin", secure=False)

    loader = SilverToGold()
    today = dt.utcnow().date().isoformat()
    sources = ["bbc", "cnn", "aljazeera", "hespress", "akhbarona", "reuters"]
    total = 0

    for source in sources:
        total += loader.load(source=source, date=today)

    print(f"[DAG] Gold : {total} articles chargés dans MySQL.")
    context["ti"].xcom_push(key="gold_count", value=total)


def task_quality_check(**context):
    """Tâche 4 : Vérification qualité avec DataQualityChecker"""
    sys.path.insert(0, PROJECT_ROOT)
    import io
    import pandas as pd
    from minio import Minio
    from tests.data_quality import DataQualityChecker

    minio   = Minio("172.18.0.2:9000", access_key="minioadmin",
                    secret_key="minioadmin", secure=False)
    checker = DataQualityChecker()
    sources = ["bbc", "cnn", "aljazeera", "hespress", "akhbarona", "reuters"]

    from datetime import datetime as dt
    today = dt.utcnow().date().isoformat()

    scores = []
    for source in sources:
        try:
            key  = f"{source}/{today.replace('-', '/')}/articles.parquet"
            data = minio.get_object("silver", key).read()
            df   = pd.read_parquet(io.BytesIO(data))

            rapport = checker.run(df, source=source)
            checker.print_rapport(rapport)
            scores.append(rapport["score"])

        except Exception as e:
            print(f"[QUALITÉ]  {source} : {e}")

    if scores:
        avg = round(sum(scores) / len(scores), 1)
        print(f"\n[QUALITÉ] Score moyen : {avg}%")
        if avg < 70:
            raise Exception(f"Qualité insuffisante : score moyen {avg}% < 70%")

    print("[QUALITÉ]  Vérification terminée.")


# ── Définition des tâches ────────────────────────────────────────

start = EmptyOperator(task_id="start", dag=dag)
end   = EmptyOperator(task_id="end",   dag=dag)

t1 = PythonOperator(
    task_id="scraping_toutes_sources",
    python_callable=task_scraping,
    dag=dag,
)

t2 = PythonOperator(
    task_id="bronze_vers_silver",
    python_callable=task_bronze_to_silver,
    dag=dag,
)

t3 = PythonOperator(
    task_id="silver_vers_gold",
    python_callable=task_silver_to_gold,
    dag=dag,
)

t4 = PythonOperator(
    task_id="verification_qualite",
    python_callable=task_quality_check,
    dag=dag,
)

# ── Ordre d'exécution ────────────────────────────────────────────
start >> t1 >> t2 >> t3 >> t4 >> end