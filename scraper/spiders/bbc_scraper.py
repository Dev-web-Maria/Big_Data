import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import sys
import os

# Permet d'importer depuis la racine du projet
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from scraper.utils.cleaner import clean_html, normalize_text, detect_language


class BBCScraper:
    BASE_URL = "https://www.bbc.com/news"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    def scrape(self, max_articles=10):
        print(f"[BBC] Démarrage du scraping...")
        articles = []

        try:
            resp = requests.get(self.BASE_URL, headers=self.HEADERS, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"[BBC] Erreur page principale : {e}")
            return articles

        soup = BeautifulSoup(resp.text, "lxml")

        # Récupérer les liens d'articles
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/news/" in href and href.count("/") >= 3:
                full_url = (
                    f"https://www.bbc.com{href}"
                    if href.startswith("/")
                    else href
                )
                if full_url not in links and "bbc.com/news" in full_url:
                    links.append(full_url)

        print(f"[BBC] {len(links)} liens trouvés, scraping des {max_articles} premiers...")

        for url in links[:max_articles]:
            try:
                article = self._fetch_article(url)
                if article:
                    articles.append(article)
                    print(f"[BBC] {article['titre'][:70]}...")
                time.sleep(1)  # Délai poli entre requêtes
            except Exception as e:
                print(f"[BBC] Erreur sur {url} : {e}")

        print(f"[BBC] Terminé : {len(articles)} articles collectés.")
        return articles

    def _fetch_article(self, url):
        resp = requests.get(url, headers=self.HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")

        # Titre
        titre_tag = soup.find("h1")
        if not titre_tag:
            return None
        titre = normalize_text(titre_tag.get_text().strip())

        # Contenu
        paragraphs = soup.select("article p, [data-component='text-block'] p")
        contenu = clean_html(" ".join(p.get_text() for p in paragraphs))

        # Filtre : ignorer les articles trop courts
        if len(contenu) < 100:
            return None

        # Date
        time_tag = soup.find("time")
        date_pub = ""
        if time_tag and time_tag.get("datetime"):
            date_pub = time_tag["datetime"][:10]
        else:
            date_pub = datetime.utcnow().date().isoformat()

        # Catégorie depuis l'URL  (ex: /news/world -> "world")
        parts = url.replace("https://www.bbc.com/", "").split("/")
        categorie = parts[1] if len(parts) > 1 else "general"

        return {
            "titre":            titre,
            "auteur":           "BBC News",
            "date_publication": date_pub,
            "categorie":        categorie,
            "contenu":          contenu,
            "source":           "bbc",
            "url":              url,
            "langue":           detect_language(contenu),
            "scraped_at":       datetime.utcnow().isoformat(),
        }


if __name__ == "__main__":
    scraper = BBCScraper()
    articles = scraper.scrape(max_articles=5)

    print(f"\n{'='*60}")
    print(f"RÉSULTAT : {len(articles)} articles")
    print('='*60)
    for i, art in enumerate(articles, 1):
        print(f"\n[{i}] {art['titre']}")
        print(f"    Date     : {art['date_publication']}")
        print(f"    Catégorie: {art['categorie']}")
        print(f"    Langue   : {art['langue']}")
        print(f"    Mots     : {len(art['contenu'].split())}")
        print(f"    URL      : {art['url']}")