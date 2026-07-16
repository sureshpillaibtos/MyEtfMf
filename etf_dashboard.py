import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# Page Configuration
#st.set_page_config(page_title="Global ETF Smart Dashboard", layout="wide")

st.title("🛡️ Strategic ETF Analytics & Smart Alerts")
st.markdown("Automated algorithmic rules tracking macro dips and peak-value exhaustion.")
st.divider()

# ETF Database Dictionary
etf_dict = {
    "Core Indian ETFs": {
        "Nippon India Nifty 50 BeES": "NIFTYBEES.NS",
        "Nippon India Nifty Next 50 Junior BeES": "JUNIORBEES.NS",
        "Nippon India ETF Nifty Midcap 150": "MID150BEES.NS"
    },
    "Japan Allocation (US/Global Listed)": {
        "iShares MSCI Japan ETF (Broad Exposure)": "EWJ",
        "WisdomTree Japan Hedged Equity Fund": "DXJ"
    }
}

# Sidebar Navigation
st.sidebar.header("🔧 Dashboard Configuration")
category = st.sidebar.selectbox("Select Portfolio Core", list(etf_dict.keys()))
selected_etf_name = st.sidebar.selectbox("Select ETF", list(etf_dict[category].keys()))
ticker = etf_dict[category][selected_etf_name]

time_horizon = st.sidebar.selectbox(
    "Select Time Period", 
    ["1 Month", "6 Months", "1 Year", "3 Years", "5 Years", "Maximum"],
    index=2
)

period_mapping = {
    "1 Month": "1mo", "6 Months": "6mo", "1 Year": "1y", 
    "3 Years": "3y", "5 Years": "5y", "Maximum": "max"
}
selected_period = period_mapping[time_horizon]

# Helper function to compute standard 14-day RSI
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10) # preventing division by zero
    return 100 - (100 / (1 + rs))

# Fetching Data safely
@st.cache_data(ttl=3600)
def load_data(ticker_symbol, period):
    ticker_obj = yf.Ticker(ticker_symbol)
    # Pull maximum needed context to establish long-term peaks accurately
    hist = ticker_obj.history(period="max" if period in ["3y", "5y", "max"] else "1y")
    
    try:
        currency = ticker_obj.history_metadata.get('currency', 'USD')
    except Exception:
        currency = 'INR' if '.NS' in ticker_symbol else 'USD'
        
    return hist, currency

try:
    with st.spinner(f"Fetching real-time data for {ticker}..."):
        raw_df, currency = load_data(ticker, selected_period)

    if not raw_df.empty:
        raw_df = raw_df.dropna(subset=['Close'])
        
        # 1. Technical Analysis Engineering
        raw_df['RSI'] = calculate_rsi(raw_df['Close'], period=14)
        
        # Define 252 trading days (~1 Year) rolling peak high
        raw_df['Rolling_High'] = raw_df['Close'].rolling(window=252, min_periods=1).max()
        raw_df['Drawdown_Pct'] = ((raw_df['Close'] - raw_df['Rolling_High']) / raw_df['Rolling_High']) * 100
        
        # Filter dataframe rows to map user requested visual window
        # (This keeps indicator math precise relative to long term history)
        if selected_period != 'max':
            delta_map = {"1mo": 30, "6mo": 180, "1y": 365, "3y": 1095, "5y": 1825}
            days_to_keep = delta_map.get(selected_period, 365)
            df = raw_df.tail(days_to_keep).copy()
        else:
            df = raw_df.copy()

        # Target absolute current data metrics
        current_price = float(df['Close'].iloc[-1])
        current_rsi = float(df['RSI'].iloc[-1])
        current_drawdown = float(df['Drawdown_Pct'].iloc[-1])
        all_time_high = float(raw_df['Close'].max())
        
        previous_close = float(df['Close'].iloc[0]) if len(df) > 1 else current_price
        price_change = current_price - previous_close
        pct_change = (price_change / previous_close) * 100

        # 2. Smart Engine Automated Alerts Box
        st.subheader("🚨 Real-Time System Signals")
        
        # Alert logic evaluation
        if current_rsi <= 35 or current_drawdown <= -10.0:
            st.success(
                f"🔥 **BUY THE DIP OPPORTUNITY:** This ETF is on sale! "
                f"It has pulled back **{current_drawdown:.1f}%** from its recent peak highs. "
                f"RSI is sitting oversold at **{current_rsi:.1f}**, historically presenting excellent long-term capital entries."
            )
        elif current_rsi >= 70:
            st.warning(
                f"⚠️ **PEAK MOMENTUM WARNING:** Price is overstretched in the short term. "
                f"RSI is heavily overbought at **{current_rsi:.1f}**. It is sitting just **{abs(current_price - all_time_high)/all_time_high*100:.1f}%** "
                f"below its absolute historical peak top. Consider pausing lump sums and continuing via standard SIP."
            )
        else:
            st.info(
                f"⚖️ **NEUTRAL ACCUMULATION:** The ETF is trading within normal bands. "
                f"Current RSI is **{current_rsi:.1f}** and it is **{abs(current_drawdown):.1f}%** off its rolling high. "
                f"Safe for scheduled standard monthly DCA/SIP buying."
            )

        st.divider()

        # Layout Main Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Price", f"{current_price:.2f} {currency}")
        col2.metric("Period Return", f"{pct_change:+.2f}%", f"{price_change:+.2f} {currency}")
        col3.metric("RSI (14-Day Momentum)", f"{current_rsi:.1f}")
        col4.metric("Distance From Peak", f"{current_drawdown:+.1f}%")
        
        st.divider()

        # Interactive Chart Layout
        st.subheader(f"📊 {selected_etf_name} ({ticker}) Trend Analysis")
        
        fig = go.Figure()
        # Closing Price
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Closing Price', line=dict(color='#1f77b4', width=2)))
        # Rolling High Reference
        fig.add_trace(go.Scatter(x=df.index, y=df['Rolling_High'], mode='lines', name='Rolling High', line=dict(color='#2ca02c', width=1.5, dash='dash')))
        
        fig.update_layout(
            xaxis_title="Date", yaxis_title=f"Price ({currency})",
            hovermode="x unified", template="plotly_white", height=450,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig, theme="streamlit")

        # Raw Data View
        with st.expander("👁️ Review Technical Indicators Table"):
            st.dataframe(df[['Open', 'High', 'Low', 'Close', 'RSI', 'Drawdown_Pct']].sort_index(ascending=False))
            
    else:
        st.error("No historical data available for the chosen parameters.")

except Exception as e:
    st.error(f"An error occurred while building the dashboard: {e}")
