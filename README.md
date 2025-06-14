# CryptoWeather Sentiment Index

Ce projet est un projet webmining fusionnant du scraping de données et du sentiment analysis.

## Comment lancer le projet

1. Cloner le repo
2. Créer un environnement virtuel avec `python -m venv .venv`
3. Activer l'environnement virtuel avec `source .venv/bin/activate`
4. Installer les dépendances avec `pip install -r requirements.txt`
5. Lancer le serveur backend avec `uvicorn backend.main:app --host 0.0.0.0 --port 8080`
6. Lancer le frontend avec `cd frontend && streamlit run app.py --server.port=8501 --server.address=0.0.0.0`

## Comment lancer le serveur

1. Lancer le serveur
2. Lancer le frontend
