# CryptoWeather Sentiment Index

Ce projet est un projet webmining fusionnant du scraping de données sur deux sites de news de crypto-monnaies. Nous avons entrainer notre propre modèle d'analyse de sentiment et nous l'utilisons pour calculer des metrics d'anaylse de sentiment pour chaque crypto-monnaie.

## La documentation du projet

La documentation du projet est dans le fichier `rapport_cryptoweather.pdf`.

## Comment lancer le projet

1. Cloner le repo
2. Créer un environnement virtuel avec `python -m venv .venv`
3. Activer l'environnement virtuel avec `source .venv/bin/activate`
4. Installer les dépendances avec `pip install -r requirements.txt`
5. Télécharger le modèle de sentiment avec ce lien https://www.swisstransfer.com/d/7b120a02-8722-4fdc-83b5-9237ad61ce2b
6. Dézipper et renommer le dossier en `bert_sentiment_regression_v3` et placer le dans le dossier `backend/model/output`
7. Lancer le serveur backend avec `uvicorn backend.main:app --host 0.0.0.0 --port 8080`
8. Lancer le frontend avec `cd frontend && streamlit run app.py --server.port=8501 --server.address=0.0.0.0`

## Help

- La commande pour créer un dataset vierge est `python backend/processor/h5_utilities.py`
