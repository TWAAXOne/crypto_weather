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

MAX_SCROLL_ATTEMPTS = 5

class CryptoNewsMarketsScraper:
    def __init__(self, headless=True, max_articles=-1):
        self.headless = headless
        self.max_articles = max_articles
        self.scraped = 0
        self.seen_links = set()
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
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "a.post-loop__media-link")) > old_count
            )
            return True
        except TimeoutException:
            return False

    def _retry_find_text(self, selector, retries=3, delay=0.5, timeout=5):
        for _ in range(retries):
            try:
                return WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                ).text
            except (StaleElementReferenceException, TimeoutException):
                time.sleep(delay)
        return None

    def _retry_find_all_texts(self, selector, retries=3, delay=0.5):
        for _ in range(retries):
            try:
                elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                return [e.text for e in elems]
            except StaleElementReferenceException:
                time.sleep(delay)
        return []

    def stream_articles(self):
        base_url = "https://crypto.news/markets/"
        self.driver.get(base_url)
        self._clear_cookie_banner()

        selector = "a.post-loop__media-link"
        while True:
            if 0 <= self.max_articles <= self.scraped:
                break

            try:
                thumbs = self._safe_find_elements(selector)
            except TimeoutException:
                break

            total = len(thumbs)
            for idx in range(total):
                if 0 <= self.max_articles <= self.scraped:
                    break

                try:
                    thumb = self.driver.find_elements(By.CSS_SELECTOR, selector)[idx]
                except (IndexError, StaleElementReferenceException):
                    continue

                title = thumb.text or ""
                if not any(kw.lower() in title.lower() for kw in CRYPTO_KEYWORDS):
                    continue

                try:
                    url = thumb.get_attribute('href')
                except StaleElementReferenceException:
                    continue
                if not url or url in self.seen_links:
                    continue
                self.seen_links.add(url)

                self.driver.execute_script("window.open(arguments[0]);", url)
                self.driver.switch_to.window(self.driver.window_handles[-1])

                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )

                # retry global
                success = False
                for _ in range(3):
                    try:
                        date = self._retry_find_text('.post-detail__date') or 'Date non trouvée'
                        paras = self._retry_find_all_texts('div.post-detail__container p')
                        content = '\n'.join(paras)
                        yield {'url': url, 'date': date, 'content': content}
                        self.scraped += 1
                        success = True
                        break
                    except Exception:
                        time.sleep(1)

                if not success:
                    # skip if permanently failing
                    pass

                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])

            # pagination
            old_count = total
            self._clear_cookie_banner()

            try:
                btn = self.driver.find_element(By.CSS_SELECTOR, "button.alm-load-more-btn.more")
                WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.alm-load-more-btn.more"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                btn.click()
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.find_element(By.CSS_SELECTOR, "button.alm-load-more-btn.more").text.strip().lower() == 'loading...'
                )
                if not self._wait_for_new_articles(old_count):
                    break
            except (NoSuchElementException, TimeoutException, ElementClickInterceptedException):
                # fallback scroll
                if thumbs:
                    self._small_scroll(element=thumbs[-1], pixels=300)
                else:
                    self._small_scroll(pixels=300)
                # time.sleep(1)
                if not self._wait_for_new_articles(old_count):
                    break

    def close(self):
        self.driver.quit()

if __name__ == '__main__':
    scraper = CryptoNewsMarketsScraper(headless=True, max_articles=-1)
    try:
        for article in scraper.stream_articles():
            print(f"URL: {article['url']}")
            print(f"Date: {article['date']}")
            print(f"Extrait: {article['content'][:200]}…")
            print('---')
    finally:
        scraper.close()
