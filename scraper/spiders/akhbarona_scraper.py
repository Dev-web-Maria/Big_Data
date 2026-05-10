import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time, sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from scraper.utils.cleaner import clean_html, normalize_text, detect_language

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

class AkhbaronaScraper:
    BASE_URL = "https://www.akhbarona.com"

    def scrape(self, max_articles: int = 10) -> list:
        print("[AKHBARONA] Démarrage du scraping...")
        articles = []

        try:
            resp = requests.get(self.BASE_URL, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"[AKHBARONA]  Page principale inaccessible : {e}")
            return articles

        soup = BeautifulSoup(resp.text, "lxml")

        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = (
                f"{self.BASE_URL}{href}"
                if href.startswith("/")
                else href
            )

            if "akhbarona.com" not in full_url:
                continue

            # Extraire le nom du fichier : /economy/425405.html → "425405"
            filename = full_url.rstrip("/").split("/")[-1].replace(".html", "")

            # Garder uniquement les URLs dont le fichier est purement numérique
            # Ex: 425405.html ok  |  index.1.html non  |  index.html non
            if filename.isdigit() and full_url not in links:
                links.append(full_url)

        print(f"[AKHBARONA] {len(links)} articles candidats (IDs numériques)")

        for url in links[:max_articles * 2]:
            if len(articles) >= max_articles:
                break
            try:
                art = self._fetch_article(url)
                if art:
                    articles.append(art)
                    print(f"[AKHBARONA]  {art['titre'][:65]}...")
                time.sleep(1)
            except Exception as e:
                print(f"[AKHBARONA]  {url[:50]} : {e}")

        print(f"[AKHBARONA] Terminé : {len(articles)} articles.")
        return articles

    def _fetch_article(self, url: str) -> dict:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")

        # ── Titre (sélecteur confirmé par diagnostic) ──
        titre_el = soup.select_one("h1.artical-content-heads")
        if not titre_el:
            titre_el = soup.find("h1")
        if not titre_el:
            return None

        titre = normalize_text(titre_el.get_text().strip())
        if len(titre) < 5:
            return None

        # ── Contenu (sélecteur confirmé : div.bodystr) ──
        content_div = soup.select_one("div.bodystr")
        if content_div:
            paragraphs = [p.get_text() for p in content_div.find_all("p")]
            contenu = clean_html(" ".join(paragraphs))
        else:
            contenu = ""

        # Fallback : tous les <p> non vides de la page
        if len(contenu) < 80:
            all_p = [
                p.get_text().strip()
                for p in soup.find_all("p")
                if len(p.get_text().strip()) > 40
            ]
            contenu = clean_html(" ".join(all_p[:10]))

        if len(contenu) < 80:
            return None

        # ── Date ──
        date_pub = datetime.utcnow().date().isoformat()
        time_el = soup.find("time")
        if time_el:
            date_pub = (
                time_el.get("datetime") or time_el.get_text()
            ).strip()[:10]
        else:
            # Essayer depuis l'URL : /economy/425405.html -> pas de date
            # Essayer une balise meta
            meta_date = soup.find("meta", {"property": "article:published_time"})
            if meta_date and meta_date.get("content"):
                date_pub = meta_date["content"][:10]

        # ── Catégorie depuis l'URL ──
        # Ex: /economy/425405.html -> "economy"
        url_parts = url.replace("https://www.akhbarona.com/", "").split("/")
        categorie = url_parts[0] if url_parts and not url_parts[0].isdigit() else "general"

        return {
            "titre":            titre,
            "auteur":           "Akhbarona",
            "date_publication": date_pub,
            "categorie":        categorie,
            "contenu":          contenu,
            "source":           "akhbarona",
            "url":              url,
            "langue":           detect_language(contenu),
            "scraped_at":       datetime.utcnow().isoformat(),
        }


if __name__ == "__main__":
    scraper = AkhbaronaScraper()
    articles = scraper.scrape(max_articles=5)
    print(f"\nRÉSULTAT : {len(articles)} articles")
    for a in articles:
        print(f"  [{a['langue']}] [{a['categorie']}] {a['titre'][:65]}")