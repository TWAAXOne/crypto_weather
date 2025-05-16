from scrape import run_scraper

if __name__ == "__main__":
    print("🚀 Démarrage du scraping...")
    articles = run_scraper(max_articles=10)

    print(f"✅ {len(articles)} articles récupérés.")

    # Optionnel : sauvegarder les données récupérées dans un fichier JSON
    import json

    with open("articles.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)

    print("📄 Articles enregistrés dans articles.json")