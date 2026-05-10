import scrapy
import sys, os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from scraper.utils.cleaner import clean_html, normalize_text, detect_language


class HespressSpider(scrapy.Spider):
    name = "hespress"
    allowed_domains = ["hespress.com", "www.hespress.com"]
    start_urls = ["https://hespress.com/"]

    articles = [] 

    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "CONCURRENT_REQUESTS": 1,
        "ROBOTSTXT_OBEY": False,
        "LOG_LEVEL": "WARNING",
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "USER_AGENT": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    def parse(self, response):
        """Page d'accueil → récupère les liens d'articles."""

        # Les URLs Hespress contiennent un ID numérique à la fin : -1738969.html
        links = []
        for href in response.css("a::attr(href)").getall():
            # Garder seulement les URLs avec un ID numérique
            if "hespress.com" in href and href.endswith(".html"):
                parts = href.rstrip(".html").split("-")
                if parts and parts[-1].isdigit():
                    if href not in links:
                        links.append(href)

        self.logger.warning(f"[HESPRESS] {len(links)} liens d'articles trouvés")

        for link in links[:10]:  # 10 articles max pour le test
            yield scrapy.Request(link, callback=self.parse_article)

    def parse_article(self, response):
        """Page article → extrait les données."""

        # Titre : h1.post-title (confirmé par le diagnostic)
        titre = response.css("h1.post-title::text").get("")
        if not titre:
            titre = response.css("h1::text").get("")
        titre = normalize_text(titre.strip())

        if not titre or len(titre) < 3:
            return

        # Contenu : div.article-content p (confirmé par le diagnostic)
        paragraphs = response.css("div.article-content p::text").getall()

        # Fallback si vide
        if not paragraphs:
            paragraphs = response.css("div.article-container p::text").getall()

        contenu = clean_html(" ".join(paragraphs))

        if len(contenu) < 80:
            return

        # Date
        date_pub = (
            response.css("time::attr(datetime)").get() or
            response.css(".post-date::text").get() or
            datetime.utcnow().date().isoformat()
        )
        date_pub = str(date_pub).strip()[:10]

        # Catégorie depuis l'URL
        # Ex: hespress.com/sport/... ou hespress.com/politique/...
        url_parts = response.url.split("/")
        categorie = "general"
        for part in url_parts:
            if part and part not in ["https:", "", "www.hespress.com", "hespress.com"]:
                # Ignorer la partie slug arabe (contient %)
                if "%" not in part and not part.endswith(".html"):
                    categorie = part
                    break

        article = {
            "titre":            titre,
            "auteur":           response.css(".author-name::text, .post-author a::text").get("Hespress") or "Hespress",
            "date_publication": date_pub,
            "categorie":        categorie,
            "contenu":          contenu,
            "source":           "hespress",
            "url":              response.url,
            "langue":           detect_language(contenu),
            "scraped_at":       datetime.utcnow().isoformat(),
        }

        HespressSpider.articles.append(article)
        self.logger.warning(f"[HESPRESS] ✓ {titre[:60]}")
        yield article