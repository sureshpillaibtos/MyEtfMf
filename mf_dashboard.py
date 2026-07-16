import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import time

# Page Configuration
#st.set_page_config(page_title="Indian Mutual Fund Smart Accumulator", layout="wide")

st.title("🎯 Indian Mutual Fund Smart Accumulator")
st.markdown("Automate your mutual fund lumpsum and SIP decisions using AMFI data (RSI & Drawdown).")
st.divider()


# Curated List of Top Indian Mutual Funds mapped to official AMFI Scheme Codes (Direct-Growth)
mf_dict = {
    "Flexi Cap / Large & Mid Cap": {
        "Parag Parikh Flexi Cap Direct-Growth": "122639",
        "Quant Active Fund Direct-Growth": "120823",
        "HDFC Large and Mid Cap Direct-Growth": "130498",
        "Mirae Asset Large & Midcap Fund - Direct Growth": "118834",
        "JM Flexi Cap Fund - Direct Growth": "125494",
        "ICICI Prudential Large & Mid Cap Fund - Direct Growth": "120503"
    },
    "Small & Mid Cap (Aggressive Growth)": {
        "Nippon India Small Cap Direct-Growth": "119598",
        "Quant Small Cap Direct-Growth": "120828",
        "HDFC Mid-Cap Opportunities Direct-Growth": "118989",
        "Motilal Oswal Midcap Direct-Growth": "127042",
        "Invesco India Mid Cap Fund - Direct Growth": "120503",
        "Bandhan Small Cap Fund - Direct Growth": "125354"
    },
    "Large Cap / Passive Index": {
        "UTI Nifty 50 Index Fund Direct-Growth": "120716",
        "ICICI Prudential Bluechip Direct-Growth": "120032",
        "HDFC Index Fund - Nifty 50 Plan - Direct Growth":	"119552",
        "SBI Nifty Index Fund - Direct Growth":	"119827",
        "ICICI Prudential Nifty 50 Index Fund - Direct Growth":	"120620",
        "Canara Robeco Large Cap Fund - Direct Growth":	"118269"
    },
    "Hybrid & Sectoral / International": {
        "HDFC Balanced Advantage Direct-Growth": "118968",
        "ICICI Prudential Equity & Debt Direct-Growth": "120251",
        "Tata Digital India Fund Direct-Growth": "135800",
        "SBI Equity Hybrid Fund - Direct Growth":	"119609",
        "ICICI Prudential Technology Fund - Direct Growth":	"120594",
        "Motilal Oswal Nasdaq 100 FoF - Direct Growth":	"145552",
        "Mirae Asset NYSE FANG+ ETF FoF - Direct Growth":	"148928"

    }
}

# Sidebar UI
st.sidebar.header("⚙️ Fund Selector")
category = st.sidebar.selectbox("Select MF Category", list(mf_dict.keys()))
selected_mf_name = st.sidebar.selectbox("Select Mutual Fund", list(mf_dict[category].keys()))
scheme_code = mf_dict[category][selected_mf_name]

time_horizon = st.sidebar.selectbox(
    "Set Analysis Window", 
    ["1 Month", "6 Months", "1 Year", "3 Years", "5 Years", "Maximum"],
    index=2
)

# Custom RSI Calculation (Classic 14-period momentum formula)
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10) # prevents division-by-zero
    return 100 - (100 / (1 + rs))

# Fetching NAV Data safely from MFAPI.in
@st.cache_data(ttl=14400) # Cache for 4 hours (Mutual fund NAVs update only once a day)
def load_mfapi_data(code):
    url = f"https://api.mfapi.in/mf/{code}"
    max_retries = 3
    timeout_seconds = 25

    for attempt in range(max_retries):
        try:
            # We increase timeout to 25s to give the free API server breathing room
            response = requests.get(url, timeout=timeout_seconds)
            response.raise_for_status()
            json_data = response.json()
            
            # Extract NAV list
            nav_list = json_data.get("data", [])
            if not nav_list:
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(nav_list)
            df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
            df["nav"] = pd.to_numeric(df["nav"])
            
            # Sort chronologically (Oldest to Newest)
            df = df.sort_values("date").reset_index(drop=True)
            df.set_index("date", inplace=True)
            
            # Rename column to standard 'Close' for our indicator pipeline
            df.rename(columns={"nav": "Close"}, inplace=True)
            return df
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt < max_retries - 1:
                # Wait 2 seconds before retrying to let the API server breathe
                time.sleep(2)
                continue
            else:
                st.error(
                    "⚠️ **MFAPI Server is Busy:** The free AMFI data server is currently experiencing high traffic. "
                    "Please try switching to another fund or refresh the page in a few moments."
                )
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Error fetching data from MFAPI: {e}")
            return pd.DataFrame()

