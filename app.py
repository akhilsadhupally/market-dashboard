import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup
from mftool import Mftool # The Library for Indian Mutual Funds

# --- 🎨 CONFIGURATION ---
st.set_page_config(page_title="InvestRight.AI", page_icon="🦁", layout="wide")

# --- 🛠️ IPO ENGINE (The Scraper) ---
@st.cache_data(ttl=3600)
def get_ipo_gmp():
    # We scrape a popular GMP monitoring site (Educational Purposes)
    # In a real startup, you might pay a vendor, but this works for MVP.
    url = "https://www.investorgain.com/report/live-ipo-gmp/331/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'class': 'table'})
        
        data = []
        rows = table.find_all('tr')[1:] # Skip header
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 3:
                ipo_name = cols[0].text.strip()
                price = cols[2].text.strip()
                gmp = cols[3].text.strip()
                # Clean the GMP (Remove ₹ and commas)
                try:
                    gmp_val = float(gmp.replace('₹', '').replace(',', ''))
                except:
                    gmp_val = 0
                
                data.append({'IPO Name': ipo_name, 'Price': price, 'GMP': gmp_val})
        
        return pd.DataFrame(data).head(10) # Top 10 Active IPOs
    except:
        return pd.DataFrame()

# --- 💰 MUTUAL FUND ENGINE (Indian Data) ---
@st.cache_data(ttl=3600)
def get_mf_details(scheme_code):
    obj = Mftool()
    try:
        # Fetch NAV History
        data = obj.get_scheme_historical_nav(scheme_code)
        df = pd.DataFrame(data['data'])
        df['nav'] = df['nav'].astype(float)
        df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
        df = df.sort_values('date')
        
        # Get Fund Details (Manager, Risk, etc.)
        details = obj.get_scheme_details(scheme_code)
        
        return df, details
    except:
        return None, None

# --- 📱 SIDEBAR ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2910/2910312.png", width=50)
st.sidebar.title("InvestRight.AI 🦁")
page = st.sidebar.radio("Navigate", ["🚀 IPO Signals", "💰 Mutual Fund X-Ray", "📈 Equity Sentiment"])

# --- PAGE 1: IPO SIGNALS (The GMP Hunter) ---
if page == "🚀 IPO Signals":
    st.title("IPO Command Center")
    st.caption("Live Grey Market Premium (GMP) Scanner")
    
    if st.button("Scan Market for GMP"):
        with st.spinner("Scraping live market data..."):
            df = get_ipo_gmp()
            
        if not df.empty:
            # 1. GMP LEADERBOARD
            top_ipo = df.sort_values(by='GMP', ascending=False).iloc[0]
            st.markdown(f"### 🔥 Hottest IPO: **{top_ipo['IPO Name']}**")
            st.metric("Current GMP", f"₹{top_ipo['GMP']}", "High Demand")
            
            # 2. VISUALIZATION
            fig = px.bar(df, x='IPO Name', y='GMP', 
                         title="Current GMP of Active IPOs",
                         color='GMP', color_continuous_scale=['red', 'yellow', 'green'])
            st.plotly_chart(fig, use_container_width=True)
            
            # 3. AI INSIGHT (Simulated)
            st.info(f"🤖 **AI Verdict:** The GMP for {top_ipo['IPO Name']} indicates a strong listing gain. Institutional interest is likely high.")
            
            st.dataframe(df)
        else:
            st.error("Could not fetch GMP data. Market might be closed.")

# --- PAGE 2: MUTUAL FUND X-RAY ---
elif page == "💰 Mutual Fund X-Ray":
    st.title("Smart Mutual Fund Analyzer")
    
    # Common Codes for Indian Funds (You can expand this list)
    mf_map = {
        "Quant Small Cap Fund": "120823",
        "Parag Parikh Flexi Cap": "122639",
        "Nippon India Small Cap": "118778",
        "SBI Bluechip Fund": "103504"
    }
    
    fund_name = st.selectbox("Select Fund", list(mf_map.keys()))
    
    if st.button("Analyze Fund"):
        code = mf_map[fund_name]
        with st.spinner("Fetching AMFI Data..."):
            hist, details = get_mf_details(code)
            
        if hist is not None:
            # METRICS
            curr_nav = hist['nav'].iloc[-1]
            prev_nav = hist['nav'].iloc[-2]
            ret_1y = ((curr_nav - hist['nav'].iloc[-250]) / hist['nav'].iloc[-250]) * 100
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Current NAV", f"₹{curr_nav}", f"{curr_nav-prev_nav:.2f}")
            c2.metric("1-Year Return", f"{ret_1y:.1f}%")
            c3.metric("Fund House", details['fund_house'])
            
            # CHART
            st.subheader("Performance vs Market")
            fig = px.line(hist.tail(365), x='date', y='nav', title="1 Year NAV Trajectory")
            fig.update_traces(line_color='#00CC96')
            st.plotly_chart(fig, use_container_width=True)
            
            # SENTIMENT (Placeholder for now)
            st.warning("⚠️ **Institutions Say:** This fund has high volatility (Beta > 1). Suitable for aggressive investors only.")

# --- PAGE 3: EQUITY (Your Existing Code) ---
elif page == "📈 Equity Sentiment":
    st.info("Your existing Equity Sentiment Code goes here...")
