# u_today_scraper.py
import time
import sys
import os
# Ajouter le chemin parent pour importer le module processor
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from processor.date_parser import parse_date_with_context

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

class UTodayScraper:
    def __init__(self, headless=True, max_articles=-1):
        self.headless = headless
        self.max_articles = max_articles
        self.seen_links = set()
        self.scraped_count = 0
        self.driver = self._init_driver()

    def _init_driver(self):
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--log-level=3")
        return webdriver.Chrome(options=chrome_options)

    def _clear_cookie_banner(self):
        try:
            btn = self.driver.find_element(By.CSS_SELECTOR, "#cookie-consent button, .cookie-consent button")
            btn.click()
        except Exception:
            self.driver.execute_script(
                "document.querySelectorAll('#cookie-consent, .cookie-consent').forEach(e => e.remove());"
            )

    def _safe_find_elements(self, selector, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
        )

    def _small_scroll(self, element=None, pixels=300):
        if element:
            self.driver.execute_script(
                "arguments[0].scrollIntoView(); window.scrollBy(0, arguments[1]);",
                element, pixels
            )
        else:
            self.driver.execute_script("window.scrollBy(0, arguments[0]);", pixels)

    def _wait_for_new_articles(self, old_count, timeout=10):
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "a.news__item-body")) > old_count
            )
            return True
        except TimeoutException:
            return False

    def _retry_on_stale(self, fn, retries=3, delay=1):
        for _ in range(retries):
            try:
                return fn()
            except StaleElementReferenceException:
                time.sleep(delay)
        return fn()

    def stream_articles(self):
        """
        Générateur qui yield dicts: {'url': ..., 'date': ..., 'content': ...}
        """
        base_url = "https://u.today/latest-cryptocurrency-news"
        self.driver.get(base_url)
        self._clear_cookie_banner()

        selector = "a.news__item-body"
        while True:
            if 0 <= self.max_articles <= self.scraped_count:
                break

            try:
                items = self._safe_find_elements(selector)
            except TimeoutException:
                break

            total = len(items)
            for idx in range(total):
                if 0 <= self.max_articles <= self.scraped_count:
                    break

                try:
                    item = self.driver.find_elements(By.CSS_SELECTOR, selector)[idx]
                except (IndexError, StaleElementReferenceException):
                    continue

                text = item.text or ""
                if not any(kw.lower() in text.lower() for kw in CRYPTO_KEYWORDS):
                    continue

                try:
                    url = item.get_attribute('href')
                except StaleElementReferenceException:
                    continue
                if not url or url in self.seen_links:
                    continue
                self.seen_links.add(url)

                # Ouvrir l'article et extraire date & contenu
                self.driver.execute_script("window.open(arguments[0]);", url)
                self.driver.switch_to.window(self.driver.window_handles[-1])
                try:
                    WebDriverWait(self.driver, 10).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                    # Date
                    def grab_date():
                        return self.driver.find_element(By.CSS_SELECTOR, ".article__short-date").text
                    try:
                        date = self._retry_on_stale(grab_date)
                    except TimeoutException:
                        date = None
                    # Contenu
                    def grab_content():
                        paras = self.driver.find_elements(By.CSS_SELECTOR, "div.article__content p")
                        return "\n".join(p.text for p in paras)
                    content = self._retry_on_stale(grab_content)

                    # Parser la date avec le contexte U.Today
                    if date:
                        parsed_date = parse_date_with_context(date, url)
                    else:
                        parsed_date = date
                    
                    yield {'url': url, 'date': parsed_date, 'content': content}
                    self.scraped_count += 1
                except Exception:
                    pass
                finally:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])

            # Pagination via scroll
            old_count = total
            self._clear_cookie_banner()
            loaded = False
            for attempt in range(1, MAX_SCROLL_ATTEMPTS + 1):
                if items:
                    self._small_scroll(element=items[-1], pixels=300 * attempt)
                else:
                    self._small_scroll(pixels=300 * attempt)
                # time.sleep(1)
                if self._wait_for_new_articles(old_count):
                    loaded = True
                    break
            if not loaded:
                break

    def close(self):
        self.driver.quit()


if __name__ == '__main__':
    scraper = UTodayScraper(headless=True, max_articles=-1)
    try:
        for article in scraper.stream_articles():
            print(f"URL: {article['url']}")
            print(f"Date: {article['date']}")
            print(f"Extrait: {article['content'][:200]}…")
            print("---")
    finally:
        scraper.close()
