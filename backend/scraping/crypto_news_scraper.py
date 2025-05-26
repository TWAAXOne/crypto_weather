import time
from selenium import webdriver
from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

def _clear_cookie_banner(driver):
    """Ferme ou supprime le bandeau de cookies qui peut bloquer les clics."""
    try:
        btn = driver.find_element(By.CSS_SELECTOR, "#cookie-consent button, .cookie-consent button")
        btn.click()
    except Exception:
        driver.execute_script("""
            document.querySelectorAll('#cookie-consent, .cookie-consent')
                    .forEach(el => el.remove());
        """)

def small_scroll(driver, element=None, pixels=300):
    if element:
        driver.execute_script(
            "arguments[0].scrollIntoView(); window.scrollBy(0, arguments[1]);",
            element, pixels
        )
    else:
        driver.execute_script("window.scrollBy(0, arguments[0]);", pixels)

def wait_for_new_articles(driver, old_count, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "a.post-loop__media-link")) > old_count
        )
        return True
    except TimeoutException:
        return False

def safe_find_elements(driver, selector, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
    )

def retry_find_text(driver, css_selector, retries=3, delay=0.5, timeout=5):
    """Récupère .text d’un élément en gérant les stale, ou renvoie None."""
    for _ in range(retries):
        try:
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
            ).text
        except (StaleElementReferenceException, TimeoutException):
            time.sleep(delay)
    return None

def retry_find_all_texts(driver, css_selector, retries=3, delay=0.5):
    """Récupère la liste de .text de plusieurs éléments, ou [] en échec."""
    for _ in range(retries):
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, css_selector)
            return [e.text for e in elems]
        except StaleElementReferenceException:
            time.sleep(delay)
    return []

def scrape_markets(driver, max_articles=-1):
    base_url = "https://crypto.news/markets/"
    driver.get(base_url)
    _clear_cookie_banner(driver)

    scraped = 0
    seen_links = set()
    selector = "a.post-loop__media-link"

    while True:
        if 0 <= max_articles <= scraped:
            break
        try:
            thumbs = safe_find_elements(driver, selector)
        except TimeoutException:
            print("Aucun article détecté, arrêt.")
            break

        total = len(thumbs)

        for idx in range(total):
            if 0 <= max_articles <= scraped:
                break

            # re-fetch pour éviter stale
            try:
                thumb = driver.find_elements(By.CSS_SELECTOR, selector)[idx]
            except (IndexError, StaleElementReferenceException):
                continue

            title = thumb.text or ""
            if not any(kw.lower() in title.lower() for kw in CRYPTO_KEYWORDS):
                continue

            try:
                link = thumb.get_attribute("href")
            except StaleElementReferenceException:
                continue

            if not link or link in seen_links:
                continue
            seen_links.add(link)

            # ouvre l'article dans un nouvel onglet
            driver.execute_script("window.open(arguments[0]);", link)
            driver.switch_to.window(driver.window_handles[-1])
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # retry global sur scrap article
            success = False
            for attempt in range(3):
                try:
                    date = retry_find_text(driver, ".post-detail__date") or "Date non trouvée"
                    paras = retry_find_all_texts(driver, "div.post-detail__container p")
                    text_body = "\n".join(paras)

                    print(f"\n=== Article #{scraped+1} ===")
                    print(f"URL   : {link}")
                    print(f"Date  : {date}")
                    print(f"Extrait:\n{text_body[:300]}…")
                    success = True
                    break

                except Exception as e:
                    # si stale ou autre, on réessaie après un bref délai
                    time.sleep(1)

            if not success:
                print(f"⚠️ Échec chargement après retries : {link}")

            # ferme l'onglet et revient
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            scraped += 1

        else:
            # pagination
            old_count = total
            _clear_cookie_banner(driver)

            try:
                btn = driver.find_element(By.CSS_SELECTOR, "button.alm-load-more-btn.more")
            except NoSuchElementException:
                last = driver.find_elements(By.CSS_SELECTOR, selector)
                small_scroll(driver, element=last[-1] if last else None, pixels=300)
                time.sleep(1)
                if not wait_for_new_articles(driver, old_count):
                    break
            else:
                try:
                    btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.alm-load-more-btn.more"))
                    )
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    btn.click()
                    WebDriverWait(driver, 10).until(
                        lambda d: d.find_element(By.CSS_SELECTOR, "button.alm-load-more-btn.more")
                                  .text.strip().lower() == "loading..."
                    )
                    if not wait_for_new_articles(driver, old_count):
                        break
                except (TimeoutException, ElementClickInterceptedException) as e:
                    print(f"⚠️ Échec clic Show More ({e}), fallback scroll")
                    last = driver.find_elements(By.CSS_SELECTOR, selector)
                    small_scroll(driver, element=last[-1] if last else None, pixels=300)
                    time.sleep(1)
                    if not wait_for_new_articles(driver, old_count):
                        break

            continue

        break

    print(f"\n🟢 Scraping terminé : {scraped} articles récupérés.")

if __name__ == "__main__":
    driver = init_driver(headless=True)
    try:
        scrape_markets(driver, max_articles=-1)
    finally:
        driver.quit()
