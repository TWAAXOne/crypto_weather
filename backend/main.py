from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import torch
from torch import nn
from transformers import AutoTokenizer, AutoModel
import os
import json

from scraping.scrape import run_scraper


# ==== Regression Model ====

class BertRegressor(nn.Module):
    def __init__(self, model_name="bert-base-uncased"):
        super(BertRegressor, self).__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(0.3)
        self.regressor = nn.Linear(self.bert.config.hidden_size, 1)

    def forward(self, input_ids, attention_mask=None, token_type_ids=None):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids)
        cls_output = self.dropout(outputs.last_hidden_state[:, 0, :])
        return self.regressor(cls_output).squeeze(-1)

# ==== Request Format ====

class Article(BaseModel):
    title: str
    content: str

class ArticlesRequest(BaseModel):
    articles: List[Article]

# ==== Initialize FastAPI ====

app = FastAPI()

# ==== Load Model & Tokenizer ====

MODEL_NAME = "bert-base-uncased"
MODEL_PATH = os.path.join("model", "output", "bert_sentiment_regression_uncased")
MODEL_BIN = os.path.join(MODEL_PATH, "pytorch_model.bin")

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = BertRegressor(model_name=MODEL_NAME)
model.load_state_dict(torch.load(MODEL_BIN, map_location="cpu"))
model.eval()

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

print(f"[INFO] Loaded regression model from {MODEL_BIN}")

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

# ==== API Endpoint ====

def engage_scraping():
    articles = run_scraper(max_articles=5)  # or any number you want
    return {"articles": articles}


@app.post("/engage_analysis")
async def engage_analysis():
    data = engage_scraping()
    articles = data["articles"]  # assuming the JSON has a top-level "articles" list

    texts = [f"{article['title']}. {article['content']}" for article in articles]
    encodings = tokenizer(texts, truncation=True, padding=True, return_tensors="pt", max_length=512)
    encodings = {k: v.to(device) for k, v in encodings.items()}

    with torch.no_grad():
        predictions = model(**encodings).cpu().numpy().tolist()

    avg_score = sum(predictions) / len(predictions)
    status = get_sentiment_status(avg_score)

    return {
        "average_sentiment_score": round(avg_score, 4),
        "status": status,
        "individual_scores": [round(p, 4) for p in predictions]
    }

