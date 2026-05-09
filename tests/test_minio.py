from minio import Minio

client = Minio(
    'localhost:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False
)

try:
    # Créer les buckets s'ils n'existent pas
    for bucket in ['bronze', 'silver', 'gold']:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            print(f'Bucket créé : {bucket}')
        else:
            print(f'Bucket déjà existant : {bucket}')

    buckets = [b.name for b in client.list_buckets()]
    print('\nBuckets disponibles :', buckets)

except Exception as e:
    print('Erreur :', e)