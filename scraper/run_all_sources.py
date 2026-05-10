# scraper/run_all_sources.py
"""
Lance le scraping de toutes les sources et écrit dans MinIO Bronze.
Usage : python scraper/run_all_sources.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scraper.spiders.bbc_scraper       import BBCScraper
from scraper.spiders.rss_scraper       import RssScraper
from scraper.spiders.akhbarona_scraper import AkhbaronaScraper
from etl.bronze_to_silver.minio_writer import MinIOWriter

# ── Configuration des sources ─────────────────────────────────────
SOURCES = [
    {"name": "bbc",       "scraper": lambda: BBCScraper().scrape(max_articles=10)},
    {"name": "cnn",       "scraper": lambda: RssScraper("cnn").scrape(max_articles=10)},
    {"name": "reuters",   "scraper": lambda: RssScraper("reuters").scrape(max_articles=10)},
    {"name": "aljazeera", "scraper": lambda: RssScraper("aljazeera").scrape(max_articles=10)},
    {"name": "akhbarona", "scraper": lambda: AkhbaronaScraper().scrape(max_articles=10)},
]

# Hespress via Scrapy (traitement séparé car CrawlerProcess)
ENABLE_HESPRESS = True


def run_hespress(max_articles=10):
    from scrapy.crawler import CrawlerProcess
    from scraper.spiders.hespress_spider import HespressSpider
    HespressSpider.articles = []
    process = CrawlerProcess(settings={
        "LOG_LEVEL": "ERROR",
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
    })
    process.crawl(HespressSpider)
    process.start()
    return HespressSpider.articles[:max_articles]


def run_all():
    writer  = MinIOWriter()
    summary = []

    print("\n" + "*  " * 20)
    print("   SCRAPING TOUTES SOURCES → BRONZE")
    print("*  " * 20 + "\n")

    # ── Sources standard ──────────────────────────────────────────
    for src in SOURCES:
        name = src["name"]
        print(f"\n{'─'*50}")
        print(f"  SOURCE : {name.upper()}")
        print(f"{'─'*50}")
        try:
            articles = src["scraper"]()
            if articles:
                key = writer.write_bronze(articles, source=name)
                summary.append({
                    "source":  name,
                    "count":   len(articles),
                    "key":     key,
                    "status":  "done"
                })
            else:
                summary.append({"source": name, "count": 0, "status": "  0 articles"})
        except Exception as e:
            print(f"   Erreur : {e}")
            summary.append({"source": name, "count": 0, "status": f" {e}"})

    # ── Hespress ──────────────────────────────────────────────────
    if ENABLE_HESPRESS:
        print(f"\n{'─'*50}")
        print(f"  SOURCE : HESPRESS")
        print(f"{'─'*50}")
        try:
            articles = run_hespress(max_articles=10)
            if articles:
                key = writer.write_bronze(articles, source="hespress")
                summary.append({"source": "hespress", "count": len(articles),
                                 "key": key, "status": "done"})
            else:
                summary.append({"source": "hespress", "count": 0, "status": "  0 articles"})
        except Exception as e:
            print(f"  ✗ Erreur Hespress : {e}")
            summary.append({"source": "hespress", "count": 0, "status": f" {e}"})

    # ── Résumé final ──────────────────────────────────────────────
    print("\n\n" + "=" * 55)
    print("  RÉSUMÉ FINAL — COUCHE BRONZE")
    print("=" * 55)
    total = 0
    for s in summary:
        count = s["count"]
        total += count
        print(f"  {s['status']}  {s['source']:<12} → {count:>3} articles")
    print("─" * 55)
    print(f"  {'TOTAL':<16} → {total:>3} articles dans MinIO Bronze")
    print("=" * 55)

    # ── Listing des fichiers dans MinIO ───────────────────────────
    print("\n Fichiers dans MinIO /bronze :\n")
    all_files = writer.list_bronze_files()
    for f in all_files:
        size_kb = round(f["size"] / 1024, 1)
        print(f"  {f['path']:<55} {size_kb:>7} KB")

    return summary


if __name__ == "__main__":
    run_all()