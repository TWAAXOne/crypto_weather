import logging
import os
import json
from typing import List

import torch
from torch import nn
from transformers import AutoTokenizer, AutoModel
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from scraping.scrape import run_scraper

# ==== Logging Configuration ====
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("fastapi_service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==== Regression Model Definition ====

class BertRegressor(nn.Module):
    def __init__(self, model_name="bert-base-uncased"):
        super(BertRegressor, self).__init__()
        logger.debug(f"Loading BERT model: {model_name}")
        self.bert = AutoModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(0.3)
        self.regressor = nn.Linear(self.bert.config.hidden_size, 1)

    def forward(self, input_ids, attention_mask=None, token_type_ids=None):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids)
        cls_output = self.dropout(outputs.last_hidden_state[:, 0, :])
        return self.regressor(cls_output).squeeze(-1)

# ==== Request Models ====

class Article(BaseModel):
    title: str
    content: str

class ArticlesRequest(BaseModel):
    articles: List[Article]

# ==== Initialize FastAPI ====

app = FastAPI()
logger.info("FastAPI app initialized.")

# ==== Load Model & Tokenizer ====

MODEL_NAME = "bert-base-uncased"
MODEL_PATH = os.path.join("model", "output", "bert_sentiment_regression_uncased")
MODEL_BIN = os.path.join(MODEL_PATH, "pytorch_model.bin")

logger.debug(f"Loading tokenizer from {MODEL_PATH}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

logger.debug(f"Initializing model and loading weights from {MODEL_BIN}")
model = BertRegressor(model_name=MODEL_NAME)
model.load_state_dict(torch.load(MODEL_BIN, map_location="cpu"))
model.eval()

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Model running on device: {device}")
model.to(device)

# ==== Sentiment Status Mapping ====

def get_sentiment_status(avg_score: float) -> str:
    if avg_score <= -0.6:
        return "Extreme fear"
    elif avg_score <= -0.2:
        return "Fear"
    elif avg_score <= 0.2:
        return "Neutral"
    elif avg_score <= 0.6:
        return "Greed"
    else:
        return "Extreme greed"

# ==== Scraping Endpoint ====

@app.get("/engage_scraping", response_class=JSONResponse)
def engage_scraping_api():
    logger.info("Scraping request received.")
    try:
        articles = run_scraper(max_articles=5)
        logger.debug(f"Scraped {len(articles)} articles.")
        return {"status": "success", "articles": articles}
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})

# ==== Analysis Endpoint ====

@app.post("/engage_analysis")
async def engage_analysis():
    logger.info("Sentiment analysis request received.")
    data = engage_scraping_api()
    if data.get("status") != "success":
        logger.error("Scraping step failed in analysis pipeline.")
        return JSONResponse(status_code=500, content={"error": data.get("detail", "Scraping failed")})

    articles = data["articles"]
    texts = [f"{article['title']}. {article['content']}" for article in articles]
    logger.debug("Tokenizing input texts.")
    encodings = tokenizer(texts, truncation=True, padding=True, return_tensors="pt", max_length=512)
    encodings = {k: v.to(device) for k, v in encodings.items()}

    logger.debug("Running model inference.")
    with torch.no_grad():
        predictions = model(**encodings).cpu().numpy().tolist()

    avg_score = sum(predictions) / len(predictions)
    status = get_sentiment_status(avg_score)

    logger.info(f"Average sentiment score: {avg_score:.4f}, Status: {status}")
    return {
        "average_sentiment_score": round(avg_score, 4),
        "status": status,
        "individual_scores": [round(p, 4) for p in predictions]
    }
