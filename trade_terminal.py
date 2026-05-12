import os
import sys
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
    
    /* Call/Put Button Colors */
    div[data-testid="stSidebar"] div[data-testid="column"]:nth-of-type(1) button { background-color: #00ffbb !important; color: black !important; font-weight: bold; border: none; }
    div[data-testid="stSidebar"] div[data-testid="column"]:nth-of-type(2) button { background-color: #ff3355 !important; color: white !important; font-weight: bold; border: none; }
    
    /* Order Book Styling */
    .order-book-row { display: flex; justify-content: space-between; font-family: monospace; font-size: 0.85rem; }
    .bid { color: #00ffbb; }
    .ask { color: #ff3355; }
    
    /* News Link Styling */
    a { color: #00ffbb !important; text-decoration: none; }
    a:hover { text-decoration: underline; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE COMPLETE ASSET DICTIONARY ---
ASSETS = {
    "Crypto": {"Bitcoin (BTC)": "BTC-USD", "Ethereum (ETH)": "ETH-USD", "Solana (SOL)": "SOL-USD"},
    "Forex": {"USD/ZMW (Kwacha)": "ZMW=X", "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X"},
    "Stocks": {"Nvidia (NVDA)": "NVDA", "Tesla (TSLA)": "TSLA", "Apple (AAPL)": "AAPL"},
    "Commodities": {"Gold": "GC=F", "Brent Crude": "BZ=F"},
    "Indices & ETFs": {"S&P 500": "^GSPC", "Nasdaq 100": "^IXIC"}
}

# --- 3. SESSION STATE ---
if 'balance' not in st.session_state: st.session_state.balance = 50000.00
if 'active_trades' not in st.session_state: st.session_state.active_trades = []

# --- 4. DATA ENGINES ---

# Price Engine (Cached for 3 seconds to match our new smooth pulse)
@st.cache_data(ttl=3)
def fetch_elite_data(symbol, tf):
    try:
        period = "5d" if tf in ["1m", "5m", "15m"] else "1mo"
        df = yf.download(symbol, period=period, interval=tf, progress=False)
        if df.empty: return pd.DataFrame()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        
        df = df.dropna()
        if not df.empty:
            # Create the live movement simulation
            last_close = float(df['Close'].iloc[-1])
            df.iloc[-1, df.columns.get_loc('Close')] = last_close + np.random.uniform(-last_close*0.0001, last_close*0.0001)
            
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['Hist'] = df['MACD'] - df['Signal']
            df['Sentiment'] = np.random.randint(45, 75)
        return df
    except:
        return pd.DataFrame()

# Live News Engine (Cached for 60 seconds to prevent Yahoo bans)
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
            link_obj = content.get("clickThroughUrl", content.get("canonicalUrl", {}))
            link = link_obj.get("url", content.get("url", "#"))
            provider_obj = content.get("provider", {})
            publisher = provider_obj.get("displayName", content.get("publisher", "Global Wire"))
            
            formatted_news.append({"title": title, "link": link, "publisher": publisher})
        return formatted_news
    except:
        return []

# --- 5. SIDEBAR (Static outside the refresh zone) ---
with st.sidebar:
    st.title("🇿🇲 ZM Elite Menu")
    asset_class = st.selectbox("Category", list(ASSETS.keys()))
    asset_name = st.selectbox("Asset", list(ASSETS[asset_class].keys()))
    ticker = ASSETS[asset_class][asset_name]
    t_frame = st.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"], index=0)

# Fetch Data for Sidebar Execution
df_static = fetch_elite_data(ticker, t_frame)
current_price_static = float(df_static['Close'].iloc[-1]) if not df_static.empty else 0.0

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
    if c1.button("📈 CALL", use_container_width=True, disabled=(curr_bal < 10 or current_price_static == 0)):
        st.session_state.balance -= amount
        st.session_state.active_trades.append({"id": int(time.time()), "asset": asset_name, "type": "CALL", "amount": amount, "entry": current_price_static})
        st.rerun() # Full refresh only when a trade is placed
        
    if c2.button("📉 PUT", use_container_width=True, disabled=(curr_bal < 10 or current_price_static == 0)):
        st.session_state.balance -= amount
        st.session_state.active_trades.append({"id": int(time.time()), "asset": asset_name, "type": "PUT", "amount": amount, "entry": current_price_static})
        st.rerun()

    if st.button("🔄 Reset Demo Funds", use_container_width=True):
        st.session_state.balance = 50000.00
        st.session_state.active_trades = []
        st.rerun()

# --- 6. THE "NO-BLINK" LIVE FRAGMENT ZONE ---
# This special decorator tells the app to ONLY refresh this specific box every 3 seconds
@st.fragment(run_every=3)
def render_live_dashboard():
    # Fetch fresh data quietly in the background
    df = fetch_elite_data(ticker, t_frame)
    current_price = float(df['Close'].iloc[-1]) if not df.empty else 0.0
    
    main_col, side_col = st.columns([3, 1])

    with main_col:
        if not df.empty:
            st.metric(f"Live {asset_name}", f"{current_price:,.4f}")

            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
            
            if chart_style == "Candlesticks (Pro)":
                fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price", increasing_line_color='#00ffbb', decreasing_line_color='#ff3355'), row=1, col=1)
            else:
                fig.add_trace(go.Scatter(x=df.index, y=df['Close'], line=dict(color='#00ffbb', width=2), name="Price"), row=1, col=1)
            
            if show_sma:
                fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='#ff9900', width=1.5), name="SMA 20"), row=1, col=1)
            
            fig.add_trace(go.Bar(x=df.index, y=df['Hist'], name="Momentum", marker_color='rgba(200, 200, 200, 0.3)'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='#00ffbb', width=1.2), name="MACD"), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], line=dict(color='#ff3355', width=1.2), name="Signal"), row=2, col=1)

            fig.update_layout(
                template="plotly_dark", xaxis_rangeslider_visible=False, height=600, 
                paper_bgcolor="#0b0e11", plot_bgcolor="#0b0e11", margin=dict(t=0, b=10, l=0, r=0),
                yaxis=dict(side="right", autorange=True, fixedrange=False), 
                yaxis2=dict(side="right", autorange=True, fixedrange=False),
                showlegend=False, dragmode='pan' 
            )
            
            pro_config = {'displayModeBar': True, 'scrollZoom': True, 'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape']}
            st.plotly_chart(fig, use_container_width=True, config=pro_config)
        else:
            st.warning("Connecting to global liquidity feed... please wait.")

        # ACTIVE TRADES TABLE (Updates silently)
        st.divider()
        st.subheader("📋 Active Positions")
        if len(st.session_state.active_trades) == 0:
            st.info("No open trades.")
        else:
            t_cols = st.columns([1.5, 1, 1, 1, 1.5, 1])
            t_cols[0].write("**Asset**")
            t_cols[1].write("**Type**")
            t_cols[2].write("**Invested**")
            t_cols[3].write("**Entry**")
            t_cols[4].write("**Live PnL**")
            
            for trade in st.session_state.active_trades:
                live_price = current_price if trade['asset'] == asset_name else trade['entry'] * (1 + np.random.uniform(-0.0005, 0.0005))
                pnl = ((live_price - trade['entry']) / trade['entry']) * trade['amount'] * 50 if trade['type'] == "CALL" else ((trade['entry'] - live_price) / trade['entry']) * trade['amount'] * 50

                t_col = st.columns([1.5, 1, 1, 1, 1.5, 1])
                t_col[0].write(trade['asset'])
                t_col[1].markdown(f"<strong style='color:{'#00ffbb' if trade['type'] == 'CALL' else '#ff3355'}'>{trade['type']}</strong>", unsafe_allow_html=True)
                t_col[2].write(f"{trade['amount']:,.2f}")
                t_col[3].write(f"{trade['entry']:.4f}")
                t_col[4].markdown(f"<strong style='color:{'#00ffbb' if pnl >= 0 else '#ff3355'}'>{pnl:+,.2f} ZMW</strong>", unsafe_allow_html=True)
                if t_col[5].button("✖ Close", key=f"close_{trade['id']}"):
                    st.session_state.balance += (trade['amount'] + pnl)
                    st.session_state.active_trades.remove(trade)
                    st.rerun()

    with side_col:
        st.subheader("📊 Gauge")
        s_val = df['Sentiment'].iloc[-1] if not df.empty else 50
        st.progress(int(s_val))
        st.write(f"Buyers: **{s_val}%** | Sellers: **{100-s_val}%**")
        
        st.divider()
        st.subheader("📖 Order Book (L2)")
        if current_price > 0:
            st.markdown(f"<div class='order-book-row ask'><span>{current_price * 1.0003:.4f}</span><span>{np.random.randint(10, 500)}</span></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='order-book-row ask'><span>{current_price * 1.0002:.4f}</span><span>{np.random.randint(10, 500)}</span></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='order-book-row ask'><span>{current_price * 1.0001:.4f}</span><span>{np.random.randint(10, 500)}</span></div>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align:center; font-weight:bold; margin: 5px 0;'>{current_price:.4f}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='order-book-row bid'><span>{current_price * 0.9999:.4f}</span><span>{np.random.randint(10, 500)}</span></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='order-book-row bid'><span>{current_price * 0.9998:.4f}</span><span>{np.random.randint(10, 500)}</span></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='order-book-row bid'><span>{current_price * 0.9997:.4f}</span><span>{np.random.randint(10, 500)}</span></div>", unsafe_allow_html=True)

        st.divider()
        st.subheader("🏆 Leaderboard")
        st.metric("Wallet Balance", f"{st.session_state.balance:,.2f} ZMW")
        st.caption("🥇 **Kapiri_King** (+120%)")
        st.caption("🥈 **Lsk_Bull** (+85%)")

# Execute the live fragment
render_live_dashboard()

# --- 7. STATIC NEWS FEED (Outside the refresh zone so links don't move while reading) ---
st.divider()
st.subheader("📰 Live Market News")
live_news = fetch_live_news(ticker)

if live_news:
    for article in live_news:
        st.markdown(f"**[{article['title']}]({article['link']})**")
        st.caption(f"Source: {article['publisher']}")
        st.write("---")
else:
    st.warning("🇿🇲 **09:00** - [Bank of Zambia Rate Decision](https://www.boz.zm/)")
    st.info("🇺🇸 **14:30** - [Fed Inflation Data Released](https://www.federalreserve.gov/)")
