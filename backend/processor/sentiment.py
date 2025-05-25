# backend/processor/sentiment.py

import logging
import torch
from torch import nn
from transformers import AutoTokenizer, AutoModel

logger = logging.getLogger(__name__)

class BertRegressor(nn.Module):
    def __init__(self, model_name="bert-base-uncased", model_path="model/output/bert_sentiment_regression_uncased"):
        super().__init__()
        logger.debug(f"Loading BERT model from {model_name} at {model_path}")
        self.bert = AutoModel.from_pretrained(model_path)
        self.dropout = nn.Dropout(0.3)
        self.regressor = nn.Linear(self.bert.config.hidden_size, 1)

    def forward(self, input_ids, attention_mask=None, token_type_ids=None):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids)
        cls = self.dropout(outputs.last_hidden_state[:, 0, :])
        return self.regressor(cls).squeeze(-1)

# Initialisation globale
MODEL_PATH = "backend/model/output/bert_sentiment_regression_uncased"
TOKENIZER = AutoTokenizer.from_pretrained(MODEL_PATH)
MODEL = BertRegressor(model_path=MODEL_PATH)
MODEL.load_state_dict(torch.load(f"{MODEL_PATH}/pytorch_model.bin", map_location="cpu"))
MODEL.eval()
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL.to(DEVICE)

def compute_sentiment(text: str) -> float:
    """Retourne un score de sentiment entre -1 et +1."""
    # Tokenisation
    enc = TOKENIZER([text], truncation=True, padding=True, max_length=512, return_tensors="pt")
    enc = {k: v.to(DEVICE) for k, v in enc.items()}
    # Inference
    with torch.no_grad():
        score = MODEL(**enc).cpu().item()
    return score