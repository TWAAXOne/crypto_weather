import time

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

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
    except:
        return False

def scrape_markets(driver, max_articles=-1):
    base_url = "https://crypto.news/markets/"
    driver.get(base_url)

    scraped = 0
    seen_links = set()

    while True:
        # 1) on compte dynamiquement les miniatures
        selector = "a.post-loop__media-link"
        total = len(driver.find_elements(By.CSS_SELECTOR, selector))

        # stop si on a atteint le max
        if 0 <= max_articles <= scraped:
            break

        # 2) on itère par indice en refetchant à chaque fois
        for idx in range(total):
            try:
                thumb = driver.find_elements(By.CSS_SELECTOR, selector)[idx]
            except StaleElementReferenceException:
                # si l'élément a disparu/rechargé, on passe au suivant
                continue

            link_text = thumb.text or ""
            # filtre top10
            if not any(kw.lower() in link_text.lower() for kw in CRYPTO_KEYWORDS):
                continue

            link = thumb.get_attribute("href")
            if not link or link in seen_links:
                continue
            seen_links.add(link)

            # ouvrir et scraper
            driver.execute_script("window.open(arguments[0]);", link)
            driver.switch_to.window(driver.window_handles[1])

            try:
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                # date
                try:
                    date = driver.find_element(By.CSS_SELECTOR, ".post-detail__date").text
                except:
                    date = "Date non trouvée"
                # contenu
                paragraphs = driver.find_elements(By.CSS_SELECTOR, "div.post-detail__container p")
                text_body = "\n".join(p.text for p in paragraphs)

                print(f"\n=== Article #{scraped+1} ===")
                print(f"URL   : {link}")
                print(f"Date  : {date}")
                print(f"Extrait:\n{text_body[:300]}…")

            except Exception as e:
                print(f" Échec chargement : {link} ({e})")
            finally:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

            scraped += 1
            if 0 <= max_articles <= scraped:
                break
        else:
            # si on n'a pas breaké pour max_articles, on scroll pour charger la suite
            old_count = total
            if total:
                # recalcule thumb pour la dernière miniature visible
                last_thumb = driver.find_elements(By.CSS_SELECTOR, selector)[-1]
                small_scroll(driver, element=last_thumb, pixels=300)
            else:
                small_scroll(driver, pixels=300)
            time.sleep(1)
            if not wait_for_new_articles(driver, old_count):
                break
            continue

        break

    print(f"\n Scraping terminé : {scraped} articles récupérés.")

if __name__ == "__main__":
    driver = init_driver(headless=True)
    try:
        scrape_markets(driver, max_articles=-1)
    finally:
        driver.quit()
