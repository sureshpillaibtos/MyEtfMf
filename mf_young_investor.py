import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go

st.title("👶 Young Investor Core Strategic Portfolio")
st.markdown("Aggressive diversification allocation tailored for long-term compound runways.")
st.divider()

# Portfolio Assets mapped to target allocation weights and AMFI codes
portfolio = {
    "Parag Parikh Flexi Cap Direct-Growth": {"weight": 30, "code": "122639", "style": "Active Flexi Cap"},
    "UTI Nifty 50 Index Fund Direct-Growth": {"weight": 30, "code": "120716", "style": "Passive Large Cap"},
    "Motilal Oswal Midcap Direct-Growth": {"weight": 20, "code": "127042", "style": "Active Mid Cap"},
    "Nippon India Small Cap Direct-Growth": {"weight": 10, "code": "119598", "style": "Active Small Cap"},
    "Motilal Oswal Nasdaq 100 FOF Direct-Growth": {"weight": 10, "code": "145552", "style": "Global Tech (US)"}
}

# Target selection layout
st.subheader("📊 Portfolio Strategic Asset Weights")
cols = st.columns(5)
for idx, (name, metadata) in enumerate(portfolio.items()):
    cols[idx].metric(label=metadata["style"], value=f"{metadata['weight']}%", delta=name.split()[0])

st.divider()

selected_mf_name = st.selectbox("Select Fund to Analyze Real-Time Signals", list(portfolio.keys()))
scheme_code = portfolio[selected_mf_name]["code"]

time_horizon = st.selectbox("Set Analysis Window", ["1 Month", "6 Months", "1 Year", "3 Years", "5 Years", "Maximum"], index=2)

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
    with st.spinner("Fetching AMFI structural history..."):
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
        
        # Display Banners
        if current_rsi <= 35 or current_drawdown <= -10.0:
            st.success(f"🔥 **BUYING ZONE:** {selected_mf_name} is in a clear value dip down **{current_drawdown:.2f}%** from peak high.")
        elif current_rsi >= 68:
            st.warning(f"⚠️ **PEAK MOMENTUM:** RSI is at **{current_rsi:.1f}** (Overbought). Stick to standard SIPs.")
        else:
            st.info(f"⚖️ **NEUTRAL ACCUMULATION:** Normal bands. RSI is **{current_rsi:.1f}**.")

        # Metric Displays
        m1, m2, m3 = st.columns(3)
        m1.metric("Current NAV", f"₹{current_nav:.2f}")
        m2.metric("RSI (14-Day)", f"{current_rsi:.1f}")
        m3.metric("Distance Off 1-Yr Peak", f"{current_drawdown:.2f}%")

        # Plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='NAV', line=dict(color='#2ca02c')))
        fig.update_layout(template="plotly_white", height=400, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, theme="streamlit")
except Exception as e:
    st.error(f"Error compiling: {e}")