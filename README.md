# Architecture de Donnees pour l'Analyse des Articles de Presse

## Description

Ce projet propose une architecture Data Lakehouse complete pour la collecte automatisée, le traitement et l'analyse d'articles de presse provenant de sources marocaines et internationales. Il met en oeuvre une architecture Medallion (Bronze, Silver, Gold) combinant stockage distribue, ingestion batch et streaming, orchestration et visualisation.

## Architecture globale

Le pipeline de donnees suit le flux suivant :

    Sources Web --> Scraping --> Kafka --> MinIO Bronze
                                              |
                                         ETL Silver
                                              |
                                         ETL Gold
                                              |
                                    MySQL Data Warehouse
                                              |
                                     Airflow Orchestration
                                              |
                                       Power BI Dashboard

## Technologies utilisees

| Composant          | Technologie              | Role                          |
|--------------------|--------------------------|-------------------------------|
| Scraping           | Python, Scrapy, BS4      | Collecte des articles         |
| Streaming          | Apache Kafka             | Ingestion temps reel          |
| Data Lake          | MinIO                    | Stockage Bronze/Silver/Gold   |
| Traitement         | Pandas, PyArrow          | Transformation ETL            |
| Data Warehouse     | MySQL                    | Modele en etoile              |
| Orchestration      | Apache Airflow           | Planification pipeline        |
| Conteneurisation   | Docker, Docker Compose   | Deploiement unifié            |
| Visualisation      | Power BI                 | Dashboards analytiques        |

## Sources de donnees

| Source    | Pays  | Langue | Methode       |
|-----------|-------|--------|---------------|
| Hespress  | Maroc | AR     | Scrapy        |
| Akhbarona | Maroc | AR     | BeautifulSoup |
| BBC       | UK    | EN     | BeautifulSoup |
| CNN       | USA   | EN     | RSS           |
| Al Jazeera| Qatar | EN     | RSS           |
| Reuters   | UK    | EN     | RSS           |

## Structure du projet

    press_lakehouse/
    |-- scraper/
    |   |-- spiders/          # Scrapers par source
    |   |-- utils/            # Nettoyage et detection langue
    |   `-- run_all_sources.py
    |-- streaming/
    |   |-- producer/         # Kafka Producer
    |   `-- consumer/         # Kafka Consumer -> MinIO
    |-- etl/
    |   |-- bronze_to_silver/ # Nettoyage et transformation
    |   `-- silver_to_gold/   # Chargement Data Warehouse
    |-- airflow/
    |   `-- dags/             # DAG Airflow principal
    |-- warehouse/
    |   `-- schema/           # Schema MySQL en etoile
    |-- tests/
    |   `-- data_quality.py   # Controle qualite des donnees
    |-- docker/
    |   `-- docker-compose.yml
    |-- Dockerfile
    |-- requirements.txt
    `-- README.md

## Architecture Medallion

### Couche Bronze
Stockage des donnees brutes au format JSON dans MinIO.
Organisation : bronze/{source}/{YYYY}/{MM}/{DD}/batch_{timestamp}.json
Aucune transformation appliquee — conservation integrale des donnees source.

### Couche Silver
Donnees nettoyees et standardisees au format Parquet dans MinIO.
Transformations appliquees : suppression HTML, normalisation texte,
detection langue, validation dates, calcul nombre de mots.

### Couche Gold
Modele en etoile dans MySQL pour les analyses BI.
Tables : fact_articles, dim_date, dim_source, dim_categorie.

## Demarrage rapide

### Prerequis
- Docker Desktop 24+
- Python 3.11+
- Anaconda ou venv

### Installation

    git clone https://github.com/Dev-web-Maria/Big_Data.git
    cd press_lakehouse
    conda create -n press_lakehouse python=3.11 -y
    conda activate press_lakehouse
    pip install -r requirements.txt
    cp .env.example .env

### Lancement de l'infrastructure

    cd docker
    docker-compose up -d

### Lancement du pipeline

    # Scraping batch toutes sources
    python scraper/run_all_sources.py

    # Streaming Kafka (2 terminaux)
    python streaming/consumer/minio_consumer.py
    python streaming/producer/article_producer.py

    # ETL Bronze -> Silver -> Gold
    python tests/test_silver.py
    python tests/test_gold.py

    # Audit qualite
    python tests/test_quality_full.py

### Acces aux interfaces

| Interface     | URL                    | Credentials        |
|---------------|------------------------|--------------------|
| MinIO Console | http://localhost:9001  | minioadmin/minioadmin |
| Airflow       | http://localhost:8082  | admin/admin123     |
| Kafka UI      | http://localhost:8080  | -                  |

## Qualite des donnees

Dimensions evaluees :
- Completude : champs obligatoires non nuls
- Validite : format URLs, dates, longueur contenu
- Coherence : absence de doublons, plage de dates valide

## Pipeline Airflow

Le DAG press_lakehouse_pipeline s'execute toutes les heures et orchestre :
1. scraping_toutes_sources
2. bronze_vers_silver
3. silver_vers_gold
4. verification_qualite

## Variables d'environnement

Copier .env.example vers .env et adapter les valeurs :

    MINIO_ROOT_USER=minioadmin
    MINIO_ROOT_PASSWORD=minioadmin
    MINIO_ENDPOINT=localhost:9000
    
    KAFKA_BOOTSTRAP_SERVERS=localhost:9092
    KAFKA_TOPIC_RAW=raw-articles
    
    MYSQL_ROOT_PASSWORD=root123
    MYSQL_DATABASE=press_warehouse
    MYSQL_USER=press_user
    MYSQL_PASSWORD=press_pass

## Guide de demarrage 

### Prerequis
- Docker Desktop lancé
- Environnement conda active : conda activate press_lakehouse

### Etape 1 — Lancer toute l'infrastructure

cd docker
docker-compose up -d


### Etape 2 — Verifier que tout tourne

docker ps

5 conteneurs avec status Up :
- minio_storage
- mysql_dw
- kafka_broker
- zookeeper
- airflow

### Etape 3 — Creer le schema MySQL (premier lancement uniquement)

cd ..
python warehouse/schema/create_schema.py

### Etape 4 — Creer les buckets MinIO (premier lancement uniquement)

python tests/test_minio.py

### Etape 5 — Creer le topic Kafka (premier lancement uniquement)

docker exec kafka_broker kafka-topics --create --topic raw-articles --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

### Etape 6 — Lancer le pipeline complet

python scraper/run_all_sources.py
python tests/test_silver.py
python tests/test_gold.py
python tests/test_quality_full.py

### Etape 7 — Creer l'utilisateur Airflow (premier lancement uniquement)

docker exec -it airflow airflow users create --username admin --password admin123 --firstname Admin --lastname User --role Admin --email admin@press.com

### Etape 8 — Demo streaming Kafka (2 terminaux separes)

Terminal 1 :
python streaming/consumer/minio_consumer.py

Terminal 2 :
python streaming/producer/article_producer.py

### Acces aux interfaces

MinIO Console : http://localhost:9001
  Login : minioadmin
  Mot de passe : minioadmin

Airflow : http://localhost:8082
  Login : admin
  Mot de passe : admin123

Power BI : ouvrir dashboard/press_lakehouse_dashboard.pbix
  Cliquer sur Actualiser pour charger les nouvelles donnees

