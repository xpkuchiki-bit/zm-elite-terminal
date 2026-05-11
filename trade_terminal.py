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

# Custom CSS for Elite Styling (Including Call/Put Button Colors)
st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: white; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #00ffbb; }
    .stProgress > div > div > div > div { background-color: #00ffbb; }
    
    /* Target the CALL and PUT buttons specifically to make them Green and Red */
    div[data-testid="stSidebar"] div[data-testid="column"]:nth-of-type(1) button { background-color: #00ffbb !important; color: black !important; font-weight: bold; border: none; }
    div[data-testid="stSidebar"] div[data-testid="column"]:nth-of-type(2) button { background-color: #ff3355 !important; color: white !important; font-weight: bold; border: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE COMPLETE ASSET DICTIONARY ---
ASSETS = {
    "Crypto": {"Bitcoin (BTC)": "BTC-USD", "Ethereum (ETH)": "ETH-USD", "Solana (SOL)": "SOL-USD", "Ripple (XRP)": "XRP-USD", "Dogecoin (DOGE)": "DOGE-USD"},
    "Forex": {"USD/ZMW (Kwacha)": "ZMW=X", "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X", "AUD/USD": "AUDUSD=X"},
    "Stocks": {"Nvidia (NVDA)": "NVDA", "Tesla (TSLA)": "TSLA", "Apple (AAPL)": "AAPL", "Microsoft (MSFT)": "MSFT", "Amazon (AMZN)": "AMZN"},
    "Commodities": {"Gold": "GC=F", "Silver": "SI=F", "Brent Crude": "BZ=F", "Copper": "HG=F"},
    "Indices & ETFs": {"S&P 500": "^GSPC", "Nasdaq 100": "^IXIC", "Bitcoin ETF (IBIT)": "IBIT"}
}

# --- 3. SESSION STATE ---
if 'balance' not in st.session_state: st.session_state.balance = 50000.00
if 'active_trades' not in st.session_state: st.session_state.active_trades = []
if 'acknowledged' not in st.session_state: st.session_state.acknowledged = False

# --- 4. SEC COMPLIANCE DIALOG (Restored Feature) ---
if not st.session_state.acknowledged:
    @st.dialog("🇿🇲 SEC Zambia Regulatory Portal")
    def auth_dialog():
        st.warning("High-Risk Financial Instrument Warning")
        st.write("This platform is operating under the SEC Zambia Sandbox Framework. Trading involves significant risk to capital.")
        if st.button("I AGREE & ENTER TERMINAL", use_container_width=True):
            st.session_state.acknowledged = True
            st.rerun()
    auth_dialog()
    st.stop() # Pauses the app until the user agrees

# --- 5. DATA ENGINE (WITH "FLATTENER" BUG FIX) ---
@st.cache_data(ttl=1)
def fetch_elite_data(symbol, tf):
    try:
        # Determine period based on timeframe
        period = "5d" if tf in ["1m", "5m", "15m"] else "1mo"
        df = yf.download(symbol, period=period, interval=tf, progress=False)
        
        if df.empty: return pd.DataFrame()

        # 🔥 Flatten yfinance's Multi-Index bug so Plotly can read the candles perfectly
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        
        df = df.dropna()
        
        if not df.empty:
            # Live Volatility Pulse
            last_close = float(df['Close'].iloc[-1])
            df.iloc[-1, df.columns.get_loc('Close')] = last_close + np.random.uniform(-last_close*0.0001, last_close*0.0001)
            
            # Technical Indicators
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

# --- FETCH DATA BEFORE SIDEBAR TO GET EXACT ENTRY PRICE ---
with st.sidebar:
    st.title("🇿🇲 ZM Elite Menu")
    asset_class = st.selectbox("Category", list(ASSETS.keys()))
    asset_name = st.selectbox("Asset", list(ASSETS[asset_class].keys()))
    ticker = ASSETS[asset_class][asset_name]
    t_frame = st.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"], index=0)

# Fetch Current Data
df = fetch_elite_data(ticker, t_frame)
current_price = float(df['Close'].iloc[-1]) if not df.empty else 0.0

# --- 6. SIDEBAR: EXECUTION ENGINE ---
with st.sidebar:
    st.divider()
    chart_style = st.radio("View Mode", ["Candlesticks (Pro)", "Line (Simple)"])
    show_sma = st.checkbox("Show SMA 20 Trendline", value=True)
    
    st.divider()
    st.subheader("Order Placement")
    curr_bal = float(st.session_state.balance)
    
    # Anti-Crash Bankrupt Logic
    if curr_bal < 10.0:
        st.error("Bankrupt! Reset below.")
        amount = 0.0
    else:
        amount = st.number_input("Investment (ZMW)", min_value=10.0, max_value=max(10.0, curr_bal), value=min(1000.0, curr_bal))
    
    c1, c2 = st.columns(2)
    # CALL / LONG LOGIC
    if c1.button("📈 CALL", use_container_width=True, disabled=(curr_bal < 10 or current_price == 0)):
        st.session_state.balance -= amount
        trade = {"id": int(time.time()), "asset": asset_name, "type": "CALL", "amount": amount, "entry": current_price}
        st.session_state.active_trades.append(trade)
        st.toast(f"LONG {asset_name} Opened at {current_price:.4f}")

    # PUT / SHORT LOGIC
    if c2.button("📉 PUT", use_container_width=True, disabled=(curr_bal < 10 or current_price == 0)):
        st.session_state.balance -= amount
        trade = {"id": int(time.time()), "asset": asset_name, "type": "PUT", "amount": amount, "entry": current_price}
        st.session_state.active_trades.append(trade)
        st.toast(f"SHORT {asset_name} Opened at {current_price:.4f}")

    if st.button("🔄 Reset Demo Funds (K50k)", use_container_width=True):
        st.session_state.balance = 50000.00
        st.session_state.active_trades = [] # Clears active trades
        st.rerun()

    st.divider()
    
    # Restored Local Deposit Portal
    with st.expander("💳 Local Deposit Portal"):
        st.radio("Network", ["MTN MoMo", "Airtel Money", "ZANACO App"])
        st.text_input("Zambian Number")
        st.button("Request USSD Push")
        
    # Restored Support Portal
    with st.expander("🎧 Priority Support"):
        st.text_area("Issue description...")
        st.button("Open Ticket")

# --- 7. MAIN DASHBOARD ---
main_col, side_col = st.columns([3, 1])

with main_col:
    if not df.empty:
        st.metric(f"Live {asset_name}", f"{current_price:,.4f}")

        # Subplots: Price on top, MACD on bottom
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
        
        # Price Action
        if chart_style == "Candlesticks (Pro)":
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], 
                name="Price", increasing_line_color='#00ffbb', decreasing_line_color='#ff3355'
            ), row=1, col=1)
        else:
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], line=dict(color='#00ffbb', width=2), name="Price"), row=1, col=1)
        
        # SMA Overlay
        if show_sma:
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='#ff9900', width=1.5), name="SMA 20"), row=1, col=1)
        
        # MACD Panel
        fig.add_trace(go.Bar(x=df.index, y=df['Hist'], name="Momentum", marker_color='rgba(200, 200, 200, 0.3)'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='#00ffbb', width=1.2), name="MACD"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], line=dict(color='#ff3355', width=1.2), name="Signal"), row=2, col=1)

        # STRICT AUTO-SCALING
        fig.update_layout(
            template="plotly_dark", xaxis_rangeslider_visible=False, height=600, 
            paper_bgcolor="#0b0e11", plot_bgcolor="#0b0e11", margin=dict(t=0, b=10, l=0, r=0),
            yaxis=dict(side="right", autorange=True, fixedrange=False), 
            yaxis2=dict(side="right", autorange=True, fixedrange=False),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.error(f"Waiting for {asset_name} market data... (If issue persists, market may be closed).")

    # --- ACTIVE TRADES TABLE (Live PnL Engine) ---
    st.divider()
    st.subheader("📋 Active Positions")
    if len(st.session_state.active_trades) == 0:
        st.info("No open trades. Select an asset and click CALL or PUT to enter the market.")
    else:
        # Create table headers
        t_cols = st.columns([1.5, 1, 1, 1, 1.5, 1])
        t_cols[0].write("**Asset**")
        t_cols[1].write("**Type**")
        t_cols[2].write("**Invested**")
        t_cols[3].write("**Entry**")
        t_cols[4].write("**Live PnL**")
        t_cols[5].write("**Action**")

        for trade in st.session_state.active_trades:
            # LIVE PnL MATH (50x Leverage applied)
            if trade['asset'] == asset_name:
                live_price = current_price
            else:
                live_price = trade['entry'] * (1 + np.random.uniform(-0.0005, 0.0005))
            
            if trade['type'] == "CALL":
                pnl = ((live_price - trade['entry']) / trade['entry']) * trade['amount'] * 50
            else:
                pnl = ((trade['entry'] - live_price) / trade['entry']) * trade['amount'] * 50

            # Render Row
            t_col = st.columns([1.5, 1, 1, 1, 1.5, 1])
            t_col[0].write(trade['asset'])
            type_color = "#00ffbb" if trade['type'] == "CALL" else "#ff3355"
            t_col[1].markdown(f"<strong style='color:{type_color}'>{trade['type']}</strong>", unsafe_allow_html=True)
            t_col[2].write(f"{trade['amount']:,.2f}")
            t_col[3].write(f"{trade['entry']:.4f}")
            
            pnl_color = "#00ffbb" if pnl >= 0 else "#ff3355"
            t_col[4].markdown(f"<strong style='color:{pnl_color}'>{pnl:+,.2f} ZMW</strong>", unsafe_allow_html=True)
            
            # Close Trade Logic
            if t_col[5].button("✖ Close", key=f"close_{trade['id']}"):
                st.session_state.balance += (trade['amount'] + pnl) # Return capital + profit/loss
                st.session_state.active_trades.remove(trade)
                st.rerun()

with side_col:
    st.subheader("📊 Sentiment Gauge")
    sentiment_val = df['Sentiment'].iloc[-1] if not df.empty else 50
    st.write(f"Buyers: **{sentiment_val}%** | Sellers: **{100-sentiment_val}%**")
    st.progress(int(sentiment_val))
    
    st.divider()
    st.subheader("🏆 Leaderboard")
    st.metric("Wallet Balance", f"{st.session_state.balance:,.2f} ZMW")
    st.caption("🥇 **Kapiri_King** (+120%)")
    st.caption("🥈 **Lsk_Bull** (+85%)")
    st.caption("🥉 **You (Trader_1)** (Live)")
    
    st.divider()
    st.subheader("📅 Eco Calendar")
    st.warning("🇿🇲 **09:00** - Bank of Zambia Rate")
    st.info("🇺🇸 **14:30** - Fed Inflation Data")

# --- 8. HEARTBEAT ENGINE ---
time.sleep(1)
st.rerun()