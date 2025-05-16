# Cahier des Charges – CryptoWeather Sentiment Index

TODO:

1. Vérifier si l'on a le droit de scraper le site de cointelegraph - Abdullah

- chercher les sites web

2. Réparer le scrapper - Abdullah
3. Créer un dataset de test/validation avec les données scraper - Charly
4. Faut scrapper beaucoup de données + real time - Richard
5. Il faut faire l'analyse par crypto monnaie et le time series - Maxime

- Interface de l'application

6. Diagramme de Gantt de la planification du projet - Richard

---

## • General Goal of the Project

The objective of this project is to create an intelligent and interactive platform that captures and analyzes real-time sentiment from cryptocurrency-related news articles. The platform generates a **Crypto Sentiment Index**, offering users an immediate understanding of the market's emotional state, ranging from **"Extreme Fear"** to **"Extreme Greed"**.

---

## • Context and Objectives

Cryptocurrency markets are highly reactive to public opinion and media influence. Sentiment analysis provides an effective way to quantify that influence. This project was developed in the context of the _Web Mining_ module , with the following goals:

- Collect real-time news related to Bitcoin and crypto markets.
- Analyze the tone and sentiment of these articles using a trained model.
- Translate sentiment scores into an aggregated index for intuitive visualization.
- Provide users with a tool to interpret current market psychology.

---

## • Presentation of the Data Used

The data used for training consists of Bitcoin news articles collected between **2021 and 2024**, available via a public dataset on Kaggle titled:  
**“Sentiment Analysis of Bitcoin News (2021 - 2024)”**.  
Each entry includes:

- `Short Description`: A summary of the article.
- `Accurate Sentiments`: A manually annotated sentiment score ranging from -1 to 1.

---

## • Data Sources and Usage Rights

- **Training data**: Openly available on Kaggle, used in accordance with its licensing for academic and research purposes.
- **Live data**: Scraped from the public news website **[https://cointelegraph.com](https://cointelegraph.com)**, strictly for temporary analysis within the app and not stored or redistributed.

---

## • Description (Attributes, Quantity)

**Training data** includes approximately several thousand labeled news headlines and summaries, each with:

- `text` (string): The news description.
- `score` (float): A sentiment score between -1 (extremely negative) and 1 (extremely positive).

**Live scraped data** includes:

- `title` (string): Headline of the article.
- `content` (string): Main article body.

A maximum of 10 live articles are processed per session for performance and relevance.

---

## • Extraction (Methods)

- **Training**: CSV import and preprocessing using pandas and scikit-learn.
- **Live Articles**: Extracted using **Selenium** with **undetected-chromedriver** in headless mode. The scraper loads the Cointelegraph homepage, scrolls dynamically, and opens each article in a new browser tab to extract full content.

---

## • Overall Architecture / Technologies Used

- **Frontend**: Streamlit web interface for launching analysis and visualizing the sentiment index.
- **Backend**: FastAPI application hosting endpoints for scraping and model inference.
- **Model**: PyTorch-based custom BERT regression model.
- **Deployment**: Dockerized services for portability and testing.

---

## • Techniques, Methods, and Algorithms for Analysis

- A **custom regression model** based on **BERT (base-uncased)** is fine-tuned on the Kaggle dataset to predict a continuous sentiment score.
- Input text is tokenized using HuggingFace Transformers.
- The model outputs a sentiment value, and an average score is computed across articles.
- Status categories ("Fear", "Neutral", etc.) are derived based on score thresholds.

### Why a Custom Model?

Generic pre-trained sentiment models are usually trained on social media, movie reviews, or generic news corpora. They often fail to capture domain-specific language found in cryptocurrency media (e.g., market jargon, technical terms, emotional cues related to financial risk).  
Training a **custom BERT regression model** on domain-relevant data ensures:

- Higher precision and contextual awareness.
- Scoring calibrated to the crypto finance domain.
- Better generalization for real-world market articles.

---

## • Statistical Description / Estimation

The system is based on **regression**:

- Model output: Continuous score ∈ [-1, 1].
- Final output: Average score from 5–10 articles.
- The score is mapped into 5 qualitative categories via a visual gauge:
  - Extreme Fear
  - Fear
  - Neutral
  - Greed
  - Extreme Greed

---

## • Expected Results

- A numeric sentiment index updated on user request.
- A readable label indicating current market mood.
- A gauge visual (Plotly) showing where the market lies between “Fear” and “Greed”.

---

## • Risks, Critical Points, or Problems Encountered

- **Website structure volatility**: Scraper depends on Cointelegraph's layout and may break if the site changes.
- **Latency**: Analysis requires 1-2 min per request due to live scraping and model inference.
- **Model limits**: BERT input is capped at 512 tokens, which truncate long articles.
- **Generalization**: Even with fine-tuning, unexpected article styles may reduce accuracy.

---

## • Planning of Next Project Steps

The following steps are planned for the successful execution of the project:

- Preparing and cleaning the training dataset.
- Preparing the scraping script to gather live crypto news articles.
- Fine-tuning the BERT regression model on sentiment-labeled crypto news.
- Designing the Streamlit frontend interface.
- Implementing the FastAPI backend for scraping and model inference.
- Integrating all components within a Docker environment.

---
