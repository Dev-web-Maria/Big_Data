import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
import sys, os, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from scraper.utils.cleaner import clean_html, normalize_text, detect_language

# ── Configuration des sources RSS ────────────────────────────────
RSS_SOURCES = {
    "cnn": {
        "feeds": [
            "http://rss.cnn.com/rss/edition.rss",
            "http://rss.cnn.com/rss/edition_world.rss",
            "http://rss.cnn.com/rss/edition_technology.rss",
        ],
        "langue_defaut": "en",
    },
    "reuters": {
        "feeds": [
            # Nouveaux endpoints Reuters + AP News comme fallback
            "https://feeds.bbci.co.uk/news/world/rss.xml",      
            "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
            "https://feeds.npr.org/1001/rss.xml",
        ],
        "langue_defaut": "en",
    },
    "aljazeera": {
        "feeds": [
            "https://www.aljazeera.com/xml/rss/all.xml",
        ],
        "langue_defaut": "en",
    },
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml",
}

# Namespaces XML courants dans les RSS
NS = {
    "media":   "http://search.yahoo.com/mrss/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc":      "http://purl.org/dc/elements/1.1/",
}


class RssScraper:

    def __init__(self, source_name: str):
        if source_name not in RSS_SOURCES:
            raise ValueError(f"Source inconnue : {source_name}. Disponibles : {list(RSS_SOURCES)}")
        self.source_name = source_name
        self.config      = RSS_SOURCES[source_name]

    def scrape(self, max_articles: int = 15) -> list:
        print(f"[{self.source_name.upper()}] Démarrage RSS...")
        all_articles = []

        for feed_url in self.config["feeds"]:
            try:
                articles = self._parse_feed(feed_url, max_articles)
                all_articles.extend(articles)
                print(f"[{self.source_name.upper()}] Feed OK : {len(articles)} articles ({feed_url[:60]}...)")
                time.sleep(1)
            except Exception as e:
                print(f"[{self.source_name.upper()}] ✗ Feed échoué : {e}")

        # Dédoublonner sur l'URL
        seen = set()
        unique = []
        for art in all_articles:
            if art["url"] not in seen:
                seen.add(art["url"])
                unique.append(art)

        result = unique[:max_articles]
        print(f"[{self.source_name.upper()}] Terminé : {len(result)} articles uniques.")
        return result

    def _parse_feed(self, feed_url: str, max_articles: int) -> list:
        resp = requests.get(feed_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        root = ET.fromstring(resp.content)

        # Trouver le channel
        channel = root.find("channel")
        if channel is None:
            channel = root  # Certains RSS n'ont pas de <channel>

        articles = []
        for item in channel.findall("item")[:max_articles]:
            art = self._parse_item(item)
            if art:
                articles.append(art)

        return articles

    def _parse_item(self, item) -> dict:
        # Titre
        titre_el = item.find("title")
        titre = normalize_text(titre_el.text or "") if titre_el is not None else ""
        if not titre or len(titre) < 5:
            return None

        # URL
        link_el = item.find("link")
        url = (link_el.text or "").strip() if link_el is not None else ""
        if not url.startswith("http"):
            return None

        # Contenu : description > content:encoded > media:description
        contenu = ""
        for tag in ["description", f"{{{NS['content']}}}encoded", "summary"]:
            el = item.find(tag)
            if el is not None and el.text:
                contenu = clean_html(el.text)
                if len(contenu) > 50:
                    break

        if len(contenu) < 30:
            contenu = titre  # Fallback minimal

        # Date
        date_pub = datetime.utcnow().date().isoformat()
        pub_date_el = item.find("pubDate")
        if pub_date_el is not None and pub_date_el.text:
            try:
                date_pub = parsedate_to_datetime(pub_date_el.text).date().isoformat()
            except Exception:
                pass

        # Catégorie
        cat_el = item.find("category")
        categorie = (cat_el.text or "general").strip().lower() if cat_el is not None else "general"

        # Auteur
        author_el = item.find("author") or item.find(f"{{{NS['dc']}}}creator")
        auteur = (author_el.text or self.source_name.upper()).strip() if author_el is not None else self.source_name.upper()

        return {
            "titre":            titre,
            "auteur":           auteur,
            "date_publication": date_pub,
            "categorie":        categorie,
            "contenu":          contenu,
            "source":           self.source_name,
            "url":              url,
            "langue":           detect_language(contenu),
            "scraped_at":       datetime.utcnow().isoformat(),
        }


if __name__ == "__main__":
    for source in ["cnn", "reuters", "aljazeera"]:
        scraper = RssScraper(source)
        articles = scraper.scrape(max_articles=5)
        print(f"\n{'='*50}")
        print(f"{source.upper()} — {len(articles)} articles")
        print('='*50)
        for a in articles:
            print(f"  [{a['langue']}] {a['titre'][:65]}")