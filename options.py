"""
Finance News + Fundamentals + Sentiment Dashboard
-------------------------------------------------
Fetches 1-week stock-market & finance news using Google News RSS,
runs sentiment analysis, and displays live fundamentals & stock charts via yfinance.

Run:
    pip install streamlit yfinance feedparser pandas requests matplotlib textblob
    streamlit run finance_news_fundamentals_app.py
"""

import streamlit as st
import yfinance as yf
import feedparser
import pandas as pd
import requests
from datetime import datetime, timedelta
import re
import matplotlib.pyplot as plt
from io import BytesIO
from textblob import TextBlob

# ---------------------------- UI CONFIG ----------------------------
st.set_page_config(page_title="Finance News + Fundamentals + Sentiment", layout="wide")
st.markdown("""
    <style>
    body { background-color: #0A1828; color: #EAF4FF; }
    .headline { font-size:18px; color:#84E1D9; font-weight:600; }
    .meta { color:#7FBEEB; font-size:13px; }
    .desc { color:#B9D9E9; margin-top:6px; }
    .fund-card { background:rgba(255,255,255,0.05); border-radius:10px; padding:10px; margin-top:5px; }
    .sentiment { font-weight:600; padding:3px 8px; border-radius:5px; }
    .pos { background:#2ECC71; color:#0A1828; }
    .neu { background:#BDC3C7; color:#0A1828; }
    .neg { background:#E74C3C; color:white; }
    .stButton>button { background:linear-gradient(90deg,#29ABE2,#84E1D9); color:#0A1828; border:none; font-weight:bold; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------- FETCH NEWS ----------------------------
def fetch_google_news(query="stock market finance India", days=7, max_items=40):
    q = requests.utils.requote_uri(query)
    feed_url = f"https://news.google.com/rss/search?q={q}+when:7d&hl=en-IN&gl=IN&ceid=IN:en"
    d = feedparser.parse(feed_url)
    cutoff = datetime.utcnow() - timedelta(days=days)
    articles = []
    for e in d.entries:
        pub = None
        if hasattr(e, "published_parsed") and e.published_parsed:
            pub = datetime(*e.published_parsed[:6])
        if pub and pub < cutoff:
            continue
        articles.append({
            "title": e.get("title"),
            "link": e.get("link"),
            "summary": e.get("summary", ""),
            "published": pub.strftime("%b %d, %Y") if pub else "",
        })
        if len(articles) >= max_items:
            break
    return articles

# ---------------------------- SENTIMENT ANALYSIS ----------------------------
def analyze_sentiment(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity > 0.1:
        label = "Positive"; cls = "pos"
    elif polarity < -0.1:
        label = "Negative"; cls = "neg"
    else:
        label = "Neutral"; cls = "neu"
    return label, cls, polarity

# ---------------------------- DETECT & FETCH FUNDAMENTALS ----------------------------
def detect_ticker(title):
    tickers = []
    tokens = re.findall(r'\b[A-Z]{2,6}\b', title)
    for t in tokens:
        tickers.append(t)
        tickers.append(f"{t}.NS")
    return tickers

def get_fundamentals(ticker):
    try:
        tk = yf.Ticker(ticker)
        info = tk.info
        fund = {
            "Company": info.get("longName", ticker),
            "Sector": info.get("sector"),
            "Industry": info.get("industry"),
            "Market Cap": info.get("marketCap"),
            "Current Price": info.get("currentPrice"),
            "PE Ratio": info.get("trailingPE"),
            "PB Ratio": info.get("priceToBook"),
            "Dividend Yield": info.get("dividendYield"),
            "52W High": info.get("fiftyTwoWeekHigh"),
            "52W Low": info.get("fiftyTwoWeekLow"),
        }
        return {k:v for k,v in fund.items() if v is not None}
    except Exception:
        return None

# ---------------------------- MINI STOCK CHART ----------------------------
def get_stock_chart(ticker):
    try:
        df = yf.download(ticker, period="3mo")
        if df.empty: return None
        fig, ax = plt.subplots(figsize=(6,2))
        ax.plot(df.index, df['Close'], color='#84E1D9', linewidth=1.8)
        ax.fill_between(df.index, df['Close'], color='#29ABE2', alpha=0.1)
        ax.set_title(f"{ticker} - 3 Month Trend", fontsize=9, color='#7FBEEB')
        ax.tick_params(colors='#7FBEEB', labelsize=8)
        plt.grid(alpha=0.2)
        buf = BytesIO()
        plt.savefig(buf, format="png", transparent=True, bbox_inches='tight')
        buf.seek(0)
        return buf
    except Exception:
        return None

# ---------------------------- APP BODY ----------------------------
st.title("📈 Finance News + Fundamentals + Sentiment")
st.markdown("Get the **latest (1-week)** finance and stock market news with sentiment scores and live company data.")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    query = st.text_input("News Query", "stock market OR finance OR IPO OR NIFTY OR Sensex")
    max_news = st.slider("Max News Items", 10, 60, 25)
    st.info("Tip: Use short tickers (e.g., RELIANCE, INFY) in your query to match company headlines.")

# ---------------------------- MAIN ----------------------------
with st.spinner("Fetching news..."):
    news_list = fetch_google_news(query=query, days=7, max_items=max_news)

if not news_list:
    st.warning("No recent news found. Try a different query.")
else:
    for a in news_list:
        label, cls, pol = analyze_sentiment(a['title'])
        st.markdown(f"<div class='headline'>[{a['title']}]({a['link']})</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='meta'>📅 {a['published']} | Sentiment: <span class='sentiment {cls}'>{label}</span></div>", unsafe_allow_html=True)
        if a['summary']:
            st.markdown(f"<div class='desc'>{a['summary']}</div>", unsafe_allow_html=True)

        with st.expander("📊 Show Company Fundamentals & Chart"):
            tickers = detect_ticker(a['title'])
            for t in tickers:
                fund = get_fundamentals(t)
                if fund:
                    st.markdown(f"### 🏢 {fund.get('Company','')}")
                    df = pd.DataFrame(list(fund.items()), columns=["Metric", "Value"])
                    st.markdown("<div class='fund-card'>", unsafe_allow_html=True)
                    st.table(df)
                    st.markdown("</div>", unsafe_allow_html=True)
                    chart = get_stock_chart(t)
                    if chart:
                        st.image(chart, use_column_width=False)
                    break
            else:
                st.info("No valid ticker found in this headline.")
        st.markdown("<hr style='opacity:0.2'>", unsafe_allow_html=True)

st.markdown("<br><center>⚡ Built with Streamlit • yfinance • TextBlob • Google News RSS</center>", unsafe_allow_html=True)
