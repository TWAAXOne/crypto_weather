import time

from selenium import webdriver
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
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

# Nombre maximal de tentatives de scroll pour charger plus d'articles
MAX_SCROLL_ATTEMPTS = 5

def init_driver(headless=True):
    """
    Initialise le driver Chrome avec des options pour headless, désactivation GPU, etc.
    """
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")
    return webdriver.Chrome(options=chrome_options)


def _clear_cookie_banner(driver):
    """Ferme ou supprime le bandeau de cookies s'il est présent."""
    try:
        btn = driver.find_element(By.CSS_SELECTOR, "#cookie-consent button, .cookie-consent button")
        btn.click()
    except Exception:
        driver.execute_script("""
            document.querySelectorAll('#cookie-consent, .cookie-consent')
                    .forEach(el => el.remove());
        """)


def safe_find_elements(driver, selector, timeout=10):
    """Attend puis renvoie tous les éléments correspondant au sélecteur CSS."""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
    )


def small_scroll(driver, element=None, pixels=300):
    """
    Si `element` est fourni, scroll jusqu'à lui puis descend de `pixels`, sinon scroll de `pixels`.
    """
    if element:
        driver.execute_script(
            "arguments[0].scrollIntoView(); window.scrollBy(0, arguments[1]);",
            element, pixels
        )
    else:
        driver.execute_script("window.scrollBy(0, arguments[0]);", pixels)


def wait_for_new_articles(driver, old_count, timeout=10):
    """Attend que le nombre d'articles augmente au-delà de old_count."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "a.news__item-body")) > old_count
        )
        return True
    except TimeoutException:
        return False


def retry_on_stale(fn, retries=3, delay=1):
    """
    Appelle fn() jusqu'à `retries` fois si StaleElementReferenceException survient.
    """
    for _ in range(retries):
        try:
            return fn()
        except StaleElementReferenceException:
            time.sleep(delay)
    # Dernier essai sans capturer l'exception
    return fn()


def scrape_u_today(driver, max_articles=-1):
    """
    Scrape les articles sur u.today en filtrant par CRYPTO_KEYWORDS.
    max_articles = -1 pour sans limite.
    """
    base_url = "https://u.today/latest-cryptocurrency-news"
    driver.get(base_url)
    _clear_cookie_banner(driver)
    print("Scraping U.Today…")

    scraped = 0
    seen_links = set()
    selector = "a.news__item-body"

    while True:
        if 0 <= max_articles <= scraped:
            break

        # Récupérer toutes les vignettes d'articles
        try:
            items = safe_find_elements(driver, selector)
        except TimeoutException:
            print("Aucun article détecté, arrêt.")
            break

        total = len(items)
        print(f"Articles déjà scrapés : {scraped}, visibles : {total}")

        # Parcourir par index pour éviter stale sur la liste précédente
        for idx in range(total):
            if 0 <= max_articles <= scraped:
                break

            try:
                item = driver.find_elements(By.CSS_SELECTOR, selector)[idx]
            except (IndexError, StaleElementReferenceException):
                continue

            text = item.text or ""
            if not any(kw.lower() in text.lower() for kw in CRYPTO_KEYWORDS):
                continue

            try:
                link = item.get_attribute("href")
            except StaleElementReferenceException:
                continue
            if not link or link in seen_links:
                continue
            seen_links.add(link)

            print(f"Ouverture de {link}…")
            driver.execute_script("window.open(arguments[0]);", link)
            driver.switch_to.window(driver.window_handles[-1])

            try:
                # Attendre le chargement complet
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )

                # Récupérer la date avec retry sur stale
                def grab_date():
                    return driver.find_element(By.CSS_SELECTOR, ".article__short-date").text
                try:
                    date = retry_on_stale(grab_date)
                except TimeoutException:
                    date = "Date non trouvée"

                # Récupérer le contenu avec retry
                def grab_paragraphs():
                    elems = driver.find_elements(By.CSS_SELECTOR, "div.article__content p")
                    return "\n".join(e.text for e in elems)
                body = retry_on_stale(grab_paragraphs)

                print(f"\n=== Article #{scraped+1} ===")
                print(f"URL   : {link}")
                print(f"Date  : {date}")
                print(f"Extrait:\n{body[:300]}…\n")

            except Exception as e:
                print(f"⚠️ Erreur sur {link} : {e}")
            finally:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

            scraped += 1

        else:
            # Si on n'a pas atteint le max, scroll pour charger plus d'articles
            old_count = total
            _clear_cookie_banner(driver)
            loaded = False
            for attempt in range(1, MAX_SCROLL_ATTEMPTS + 1):
                if total:
                    small_scroll(driver, element=items[-1], pixels=300 * attempt)
                else:
                    small_scroll(driver, pixels=300 * attempt)
                time.sleep(1)
                if wait_for_new_articles(driver, old_count):
                    loaded = True
                    break
            if not loaded:
                print("Plus aucun nouvel article détecté.")
                break
            continue

        break

    print(f"\n🟢 Scraping terminé : {scraped} articles récupérés.")

if __name__ == "__main__":
    driver = init_driver(headless=True)
    try:
        scrape_u_today(driver, max_articles=-1)
    finally:
        driver.quit()
