import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

# Top 10 cryptos de CoinMarketCap (stocké en dur)
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

MAX_SCROLL_ATTEMPTS = 5

def init_driver(headless=True):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")
    return webdriver.Chrome(options=chrome_options)

def small_scroll(driver, element=None, pixels=300):
    """
    Si `element` est fourni, scroll jusqu'à lui puis on descend encore de `pixels`.
    Sinon, on scroll simplement de `pixels`.
    """
    if element:
        driver.execute_script(
            "arguments[0].scrollIntoView(); window.scrollBy(0, arguments[1]);",
            element, pixels
        )
    else:
        driver.execute_script("window.scrollBy(0, arguments[0]);", pixels)

def wait_for_new_articles(driver, old_count, timeout=10):
    """
    Attend que le nombre de liens augmente.
    """
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "a.news__item-body")) > old_count
        )
        return True
    except:
        return False

def scrape_u_today(driver, max_articles=-1):
    base_url = "https://u.today/latest-cryptocurrency-news"
    driver.get(base_url)
    print("Scraping U.Today...")
    scraped = 0
    seen_links = set()

    while True:
        # 1) récupérer tous les liens d'articles
        items = driver.find_elements(By.CSS_SELECTOR, "a.news__item-body")
        if 0 <= max_articles <= scraped:
            break

        print(f"Articles déjà scrapés : {scraped}")
        for item in items:
            link_text = item.text or ""
            # Filtrer selon le top 10, insensible à la casse
            if not any(keyword.lower() in link_text.lower() for keyword in CRYPTO_KEYWORDS):
                continue

            link = item.get_attribute("href")
            if not link or link in seen_links:
                continue
            seen_links.add(link)

            print(f"Ouverture de {link}…")
            # 2) ouvrir l'article dans un nouvel onglet
            driver.execute_script("window.open(arguments[0]);", link)
            driver.switch_to.window(driver.window_handles[1])

            try:
                # attendre que le chargement statique soit complet
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )

                # 3) récupérer la date via .article__short-date
                try:
                    date = driver.find_element(By.CSS_SELECTOR, ".article__short-date").text
                except:
                    date = "Date non trouvée"

                # 4) scraper tous les <p>
                paragraphs = driver.find_elements(By.CSS_SELECTOR, "div.article__content p")
                text = "\n".join(p.text for p in paragraphs)

                print(f"\n=== Article #{scraped + 1} ===")
                print(f"URL   : {link}")
                print(f"Date  : {date}")
                print(f"Extrait:\n{text}…\n")

            except Exception as e:
                print(f" Erreur sur {link} : {e}")
            finally:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

            scraped += 1
            if 0 <= max_articles <= scraped:
                break
        else:
            # 5) si on arrive au bout sans avoir atteint max, on scroll plusieurs fois
            old_count = len(items)
            loaded = False
            for attempt in range(1, MAX_SCROLL_ATTEMPTS + 1):
                if items:
                    small_scroll(driver, element=items[-1], pixels=300 * attempt)
                else:
                    small_scroll(driver, pixels=300 * attempt)
                time.sleep(1)
                if wait_for_new_articles(driver, old_count):
                    loaded = True
                    break
            if not loaded:
                break
            continue

        break

    print(f"\n Scraping terminé : {scraped} articles récupérés.")

if __name__ == "__main__":
    driver = init_driver(headless=True)
    try:
        # max_articles=-1 pour scraper sans limite
        scrape_u_today(driver, max_articles=-1)
    finally:
        driver.quit()
