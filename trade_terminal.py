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

# --- 1. PRO UI CONFIGURATION (ZERO-SCROLL EDITION) ---
st.set_page_config(
    layout="wide", 
    page_title="ZM Elite Terminal", 
    page_icon="💹", 
    initial_sidebar_state="expanded",
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}
)

st.markdown("""
    <style>
    /* Compress the app padding for Zero-Scroll, leaving exactly 3.5rem at the top for the arrow */
    .stApp { background-color: #0b0e11; color: white; }
    .block-container { padding-top: 3.5rem !important; padding-bottom: 0rem !important; max-width: 100% !important; }
    
    /* 🔥 THE BULLETPROOF HIDE: Use 'visibility: hidden' so the structural flexbox doesn't collapse 🔥 */
    [data-testid="stToolbar"] { visibility: hidden !important; }
    .stAppDeployButton { display: none !important; }
    header { background: transparent !important; }
    
    /* 🔥 THE ARROW LIFESAVER: Targets all known Streamlit IDs to force the arrow to stay visible 🔥 */
    [data-testid="collapsedControl"], [data-testid="stSidebarCollapsedControl"] { 
        display: flex !important; 
        visibility: visible !important; 
        color: #00ffbb !important; 
        z-index: 99999 !important; 
    }
    
    div[data-testid="stMetricValue"] { font-size: 1.5rem; color: #00ffbb; }
    .stProgress > div > div > div > div { background-color: #00ffbb; }
    
    /* Custom Green and Red Call/Put Buttons */
    div[data-testid="stSidebar"] div[data-testid="column"]:nth-of-type(1) button { background-color: #00ffbb !important; color: black !important; font-weight: bold; border: none; }
    div[data-testid="stSidebar"] div[data-testid="column"]:nth-of-type(2) button { background-color: #ff3355 !important; color: white !important; font-weight: bold; border: none; }
    
    /* Order Book & Ticker Styling */
    .order-book-row { display: flex; justify-content: space-between; font-family: monospace; font-size: 0.85rem; padding: 2px 0; }
    .bid { color: #00ffbb; }
    .ask { color: #ff3355; }
    .live-ticker { font-size: 1.8rem; font-weight: bold; color: #00ffbb; font-family: monospace; margin-bottom: -15px; margin-top: -10px;}
    
    /* Sleek Tab Styling */
    .stTabs [data-baseweb="tab-list"] { background-color: transparent; }
    .stTabs [data-baseweb="tab"] { color: #a1a5b0; font-weight: bold; font-size: 0.85rem; }
    .stTabs [aria-selected="true"] { color: #00ffbb !important; }
    
    a { color: #00ffbb !important; text-decoration: none; }
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
FLAT_ASSETS = {name: ticker for category, assets in ASSETS.items() for name, ticker in assets.items()}

# --- 3. SESSION STATE ---
if 'balance' not in st.session_state: st.session_state.balance = 50000.00
if 'active_trades' not in st.session_state: st.session_state.active_trades = []
if 'acknowledged' not in st.session_state: st.session_state.acknowledged = False

# --- 4. SEC COMPLIANCE GATEWAY ---
if not st.session_state.acknowledged:
    st.markdown("<br><br><h1 style='text-align: center; color: #00ffbb;'>🇿🇲 ZM Elite Terminal</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: white;'>SEC Zambia Regulatory Sandbox</h3>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color: #333;'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.warning("⚠️ **High-Risk Financial Instrument Warning**")
        st.info("This platform is operating under the SEC Zambia Sandbox Framework. Trading involves significant risk to capital.")
        st.markdown("""<style>div.stButton > button { background-color: #00ffbb; color: black; font-weight: bold; width: 100%; border: none; padding: 15px; }</style>""", unsafe_allow_html=True)
        if st.button("I AGREE & ENTER TERMINAL"):
            st.session_state.acknowledged = True
            st.rerun()
    st.stop()

# --- 5. DATA ENGINES WITH HEIKIN-ASHI & ATR MATH ---
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
            
            # KVB
            df['KVB_Mid'] = df['Close'].rolling(window=20).mean()
            df['KVB_Std'] = df['Close'].rolling(window=20).std()
            df['KVB_Upper'] = df['KVB_Mid'] + (df['KVB_Std'] * 2.5)
            df['KVB_Lower'] = df['KVB_Mid'] - (df['KVB_Std'] * 2.5)
            
            # ZEMO
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi_raw = 100 - (100 / (1 + rs))
            df['ZEMO'] = rsi_raw.ewm(span=5, adjust=False).mean()
            
            # ATR
            df['TR'] = np.maximum((df['High'] - df['Low']), np.maximum(abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))))
            df['ATR'] = df['TR'].rolling(window=14).mean()
            
            # Heikin-Ashi
            df['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
            ha_o = [(df['Open'].iloc[0] + df['Close'].iloc[0]) / 2]
            for i in range(1, len(df)): ha_o.append((ha_o[i-1] + df['HA_Close'].iloc[i-1]) / 2)
            df['HA_Open'] = ha_o
            df['HA_High'] = df[['High', 'HA_Open', 'HA_Close']].max(axis=1)
            df['HA_Low'] = df[['Low', 'HA_Open', 'HA_Close']].min(axis=1)
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
        for item in news_data[:10]: 
            content = item.get("content", item)
            formatted_news.append({"title": content.get("title", "Market Update"), "link": content.get("clickThroughUrl", content.get("canonicalUrl", {})).get("url", "#"), "publisher": content.get("provider", {}).get("displayName", "Global Wire")})
        return formatted_news
    except:
        return []

@st.cache_data
def convert_df(df):
    return df.to_csv(index=True).encode('utf-8')

# --- 6. SIDEBAR MENU & EXECUTION ---
with st.sidebar:
    st.markdown("<h2 style='margin-top:-20px;'>🇿🇲 ZM Elite</h2>", unsafe_allow_html=True)
    asset_class = st.selectbox("Category", list(ASSETS.keys()), label_visibility="collapsed")
    asset_name = st.selectbox("Asset", list(ASSETS[asset_class].keys()), label_visibility="collapsed")
    ticker = ASSETS[asset_class][asset_name]
    t_frame = st.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"], index=0, label_visibility="collapsed")

base_price = fetch_live_price(ticker)

with st.sidebar:
    st.markdown("<br>", unsafe_allow_html=True)
    chart_style = st.selectbox("Chart Style", ["Candlesticks", "Heikin-Ashi", "OHLC Bars", "Line"])
    
    # Chart Toggles
    c_vol, c_sma = st.columns(2)
    show_volume = c_vol.checkbox("Show Volume", value=False)
    show_sma = c_sma.checkbox("Show SMA 20", value=False)
    
    c_fib, c_pred = st.columns(2)
    show_fib = c_fib.checkbox("Auto-Fibonacci", value=False)
    show_ai_pred = c_pred.checkbox("AI Projection", value=True)
    
    show_kvb = st.checkbox("Kwacha Volatility Bands (KVB)", value=False)
    bottom_osc = st.selectbox("Lower Panel:", ["MACD", "ZEMO", "ATR (Volatility)"])
    
    st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
    curr_bal = float(st.session_state.balance)
    st.metric("Balance", f"ZMW {curr_bal:,.2f}")
    
    if curr_bal < 10.0:
        amount = 0.0
    else:
        amount = st.number_input("Investment", min_value=10.0, max_value=max(10.0, curr_bal), value=min(1000.0, curr_bal))
    
    c1, c2 = st.columns(2)
    if c1.button("📈 CALL", use_container_width=True, disabled=(curr_bal < 10 or base_price == 0)):
        st.session_state.balance -= amount
        st.session_state.active_trades.append({"id": int(time.time()), "asset": asset_name, "type": "CALL", "amount": amount, "entry": base_price})
        st.rerun()
    if c2.button("📉 PUT", use_container_width=True, disabled=(curr_bal < 10 or base_price == 0)):
        st.session_state.balance -= amount
        st.session_state.active_trades.append({"id": int(time.time()), "asset": asset_name, "type": "PUT", "amount": amount, "entry": base_price})
        st.rerun()

    if st.button("🔄 Reset Funds", use_container_width=True):
        st.session_state.balance = 50000.00
        st.session_state.active_trades = []
        st.rerun()

    st.divider()
    with st.expander("🤖 AI Sentiment Scanner"):
        news_pool = fetch_live_news(ticker)
        if news_pool:
            score = 50 
            for article in news_pool:
                title_lower = article['title'].lower()
                for pw in ['surge', 'jump', 'bull', 'high', 'buy', 'up', 'soar', 'win']:
                    if pw in title_lower: score += 8
                for nw in ['drop', 'fall', 'bear', 'low', 'sell', 'down', 'crash', 'risk']:
                    if nw in title_lower: score -= 8
            score = max(0, min(100, score)) 
            sent_label = "🟢 BULLISH" if score >= 60 else "🔴 BEARISH" if score <= 40 else "⚪ NEUTRAL"
            sent_color = "#00ffbb" if score >= 60 else "#ff3355" if score <= 40 else "#a1a5b0"
            st.markdown(f"<h3 style='text-align: center; color: {sent_color};'>{score}%</h3>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align: center; font-weight: bold; color: {sent_color};'>{sent_label}</div>", unsafe_allow_html=True)
            st.progress(score / 100.0)
        else:
            st.info("Insufficient news data.")

    with st.expander("💽 Data & Export Center"):
        st.caption("Export raw market data for Excel/Python backtesting.")
        export_df = fetch_chart_data(ticker, t_frame)
        if not export_df.empty:
            clean_df = export_df[['Open', 'High', 'Low', 'Close', 'Volume']] if 'Volume' in export_df.columns else export_df[['Open', 'High', 'Low', 'Close']]
            csv_data = convert_df(clean_df)
            st.download_button(label=f"📥 Download {ticker} Data", data=csv_data, file_name=f"{ticker}_{t_frame}_MarketData.csv", mime='text/csv', use_container_width=True)
        
        if len(st.session_state.active_trades) > 0:
            ledger_df = pd.DataFrame(st.session_state.active_trades)
            ledger_csv = ledger_df.to_csv(index=False).encode('utf-8')
            st.download_button(label="🧾 Download My Trades", data=ledger_csv, file_name="Trade_Ledger.csv", mime='text/csv', use_container_width=True)

    with st.expander("💳 Local Deposit Portal"):
        st.radio("Network", ["MTN MoMo", "Airtel Money", "ZANACO App"])
        st.text_input("Zambian Number")
        st.button("Request USSD Push")
        
    with st.expander("🎧 Priority Support"):
        st.text_area("Issue description...")
        st.button("Open Ticket")

# --- 7. MAIN DASHBOARD ---
@st.fragment(run_every=2)
def render_live_ticker():
    live_p = fetch_live_price(ticker) * (1 + np.random.uniform(-0.0001, 0.0001))
    st.markdown(f"<div class='live-ticker'>{asset_name} &nbsp;&nbsp; <span style='color:white;'>{live_p:,.4f}</span></div>", unsafe_allow_html=True)
render_live_ticker()

st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

main_col, side_col = st.columns([2.5, 1])

with main_col:
    df = fetch_chart_data(ticker, t_frame)
    if not df.empty:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25], specs=[[{"secondary_y": True}], [{"secondary_y": False}]])
        
        # Plot Charts
        if chart_style == "Candlesticks":
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price", increasing_line_color='#00ffbb', decreasing_line_color='#ff3355'), row=1, col=1, secondary_y=False)
        elif chart_style == "Heikin-Ashi":
            fig.add_trace(go.Candlestick(x=df.index, open=df['HA_Open'], high=df['HA_High'], low=df['HA_Low'], close=df['HA_Close'], name="Price", increasing_line_color='#00ffbb', decreasing_line_color='#ff3355'), row=1, col=1, secondary_y=False)
        elif chart_style == "OHLC Bars":
            fig.add_trace(go.Ohlc(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price", increasing_line_color='#00ffbb', decreasing_line_color='#ff3355'), row=1, col=1, secondary_y=False)
        else:
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], line=dict(color='#00ffbb', width=2), name="Price"), row=1, col=1, secondary_y=False)
        
        # AI Forecast
        if show_ai_pred and len(df) > 10:
            last_idx = df.index[-1]
            last_val = df['Close'].iloc[-1]
            avg_move = df['Close'].diff().tail(10).mean()
            delta = df.index[-1] - df.index[-2]
            future_idx = [last_idx + (delta * i) for i in range(1, 16)]
            future_vals = [last_val + (avg_move * i) for i in range(1, 16)]
            fig.add_trace(go.Scatter(x=[last_idx] + future_idx, y=[last_val] + future_vals, line=dict(color='#ff9900', width=2, dash='dot'), name="AI Forecast"), row=1, col=1)

        # Auto-Fibonacci
        if show_fib:
            max_p, min_p = df['High'].max(), df['Low'].min()
            diff = max_p - min_p
            for lvl, color in zip([0.236, 0.382, 0.5, 0.618], ['#33ff33', '#ffff33', '#ff9933', '#ff3333']):
                val = max_p - (diff * lvl)
                fig.add_hline(y=val, line_dash="dash", line_color=color, opacity=0.5, annotation_text=f"Fib {lvl}", annotation_position="top left", row=1, col=1)

        # Overlays
        if show_sma:
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='#ff9900', width=1.5), name="SMA 20"), row=1, col=1, secondary_y=False)
            
        if show_kvb:
            fig.add_trace(go.Scatter(x=df.index, y=df['KVB_Upper'], line=dict(color='rgba(255, 51, 85, 0.5)', width=1, dash='dot'), name="KVB Upper"), row=1, col=1, secondary_y=False)
            fig.add_trace(go.Scatter(x=df.index, y=df['KVB_Lower'], line=dict(color='rgba(0, 255, 187, 0.5)', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(0, 255, 187, 0.05)', name="KVB Lower"), row=1, col=1, secondary_y=False)
            
        if show_volume and 'Volume' in df.columns:
            vol_colors = ['rgba(0, 255, 187, 0.4)' if row['Close'] >= row['Open'] else 'rgba(255, 51, 85, 0.4)' for index, row in df.iterrows()]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_colors, name="Volume"), row=1, col=1, secondary_y=True)
            fig.update_yaxes(range=[0, df['Volume'].max() * 4], showticklabels=False, showgrid=False, secondary_y=True, row=1, col=1)
        
        # Lower Panel
        if bottom_osc == "MACD":
            fig.add_trace(go.Bar(x=df.index, y=df['Hist'], name="Momentum", marker_color='rgba(200, 200, 200, 0.3)'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='#00ffbb', width=1.2), name="MACD"), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], line=dict(color='#ff3355', width=1.2), name="Signal"), row=2, col=1)
        elif bottom_osc == "ZEMO":
            fig.add_trace(go.Scatter(x=df.index, y=df['ZEMO'], line=dict(color='#00ffbb', width=2), name="ZEMO"), row=2, col=1)
            fig.add_hline(y=80, line_dash="dot", line_color="#ff3355", row=2, col=1)
            fig.add_hline(y=20, line_dash="dot", line_color="#00ffbb", row=2, col=1)
            fig.update_yaxes(range=[0, 100], row=2, col=1)
        elif bottom_osc == "ATR (Volatility)":
            fig.add_trace(go.Scatter(x=df.index, y=df['ATR'], line=dict(color='#ff9900', width=2), name="ATR"), row=2, col=1)

        fig.update_layout(
            template="plotly_dark", xaxis_rangeslider_visible=False, height=500, 
            paper_bgcolor="#0b0e11", plot_bgcolor="#0b0e11", margin=dict(t=0, b=0, l=0, r=0),
            yaxis=dict(side="right", autorange=True, fixedrange=False), 
            yaxis2=dict(side="right", autorange=True, fixedrange=False),
            showlegend=False, dragmode='pan', barmode='group'
        )
        
        pro_config = {
            'displayModeBar': True, 
            'scrollZoom': True, 
            'displaylogo': False,
            'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape']
        }
        st.plotly_chart(fig, use_container_width=True, config=pro_config)
    else:
        st.warning("Awaiting market data connection...")

