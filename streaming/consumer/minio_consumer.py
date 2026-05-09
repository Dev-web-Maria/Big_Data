# streaming/consumer/minio_consumer.py
import json, io, os, time
from datetime import datetime
from collections import defaultdict
from kafka import KafkaConsumer
from minio import Minio
from dotenv import load_dotenv
load_dotenv()

class MinIOConsumer:
    """
    CONCEPT : Le Consumer lit les messages du topic Kafka et les
    persiste dans MinIO par lots (buffer).

    BUFFER STRATEGY :
    On n'écrit pas 1 fichier par article — trop de petits fichiers.
    On accumule en mémoire et on flush si :
      - buffer atteint BUFFER_SIZE articles  → flush immédiat
      - FLUSH_INTERVAL secondes écoulées    → flush par timeout
    """
    BUFFER_SIZE    = 10   # flush après 10 articles
    FLUSH_INTERVAL = 30   # ou toutes les 30 secondes

    def __init__(self):
        self.consumer = KafkaConsumer(
            os.getenv("KAFKA_TOPIC_RAW", "raw-articles"),
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            key_deserializer=lambda k: k.decode("utf-8") if k else None,

            # GROUP ID : Kafka retient la position de lecture par groupe
            # Si le consumer redémarre → il reprend où il s'était arrêté
            group_id="minio-bronze-writer",

            # "earliest" = relire depuis le début si nouveau groupe
            auto_offset_reset="earliest",
            enable_auto_commit=True,

            # Arrêt auto si aucun message pendant 30s
            consumer_timeout_ms=30000,
        )
        self.minio = Minio(
            os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("MINIO_ROOT_USER", "minioadmin"),
            secret_key=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"),
            secure=False,
        )
        # Buffer par source : {"bbc": [art1, art2], "hespress": [art3]}
        self.buffer      = defaultdict(list)
        self.last_flush  = time.time()
        self.total       = 0

    def _flush(self, source: str, articles: list):
        """Écrit un batch dans MinIO /bronze/stream_*."""
        if not articles:
            return
        now  = datetime.utcnow()
        key  = f"{source}/{now.strftime('%Y/%m/%d')}/stream_{now.strftime('%H%M%S%f')}.json"
        data = json.dumps(articles, ensure_ascii=False, indent=2).encode("utf-8")
        if not self.minio.bucket_exists("bronze"):
            self.minio.make_bucket("bronze")
        self.minio.put_object("bronze", key, io.BytesIO(data), len(data))
        self.total += len(articles)
        print(f"[CONSUMER] Flush → bronze/{key} ({len(articles)} articles | total: {self.total})")

    def _flush_all(self):
        for source, articles in self.buffer.items():
            if articles:
                self._flush(source, articles)
        self.buffer.clear()
        self.last_flush = time.time()

    def run(self):
        print("[CONSUMER] En ecoute sur raw-articles...")
        print(f"[CONSUMER] Buffer={self.BUFFER_SIZE} articles | Timeout={self.FLUSH_INTERVAL}s\n")
        try:
            for message in self.consumer:
                article = message.value
                source  = article.get("source", "unknown")
                print(f"[CONSUMER] Recu partition={message.partition} offset={message.offset} source={source} | {article.get('titre','')[:45]}")
                self.buffer[source].append(article)

                # Conditions de flush
                if (len(self.buffer[source]) >= self.BUFFER_SIZE or
                        time.time() - self.last_flush > self.FLUSH_INTERVAL):
                    print(f"[CONSUMER] Flush declenche")
                    self._flush_all()

        except KeyboardInterrupt:
            print("\n[CONSUMER] Arret — flush final...")
        finally:
            self._flush_all()
            self.consumer.close()
            print(f"[CONSUMER] Arrete. Total ecrit : {self.total} articles.")

if __name__ == "__main__":
    MinIOConsumer().run()