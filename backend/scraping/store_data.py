# store_data.py
import sys
import os
import re

# Ajoute le dossier parent de "processor" au path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(script_dir, '..')
sys.path.append(os.path.abspath(parent_dir))

from . import crypto_news_scraper
from . import u_today_scraper

from processor import h5_utilities, emoji_handler
from processor.sentiment import compute_sentiment

CRYPTO_DEFINITIONS = [
    {"name": "Bitcoin", "aliases": ["bitcoin", "btc"]},
    {"name": "Ethereum", "aliases": ["ethereum", "eth"]},
    {"name": "Tether", "aliases": ["tether", "usdt"]},
    {"name": "XRP", "aliases": ["xrp", "ripple"]},
    {"name": "Binance Coin", "aliases": ["binance coin", "bnb"]},
    {"name": "Solana", "aliases": ["solana", "sol"]},
    {"name": "USD Coin", "aliases": ["usd coin", "usdc"]},
    {"name": "Dogecoin", "aliases": ["dogecoin", "doge"]},
    {"name": "Cardano", "aliases": ["cardano", "ada"]},
    {"name": "TRON", "aliases": ["tron", "trx"]}
]

def detect_cryptos(text: str, definitions=CRYPTO_DEFINITIONS) -> list[str]:
        """
        Parcourt `definitions` pour trouver les alias présents dans `text`.
        Retourne une liste unique des `name` des cryptos détectées.
        """
        detected = set()
        text_lower = text.lower()
        for crypto in definitions:
            for alias in crypto["aliases"]:
                # mot entier uniquement (\b…\b)
                if re.search(rf"\b{re.escape(alias)}\b", text_lower):
                    detected.add(crypto["name"])
                    break
        return list(detected)

def storeData(website="cryptoNews", nbArticle = -1, h5FileName="dataset"):
    """
    website_value : str
        'cryptoNews'
        'uToday'
        'beInCrypto'
    """
    havePlaceholder = True #Check que dataset n'as plus le placeholder de création
    firstScrap = True
    linkFirstScrap = ""

    match website:
        case "cryptoNews":
            print("Scrapping cryptoNews !")
            h5Attribute = 'last_news_cryptoNews'
            scraper = crypto_news_scraper.CryptoNewsMarketsScraper(headless=True, max_articles=nbArticle)
        case "uToday":
            print("Scrapping uToday !")
            h5Attribute = 'last_news_uToday'
            scraper = u_today_scraper.UTodayScraper(headless=True, max_articles=nbArticle)
        case "beInCrypto":
            print("Scrapping beInCrypto !")
            h5Attribute = 'last_news_beInCrypto'
            scraper = None  # Not implemented yet

    try:
        for article in scraper.stream_articles():
            link = article['url']
            date = article['date']
            print("URL: ",link)
            print("Date: ", date)

            content = article['content'].replace("\n"," ")
            content = emoji_handler.remove_emojis(content)
            print(content)
            print('---')

            if link == h5_utilities.getUrlAttribute(h5Attribute,h5FileName):
                linkFirstScrap = link
                print("Data already scrapped !")
                break
            else:
                if firstScrap:
                    linkFirstScrap = link
                    print(h5_utilities.getUrlAttribute(h5Attribute,h5FileName))
                    firstScrap = False
                list_crypto = detect_cryptos(content)

                print("Cryptos détectées :", list_crypto or "Aucune")

                sentiment_score = compute_sentiment(content)

                h5_utilities.appendArticleToDataset(content,link,date,list_crypto,sentiment_score,h5FileName)
                
                if havePlaceholder:
                     if h5_utilities.getDatasetPlaceholderAttribute(h5FileName):
                         print("Remove placeholder content")
                         h5_utilities.remove_first_item(h5FileName)
                         h5_utilities.setDatasetPlaceholderAttribute(False, h5FileName)
                     havePlaceholder = False

    finally:
        h5_utilities.setUrlAttribute(h5Attribute,linkFirstScrap,h5FileName)
        scraper.close()



if __name__ == "__main__":
    nbArticle = 10
    storeData("cryptoNews",nbArticle,"dataset")
    storeData("uToday",nbArticle,"dataset")