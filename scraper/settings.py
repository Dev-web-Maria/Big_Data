# scraper/settings.py
BOT_NAME = "press_lakehouse"

SPIDER_MODULES = ["scraper.spiders"]
NEWSPIDER_MODULE = "scraper.spiders"

# Règles de politesse
DOWNLOAD_DELAY = 2
ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS = 1

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Désactiver les cookies
COOKIES_ENABLED = False

# Format de sortie
FEED_EXPORT_ENCODING = "utf-8"

# Nécessaire sur Windows avec Scrapy
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"