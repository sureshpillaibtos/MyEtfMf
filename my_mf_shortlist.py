import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go

st.title("🏆 Core Mutual Fund Shortlist for 2026")
st.markdown("Handpicked selection balancing standard passive index strategies with alpha generating large-mid-small allocations.")
st.divider()

shortlist = {
    "Parag Parikh Flexi Cap Direct-Growth": "122639",
    "UTI Nifty 50 Index Fund Direct-Growth": "120716",
    "ICICI Prudential Large & Mid Cap Fund Direct-Growth": "120596",
    "Motilal Oswal Midcap Direct-Growth": "127042",
    "Nippon India Small Cap Direct-Growth": "119598"
}

selected_mf_name = st.selectbox("Select Shortlisted Fund to View Analysis", list(shortlist.keys()))
scheme_code = shortlist[selected_mf_name]

time_horizon = st.selectbox("Select Window Lookback", ["1 Month", "6 Months", "1 Year", "3 Years", "5 Years", "Maximum"], index=2)

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=14400)
def load_mfapi_data(code):
    url = f"https://api.mfapi.in/mf/{code}"
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=25)
            response.raise_for_status()
            json_data = response.json()
            nav_list = json_data.get("data", [])
            if not nav_list: return pd.DataFrame()
            df = pd.DataFrame(nav_list)
            df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
            df["nav"] = pd.to_numeric(df["nav"])
            df = df.sort_values("date").reset_index(drop=True)
            df.set_index("date", inplace=True)
            df.rename(columns={"nav": "Close"}, inplace=True)
            return df
        except Exception:
            if attempt < 2: time.sleep(2); continue
            return pd.DataFrame()

try:
    with st.spinner("Fetching AMFI history metrics..."):
        raw_df = load_mfapi_data(scheme_code)

    if not raw_df.empty:
        raw_df['RSI'] = calculate_rsi(raw_df['Close'], period=14)
        raw_df['Rolling_High'] = raw_df['Close'].rolling(window=252, min_periods=1).max()
        raw_df['Drawdown_Pct'] = ((raw_df['Close'] - raw_df['Rolling_High']) / raw_df['Rolling_High']) * 100
        
        delta_map = {"1 Month": 30, "6 Months": 180, "1 Year": 365, "3 Years": 1095, "5 Years": 1825}
        df = raw_df.tail(delta_map.get(time_horizon, 365)).copy() if time_horizon in delta_map else raw_df.copy()

        current_nav = float(df['Close'].iloc[-1])
        current_rsi = float(df['RSI'].iloc[-1]) if not pd.isna(df['RSI'].iloc[-1]) else 50.0
        current_drawdown = float(df['Drawdown_Pct'].iloc[-1])
        
        # Display Alerts
        if current_rsi <= 35 or current_drawdown <= -10.0:
            st.success(f"🔥 **BUY SIGNAL DIPPED:** {selected_mf_name} is highly attractive, dropped **{current_drawdown:.2f}%** off rolling high peaks.")
        elif current_rsi >= 68:
            st.warning(f"⚠️ **OVERBOUGHT EXHAUSTION:** Momentum is hot at **{current_rsi:.1f}** RSI. Keep accumulating through running SIPs only.")
        else:
            st.info(f"⚖️ **NEUTRAL MARGIN:** Normal baseline trading. RSI is **{current_rsi:.1f}**.")

        # Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Current NAV", f"₹{current_nav:.2f}")
        m2.metric("RSI (14-Day)", f"{current_rsi:.1f}")
        m3.metric("Distance Off 1-Yr Peak", f"{current_drawdown:.2f}%")

        # Interactive Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='NAV', line=dict(color='#d62728')))
        fig.update_layout(template="plotly_white", height=400, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, theme="streamlit")
except Exception as e:
    st.error(f"Error compiling: {e}")