# streaming/producer/article_producer.py
import json, os, time
from kafka import KafkaProducer
from dotenv import load_dotenv
load_dotenv()

class ArticleProducer:
    """
    CONCEPT : Le Producer envoie des messages dans Kafka.
    Chaque article = 1 message.
    La CLÉ = nom de la source → garantit l'ordre par source (même partition).
    """
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",      # Kafka confirme avant de continuer
            retries=3,
        )
        self.topic = os.getenv("KAFKA_TOPIC_RAW", "raw-articles")

    def publish(self, article: dict) -> bool:
        source = article.get("source", "unknown")
        try:
            future   = self.producer.send(self.topic, key=source, value=article)
            metadata = future.get(timeout=10)  # attend confirmation
            print(f"[PRODUCER]  partition={metadata.partition} | offset={metadata.offset} | {article['titre'][:50]}")
            return True
        except Exception as e:
            print(f"[PRODUCER]  Erreur : {e}")
            return False

    def publish_batch(self, articles: list, delay: float = 0.1):
        for art in articles:
            self.publish(art)
            time.sleep(delay)
        self.producer.flush()  # vide le buffer interne
        print(f"[PRODUCER] Batch de {len(articles)} articles envoyé.")

    def close(self):
        self.producer.close()


def simulate_stream(n: int = 5, interval: float = 1.0):
    """Simule des articles en temps réel pour tester sans scraper."""
    from datetime import datetime
    import random

    SOURCES    = ["hespress", "bbc", "cnn", "aljazeera", "akhbarona"]
    CATEGORIES = ["politique", "economie", "sport", "tech", "monde"]

    producer = ArticleProducer()
    print(f"[SIMULATEUR] Envoi de {n} articles (intervalle: {interval}s) — Ctrl+C pour arrêter\n")

    for i in range(n):
        source = random.choice(SOURCES)
        article = {
            "titre":            f"Article simulé #{i+1} — {source}",
            "auteur":           f"Bot {source}",
            "date_publication": datetime.utcnow().date().isoformat(),
            "categorie":        random.choice(CATEGORIES),
            "contenu":          f"Contenu de test numéro {i+1} pour valider le pipeline Kafka. " * 5,
            "source":           source,
            "url":              f"https://{source}.com/article-{i+1}",
            "langue":           "ar" if source in ["hespress","akhbarona"] else "en",
            "scraped_at":       datetime.utcnow().isoformat(),
        }
        producer.publish(article)
        time.sleep(interval)

    producer.producer.flush() 
    producer.close()
    print("\n[SIMULATEUR] Terminé.")


if __name__ == "__main__":
    simulate_stream(n=5, interval=1.0)