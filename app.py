import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from mftool import Mftool
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import time
import random

# --- 🎨 PRO CONFIGURATION ---
st.set_page_config(
    page_title="InvestRight.AI | Pro Terminal", 
    page_icon="🦁", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Professional UI
st.markdown("""
    <style>
    .stMetric {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        border-radius: 4px 4px 0px 0px;
        font-weight: 600;
        font-size: 16px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 📚 EDUCATIONAL TOOLTIPS ---
TOOLTIPS = {
    "PE": "Price-to-Earnings Ratio: Measures if a stock is overvalued. Lower is generally better (cheaper).",
    "DE": "Debt-to-Equity: How much debt the company has vs. shareholder money. >2 is risky.",
    "ROE": "Return on Equity: How efficiently the company uses your money to generate profit. >15% is good.",
    "GMP": "Grey Market Premium: The price unofficial traders are paying before listing. High GMP = High Demand.",
    "Score": "AI Confidence Score (0-100) derived from analyzing news headlines and social chatter."
}

# --- 🛠️ DATA ENGINE ---
@st.cache_data
def load_stock_list():
    try:
        url = "https://raw.githubusercontent.com/akhilsadhupally/market-dashboard/refs/heads/main/stocks.csv"
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        if 'SYMBOL' in df.columns:
            df['Search_Label'] = df['SYMBOL'] + " - " + df['NAME OF COMPANY']
        elif 'Symbol' in df.columns:
            df['Search_Label'] = df['Symbol'] + " - " + df['Company Name']
        else:
            return pd.DataFrame()
        return df
    except:
        return pd.DataFrame({'Search_Label': ['RELIANCE - Reliance Industries', 'TATASTEEL - Tata Steel']})

stock_df = load_stock_list()

# --- 🧠 SENTIMENT ENGINE (DuckDuckGo Fix) ---
# We switched to DuckDuckGo because Google RSS was blocking the cloud server.
@st.cache_data(ttl=600)
def get_sentiment_report(query_term):
    # Search for news and discussions
    url = f"https://html.duckduckgo.com/html/?q={query_term} stock news sentiment"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    combined_data = []
    analyzer = SentimentIntensityAnalyzer()
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Parse DuckDuckGo Results
        results = soup.find_all('div', class_='result__body')[:6]
        
        for res in results:
            title_tag = res.find('a', class_='result__a')
            if title_tag:
                title = title_tag.text
                link = title_tag['href']
                snippet = res.find('a', class_='result__snippet').text if res.find('a', class_='result__snippet') else ""
                
                # Determine Source Type
                if "reddit" in link or "reddit" in title.lower():
                    source = "Reddit 💬"
                    weight = 0.6
                elif "moneycontrol" in link or "economictimes" in link:
                    source = "Financial News 📰"
                    weight = 1.5
                else:
                    source = "Web News 🌐"
                    weight = 1.0
                
                # Analyze Sentiment
                score = analyzer.polarity_scores(title + " " + snippet)['compound']
                combined_data.append({'Title': title, 'Source': source, 'Score': score, 'Link': link, 'Weight': weight})
                
    except Exception as e:
        print(f"Sentiment Error: {e}")
        return None

    if not combined_data: return None

    df = pd.DataFrame(combined_data)
    
    # Calculate Weighted Score
    weighted_score = (df['Score'] * df['Weight']).sum() / df['Weight'].sum()
    final_score = int((weighted_score + 1) * 50) # Scale -1..1 to 0..100
    
    # Professional Rating
    if final_score >= 80: rating = "Strong Buy (Bullish) 🟢"
    elif final_score >= 60: rating = "Accumulate (Positive) 📈"
    elif final_score >= 40: rating = "Hold (Neutral) ⚖️"
    elif final_score >= 20: rating = "Reduce (Cautious) ⚠️"
    else: rating = "Sell (Bearish) 🔴"
    
    return {"score": final_score, "rating": rating, "data": df, "count": len(df)}

# --- 📊 EQUITY ENGINE (Fast_Info Fix) ---
@st.cache_data(ttl=300)
def get_stock_fundamentals(ticker):
    try:
        symbol = ticker.upper() if ticker.endswith(".NS") else f"{ticker.upper()}.NS"
        stock = yf.Ticker(symbol)
        
        # 1. Price Data
        hist = stock.history(period="1y")
        if hist.empty: return None
        
        current = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        change_pct = ((current - prev) / prev) * 100
        
        # 2. Robust Fundamentals (Using fast_info)
        # fast_info is less likely to be blocked than info
        fi = stock.fast_info
        metrics = {}
        
        try:
            # Try getting detailed info first
            info = stock.info
            metrics = {
                "Market Cap": info.get("marketCap", fi.market_cap),
                "PE": info.get("trailingPE", "N/A"),
                "Div Yield": info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0,
                "52W High": info.get("fiftyTwoWeekHigh", fi.year_high),
                "DebtToEquity": info.get("debtToEquity", "N/A"),
                "ROE": info.get("returnOnEquity", 0),
                "Sector": info.get("sector", "N/A"),
                "Summary": info.get("longBusinessSummary", "Summary temporarily unavailable from source.")
            }
        except:
            # Fallback to fast_info if info fails
            metrics = {
                "Market Cap": fi.market_cap,
                "PE": "N/A", # fast_info doesn't have PE
                "Div Yield": 0,
                "52W High": fi.year_high,
                "DebtToEquity": "N/A",
                "ROE": 0,
                "Sector": "N/A",
                "Summary": "Fundamental data restricted by data provider."
            }
            
        return {"price": current, "change": change_pct, "hist": hist, "metrics": metrics}
    except Exception as e:
        return None

# --- 🚀 IPO ENGINE ---
@st.cache_data(ttl=300)
def get_ipo_data():
    try:
        sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSrY-WLkphYTFIp9FffqR_WfXE_Ta9E0SId-pKqF10ZaUXTZEW1rHY96ilINOkrA6IDaASwWiQl9TMI/pub?output=csv"
        df = pd.read_csv(sheet_url)
        df.columns = [c.lower() for c in df.columns]
        
        new_df = pd.DataFrame()
        c_name = next((c for c in df.columns if 'ipo' in c or 'company' in c), None)
        c_price = next((c for c in df.columns if 'price' in c), None)
        c_gmp = next((c for c in df.columns if 'gmp' in c or 'premium' in c), None)
        
        if not c_name: return pd.DataFrame()
        
        new_df['Company'] = df[c_name]
        new_df['Price'] = df[c_price].fillna(0)
        new_df['GMP'] = df[c_gmp].fillna(0)
        
        def clean(x): 
            try: return float(str(x).split('(')[0].replace('₹','').replace(',','').replace('%','').strip())
            except: return 0.0
            
        new_df['GMP_Val'] = new_df['GMP'].apply(clean)
        new_df['Price_Val'] = new_df['Price'].apply(clean)
        
        new_df['Gain%'] = new_df.apply(lambda row: (row['GMP_Val'] / row['Price_Val'] * 100) if row['Price_Val'] > 0 else 0.0, axis=1)
        
        return new_df.sort_values('GMP_Val', ascending=False)
    except:
        return pd.DataFrame()

# --- 💰 MF ENGINE ---
@st.cache_data(ttl=3600)
def get_mf_deep_dive(code):
    obj = Mftool()
    try:
        data = obj.get_scheme_historical_nav(code)
        df = pd.DataFrame(data['data'])
        df['nav'] = df['nav'].astype(float)
        df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
        df = df.sort_values('date')
        details = obj.get_scheme_details(code)
        
        curr_nav = df['nav'].iloc[-1]
        def get_ret(days):
            if len(df) > days: return ((curr_nav - df['nav'].iloc[-days]) / df['nav'].iloc[-days]) * 100
            return 0.0

        returns = { 
            "1Y": get_ret(365), 
            "3Y": get_ret(365*3), 
            "5Y": get_ret(365*5),
            "All": ((curr_nav - df['nav'].iloc[0]) / df['nav'].iloc[0]) * 100 
        }
        return df, details, returns
    except:
        return None, None, None

# --- 📱 APP UI ---
st.sidebar.title("🦁 InvestRight.AI")
page = st.sidebar.radio("Navigate", ["📈 Equity Research", "🚀 IPO Intelligence", "💰 Mutual Funds"])

# --- PAGE 1: EQUITY ---
if page == "📈 Equity Research":
    st.title("Equity Research Terminal")
    search = st.selectbox("Search Company", stock_df['Search_Label'].unique(), index=None, placeholder="Type Tata, Reliance, etc...")
    
    if search:
        ticker = search.split(" - ")[0]
        if st.button("Generate Report", type="primary"):
            with st.spinner(f"Fetching Intelligence for {ticker}..."):
                data = get_stock_fundamentals(ticker)
                # FORCE SENTIMENT FETCH
                sentiment = get_sentiment_report(f"{ticker} stock")
            
            if data:
                m = data['metrics']
                c1, c2, c3 = st.columns([2,1,1])
                c1.metric(f"{search}", f"₹{data['price']:,.2f}", f"{data['change']:+.2f}%")
                c2.metric("Sector", m.get('Sector', 'N/A'))
                
                # TABS
                tab_fund, tab_sent = st.tabs(["📊 Fundamentals", "🧠 Social Sentiment & Buzz"])
                
                with tab_fund:
                    # Robust display: Check if data is 'N/A' before formatting
                    fc1, fc2, fc3, fc4 = st.columns(4)
                    
                    # Safe formatting helpers
                    def safe_fmt(val, is_pct=False):
                        if isinstance(val, (int, float)):
                            return f"{val:.2f}%" if is_pct else f"{val:.2f}"
                        return "N/A"

                    fc1.metric("P/E Ratio", safe_fmt(m.get('PE')), help=TOOLTIPS['PE'])
                    fc2.metric("Debt/Equity", safe_fmt(m.get('DebtToEquity')), help=TOOLTIPS['DE'])
                    fc3.metric("ROE %", safe_fmt(m.get('ROE')*100 if isinstance(m.get('ROE'), (int,float)) else "N/A", True), help=TOOLTIPS['ROE'])
                    fc4.metric("Div Yield", safe_fmt(m.get('Div Yield'), True))
                    
                    st.line_chart(data['hist']['Close'])
                    st.info(f"**Business Summary:** {m.get('Summary', 'N/A')}")

                with tab_sent:
                    if sentiment:
                        sc1, sc2 = st.columns([1,2])
                        with sc1:
                            st.metric("AI Sentiment Score", f"{sentiment['score']}/100", help=TOOLTIPS['Score'])
                            st.progress(sentiment['score']/100)
                            st.caption(f"**Rating:** {sentiment['rating']}")
                        with sc2:
                            st.write(f"**Social Buzz & News Feed ({sentiment['count']} Sources):**")
                            for r in sentiment['data'].head(5).to_dict('records'):
                                st.markdown(f"• **{r['Source']}**: [{r['Title']}]({r['Link']})")
                    else:
                        st.warning("No social buzz detected for this stock right now.")
            else:
                st.error("Data Unavailable: The stock symbol might be delisted or the API is currently blocked.")

# --- PAGE 2: IPO ---
elif page == "🚀 IPO Intelligence":
    st.title("🚀 IPO Intelligence Center")
    ipo_df = get_ipo_data()
    
    if not ipo_df.empty:
        t_dash, t_dive = st.tabs(["🔥 GMP Dashboard", "🔍 Deep Dive Analysis"])
        
        with t_dash:
            st.dataframe(
                ipo_df[['Company', 'Price', 'GMP', 'Gain%']],
                column_config={
                    "Gain%": st.column_config.ProgressColumn("Listing Gain", format="%.1f%%", min_value=0, max_value=100),
                    "GMP": st.column_config.NumberColumn("GMP (₹)", help=TOOLTIPS['GMP'])
                }, hide_index=True, use_container_width=True
            )
            
        with t_dive:
            sel_ipo = st.selectbox("Select IPO", ipo_df['Company'].unique())
            if sel_ipo:
                row = ipo_df[ipo_df['Company'] == sel_ipo].iloc[0]
                
                gc1, gc2 = st.columns(2)
                listing_price = row['Price_Val'] + row['GMP_Val']
                
                # Logic: Don't show 0.0% if GMP is missing
                gain_display = f"{row['Gain%']:.1f}%"
                if row['GMP_Val'] == 0:
                    gain_display = "No GMP Trend Yet"
                
                gc1.metric("Expected Listing Price", f"₹{listing_price}")
                gc2.metric("Listing Gain", gain_display)
                
                st.markdown("---")
                
                # IPO SENTIMENT
                st.subheader("🧠 IPO Sentiment Rating")
                with st.spinner("Analyzing Market Mood..."):
                    ipo_sent = get_sentiment_report(f"{sel_ipo} IPO")
                
                if ipo_sent:
                    ic1, ic2 = st.columns([1,2])
                    with ic1:
                        st.metric("Hype Score", f"{ipo_sent['score']}/100")
                        st.progress(ipo_sent['score']/100)
                        st.caption(ipo_sent['rating'])
                    with ic2:
                        st.write("**Recent Chatter:**")
                        for r in ipo_sent['data'].head(3).to_dict('records'):
                            st.markdown(f"• **{r['Source']}**: [{r['Title']}]({r['Link']})")
                else:
                    st.info("No active sentiment data found.")

                st.markdown("---")
                st.subheader("🏢 Peer Comparison")
                peer = st.text_input("Compare with Listed Competitor (e.g. ZOMATO)", placeholder="Enter Symbol...")
                
                if peer:
                    with st.spinner(f"Analyzing {peer}..."):
                        pdata = get_stock_fundamentals(peer)
                    if pdata:
                        st.success(f"**{peer.upper()}** (Sector Benchmark)")
                        pe = pdata['metrics'].get('PE')
                        pe_show = f"{pe:.2f}" if isinstance(pe, (int, float)) else "N/A"
                        st.write(f"Competitor P/E Ratio: **{pe_show}**")
                        st.caption("Lower P/E than IPO implies the IPO might be expensive.")
                    else:
                        st.error("Competitor symbol not found.")

# --- PAGE 3: MUTUAL FUNDS ---
elif page == "💰 Mutual Funds":
    st.title("Mutual Fund Comparator ⚔️")
    obj = Mftool()
    schemes = obj.get_scheme_codes()
    all_funds = list(schemes.values())
    
    col1, col2 = st.columns(2)
    with col1:
        fund_a = st.selectbox("Fund A", all_funds, index=None, placeholder="Select Fund A", key="fa")
    with col2:
        fund_b = st.selectbox("Fund B (Optional)", all_funds, index=None, placeholder="Select Fund B (for comparison)", key="fb")
        
    if st.button("Analyze / Compare", type="primary"):
        if fund_a:
            code_a = list(schemes.keys())[list(schemes.values()).index(fund_a)]
            with st.spinner("Fetching Data..."):
                df_a, det_a, ret_a = get_mf_deep_dive(code_a)
                # Fetch Sentiment for Fund A
                sent_a = get_sentiment_report(f"{det_a['fund_house']} Mutual Fund")
                
                if fund_b: # COMPARE MODE
                    code_b = list(schemes.keys())[list(schemes.values()).index(fund_b)]
                    df_b, det_b, ret_b = get_mf_deep_dive(code_b)
                    
                    if df_a is not None and df_b is not None:
                        st.subheader("⚔️ Head-to-Head Comparison")
                        
                        comp_data = {
                            "Metric": ["1Y Return", "3Y Return", "5Y Return", "All Time", "Risk", "Category"],
                            "Fund A": [f"{ret_a['1Y']:.2f}%", f"{ret_a['3Y']:.2f}%", f"{ret_a['5Y']:.2f}%", f"{ret_a['All']:.2f}%", det_a.get('scheme_risk', 'N/A'), det_a.get('scheme_category', 'N/A')],
                            "Fund B": [f"{ret_b['1Y']:.2f}%", f"{ret_b['3Y']:.2f}%", f"{ret_b['5Y']:.2f}%", f"{ret_b['All']:.2f}%", det_b.get('scheme_risk', 'N/A'), det_b.get('scheme_category', 'N/A')]
                        }
                        st.table(pd.DataFrame(comp_data))
                        
                        st.subheader("Performance Chart (3 Years)")
                        merged = pd.merge(df_a[['date','nav']], df_b[['date','nav']], on='date', suffixes=('_A', '_B'))
                        st.line_chart(merged.set_index('date'))
                
                else: # SINGLE MODE
                    if df_a is not None:
                        st.subheader(f"📈 Performance: {det_a.get('scheme_name')}")
                        
                        # 1. RETURNS TABLE (RESTORED HERE)
                        rc1, rc2, rc3, rc4 = st.columns(4)
                        rc1.metric("1Y Return", f"{ret_a['1Y']:.2f}%")
                        rc2.metric("3Y Return", f"{ret_a['3Y']:.2f}%")
                        rc3.metric("5Y Return", f"{ret_a['5Y']:.2f}%")
                        rc4.metric("All Time", f"{ret_a['All']:.2f}%")
                        
                        st.line_chart(df_a.set_index('date')['nav'])
                        st.write(f"**Category:** {det_a.get('scheme_category', 'N/A')}")
                        
                        # 2. SENTIMENT SECTION (RESTORED HERE)
                        st.markdown("---")
                        st.subheader(f"📰 News & Sentiment: {det_a.get('fund_house')}")
                        
                        if sent_a:
                            sc1, sc2 = st.columns([1,2])
                            with sc1:
                                st.metric("Trust Score", f"{sent_a['score']}/100", help=TOOLTIPS['Score'])
                                st.progress(sent_a['score']/100)
                                st.caption(sent_a['rating'])
                            with sc2:
                                st.write("**Recent Chatter:**")
                                for r in sent_a['data'].head(3).to_dict('records'):
                                    st.markdown(f"• **{r['Source']}**: [{r['Title']}]({r['Link']})")
                        else:
                            st.info("No active sentiment data found for this Fund House.")
