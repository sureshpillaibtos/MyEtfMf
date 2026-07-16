import streamlit as st

# Define the individual pages pointing to your dashboard scripts
etf_page = st.Page("etf_dashboard.py", title="📈 ETF Dashboard", icon="📊")
mf_page = st.Page("mf_dashboard.py", title="🎯 Mutual Fund Accumulator", icon="💰")

# Initialize native structural navigation
pg = st.navigation([etf_page, mf_page])

# Configure global page parameters
st.set_page_config(page_title="Global Wealth Management", layout="wide")

# Run the selected page context
pg.run()
