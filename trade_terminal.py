import os
import sys
# Critical for Anaconda/Windows environment stability
os.environ['NUMBA_SKIP_REQUIREMENTS_CHECK'] = '1'

import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import time

# --- 1. PRO UI CONFIGURATION ---
st.set_page_config(layout="wide", page_title="ZM Elite Terminal", page_icon="💹")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: white; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #00ffbb; }
    .stProgress > div > div > div > div { background-color: #00ffbb; }
    
    /* Custom Green and Red Call/Put Buttons */
    div[data-testid="stSidebar"] div[data-testid="column"]:nth-of-type(1) button { background-color: #00ffbb !important; color: black !important; font-weight: bold; border: none; }
    div[data-testid="stSidebar"] div[data-testid="column"]:nth-of-type(2) button { background-color: #ff3355 !important; color: white !important; font-weight: bold; border: none; }
    
    /* Order Book & Ticker Styling */
    .order-book-row { display: flex; justify-content: space-between; font-family: monospace; font-size: 0.85rem; }
    .bid { color: #00ffbb; }
    .ask { color: #ff3355; }
    .live-ticker { font-size: 2rem; font-weight: bold; color: #00ffbb; font-family: monospace; }
    
    /* News Link Styling */
    a { color: #00ffbb !important; text-decoration: none; }
    a:hover { text-decoration: underline; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE COMPLETE, UNTRUNCATED ASSET DICTIONARY ---
ASSETS = {
    "Crypto": {
        "Bitcoin (BTC)": "BTC-USD", "Ethereum (ETH)": "ETH-USD", "Solana (SOL)": "SOL-USD", 
        "Ripple (XRP)": "XRP-USD", "Dogecoin (DOGE)": "DOGE-USD"
    },
    "Forex": {
        "USD/ZMW (Kwacha)": "ZMW=X", "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", 
        "USD/JPY": "JPY=X", "AUD/USD": "AUDUSD=X"
    },
    "Stocks": {
        "Nvidia (NVDA)": "NVDA", "Tesla (TSLA)": "TSLA", "Apple (AAPL)": "AAPL", 
        "Microsoft (MSFT)": "MSFT", "Amazon (AMZN)": "AMZN"
    },
    "Commodities": {
        "Gold": "GC=F", "Silver": "SI=F", "Brent Crude": "BZ=F", "Copper": "HG=F"
    },
    "Indices & ETFs": {
        "S&P 500": "^GSPC", "Nasdaq 100": "^IXIC", "Bitcoin ETF (IBIT)": "IBIT"
    }
}

# --- 3. SESSION STATE ---
if 'balance' not in st.session_state: st.session_state.balance = 50000.00
if 'active_trades' not in st.session_state: st.session_state.active_trades = []
if 'acknowledged' not in st.session_state: st.session_state.acknowledged = False

# --- 4. SEC COMPLIANCE DIALOG ---
if not st.session_state.acknowledged:
    @st.dialog("🇿🇲 SEC Zambia Regulatory Portal")
    def auth_dialog():
        st.warning("High-Risk Financial Instrument Warning")
        st.write("This platform is operating under the SEC Zambia Sandbox Framework. Trading involves significant risk to capital.")
        if st.button("I AGREE & ENTER TERMINAL", use_container_width=True):
            st.session_state.acknowledged = True
            st.rerun()
    auth_dialog()
    st.stop() 

# --- 5. DATA ENGINES (Decoupled Fast/Slow Lanes) ---

# Slow Lane: Chart Data (Updates every 60s so iframe stays solid for drawing)
@st.cache_data(ttl=60)
def fetch_chart_data(symbol, tf):
    try:
        period = "5d" if tf in ["1m", "5m", "15m"] else "1mo"
        df = yf.download(symbol, period=period, interval=tf, progress=False)
        if df.empty: return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        df = df.dropna()
        if not df.empty:
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['Hist'] = df['MACD'] - df['Signal']
        return df
    except:
        return pd.DataFrame()

# Fast Lane: Tick Data (Updates every 2s for PnL and Order Book)
@st.cache_data(ttl=2)
def fetch_live_price(symbol):
    try:
        df = yf.download(symbol, period="1d", interval="1m", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        return float(df['Close'].dropna().iloc[-1])
    except:
        return 0.0

# Live News Engine (Updates every 60s to prevent API bans)
@st.cache_data(ttl=60)
def fetch_live_news(symbol):
    try:
        ticker = yf.Ticker(symbol)
        news_data = ticker.news
        if not news_data: news_data = yf.Ticker("^GSPC").news
        formatted_news = []
        for item in news_data[:3]: 
            content = item.get("content", item)
            title = content.get("title", "Market Update")
            link = content.get("clickThroughUrl", content.get("canonicalUrl", {})).get("url", content.get("url", "#"))
            publisher = content.get("provider", {}).get("displayName", content.get("publisher", "Global Wire"))
            formatted_news.append({"title": title, "link": link, "publisher": publisher})
        return formatted_news
    except:
        return []

# --- 6. SIDEBAR MENU & EXECUTION ---
with st.sidebar:
    st.title("🇿🇲 ZM Elite Menu")
    asset_class = st.selectbox("Category", list(ASSETS.keys()))
    asset_name = st.selectbox("Asset", list(ASSETS[asset_class].keys()))
    ticker = ASSETS[asset_class][asset_name]
    t_frame = st.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"], index=0)

base_price = fetch_live_price(ticker)

with st.sidebar:
    st.divider()
    chart_style = st.radio("View Mode", ["Candlesticks (Pro)", "Line (Simple)"])
    show_sma = st.checkbox("Show SMA 20 Trendline", value=True)
    
    st.divider()
    st.subheader("Order Placement")
    curr_bal = float(st.session_state.balance)
    
    if curr_bal < 10.0:
        st.error("Bankrupt! Reset below.")
        amount = 0.0
    else:
        amount = st.number_input("Investment (ZMW)", min_value=10.0, max_value=max(10.0, curr_bal), value=min(1000.0, curr_bal))
    
    c1, c2 = st.columns(2)
    if c1.button("📈 CALL", use_container_width=True, disabled=(curr_bal < 10 or base_price == 0)):
        st.session_state.balance -= amount
        st.session_state.active_trades.append({"id": int(time.time()), "asset": asset_name, "type": "CALL", "amount": amount, "entry": base_price})
        st.rerun()
    if c2.button("📉 PUT
