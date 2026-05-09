import pandas as pd
from datetime import datetime

class DataQualityChecker:
    """
    Vérifie la qualité d'un DataFrame d'articles.
    Retourne un rapport détaillé avec score global.
    """

    # Seuils acceptables (en %)
    THRESHOLDS = {
        "titre_vide":       5,   # max 5% de titres vides
        "contenu_court":   90,   # max 90% de contenus < 50 mots
        "url_invalide":     2,   # max 2% d'URLs invalides
        "date_invalide":    5,   # max 5% de dates invalides
        "doublons":         0,   # 0 doublon toléré
    }

    def check_completeness(self, df: pd.DataFrame) -> dict:
        """Complétude : champs obligatoires non nuls."""
        total = len(df)
        if total == 0:
            return {}

        results = {}
        champs = ["titre", "url", "source", "date_publication", "contenu"]

        for champ in champs:
            if champ not in df.columns:
                results[champ] = {"null_count": total, "null_pct": 100.0, "passed": False}
                continue

            null_count = df[champ].isnull().sum() + (df[champ] == "").sum()
            null_pct   = round(100 * null_count / total, 2)
            results[champ] = {
                "null_count": int(null_count),
                "null_pct":   null_pct,
                "passed":     null_pct <= self.THRESHOLDS.get(f"{champ}_vide", 5)
            }

        return results

    def check_validity(self, df: pd.DataFrame) -> dict:
        """Validité : les valeurs respectent les règles métier."""
        total = len(df)
        if total == 0:
            return {}

        results = {}

        # 1. Titre minimum 5 caractères
        titres_courts = (df["titre"].str.len() < 5).sum() if "titre" in df else total
        results["titre_min_length"] = {
            "count":  int(titres_courts),
            "pct":    round(100 * titres_courts / total, 2),
            "passed": (100 * titres_courts / total) <= self.THRESHOLDS["titre_vide"]
        }

        # 2. URL valide
        urls_invalides = (~df["url"].str.startswith("http", na=False)).sum() if "url" in df else total
        results["url_format"] = {
            "count":  int(urls_invalides),
            "pct":    round(100 * urls_invalides / total, 2),
            "passed": (100 * urls_invalides / total) <= self.THRESHOLDS["url_invalide"]
        }

        # 3. Date valide
        if "date_publication" in df:
            dates_invalides = pd.to_datetime(
                df["date_publication"], errors="coerce"
            ).isnull().sum()
        else:
            dates_invalides = total
        results["date_format"] = {
            "count":  int(dates_invalides),
            "pct":    round(100 * dates_invalides / total, 2),
            "passed": (100 * dates_invalides / total) <= self.THRESHOLDS["date_invalide"]
        }

        # 4. Contenu minimum 50 mots
        if "nb_mots" in df:
            contenus_courts = (df["nb_mots"] < 50).sum()
        elif "contenu" in df:
            contenus_courts = (df["contenu"].str.split().str.len() < 50).sum()
        else:
            contenus_courts = 0
        results["contenu_min_mots"] = {
            "count":  int(contenus_courts),
            "pct":    round(100 * contenus_courts / total, 2),
            "passed": (100 * contenus_courts / total) <= self.THRESHOLDS["contenu_court"]
        }

        return results

    def check_coherence(self, df: pd.DataFrame) -> dict:
        total = len(df)
        if total == 0:
            return {}

        results = {}

        # Doublons dans le MÊME batch uniquement
        doublons = df["url"].duplicated(keep="first").sum() if "url" in df else 0
        results["doublons_url"] = {
            "count":  int(doublons),
            "pct":    round(100 * doublons / total, 2),
            "passed": (100 * doublons / total) <= 20  # ← 20% toléré (multi-dates)
        }

        # Dates dans une plage logique
        if "date_publication" in df:
            dates = pd.to_datetime(df["date_publication"], errors="coerce")
            hors_plage = (~dates.between(
                "2020-01-01", datetime.utcnow().isoformat()
            )).sum()
        else:
            hors_plage = 0
        results["dates_hors_plage"] = {
            "count":  int(hors_plage),
            "pct":    round(100 * hors_plage / total, 2),
            "passed": (100 * hors_plage / total) <= 5
        }

        # Sources connues
        sources_connues = {"bbc","cnn","reuters","aljazeera","hespress","akhbarona"}
        if "source" in df:
            sources_inconnues = (~df["source"].isin(sources_connues)).sum()
        else:
            sources_inconnues = 0
        results["sources_inconnues"] = {
            "count":  int(sources_inconnues),
            "pct":    round(100 * sources_inconnues / total, 2),
            "passed": sources_inconnues == 0
        }

        return results

    def run(self, df: pd.DataFrame, source: str = "") -> dict:
        """Lance tous les checks et retourne le rapport complet."""
        total = len(df)

        completeness = self.check_completeness(df)
        validity     = self.check_validity(df)
        coherence    = self.check_coherence(df)

        # Score global : % de checks passés
        all_checks = (
            list(completeness.values()) +
            list(validity.values()) +
            list(coherence.values())
        )
        passed = sum(1 for c in all_checks if c.get("passed", False))
        score  = round(100 * passed / len(all_checks), 1) if all_checks else 0

        rapport = {
            "source":       source,
            "total":        total,
            "completeness": completeness,
            "validity":     validity,
            "coherence":    coherence,
            "score":        score,
            "all_passed":   score == 100.0,
            "checked_at":   datetime.utcnow().isoformat(),
        }

        return rapport

    def print_rapport(self, rapport: dict):
        """Affiche le rapport de qualité de façon lisible."""
        print(f"\n{'='*60}")
        print(f"  RAPPORT QUALITÉ — {rapport['source'].upper()}")
        print(f"  Score global : {rapport['score']}% | {rapport['total']} articles")
        print(f"{'='*60}")

        sections = [
            ("COMPLÉTUDE",  rapport["completeness"]),
            ("VALIDITÉ",    rapport["validity"]),
            ("COHÉRENCE",   rapport["coherence"]),
        ]

        for section_name, checks in sections:
            print(f"\n  [{section_name}]")
            for check_name, result in checks.items():
                icon  = "✅" if result.get("passed") else "❌"
                count = result.get("count", result.get("null_count", 0))
                pct   = result.get("pct",   result.get("null_pct",   0))
                print(f"    {icon} {check_name:<25} : {count} cas ({pct}%)")

        status = "✅ QUALITÉ OK" if rapport["all_passed"] else "❌ QUALITÉ INSUFFISANTE"
        print(f"\n  → {status}")
        print(f"{'='*60}")