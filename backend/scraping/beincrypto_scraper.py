import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

# Top 10 cryptos (CoinMarketCap)
CRYPTO_KEYWORDS = [
    "Bitcoin", "BTC",
    "Ethereum", "ETH",
    "Tether", "USDT",
    "XRP",
    "Binance Coin", "BNB",
    "Solana", "SOL",
    "USD Coin", "USDC",
    "Dogecoin", "DOGE",
    "Cardano", "ADA",
    "TRON", "TRX"
]

def init_driver(headless=True):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")
    return webdriver.Chrome(options=chrome_options)

def scrape_beincrypto(driver, max_articles=-1):
    base_url = "https://beincrypto.com/news/"
    driver.get(base_url)
    scraped = 0
    seen_links = set()
    while True:
        # 1) récupérer tous les liens d'articles
        items = driver.find_elements(
            By.CSS_SELECTOR,
            'div[data-el="bic-c-news-big"] a.hover\\:no-underline'
        )
        for item in items:
            link_text = item.text or ""
            # 2) filtrer sur nos mots-clés
            if not any(kw.lower() in link_text.lower() for kw in CRYPTO_KEYWORDS):
                continue

            link = item.get_attribute("href")
            if not link or link in seen_links:
                continue
            seen_links.add(link)

            # 3) ouvrir dans un nouvel onglet et passer dessus
            driver.execute_script("window.open(arguments[0]);", link)
            driver.switch_to.window(driver.window_handles[-1])

            try:
                # 4) attendre que la page soit complètement chargée
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )

                # 5) extraire la date (<time>)
                try:
                    time_el = driver.find_element(By.TAG_NAME, "time")
                    date = time_el.get_attribute("datetime") or time_el.text
                except:
                    date = "Date non trouvée"

                # 6) scraper tous les <p>
                paragraphs = driver.find_elements(By.CSS_SELECTOR, "div.entry-content p")
                text_body = "\n".join(p.text for p in paragraphs)

                # 7) affichage
                print(f"\n=== Article #{scraped+1} ===")
                print(f"URL   : {link}")
                print(f"Date  : {date}")
                print(f"Extrait:\n{text_body}…\n")

            except Exception as e:
                print(f" Erreur sur {link} : {e}")

            finally:
                # fermer l'onglet et revenir au principal
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

            scraped += 1
            if 0 <= max_articles <= scraped:
                break
        else:
            # 8) pagination : cliquer sur « next » tant que le bouton existe
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, "a.pagination-arrow")
                driver.execute_script("arguments[0].click();", next_btn)

                # attendre la navigation
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(1)
                continue
            except:
                # plus de bouton → fin
                break

        # sortie si on a atteint max_articles
        break

    print(f"\n Scraping terminé : {scraped} articles récupérés.")

if __name__ == "__main__":
    driver = init_driver(headless=True)
    try:
        scrape_beincrypto(driver, max_articles=-1)
    finally:
        driver.quit()
