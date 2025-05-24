import time
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

import sys
import os

# Ajoute le dossier parent de "processor" au path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(script_dir, '..')
sys.path.append(os.path.abspath(parent_dir))

from processor import h5_utilities, emoji_handler


CRYPTO_KEYWORDS = [
    "Bitcoin","BTC","Ethereum","ETH","Tether","USDT","XRP",
    "Binance Coin","BNB","Solana","SOL","USD Coin","USDC",
    "Dogecoin","DOGE","Cardano","ADA","TRON","TRX"
]

class CryptoScraper:
    def __init__(self, driver, config, h5FileName = "dataset"):
        """
        config = {
          "base_url": str,
          "item_selector": str,
          "date_selector": str,
          "content_selector": str,
          "pagination": "scroll" or "next",
          # si scroll:
          "wait_new_selector": str,
          # si next:
          "next_button_selector": str
        }

        h5FileName : dataset file name without extension, default value = "dataset"
        """
        self.driver = driver
        self.cfg = config
        self.seen = set()
        self.scraped = 0
        self.h5FileName = h5FileName
        self.havePlaceholder = True #Check que dataset n'as plus le placeholder de création

    def _matches_keyword(self, text):
        t = text.lower()
        return any(kw.lower() in t for kw in CRYPTO_KEYWORDS)

    def _open_and_scrape(self, link):
        self.driver.execute_script("window.open(arguments[0]);", link)
        self.driver.switch_to.window(self.driver.window_handles[-1])
        try:
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            # date
            try:
                date = self.driver.find_element(By.CSS_SELECTOR,
                                                 self.cfg["date_selector"]).get_attribute("datetime") \
                       or self.driver.find_element(By.CSS_SELECTOR, self.cfg["date_selector"]).text
            except:
                date = "Date non trouvée"
            # contenu
            paras = self.driver.find_elements(By.CSS_SELECTOR,
                                              self.cfg["content_selector"])
            body = "\n".join(p.text for p in paras)

            content = body.replace("\n"," ")
            content = emoji_handler.remove_emojis(content)

            print(f"\n=== Article #{self.scraped+1} ===")
            print("URL   :", link)
            print("Date  :", date)
            print("Extrait:", content, "…")

            #Put regex crypto here
            list_crypto = ["btc","ether"]

            h5_utilities.appendArticleToDataset(content,link,date,list_crypto,0.0,self.h5FileName)
            if self.havePlaceholder:
                if h5_utilities.getDatasetPlaceholderAttribute(self.h5FileName):
                    print("Remove placeholder content")
                    h5_utilities.remove_first_item(self.h5FileName)
                    h5_utilities.setDatasetPlaceholderAttribute(False, self.h5FileName)
                else:
                    print("No Placeholder content to remove")
                    pass

                self.havePlaceholder = False

        except Exception as e:
            print(" Erreur sur", link, ":", e)
        finally:
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
        self.scraped += 1

    def _paginate_scroll(self):
        old = len(self.driver.find_elements(By.CSS_SELECTOR,
                                            self.cfg["item_selector"]))
        last = self.driver.find_elements(By.CSS_SELECTOR,
                                         self.cfg["item_selector"])[-1]
        self.driver.execute_script(
            "arguments[0].scrollIntoView(); window.scrollBy(0, 200);", last
        )
        time.sleep(1)
        WebDriverWait(self.driver, 5).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR,
                                          self.cfg["wait_new_selector"])) > old
        )

    def _paginate_next(self):
        btn = self.driver.find_element(By.CSS_SELECTOR,
                                       self.cfg["next_button_selector"])
        self.driver.execute_script("arguments[0].click()", btn)
        WebDriverWait(self.driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(1)

    def run(self, max_articles=-1):
        self.driver.get(self.cfg["base_url"])
        while True:
            items = self.driver.find_elements(By.CSS_SELECTOR,
                                              self.cfg["item_selector"])
            for idx in range(len(items)):
                try:
                    item = self.driver.find_elements(By.CSS_SELECTOR,
                                                     self.cfg["item_selector"])[idx]
                except StaleElementReferenceException:
                    continue
                text = item.text or ""
                if not self._matches_keyword(text):
                    continue
                link = item.get_attribute("href")
                if not link or link in self.seen:
                    continue
                self.seen.add(link)
                self._open_and_scrape(link)
                if 0 <= max_articles <= self.scraped:
                    return
            # pagination
            if self.cfg["pagination"] == "scroll":
                self._paginate_scroll()
            else:
                try:
                    self._paginate_next()
                except:
                    return

if __name__ == "__main__":
    opts = Options()
    opts.add_argument("--headless")
    driver = webdriver.Chrome(options=opts)
    try:
        sites = [
            {
              "base_url": "https://crypto.news/markets/",
              "item_selector": "a.post-loop__media-link",
              "wait_new_selector": "a.post-loop__media-link",
              "date_selector": ".post-detail__date",
              "content_selector": "div.post-detail__container p",
              "pagination": "scroll"
            },
            {
              "base_url": "https://u.today/latest-cryptocurrency-news",
              "item_selector": "a.news__item-body",
              "wait_new_selector": "a.news__item-body",
              "date_selector": ".article__short-date",
              "content_selector": "div.article__content p",
              "pagination": "scroll"
            },
            {
              "base_url": "https://beincrypto.com/news/",
              "item_selector": 'div[data-el="bic-c-news-big"] a.hover\\:no-underline',
              "next_button_selector": 'a.pagination-arrow',
              "date_selector": "time.date",
              "content_selector": "div.entry-content p",
              "pagination": "next"
            }
        ]
        for cfg in sites:
            print("\n\n▶▶▶ Scraping", cfg["base_url"])
            scraper = CryptoScraper(driver, cfg)
            scraper.run(max_articles=10)
    finally:
        driver.quit()
