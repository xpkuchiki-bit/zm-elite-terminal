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

# --- 1. PRO UI CONFIGURATION (IQ OPTION STYLE) ---
st.set_page_config(layout="wide", page_title="ZM Elite Terminal", page_icon="💹", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Dark Theme Base */
    .stApp { background-color: #1b1e24; color: #a1a5b0; }
    
    /* Hide Default Header/Footer */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Hide the sidebar toggle button to force the single-page look */
    [data-testid="collapsedControl"] { display: none; }
    
    /* Metric & Text Styling */
    div[data-testid="stMetricValue"] { font-size: 1.5rem; color: #ffffff; }
    div[data-testid="stMetricLabel"] { color: #a1a5b0; }
    
    /* IQ Option Style Big Buttons */
    div[data-testid="column"]:nth-of-type(1) button { 
        background-color: #26a69a !important; /* IQ Option Green */
        color: white !important; 
        font-weight: bold; 
        font-size: 1.2rem;
        height: 70px;
        border-radius: 8px;
        border: none;
        width: 100%;
    }
    div[data-testid="column"]:nth-of-type(2) button { 
        background-color: #ef5350 !important; /* IQ Option Red */
        color: white !important; 
        font-weight: bold; 
        font-size: 1.2rem;
        height: 70px;
        border-radius: 8px;
        border: none;
        width: 100%;
    }
    
    /* Sub-tabs styling to look sleek */
    .stTabs [data-baseweb="tab-list"] { background-color: #23272e; border-radius: 8px; padding: 5px; }
    .stTabs [data-baseweb="tab"] { color: #a1a5b0; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; background-color: #313640; border-radius: 5px; }
    
    /* Order Book & Links */
    .bid { color: #26a69a; }
    .ask { color: #ef5350; }
    a { color: #26a69a !important; text-decoration: none; }
    a:hover { text-decoration: underline; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ASSET DICTIONARY ---
ASSETS = {
    "Crypto": {"Bitcoin (BTC)": "BTC-USD", "Ethereum (ETH)": "ETH-USD", "Solana (SOL)": "SOL-USD", "Ripple (XRP)": "XRP-USD"},
    "Forex": {"USD/ZMW (Kwacha)": "ZMW=X", "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X"},
    "Stocks": {"Nvidia (NVDA)": "NVDA", "Tesla (TSLA)": "TSLA", "Apple (AAPL)": "AAPL"},
    "Commodities": {"Gold": "GC=F", "Brent Crude": "BZ=F"},
    "Indices & ETFs": {"S&P 500": "^GSPC", "Nasdaq 100": "^IXIC"}
}

# --- 3. SESSION STATE ---
if 'balance' not in st.session_state: st.session_state.balance = 10000.00
if 'active_trades' not in st.session_state: st.session_state.active_trades = []
if 'acknowledged' not in st.session_state: st.session_state.acknowledged = False

if not st.session_state.acknowledged:
    @st.dialog("🇿🇲 SEC Zambia Regulatory Portal")
    def auth_dialog():
        st.warning("High-Risk Financial Instrument Warning")
        st.write("This platform is operating under the SEC Zambia Sandbox Framework.")
        if st.button("I AGREE & ENTER TERMINAL", use_container_width=True):
            st.session_state.acknowledged = True
            st.rerun()
    auth_dialog()
    st.stop() 

# --- 4. DATA ENGINES ---
@st.cache_data(ttl=60)
def fetch_chart_data(symbol, tf):
    try:
        period = "5d" if tf in ["1m", "5m"] else "1mo"
        df = yf.download(symbol, period=period, interval=tf, progress=False)
        if df.empty: return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        df = df.dropna()
        if not df.empty:
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=2)
def fetch_live_price(symbol):
    try:
        df = yf.download(symbol, period="1d", interval="1m", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        return float(df['Close'].dropna().iloc[-1])
    except:
        return 0.0

@st.cache_data(ttl=60)
def fetch_live_news(symbol):
    try:
        ticker = yf.Ticker(symbol)
        news_data = ticker.news
        if not news_data: news_data = yf.Ticker("^GSPC").news
        formatted_news = []
        for item in news_data[:4]: 
            content = item.get("content", item)
            formatted_news.append({
                "title": content.get("title", "Market Update"),
                "link": content.get("clickThroughUrl", content.get("canonicalUrl", {})).get("url", "#"),
                "publisher": content.get("provider", {}).get("displayName", "Global Wire")
            })
        return formatted_news
    except:
        return []

# --- 5. TOP NAVIGATION BAR (IQ Style) ---
top_col1, top_col2, top_col3, top_col4 = st.columns([1, 2, 6, 2])
with top_col1:
    st.markdown("<h3 style='color: #26a69a; margin-top: 0;'>ZM Elite</h3>", unsafe_allow_html=True)
with top_col2:
    asset_class = st.selectbox("Market", list(ASSETS.keys()), label_visibility="collapsed")
    asset_name = st.selectbox("Asset", list(ASSETS[asset_class].keys()), label_visibility="collapsed")
    ticker = ASSETS[asset_class][asset_name]
with top_col3:
    # Empty space to push balance to the right
    pass
with top_col4:
    st.markdown(f"<div style='text-align: right; color: #26a69a; font-size: 1.5rem; font-weight: bold;'>${st.session_state.balance:,.2f}</div>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: right; font-size: 0.8rem; margin-top: -10px;'>Demo account ⯆</div>", unsafe_allow_html=True)

st.markdown("<hr style='margin: 0.5em 0; border-color: #313640;'>", unsafe_allow_html=True)

# --- 6. MAIN LAYOUT (Chart Left, Exec Right) ---
chart_col, exec_col = st.columns([3.5, 1])
base_price = fetch_live_price(ticker)

with chart_col:
    # Fast Ticker Overlay
    @st.fragment(run_every=2)
    def render_live_ticker():
        live_p = fetch_live_price(ticker) * (1 + np.random.uniform(-0.0001, 0.0001))
        st.markdown(f"**{asset_name}** | Live: <span style='color:#26a69a;'>{live_p:,.4f}</span>", unsafe_allow_html=True)
    render_live_ticker()

    # The Heavy Chart
    t_frame = "1m" # Locked to 1m for day trading feel
    df = fetch_chart_data(ticker, t_frame)
    if not df.empty:
        fig = go.Figure(data=[go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
            increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
        )])
        fig.update_layout(
            template="plotly_dark", height=500, margin=dict(t=10, b=10, l=0, r=0),
            paper_bgcolor="#1b1e24", plot_bgcolor="#1b1e24", 
            xaxis=dict(showgrid=True, gridcolor='#2b303a'),
            yaxis=dict(side="right", showgrid=True, gridcolor='#2b303a'),
            showlegend=False, dragmode='pan',
            xaxis_rangeslider_visible=False
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'scrollZoom': True, 'displaylogo': False})
    
    # --- ALL FEATURES PACKED INTO CLEAN TABS ---
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Active Positions", "📖 Order Book", "📰 Market News", "🏆 Leaderboard"])
    
    with tab1:
        @st.fragment(run_every=2)
        def render_trades():
            if len(st.session_state.active_trades) == 0:
                st.info("No open positions.")
            else:
                for trade in st.session_state.active_trades:
                    live_p = fetch_live_price(ticker) * (1 + np.random.uniform(-0.0001, 0.0001))
                    sim_p = live_p if trade['asset'] == asset_name else trade['entry'] * (1 + np.random.uniform(-0.0005, 0.0005))
                    pnl = ((sim_p - trade['entry']) / trade['entry']) * trade['amount'] * 50 if trade['type'] == "CALL" else ((trade['entry'] - sim_p) / trade['entry']) * trade['amount'] * 50
                    
                    tc1, tc2, tc3, tc4, tc5 = st.columns([2, 1, 1.5, 1.5, 1])
                    tc1.write(trade['asset'])
                    tc2.markdown(f"<strong style='color:{'#26a69a' if trade['type'] == 'CALL' else '#ef5350'}'>{trade['type']}</strong>", unsafe_allow_html=True)
                    tc3.write(f"${trade['amount']:,.2f}")
                    tc4.markdown(f"<strong style='color:{'#26a69a' if pnl >= 0 else '#ef5350'}'>{pnl:+, .2f}</strong>", unsafe_allow_html=True)
                    if tc5.button("Close", key=f"c_{trade['id']}"):
                        st.session_state.balance += (trade['amount'] + pnl)
                        st.session_state.active_trades.remove(trade)
                        st.rerun()
        render_trades()

    with tab2:
        @st.fragment(run_every=2)
        def render_order_book():
            cp = fetch_live_price(ticker)
            if cp > 0:
                cp = cp * (1 + np.random.uniform(-0.0001, 0.0001))
                st.markdown(f"<div class='order-book-row ask'><span>{cp * 1.0003:.4f}</span><span>{np.random.randint(10, 500)}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='order-book-row ask'><span>{cp * 1.0002:.4f}</span><span>{np.random.randint(10, 500)}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='margin: 5px 0; color:#fff;'>Spread: 0.0001</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='order-book-row bid'><span>{cp * 0.9999:.4f}</span><span>{np.random.randint(10, 500)}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='order-book-row bid'><span>{cp * 0.9998:.4f}</span><span>{np.random.randint(10, 500)}</span></div>", unsafe_allow_html=True)
        render_order_book()
        
    with tab3:
        live_news = fetch_live_news(ticker)
        for article in live_news:
            st.markdown(f"**[{article['title']}]({article['link']})** - *{article['publisher']}*")

    with tab4:
        st.write("🥇 **Kapiri_King** (+120%)")
        st.write("🥈 **Lsk_Bull** (+85%)")

with exec_col:
    st.markdown("<div style='background-color: #23272e; padding: 20px; border-radius: 10px; height: 500px;'>", unsafe_allow_html=True)
    
    st.caption("Time")
    st.selectbox("Expiry", ["1 Minute", "5 Minutes", "15 Minutes"], label_visibility="collapsed")
    
    st.caption("Amount ($)")
    curr_bal = float(st.session_state.balance)
    amount = st.number_input("Invest", min_value=1.0, max_value=max(1.0, curr_bal), value=min(10.0, curr_bal), label_visibility="collapsed")
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center; color: #a1a5b0;'>Expected return</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align: center; color: #26a69a; font-weight: bold; font-size: 1.2rem;'>+${(amount * 0.87):.2f} (87%)</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    b_col1, b_col2 = st.columns(2)
    if b_col1.button("Higher ↗", disabled=(curr_bal < 1 or base_price == 0)):
        st.session_state.balance -= amount
        st.session_state.active_trades.append({"id": int(time.time()), "asset": asset_name, "type": "CALL", "amount": amount, "entry": base_price})
        st.rerun()
        
    if b_col2.button("Lower ↘", disabled=(curr_bal < 1 or base_price == 0)):
        st.session_state.balance -= amount
        st.session_state.active_trades.append({"id": int(time.time()), "asset": asset_name, "type": "PUT", "amount": amount, "entry": base_price})
        st.rerun()
        
    st.markdown("</div>", unsafe_allow_html=True)
