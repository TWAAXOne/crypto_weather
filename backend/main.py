import logging
import os
import sys
from datetime import datetime, timedelta

import pandas as pd
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# === Ensure backend/ is on PYTHONPATH so `import scraping…` works ===
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))       # .../project/backend
sys.path.insert(0, BASE_DIR)

# now this will resolve to backend/scraping/generic_scraper.py
from scraping.generic_scraper import main as run_generic_scraper
from processor.h5_utilities import getDataset, getDatasetLength

# ==== Logging Configuration ====
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("fastapi_service.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ==== Paths ====
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))    # project root; dataset.h5 lives here

# ==== Crypto Definitions ====
CRYPTO_DEFINITIONS = [
    {"name": "Bitcoin",       "aliases": ["bitcoin", "btc"]},
    {"name": "Ethereum",      "aliases": ["ethereum", "eth"]},
    {"name": "Tether",        "aliases": ["tether", "usdt"]},
    {"name": "XRP",           "aliases": ["xrp", "ripple"]},
    {"name": "Binance Coin",  "aliases": ["binance coin", "bnb"]},
    {"name": "Solana",        "aliases": ["solana", "sol"]},
    {"name": "USD Coin",      "aliases": ["usd coin", "usdc"]},
    {"name": "Dogecoin",      "aliases": ["dogecoin", "doge"]},
    {"name": "Cardano",       "aliases": ["cardano", "ada"]},
    {"name": "TRON",          "aliases": ["tron", "trx"]}
]

def get_sentiment_status(avg_score: float) -> str:
    if avg_score <= -0.6: return "Extreme fear"
    if avg_score <= -0.2: return "Fear"
    if avg_score <=  0.2: return "Neutral"
    if avg_score <=  0.6: return "Greed"
    return "Extreme greed"

def read_h5_and_compute() -> dict:
    # 1) Load HDF5 from project root
    h5_path = os.path.join(PROJECT_ROOT, "dataset.h5")
    if not os.path.exists(h5_path):
        raise FileNotFoundError(f"{h5_path} not found")

    base_name = os.path.splitext(h5_path)[0]  # e.g. "/.../dataset"

    content, links, dates, cryptos, sentiments = getDataset(
        datasetFileName=base_name,
        isTrainDataset=True
    )

    # 2) Build DataFrame
    dt = pd.to_datetime(dates, errors="coerce", utc=True).tz_convert(None)
    df = pd.DataFrame({
        "date":      dt,
        "crypto":    cryptos,
        "sentiment": sentiments.astype(float),
        "content":   content,
        "link":      links
    }).dropna(subset=["date"])

    now = datetime.utcnow()
    windows = {
        "1h":  now - timedelta(hours=1),
        "24h": now - timedelta(days=1),
        "7d":  now - timedelta(days=7),
        "30d": now - timedelta(days=30),
    }

    result = {}

    # 3) Global counts, averages & statuses
    for label, cutoff in windows.items():
        sub   = df[df["date"] >= cutoff]
        count = len(sub)
        avg   = float(sub["sentiment"].mean()) if count else 0.0
        result[f"count_{label}"]  = count
        result[f"avg_{label}"]    = round(avg, 4)
        result[f"status_{label}"] = get_sentiment_status(avg)

    # 4) Daily timeseries
    df_daily = (
        df.set_index("date")["sentiment"]
          .resample("D").mean().fillna(0.0)
          .reset_index()
    )
    result["timeseries"] = {
        "dates":      df_daily["date"].dt.strftime("%Y-%m-%d").tolist(),
        "sentiments": [float(x) for x in df_daily["sentiment"].tolist()]
    }

    # 5) Per‐crypto metrics
    per_crypto = {}
    for cd in CRYPTO_DEFINITIONS:
        name = cd["name"]
        mask = df["crypto"].apply(lambda lst: name in lst)
        stats = {}
        for label, cutoff in windows.items():
            sub   = df[mask & (df["date"] >= cutoff)]
            count = len(sub)
            avg   = float(sub["sentiment"].mean()) if count else 0.0
            stats[f"count_{label}"]  = count
            stats[f"avg_{label}"]    = round(avg, 4)
            stats[f"status_{label}"] = get_sentiment_status(avg)
        per_crypto[name] = stats
    result["per_crypto"] = per_crypto

    # 6) 100 most recent articles
    df_sorted = df.sort_values("date", ascending=False).head(100)
    result["recent_articles"] = [
        {
            "date":      d.strftime("%Y-%m-%d %H:%M:%S"),
            "crypto":    c,
            "sentiment": float(s),
            "link":      l,
            "content":   ct[:200] + ("…" if len(ct) > 200 else "")
        }
        for d, c, s, l, ct in zip(
            df_sorted["date"],
            df_sorted["crypto"],
            df_sorted["sentiment"],
            df_sorted["link"],
            df_sorted["content"]
        )
    ]

    # 7) Total dataset length
    result["dataset_length"] = int(getDatasetLength(datasetFileName=base_name))

    return result

# ==== FastAPI Application ====
app = FastAPI()
logger.info("FastAPI app initialized.")

@app.get("/sentiment_summary", response_class=JSONResponse)
def sentiment_summary():
    try:
        return read_h5_and_compute()
    except FileNotFoundError as e:
        logger.error(str(e))
        return JSONResponse(status_code=404, content={"error": str(e)})

@app.post("/engage_analysis", response_class=JSONResponse)
async def engage_analysis():
    logger.info("Launching scraper to update dataset.h5")
    try:
        run_generic_scraper()
    except Exception as e:
        logger.error(f"Error running scraper: {e}")
    try:
        return read_h5_and_compute()
    except FileNotFoundError as e:
        logger.error(str(e))
        return JSONResponse(status_code=500, content={"error": str(e)})