with side_col:
    # ALL TABS RE-INTEGRATED
    tab_pos, tab_soc, tab_grid, tab_ob, tab_news = st.tabs(["Positions", "Social", "Grid", "L2 Data", "News"])

    with tab_pos:
        @st.fragment(run_every=2)
        def render_positions():
            if len(st.session_state.active_trades) == 0:
                st.info("No open trades.")
            else:
                live_p = fetch_live_price(ticker) * (1 + np.random.uniform(-0.0001, 0.0001))
                for trade in st.session_state.active_trades:
                    sim_price = live_p if trade['asset'] == asset_name else trade['entry'] * (1 + np.random.uniform(-0.0005, 0.0005))
                    pnl = ((sim_price - trade['entry']) / trade['entry']) * trade['amount'] * 50 if trade['type'] == "CALL" else ((trade['entry'] - sim_price) / trade['entry']) * trade['amount'] * 50
                    
                    st.markdown(f"**{trade['asset']}** (<span style='color:{'#00ffbb' if trade['type'] == 'CALL' else '#ff3355'}'>{trade['type']}</span>)", unsafe_allow_html=True)
                    st.write(f"PnL: **{pnl:+,.2f} ZMW**")
                    if st.button("Close", key=f"close_{trade['id']}", use_container_width=True):
                        st.session_state.balance += (trade['amount'] + pnl)
                        st.session_state.active_trades.remove(trade)
                        st.rerun() 
                    st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
        render_positions()
        
    with tab_soc:
        st.markdown("<h4 style='color:#00ffbb;'>Top Traders (24h)</h4>", unsafe_allow_html=True)
        st.markdown("**1. Kapiri_King** | Win Rate: 82%")
        st.caption("Current Position: CALL on BTC")
        st.button("Auto-Copy 🤖", key="copy1", use_container_width=True)
        st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
        
        st.markdown("**2. Lsk_Bull** | Win Rate: 76%")
        st.caption("Current Position: PUT on NVDA")
        st.button("Auto-Copy 🤖", key="copy2", use_container_width=True)
        st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)

    with tab_grid:
        grid_tickers = st.multiselect("Select up to 2 assets:", list(FLAT_ASSETS.keys()), max_selections=2, label_visibility="collapsed")
        if grid_tickers:
            for asset_key in grid_tickers:
                st.markdown(f"<div style='text-align: center; color: #00ffbb; font-weight: bold; font-size: 0.9rem;'>{asset_key}</div>", unsafe_allow_html=True)
                gdf = fetch_chart_data(FLAT_ASSETS[asset_key], t_frame)
                if not gdf.empty:
                    gfig = go.Figure(data=[go.Candlestick(x=gdf.index, open=gdf['Open'], high=gdf['High'], low=gdf['Low'], close=gdf['Close'], increasing_line_color='#00ffbb', decreasing_line_color='#ff3355')])
                    gfig.update_layout(template="plotly_dark", height=150, margin=dict(t=0, b=0, l=0, r=0), paper_bgcolor="#0b0e11", plot_bgcolor="#0b0e11", xaxis_rangeslider_visible=False, showlegend=False)
                    st.plotly_chart(gfig, use_container_width=True, config={'displayModeBar': False})

    with tab_ob:
        @st.fragment(run_every=2)
        def render_order_book():
            sentiment = np.random.randint(45, 75)
            st.progress(int(sentiment))
            st.caption(f"Buyers: {sentiment}% | Sellers: {100-sentiment}%")
            
            cp = fetch_live_price(ticker)
            if cp > 0:
                cp = cp * (1 + np.random.uniform(-0.0001, 0.0001))
                st.markdown(f"<div class='order-book-row ask'><span>{cp * 1.0003:.4f}</span><span>{np.random.randint(10, 500)}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='order-book-row ask'><span>{cp * 1.0002:.4f}</span><span>{np.random.randint(10, 500)}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='order-book-row ask'><span>{cp * 1.0001:.4f}</span><span>{np.random.randint(10, 500)}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:center; font-weight:bold; margin: 10px 0; color:#fff;'>Spread: 0.0001</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='order-book-row bid'><span>{cp * 0.9999:.4f}</span><span>{np.random.randint(10, 500)}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='order-book-row bid'><span>{cp * 0.9998:.4f}</span><span>{np.random.randint(10, 500)}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='order-book-row bid'><span>{cp * 0.9997:.4f}</span><span>{np.random.randint(10, 500)}</span></div>", unsafe_allow_html=True)
        render_order_book()

    with tab_news:
        live_news = fetch_live_news(ticker)
        if live_news:
            for article in live_news[:4]:
                st.markdown(f"[{article['title']}]({article['link']})")
                st.caption(f"{article['publisher']}")
                st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
