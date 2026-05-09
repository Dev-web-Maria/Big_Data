🗞️ Press Lakehouse — Architecture Data pour l'Analyse de Presse

Projet académique Big Data — Architecture Data Lakehouse complète pour la collecte
et l'analyse d'articles de presse marocains et internationaux.

## 🏗️ Architecture
Scraping → Kafka → MinIO (Bronze/Silver/Gold) → MySQL → Airflow → Superset

## 🛠️ Technologies

| Composant | Technologie |
|-----------|------------|
| Scraping | Python, Scrapy, BeautifulSoup |
| Streaming | Apache Kafka |
| Data Lake | MinIO (S3) |
| ETL | Python, Pandas, PyArrow |
| Data Warehouse | MySQL |
| Orchestration | Apache Airflow |
| Conteneurisation | Docker |

## 📰 Sources

| Source | Pays | Langue | Méthode |
|--------|------|--------|---------|
| Hespress | Maroc | AR | Scrapy |
| Akhbarona | Maroc | AR | BeautifulSoup |
| BBC | UK | EN | BeautifulSoup |
| CNN | USA | EN | RSS |
| Al Jazeera | Qatar | EN | RSS |
| Reuters | UK | EN | RSS |

## 🚀 Démarrage rapide

### Prérequis
- Docker Desktop
- Python 3.11+
- Anaconda

### Installation

```bash
# 1. Cloner le repo
git clone https://github.com/TON_USERNAME/press_lakehouse.git
cd press_lakehouse

# 2. Créer l'environnement conda
conda create -n press_lakehouse python=3.11 -y
conda activate press_lakehouse
pip install -r requirements.txt

# 3. Configurer les variables d'environnement
cp .env.example .env
# Modifier .env avec vos paramètres

# 4. Lancer l'infrastructure
cd docker
docker-compose up -d

# 5. Lancer le scraping
python scraper/run_all_sources.py
```

## 📁 Structure du projet
press_lakehouse/
├── scraper/          # Scrapers par source
├── streaming/        # Kafka Producer/Consumer
├── etl/              # Pipeline Bronze→Silver→Gold
├── airflow/dags/     # DAG Airflow
├── warehouse/        # Schéma MySQL
├── tests/            # Tests qualité
└── docker/           # Docker Compose

## 🥉🥈🥇 Architecture Médaillon

- **Bronze** : Données brutes JSON dans MinIO
- **Silver** : Données nettoyées Parquet dans MinIO
- **Gold** : Modèle en étoile dans MySQL

## ✅ Qualité des données

Score moyen : **94.5%** sur 154 articles