try:
    with st.spinner(f"Loading official AMFI data for {selected_mf_name} (Code: {scheme_code})..."):
        raw_df = load_mfapi_data(scheme_code)

    if not raw_df.empty:
        # Calculate Technical Metrics
        raw_df['RSI'] = calculate_rsi(raw_df['Close'], period=14)
        raw_df['Rolling_High'] = raw_df['Close'].rolling(window=252, min_periods=1).max()
        raw_df['Drawdown_Pct'] = ((raw_df['Close'] - raw_df['Rolling_High']) / raw_df['Rolling_High']) * 100
        
        # Filter visually for selected timeframe
        delta_map = {"1 Month": 30, "6 Months": 180, "1 Year": 365, "3 Years": 1095, "5 Years": 1825}
        if time_horizon in delta_map:
            days_to_keep = delta_map[time_horizon]
            df = raw_df.tail(days_to_keep).copy()
        else:
            df = raw_df.copy()

        # Extract current core metrics
        current_nav = float(df['Close'].iloc[-1])
        current_rsi = float(df['RSI'].iloc[-1]) if not pd.isna(df['RSI'].iloc[-1]) else 50.0
        current_drawdown = float(df['Drawdown_Pct'].iloc[-1])
        
        previous_close = float(df['Close'].iloc[0]) if len(df) > 1 else current_nav
        nav_change = current_nav - previous_close
        pct_change = (nav_change / previous_close) * 100


        # Display currently selected fund details on the main page
        st.markdown(f"### 📊 Currently Viewing: **{selected_mf_name}**")
        st.caption(f"📁 **Category:** {category} | 🆔 **AMFI Code:** {scheme_code}")
        st.divider()

        # Smart Accumulator Logic Engine
        st.subheader("📢 Smart Accumulation Alert")


        if current_rsi <= 35 or current_drawdown <= -10.0:
            st.success(
                f"🔥 **STRONG BUY / ACCUMULATION ALERT:** {selected_mf_name} is currently resting in a sweet dip value zone! "
                f"The NAV has pulled back **{current_drawdown:.2f}%** from its rolling peak. "
                f"RSI is sitting oversold at **{current_rsi:.1f}**. This is historically a great window to deploy a lump-sum "
                f"or double up on your SIP installment!"
            )
        elif current_rsi >= 68:
            st.warning(
                f"⚠️ **PEAK OVERSTRETCH WARNING:** The fund's short term momentum is running exceptionally hot. "
                f"RSI is highly overbought at **{current_rsi:.1f}**. "
                f"Avoid dumping lump-sum amounts here; stick strictly to standard monthly SIPs to average out cost."
            )
        else:
            st.info(
                f"⚖️ **NEUTRAL SIP ACCUMULATION:** {selected_mf_name} is trading comfortably within regular channels. "
                f"RSI is sitting at **{current_rsi:.1f}** and the NAV is **{abs(current_drawdown):.2f}%** "
                f"off its rolling annual peak. Keep standard automatic transactions and SIP allocations running as planned."
            )

        st.divider()

        # Display Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current NAV (INR)", f"₹{current_nav:.2f}")
        col2.metric("NAV Period Return", f"{pct_change:+.2f}%", f"₹{nav_change:+.2f}")
        col3.metric("RSI (14-Day Momentum)", f"{current_rsi:.1f}")
        col4.metric("Distance From 1-Yr Peak", f"{current_drawdown:+.2f}%")
        
        st.divider()

        # Interactive Performance Chart (Warning free)
        st.subheader(f"📈 NAV Performance Analysis ({time_horizon})")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index, y=df['Close'], 
            mode='lines', name='NAV Price', 
            line=dict(color='#ff7f0e', width=2.5)
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=df['Rolling_High'], 
            mode='lines', name='Rolling 1-Yr Peak High', 
            line=dict(color='#4b5320', width=1.5, dash='dash')
        ))
        
        fig.update_layout(
            xaxis_title="Date", yaxis_title="NAV (INR)",
            hovermode="x unified", template="plotly_white", height=450,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig, theme="streamlit")

        # Historical Table
        with st.expander("👁️ Review Technical Indicators Table"):
            st.dataframe(df[['Close', 'RSI', 'Drawdown_Pct']].sort_index(ascending=False))
            
    else:
        st.error("No historical NAV data retrieved. Check backend connection.")

except Exception as e:
    st.error(f"Error compiling dashboard: {e}")
