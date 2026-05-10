# etl/bronze_to_silver/minio_writer.py
import json
import io
import os
from datetime import datetime
from minio import Minio
from dotenv import load_dotenv

load_dotenv()

class MinIOWriter:

    def __init__(self):
        self.client = Minio(
            os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("MINIO_ROOT_USER", "minioadmin"),
            secret_key=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"),
            secure=False
        )
        self._ensure_buckets()

    def _ensure_buckets(self):
        for bucket in ["bronze", "silver", "gold"]:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                print(f"[MINIO] Bucket créé : {bucket}")

    def write_bronze(self, articles: list, source: str) -> str:
        """
        Écrit les articles bruts dans :
        bronze/{source}/{YYYY}/{MM}/{DD}/batch_{HHMMSSffffff}.json
        """
        if not articles:
            print(f"[BRONZE] Aucun article à écrire pour {source}.")
            return ""

        now = datetime.utcnow()
        date_path = now.strftime("%Y/%m/%d")
        timestamp  = now.strftime("%H%M%S%f")
        key = f"{source}/{date_path}/batch_{timestamp}.json"

        # Sérialisation JSON
        data = json.dumps(articles, ensure_ascii=False, indent=2).encode("utf-8")

        self.client.put_object(
            bucket_name="bronze",
            object_name=key,
            data=io.BytesIO(data),
            length=len(data),
            content_type="application/json"
        )

        print(f"[BRONZE] ✓ {len(articles)} articles → s3://bronze/{key}")
        return key

    def list_bronze_files(self, source: str = None) -> list:
        """Liste tous les fichiers dans le bucket bronze."""
        prefix = f"{source}/" if source else ""
        objects = self.client.list_objects("bronze", prefix=prefix, recursive=True)
        files = []
        for obj in objects:
            files.append({
                "path":  obj.object_name,
                "size":  obj.size,
                "date":  str(obj.last_modified)[:19]
            })
        return files