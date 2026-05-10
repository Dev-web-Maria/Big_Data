"""
Test complet : Scraping BBC + Hespress → MinIO Bronze
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scraper.spiders.bbc_scraper import BBCScraper
from etl.bronze_to_silver.minio_writer import MinIOWriter


def run_bbc_to_bronze(max_articles=5):
    print("\n" + "=" * 60)
    print("PIPELINE BBC → BRONZE")
    print("=" * 60)

    # 1. Scraping
    print("\n[1/2] Scraping BBC...")
    scraper = BBCScraper()
    articles = scraper.scrape(max_articles=max_articles)
    print(f"      → {len(articles)} articles collectés")

    # 2. Écriture Bronze
    print("\n[2/2] Écriture dans MinIO Bronze...")
    writer = MinIOWriter()
    key = writer.write_bronze(articles, source="bbc")

    return key


def run_hespress_to_bronze(max_articles=5):
    print("\n" + "=" * 60)
    print("PIPELINE HESPRESS → BRONZE")
    print("=" * 60)

    # 1. Scraping Hespress via Scrapy
    print("\n[1/2] Scraping Hespress...")
    from scrapy.crawler import CrawlerProcess
    from scraper.spiders.hespress_spider import HespressSpider

    # Reset des articles entre les runs
    HespressSpider.articles = []

    process = CrawlerProcess(settings={
        "LOG_LEVEL": "ERROR",
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
    })
    process.crawl(HespressSpider)
    process.start()

    articles = HespressSpider.articles[:max_articles]
    print(f"      → {len(articles)} articles collectés")

    # 2. Écriture Bronze
    print("\n[2/2] Écriture dans MinIO Bronze...")
    writer = MinIOWriter()
    key = writer.write_bronze(articles, source="hespress")

    return key


def verify_bronze():
    print("\n" + "=" * 60)
    print("VÉRIFICATION DU CONTENU BRONZE")
    print("=" * 60)

    writer = MinIOWriter()

    for source in ["bbc", "hespress"]:
        files = writer.list_bronze_files(source=source)
        print(f"\n[{source.upper()}] {len(files)} fichier(s) dans bronze/{source}/")
        for f in files:
            print(f"  → {f['path']}")
            print(f"     Taille : {f['size']} octets | Date : {f['date']}")


if __name__ == "__main__":

    # Pipeline BBC
    run_bbc_to_bronze(max_articles=5)

    # Pipeline Hespress
    run_hespress_to_bronze(max_articles=5)

    # Vérification finale
    verify_bronze()

    print("\n" + "=" * 60)
    print("  SPRINT 1 TERMINÉ — Bronze layer opérationnel !")
    print("=" * 60)
    print("\nVérifie visuellement sur : http://localhost:9001")
    print("  Login : minioadmin / minioadmin")
    print("  Bucket bronze → bbc/ et hespress/")