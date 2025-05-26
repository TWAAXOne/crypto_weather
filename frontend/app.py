import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import requests
import logging

# === Logging Configuration ===
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("cryptoweather.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
logging.getLogger("watchdog").setLevel(logging.WARNING)

st.set_page_config(page_title="CryptoWeather", layout="centered")

# === Main title & full description ===
st.title("🌦️ CryptoWeather")
st.markdown("""
This project is part of the **Web Mining** module in the *Master of Data Science*.
The goal of this website is to analyze the sentiment of the crypto market by scraping articles that discuss it,
feeding them into a custom-trained BERT model to produce a sentiment score in [-1, +1], and visualizing the result
on a **Crypto Sentiment Index** ranging from:

**"Extreme Fear" → "Fear" → "Neutral" → "Greed" → "Extreme Greed"**

Under the hood:
- Continuous scraping of multiple crypto news sources  
- Sentiment regression with a fine-tuned BERT  
- Storage in HDF5 and real-time aggregation  
""")

SUMMARY_URL  = "http://0.0.0.0:8080/sentiment_summary"
ANALYSIS_URL = "http://0.0.0.0:8080/engage_analysis"

if "running" not in st.session_state:
    st.session_state["running"] = False

if st.button("Launch Analysis"):
    st.session_state["running"] = True

def fetch_data():
    try:
        if st.session_state["running"]:
            resp = requests.post(ANALYSIS_URL)
        else:
            resp = requests.get(SUMMARY_URL)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Error calling backend: {e}")
        return {}

data = fetch_data()

# === Auto-refresh every 30s when running ===
if st.session_state["running"]:
    st.experimental_rerun()
    st.experimental_sleep(30_000)

# === General Sentiment Section ===
st.header("General Sentiment")
st.markdown("---")

def make_gauge(score: float, status: str, title: str):
    normalized = (score + 1) * 50
    hand_angle = 360 * (-normalized / 2) / 100 - 180
    labels = ["", "<b>Extreme Greed</b>", "<b>Greed</b>",
              "<b>Neutral</b>", "<b>Fear</b>", "<b>Extreme Fear</b>"]
    colors = ["rgba(0,0,0,0)",
              "#1a9850", "#91cf60", "#fee08b", "#fc8d59", "#d73027"]
    n = len(colors) - 1
    hand_len = np.sqrt(2) / 4

    fig = go.Figure(
        data=[go.Pie(
            values=[0.5] + (np.ones(n) / 2 / n).tolist(),
            rotation=90, hole=0.5,
            marker_colors=colors,
            text=labels, textinfo="text",
            hoverinfo="skip", sort=False
        )],
        layout=go.Layout(
            title=title, showlegend=False,
            margin=dict(b=0, t=30, l=0, r=0),
            width=200, height=200,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            annotations=[go.layout.Annotation(
                text=f"<b>{score:.2f}</b><br>{status}",
                x=0.5, y=0.25, xref="paper", yref="paper",
                xanchor="center", yanchor="bottom",
                showarrow=False, font=dict(size=12, color="#333")
            )],
            shapes=[
                {"type":"circle","x0":0.48,"x1":0.52,"y0":0.48,"y1":0.52,
                 "fillcolor":"#333","line_color":"#333"},
                {"type":"line","x0":0.5,"y0":0.5,
                 "x1":0.5 + hand_len * np.cos(np.radians(hand_angle)),
                 "y1":0.5 + hand_len * np.sin(np.radians(hand_angle)),
                 "line":dict(color="#333",width=3)}
            ]
        )
    )
    return fig

# Display 3 global gauges with captions
col1, col2, col3 = st.columns(3)
for col, window in zip([col1, col2, col3], ["24h", "7d", "30d"]):
    avg    = data.get(f"avg_{window}", 0.0)
    status = data.get(f"status_{window}", "Neutral")
    count  = data.get(f"count_{window}", 0)
    col.plotly_chart(
        make_gauge(avg, status, f"Last {window}"),
        use_container_width=True,
        key=f"glob-{window}"
    )
    caption = "No data" if count == 0 else f"{count} articles"
    col.caption(caption)

# === Daily Time Series ===
if data.get("timeseries", {}).get("dates"):
    fig_ts = go.Figure(go.Scatter(
        x=data["timeseries"]["dates"],
        y=data["timeseries"]["sentiments"],
        mode="lines+markers"
    ))
    fig_ts.update_layout(
        title="Daily Average Sentiment Over Time",
        xaxis_title="Date",
        yaxis_title="Sentiment Score",
        yaxis_range=[-1, 1],
        xaxis_tickangle=-45,
        margin=dict(t=40, b=40)
    )
    st.plotly_chart(fig_ts, use_container_width=True, key="timeseries")

# === Sentiment by Cryptocurrency Section ===
st.markdown("## Sentiment by Cryptocurrency")
st.markdown("---")

if "per_crypto" in data:
    windows = ["1h", "24h", "7d", "30d"]
    for name, stats in data["per_crypto"].items():
        # Don't display if all counts are zero (no data for this crypto at all)
        non_zero = any(stats.get(f"count_{w}", 0) > 0 for w in windows)
        if not non_zero:
            continue
        st.markdown(f"**{name}**")
        cols = st.columns(4)
        for col, w in zip(cols, windows):
            avg    = stats.get(f"avg_{w}", 0.0)
            status = stats.get(f"status_{w}", "Neutral")
            count  = stats.get(f"count_{w}", 0)
            col.plotly_chart(
                make_gauge(avg, status, w),
                use_container_width=True,
                key=f"{name}-{w}"
            )
            caption = "No data" if count == 0 else f"{count} articles"
            col.caption(caption)

# === Recent Articles DataFrame ===
df100 = None
if data.get("recent_articles"):
    st.markdown("## 100 Most Recent Articles")
    df100 = pd.DataFrame(data["recent_articles"])
    st.dataframe(df100, use_container_width=True)

# === Dataset size at bottom ===
st.markdown("---")

# If the dataset was loaded, use its length (from articles OR computed on DataFrame), else fallback to backend "dataset_length"
dataset_count = 0
if df100 is not None:
    try:
        # Estimate total from the most recent df if available (safer than trusting backend!)
        dataset_count = data.get('dataset_length', 0)
        # Prefer the backend-provided value, but if it is wrong, fallback
        if dataset_count == 0:
            # If 100 in df, but backend says 0, fallback to count of all recent_articles
            dataset_count = len(df100)
    except Exception:
        dataset_count = data.get('dataset_length', 0)
else:
    dataset_count = data.get('dataset_length', 0)

st.markdown(f"**Number of items in our dataset:** {dataset_count}")