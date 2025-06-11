# main.py
import logging
import os
import sys
from datetime import datetime, timedelta
import threading
import time
from typing import Optional

import pandas as pd
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# === Ensure backend/ is on PYTHONPATH so imports work ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Import du module de scraping
from scraping.store_data import storeData
from processor.h5_utilities import getDataset, getDatasetLength

# ==== Logging Configuration ====
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("fastapi_service.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


os.environ["TOKENIZERS_PARALLELISM"] = "false" # pour éviter les warnings de tokenizers

# ==== Paths ====
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

# ==== Global variables for background scraping ====
scraping_thread: Optional[threading.Thread] = None
scraping_active = False
last_scraping_time: Optional[datetime] = None
data_cache = {} # Dictionnaire python qui stocke toutes les données calculées
cache_lock = threading.Lock() # Lock pour synchroniser l'accès au cache
cache_update_time: Optional[datetime] = None


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
    """Lit le fichier H5 et calcule les métriques"""
    h5_path = os.path.join(PROJECT_ROOT, "dataset.h5")
    if not os.path.exists(h5_path):
        raise FileNotFoundError(f"{h5_path} not found")

    base_name = os.path.splitext(h5_path)[0]

    content, links, dates, cryptos, sentiments = getDataset(
        datasetFileName=base_name,
        isTrainDataset=True
    )

    dt = pd.to_datetime(dates, format='mixed', errors="coerce", utc=True).tz_convert(None)
    df = pd.DataFrame({
        "date":      dt,
        "crypto":    cryptos,
        "sentiment": sentiments.astype(float),
        "content":   content,
        "link":      links
    }).dropna(subset=["date"]) # Supprime les valeurs NaN dans les dates, si il y en a

    now = datetime.utcnow() # Date et heure actuelle

    # Définition des fenêtres de temps pour les statistiques
    windows = {
        "1h":  now - timedelta(hours=1),
        "24h": now - timedelta(days=1),
        "7d":  now - timedelta(days=7),
        "30d": now - timedelta(days=30),
    }

    result = {}

    
    ### General Sentiment 
    # Global counts, averages & statuses
    for label, cutoff in windows.items():
        sub   = df[df["date"] >= cutoff]
        count = len(sub)
        avg   = float(sub["sentiment"].mean()) if count else 0.0
        result[f"count_{label}"]  = count # Nombre d'articles dans la fenêtre de temps
        result[f"avg_{label}"]    = round(avg, 4) # Moyenne des sentiments dans la fenêtre de temps
        result[f"status_{label}"] = get_sentiment_status(avg) # Statut du sentiment dans la fenêtre de temps

    ### Time series des sentiments moyens par jour
    # 1. Utilise la date comme index pour le regroupement temporel
    # 2. Sélectionne uniquement la colonne des sentiments
    # 3. Regroupe les données par jour et calcule la moyenne
    # 4. Remplace les jours sans données par 0
    # 5. Réinitialise l'index pour avoir la date comme colonne normale
    df_daily = (
        df.set_index("date")["sentiment"]
          .resample("D").mean().fillna(0.0)
          .reset_index()
    )
    
    # Formatage des données pour l'API :
    # - Conversion des dates en format YYYY-MM-DD
    # - Conversion des sentiments en nombres flottants
    # - Création de deux listes parallèles : dates et sentiments
    result["timeseries"] = {
        "dates":      df_daily["date"].dt.strftime("%Y-%m-%d").tolist(),
        "sentiments": [float(x) for x in df_daily["sentiment"].tolist()]
    }

    ### Per-crypto metrics
    per_crypto = {} # Dictionnaire pour stocker les statistiques par cryptomonnaie
    
    for cd in CRYPTO_DEFINITIONS:
        name = cd["name"]
        # Mask boolean qui dit si la crypto est mentionner dans le dataframe
        mask = df["crypto"].apply(lambda lst: name in lst)
        
        # Dictionnaire pour stocker les statistiques de cette cryptomonnaie
        stats = {}
        
        # Calcul des statistiques pour chaque fenêtre de temps (1h, 24h, 7d, 30d)
        for label, cutoff in windows.items():
            # Filtre les articles : doit mentionner la crypto ET être dans la fenêtre de temps
            sub   = df[mask & (df["date"] >= cutoff)]
            count = len(sub)
            avg   = float(sub["sentiment"].mean()) if count else 0.0

            stats[f"count_{label}"]  = count  # Nombre d'articles
            stats[f"avg_{label}"]    = round(avg, 4)  # Moyenne des sentiments
            stats[f"status_{label}"] = get_sentiment_status(avg)  # Statut (peur, neutralité, etc.)
        
        per_crypto[name] = stats
    
    result["per_crypto"] = per_crypto

    ### 100 most recent articles
    df_sorted = df.sort_values("date", ascending=False).head(100)
    result["recent_articles"] = [
        {
            "date":      d.strftime("%Y-%m-%d %H:%M:%S"),
            "crypto":    c,
            "sentiment": float(s),
            "link":      l,
            "content":   ct[:200] + ("…" if len(ct) > 200 else "") # On coupe le contenu à 200 caractères
        }
        for d, c, s, l, ct in zip(
            df_sorted["date"],
            df_sorted["crypto"],
            df_sorted["sentiment"],
            df_sorted["link"],
            df_sorted["content"]
        )
    ]

    # Total dataset length
    result["dataset_length"] = int(getDatasetLength(datasetFileName=base_name))
    
    # Ajouter le statut du scraping et l'heure de mise à jour
    result["scraping_active"] = scraping_active
    result["last_scraping_time"] = last_scraping_time.isoformat() if last_scraping_time else None
    result["cache_update_time"] = cache_update_time.isoformat() if cache_update_time else None
    result["scraping_thread_alive"] = scraping_thread.is_alive() if scraping_thread else False
    

    return result

def update_cache():
    """Met à jour le cache avec les dernières données"""
    global data_cache, cache_update_time
    try:
        new_data = read_h5_and_compute() # On récupère les données du fichier H5 et on les calcule
        with cache_lock:
            data_cache = new_data # On met à jour le cache avec les nouvelles données
            cache_update_time = datetime.utcnow() # On met à jour l'heure de la mise à jour du cache
        logger.info(f"Cache updated at {cache_update_time}")
    except Exception as e:
        logger.error(f"Error updating cache: {e}")

def continuous_scraping():
    """Fonction de scraping continu qui tourne en arrière-plan pour le realtime"""
    global scraping_active, last_scraping_time
    
    logger.info("Starting continuous scraping thread...")
    
    while scraping_active:
        try:
            logger.info("Starting new scraping cycle...")
            last_scraping_time = datetime.utcnow()

            logger.info("Scraping cryptoNews...")
            result1 = storeData("cryptoNews", nbArticle=10000, h5FileName="dataset")
            
            logger.info("Scraping uToday...")
            result2 = storeData("uToday", nbArticle=10000, h5FileName="dataset")
            
            
            logger.info(f"Scraping cycle completed at {last_scraping_time}")
            logger.info(f"Articles scraped - cryptoNews: {result1 if result1 else 0}, uToday: {result2 if result2 else 0}")
            
            # Courte pause avant le prochain cycle
            time.sleep(10)
            
        except Exception as e:
            logger.error(f"Error in scraping cycle: {e}")
            # En cas d'erreur, pause de 60 secondes avant de réessayer
            time.sleep(60)

    logger.info("Continuous scraping stopped")

# Thread pour mettre à jour le cache régulièrement
def cache_updater():
    """Met à jour le cache toutes les 10 secondes"""
    while True:
        time.sleep(10)
        update_cache()





# ==== FastAPI Application ====
app = FastAPI()
logger.info("FastAPI app initialized.")

# Démarrer le thread de mise à jour du cache
cache_thread = threading.Thread(target=cache_updater, daemon=True)
cache_thread.start()
logger.info("Cache updater thread started")

# Charger les données initiales au démarrage
@app.on_event("startup")
async def startup_event():
    """Charge les données initiales dans le cache au démarrage"""
    try:
        update_cache()
        logger.info("Initial data loaded into cache")
    except Exception as e:
        logger.error(f"Error loading initial data: {e}")

@app.get("/sentiment_summary", response_class=JSONResponse)
def sentiment_summary():
    """Retourne les données depuis le cache (mis à jour toutes les 10 secondes)"""
    try:
        # Si le cache est vide, essayer de le charger
        if not data_cache:
            update_cache()
        
        # Retourner les données du cache
        with cache_lock:
            return data_cache.copy()
            
    except Exception as e:
        logger.error(f"Error in sentiment_summary: {e}")
        return JSONResponse(
            status_code=500, 
            content={"error": str(e), "message": "Error retrieving data"}
        )

@app.post("/engage_analysis", response_class=JSONResponse)
async def engage_analysis():
    """Lance le scraping continu en arrière-plan et retourne les données actuelles"""
    global scraping_thread, scraping_active
    
    try:
        # Si le scraping n'est pas déjà actif, le démarrer
        if not scraping_active or scraping_thread is None or not scraping_thread.is_alive():
            scraping_active = True
            
            scraping_thread = threading.Thread(target=continuous_scraping, daemon=True)
            scraping_thread.start()
            logger.info("Scraping thread started")
            
            # Mettre à jour le cache immédiatement
            update_cache()
            
            # Retourner les données actuelles
            with cache_lock:
                return data_cache.copy()
        else:
            logger.info("Scraping already active, returning current data")
            # Si le scraping est déjà actif, retourner simplement les données actuelles
            with cache_lock:
                return data_cache.copy()
            
    except Exception as e:
        logger.error(f"Error in engage_analysis: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "message": "Error starting analysis"}
        )

@app.post("/stop_analysis", response_class=JSONResponse)
async def stop_analysis():
    """Arrête le scraping continu (optionnel)"""
    global scraping_active
    
    scraping_active = False
    logger.info("Scraping stop requested")
    
    return {
        "status": "Scraping stopped",
        "message": "Continuous scraping has been stopped.",
        "scraping_active": False
    }

# Endpoint de santé pour vérifier le statut
@app.get("/health", response_class=JSONResponse)
def health():
    """Endpoint de santé pour vérifier le statut du service"""
    return {
        "status": "healthy",
        "scraping_active": scraping_active,
        "last_scraping_time": last_scraping_time.isoformat() if last_scraping_time else None,
        "cache_update_time": cache_update_time.isoformat() if cache_update_time else None
    }