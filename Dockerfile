FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scraper/ ./scraper/
COPY etl/ ./etl/
COPY streaming/ ./streaming/
COPY tests/ ./tests/
COPY .env.example .env

CMD ["python", "scraper/run_all_sources.py"]