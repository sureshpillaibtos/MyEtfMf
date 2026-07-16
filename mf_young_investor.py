import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go

st.title("👶 Young Investor Core Strategic Portfolio")
st.markdown("Aggressive diversification allocation tailored for long-term compound runways.")
st.divider()

# Metadata storage containing tracking rules for young investor targets
portfolio_metadata = {
    "Parag Parikh Flexi Cap Direct-Growth": {
        "weight": 30, "code": "122639", "style": "Active Flexi Cap",
        "launch_date": "24-May-2013", "min_inv": "₹1,000 (SIP / Lumpsum)",
        "exit_load": "2% if redeemed within 1 year; 1% if between 1-2 years; Nil after."
    },
    "UTI Nifty 50 Index Fund Direct-Growth": {
        "weight": 30, "code": "120716", "style": "Passive Large Cap",
        "launch_date": "01-Jan-2013", "min_inv": "₹500 (SIP) / ₹5,000 (Lumpsum)",
        "exit_load": "Nil"
    },
    "Motilal Oswal Midcap Direct-Growth": {
        "weight": 20, "code": "127042", "style": "Active Mid Cap",
        "launch_date": "24-Feb-2014", "min_inv": "₹500 (SIP) / ₹5,000 (Lumpsum)",
        "exit_load": "1% if within 15 days; Nil after."
    },
    "Nippon India Small Cap Direct-Growth": {
        "weight": 10, "code": "119598", "style": "Active Small Cap",
        "launch_date": "01-Jan-2013", "min_inv": "₹100 (SIP) / ₹5,000 (Lumpsum)",
        "exit_load": "1% if within 30 days; Nil after."
    },
    "Motilal Oswal Nasdaq 100 FOF Direct-Growth": {
        "weight": 10, "code": "145552", "style": "Global Tech (US)",
        "launch_date": "29-Nov-2018", "min_inv": "₹500 (SIP) / ₹5,000 (Lumpsum)",
        "exit_load": "1% if within 3 months; Nil after."
    }
}

st.subheader("📊 Portfolio Strategic Asset Weights")
cols = st.columns(5)
for idx, (name, metadata) in enumerate(portfolio_metadata.items()):
    cols[idx].metric(label=metadata["style"], value=f"{metadata['weight']}%", delta=name.split()[0])

st.divider()

selected_mf_name = st.selectbox("Select Fund to Analyze Real-Time Signals", list(portfolio_metadata.keys()))
fund_meta = portfolio_metadata[selected_mf_name]
scheme_code = fund_meta["code"]

time_horizon = st.selectbox("Set Analysis Window", ["1 Month", "6 Months", "1 Year", "3 Years", "5 Years", "Maximum"], index=2)

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))

def calculate_cagr(df, years):
    days = int(years * 252)
    if len(df) > days:
        ending_nav = float(df['Close'].iloc[-1])
        starting_nav = float(df['Close'].iloc[-days])
        cagr = ((ending_nav / starting_nav) ** (1 / years) - 1) * 100
        return f"{cagr:.2f}%"
    return "Data N/A"

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
        return_3y = calculate_cagr(raw_df, 3)
        return_5y = calculate_cagr(raw_df, 5)
        return_10y = calculate_cagr(raw_df, 10)
        
        raw_df['RSI'] = calculate_rsi(raw_df['Close'], period=14)
        raw_df['Rolling_High'] = raw_df['Close'].rolling(window=252, min_periods=1).max()
        raw_df['Drawdown_Pct'] = ((raw_df['Close'] - raw_df['Rolling_High']) / raw_df['Rolling_High']) * 100
        
        delta_map = {"1 Month": 30, "6 Months": 180, "1 Year": 365, "3 Years": 1095, "5 Years": 1825}
        df = raw_df.tail(delta_map.get(time_horizon, 365)).copy() if time_horizon in delta_map else raw_df.copy()

        current_nav = float(df['Close'].iloc[-1])
        current_rsi = float(df['RSI'].iloc[-1]) if not pd.isna(df['RSI'].iloc[-1]) else 50.0
        current_drawdown = float(df['Drawdown_Pct'].iloc[-1])
        
        # Factsheet Overview Card Container
        with st.expander("ℹ️ View Fund Factsheet & Long Term History", expanded=True):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                st.markdown(f"🗓️ **Launch Date:** {fund_meta['launch_date']}")
                st.markdown(f"💰 **Minimum Investment:** {fund_meta['min_inv']}")
                st.markdown(f"🛑 **Exit Load:** {fund_meta['exit_load']}")
            with f_col2:
                st.markdown(f"📈 **3-Year Annualized CAGR:** **{return_3y}**")
                st.markdown(f"🚀 **5-Year Annualized CAGR:** **{return_5y}**")
                st.markdown(f"💎 **10-Year Annualized CAGR:** **{return_10y}**")

        st.divider()

        if current_rsi <= 35 or current_drawdown <= -10.0:
            st.success(f"🔥 **BUYING ZONE:** {selected_mf_name} is in a clear value dip down **{current_drawdown:.2f}%** from peak high.")
        elif current_rsi >= 68:
            st.warning(f"⚠️ **PEAK MOMENTUM:** RSI is at **{current_rsi:.1f}** (Overbought). Stick to standard SIPs.")
        else:
            st.info(f"⚖️ **NEUTRAL ACCUMULATION:** Normal bands. RSI is **{current_rsi:.1f}**.")

        m1, m2, m3 = st.columns(3)
        m1.metric("Current NAV", f"₹{current_nav:.2f}")
        m2.metric("RSI (14-Day)", f"{current_rsi:.1f}")
        m3.metric("Distance Off 1-Yr Peak", f"{current_drawdown:.2f}%")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='NAV', line=dict(color='#2ca02c')))
        fig.update_layout(template="plotly_white", height=400, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, theme="streamlit")
except Exception as e:
    st.error(f"Error compiling: {e}")