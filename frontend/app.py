import streamlit as st
import plotly.graph_objects as go
import numpy as np
import requests
import logging

# === Logging Configuration ===
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("cryptoweather.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
# Suppress verbose watchdog logs (used by Streamlit's file watcher)
logging.getLogger("watchdog").setLevel(logging.WARNING)
# === Streamlit Setup ===
st.set_page_config(page_title="CryptoWeather", layout="centered")
st.title("🌦️ CryptoWeather")

st.markdown("""
This project is part of the **Web Mining** module in the *Master of Data Science*.
The goal of this website is to analyze the sentiment of the crypto market by scraping articles that discuss it,
feeding them into a custom-trained model capable of understanding their sentiment, and then visualizing the result
on a **Crypto Sentiment Index** ranging from:

**"Extreme Fear" → "Fear" → "Neutral" → "Greed" → "Extreme Greed"**
""")

# === Backend URL ===
backendUrl = "http://backend:8080/engage_analysis"
logger.debug(f"Backend URL set to: {backendUrl}")

# === Trigger analysis with button ===
if st.button("Launch Analysis"):
    logger.info("Analysis button clicked.")
    try:
        logger.debug("Sending POST request to backend.")
        response = requests.post(backendUrl)
        response.raise_for_status()
        result = response.json()
        avg_score = result["average_sentiment_score"]
        logger.info(f"Received average sentiment score: {avg_score}")
        st.success("Analysis complete!")
    except Exception as e:
        logger.error(f"Error calling backend: {e}")
        st.error(f"Error calling backend: {e}")
        avg_score = 0.0  # fallback
else:
    logger.debug("Analysis button not clicked.")
    avg_score = 0.0  # default before clicking

# === Sentiment Mapping ===
def get_sentiment_status(score: float) -> str:
    if score <= -0.6:
        return "Extreme fear"
    elif score <= -0.2:
        return "Fear"
    elif score <= 0.2:
        return "Neutral"
    elif score <= 0.6:
        return "Greed"
    else:
        return "Extreme greed"

logger.debug(f"Calculating sentiment status for score: {avg_score}")
sentiment_status = get_sentiment_status(avg_score)
logger.info(f"Sentiment status: {sentiment_status}")

# === Normalize Score ===
normalized_score = (avg_score + 1) * 50  # from [-1,1] to [0,100]
logger.debug(f"Normalized score: {normalized_score}")

# === Gauge Settings ===
quadrant_labels = [
    "",  # center
    "<b>Extreme Greed</b>",
    "<b>Greed</b>",
    "<b>Neutral</b>",
    "<b>Fear</b>",
    "<b>Extreme Fear</b>",
]
quadrant_colors = [
    "rgba(0,0,0,0)",
    "#1a9850",
    "#91cf60",
    "#fee08b",
    "#fc8d59",
    "#d73027",
]
n_quadrants = len(quadrant_colors) - 1
hand_length = np.sqrt(2) / 4
hand_angle = 360 * (-normalized_score / 2) / 100 - 180
logger.debug(f"Hand angle for gauge: {hand_angle}")

# === Build Figure ===
fig = go.Figure(
    data=[
        go.Pie(
            values=[0.5] + (np.ones(n_quadrants) / 2 / n_quadrants).tolist(),
            rotation=90,
            hole=0.5,
            marker_colors=quadrant_colors,
            text=quadrant_labels,
            textinfo="text",
            hoverinfo="skip",
            sort=False
        ),
    ],
    layout=go.Layout(
        showlegend=False,
        margin=dict(b=0, t=0, l=0, r=0),
        width=600,
        height=600,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        annotations=[
            go.layout.Annotation(
                text=(f"<b>Sentiment Score:</b> {avg_score:.2f}<br>"
                      f"<b>Status:</b> {sentiment_status}"),
                x=0.5, xanchor="center", xref="paper",
                y=0.25, yanchor="bottom", yref="paper",
                showarrow=False,
                font=dict(size=16, color="#333")
            )
        ],
        shapes=[
            go.layout.Shape(
                type="circle",
                x0=0.48, x1=0.52,
                y0=0.48, y1=0.52,
                fillcolor="#333",
                line_color="#333",
            ),
            go.layout.Shape(
                type="line",
                x0=0.5,
                y0=0.5,
                x1=0.5 + hand_length * np.cos(np.radians(hand_angle)),
                y1=0.5 + hand_length * np.sin(np.radians(hand_angle)),
                line=dict(color="#333", width=4)
            )
        ]
    )
)

logger.debug("Displaying gauge chart.")
# === Display Gauge ===
st.plotly_chart(fig, use_container_width=True)
