# backend/processor/sentiment.py

import logging
import os
import torch
from torch import nn
from transformers import AutoTokenizer, AutoModel

logger = logging.getLogger(__name__)

class BertRegressor(nn.Module):
    def __init__(self, model_path: str):
        super().__init__()
        logger.debug(f"Loading BERT model from local path: {model_path}")
        # On passe local_files_only=True pour ne charger que du local
        self.bert = AutoModel.from_pretrained(model_path, local_files_only=True)
        self.dropout = nn.Dropout(0.3)
        self.regressor = nn.Linear(self.bert.config.hidden_size, 1)

    def forward(self, input_ids, attention_mask=None, token_type_ids=None):
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids
        )
        cls = self.dropout(outputs.last_hidden_state[:, 0, :])
        return self.regressor(cls).squeeze(-1)

# ==== Initialisation globale ====
# On construit un chemin absolu vers le dossier du modèle
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "model", "output", "bert_sentiment_regression_base_best")

# Tokenizer local
TOKENIZER = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)

# Modèle
MODEL = BertRegressor(model_path=MODEL_DIR)
MODEL.load_state_dict(
    torch.load(os.path.join(MODEL_DIR, "pytorch_model.bin"), map_location="cpu")
)
MODEL.eval()

# Device
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL.to(DEVICE)

def compute_sentiment(text: str) -> float:
    """
    Retourne un score de sentiment entre -1 et +1 basé sur le BERT entraîné.
    """
    # Tokenisation
    enc = TOKENIZER(
        [text],
        truncation=True,
        padding=True,
        max_length=512,
        return_tensors="pt"
    )
    enc = {k: v.to(DEVICE) for k, v in enc.items()}

    # Inference
    with torch.no_grad():
        score = MODEL(**enc).cpu().item()

    return score