import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from mftool import Mftool
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from collections import Counter
import re
import deprecated 

# --- 🎨 PRO CONFIGURATION ---
st.set_page_config(
    page_title="InvestRight.AI | Pro Terminal", 
    page_icon="🦁", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for "MoneyControl" style polish
st.markdown("""
    <style>
    .stMetric {
        background-color: #f9f9f9;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        border-radius: 4px 4px 0px 0px;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 📚 EDUCATIONAL TOOLTIPS (The "Teacher" Layer) ---
TOOLTIPS = {
    "PE": "Price-to-Earnings Ratio: Measures if a stock is overvalued. Lower is generally better (cheaper).",
    "PB": "Price-to-Book: Compares market price to book value. <1 suggest the stock is undervalued.",
    "DE": "Debt-to-Equity: How much debt the company has vs. shareholder money. >2 is risky.",
    "ROE": "Return on Equity: How efficiently the company uses your money to generate profit. >15% is good.",
    "Alpha": "Performance vs Benchmark. Positive Alpha means it beat the market index.",
    "Beta": "Volatility. >1 means the stock swings more than the market (Risky). <1 is safer.",
    "GMP": "Grey Market Premium: The price unofficial traders are paying before listing. High GMP = High Demand.",
    "NAV": "Net Asset Value: The price of one unit of the Mutual Fund.",
    "Expense": "Expense Ratio: The annual fee the fund charges you. Lower is better."
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

# --- 🧠 SENTIMENT 3.0 (Weighted & Credible) ---
@st.cache_data(ttl=600)
def get_sentiment_report(query_term):
    # Specialized queries for different investor needs
    queries = [
        f"{query_term} stock news merger acquisition",  # M&A
        f"{query_term} quarterly results profit",       # Earnings
        f"site:moneycontrol.com {query_term} analysis", # Credible Source
        f"site:reddit.com {query_term} discussion"      # Social Pulse
    ]
    
    combined_data = []
    all_titles = []
    analyzer = SentimentIntensityAnalyzer()
    headers = {"User-Agent": "Mozilla/5.0"}

    for q in queries:
        url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
        try:
            r = requests.get(url, headers=headers, timeout=4)
            soup = BeautifulSoup(r.text, 'xml') 
            items = soup.find_all('item')[:4]
            for item in items:
                title = item.title.text
                link = item.link.text
                
                # WEIGHTING LOGIC: News is more "Credible" than Reddit
                weight = 1.0
                if "reddit" in q: 
                    source = "Reddit 💬"
                    weight = 0.6 # Lower trust
                elif "moneycontrol" in q or "news" in q:
                    source = "Financial News 📰"
                    weight = 1.2 # Higher trust
                else: 
                    source = "Web 🌐"
                
                score = analyzer.polarity_scores(title)['compound']
                combined_data.append({
                    'Title': title, 'Source': source, 'Score': score, 'Link': link, 'Weight': weight
                })
                all_titles.append(title)
        except:
            continue
            
    if not combined_data: return None

    df = pd.DataFrame(combined_data)
    
    # Weighted Average Score
    weighted_score = (df['Score'] * df['Weight']).sum() / df['Weight'].sum()
    
    # Scale to 0-100
    final_score = int((weighted_score + 1) * 50)
    
    # Professional Rating System
    if final_score >= 80: rating = "Strong Buy (Bullish) 🟢"
    elif final_score >= 60: rating = "Accumulate (Positive) 📈"
    elif final_score >= 40: rating = "Hold (Neutral) ⚖️"
    elif final_score >= 20: rating = "Reduce (Cautious) ⚠️"
    else: rating = "Sell (Bearish) 🔴"

    # AI Summary
    text_blob = " ".join(all_titles).lower()
    ignore = ['stock', 'share', 'market', 'india', 'price', 'today', 'news', 'ltd', 'limited', 'results', 'quarter']
    words = re.findall(r'\w+', text_blob)
    keywords = [w for w in words if w not in ignore and len(w) > 3]
    topics = [word for word, count in Counter(keywords).most_common(5)]
    
    return {
        "score": final_score,
        "rating": rating,
        "topics": topics,
        "data": df
    }

# --- 📊 EQUITY DEEP DIVE ENGINE ---
@st.cache_data(ttl=300)
def get_stock_fundamentals(ticker):
    try:
        symbol = ticker.upper() if ticker.endswith(".NS") else f"{ticker.upper()}.NS"
        stock = yf.Ticker(symbol)
        
        # 1. Price Data
        hist = stock.history(period="1y") # Get 1 year for 52w calc
        if hist.empty: return None
        
        current = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        change_pct = ((current - prev) / prev) * 100
        
        # 2. Advanced Fundamentals
        info = stock.info
        
        # Shareholding (Proxy via Major Holders)
        holders = stock.major_holders
        if holders is not None:
            # Clean up the dataframe if needed
            holders.columns = ['Value', 'Holder']
        
        # Recommendations (Analyst Ratings)
        recs = stock.recommendations
        rec_summary = "N/A"
        if recs is not None and not recs.empty:
            # Get latest period mean
            rec_summary = recs.tail(5).to_dict() # simplified for display
            
        metrics = {
            "Market Cap": info.get("marketCap"),
            "Beta": info.get("beta", 0),
            "PE": info.get("trailingPE", 0),
            "EPS": info.get("trailingEps", 0),
            "Div Yield": info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0,
            "52W High": info.get("fiftyTwoWeekHigh"),
            "52W Low": info.get("fiftyTwoWeekLow"),
            "DebtToEquity": info.get("debtToEquity", 0),
            "ROE": info.get("returnOnEquity", 0),
            "Sector": info.get("sector", "N/A"),
            "Summary": info.get("longBusinessSummary", "No summary.")
        }
        
        return {"price": current, "change": change_pct, "hist": hist, "metrics": metrics, "holders": holders}
    except Exception as e:
        return None

# --- 🚀 IPO ENGINE (Stable Bridge) ---
@st.cache_data(ttl=300)
def get_ipo_data():
    try:
        # 🟢 YOUR SHEET LINK
        sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSrY-WLkphYTFIp9FffqR_WfXE_Ta9E0SId-pKqF10ZaUXTZEW1rHY96ilINOkrA6IDaASwWiQl9TMI/pub?output=csv"
        df = pd.read_csv(sheet_url)
        df.columns = [c.lower() for c in df.columns]
        
        new_df = pd.DataFrame()
        # Intelligent Column Matching
        c_name = next((c for c in df.columns if 'ipo' in c or 'company' in c), None)
        c_price = next((c for c in df.columns if 'price' in c), None)
        c_gmp = next((c for c in df.columns if 'gmp' in c or 'premium' in c), None)
        
        if not c_name: return pd.DataFrame()
        
        new_df['Company'] = df[c_name]
        new_df['Price'] = df[c_price].fillna(0)
        new_df['GMP'] = df[c_gmp].fillna(0)
        
        # Clean & Calc
        def clean(x): 
            try: return float(str(x).split('(')[0].replace('₹','').replace(',','').replace('%','').strip())
            except: return 0.0
            
        new_df['GMP_Val'] = new_df['GMP'].apply(clean)
        new_df['Price_Val'] = new_df['Price'].apply(clean)
        new_df['Gain%'] = ((new_df['GMP_Val'] / new_df['Price_Val']) * 100).fillna(0)
        
        return new_df.sort_values('GMP_Val', ascending=False)
    except:
        return pd.DataFrame()

# --- 💰 MF ENGINE (With Returns Calc) ---
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
        
        # Calculate Returns (CAGR approx)
        curr_nav = df['nav'].iloc[-1]
        
        def get_ret(days):
            if len(df) > days:
                past = df['nav'].iloc[-days]
                return ((curr_nav - past) / past) * 100
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
st.sidebar.caption("Professional Intelligence Terminal")
page = st.sidebar.radio("Navigate", ["📈 Equity Research", "🚀 IPO Intelligence", "💰 Mutual Funds"])

# --- PAGE 1: EQUITY ---
if page == "📈 Equity Research":
    st.title("Equity Research Terminal")
    st.info("Deep dive into Fundamentals, Institutional Holdings, and Sentiment.")
    
    search = st.selectbox("Search Company", stock_df['Search_Label'].unique(), index=None, placeholder="Type Tata, Reliance, etc...")
    
    if search:
        ticker = search.split(" - ")[0]
        if st.button("Generate Report", type="primary"):
            with st.spinner(f"Analyzing {ticker}..."):
                data = get_stock_fundamentals(ticker)
                sentiment = get_sentiment_report(f"{ticker} stock")
            
            if data:
                m = data['metrics']
                
                # 1. HEADER (Price & Main Tags)
                c1, c2, c3 = st.columns([2,1,1])
                c1.metric(f"{search}", f"₹{data['price']:,.2f}", f"{data['change']:+.2f}%")
                c2.metric("Sector", m['Sector'])
                
                # 2. TABS (The "Clean" UI)
                tab_fund, tab_news, tab_sent = st.tabs(["📊 Fundamentals & Holdings", "📰 News & Events", "🧠 Smart Sentiment"])
                
                with tab_fund:
                    st.subheader("Key Ratios (Hover for info)")
                    fc1, fc2, fc3, fc4 = st.columns(4)
                    fc1.metric("P/E Ratio", f"{m['PE']:.2f}", help=TOOLTIPS['PE'])
                    fc2.metric("Debt/Equity", f"{m['DebtToEquity']:.2f}", help=TOOLTIPS['DE'])
                    fc3.metric("ROE %", f"{m['ROE']*100:.2f}%", help=TOOLTIPS['ROE'])
                    fc4.metric("Div Yield", f"{m['Div Yield']:.2f}%", help=TOOLTIPS['Alpha'])
                    
                    st.markdown("---")
                    st.subheader("🏢 Shareholding Pattern (Major Holders)")
                    if data['holders'] is not None:
                        st.table(data['holders'])
                    else:
                        st.write("Shareholding data not available via API.")
                        
                with tab_news:
                    st.subheader("Recent Corporate Actions & News")
                    if sentiment and sentiment['data'] is not None:
                        # Filter for "News" sources only
                        news_only = sentiment['data'][sentiment['data']['Source'].str.contains("News")]
                        if not news_only.empty:
                            for i, row in news_only.iterrows():
                                st.info(f"📰 **{row['Title']}**\n\n[Read Article]({row['Link']})")
                        else:
                            st.write("No major news headlines found recently.")
                            
                with tab_sent:
                    if sentiment:
                        sc1, sc2 = st.columns([1,2])
                        with sc1:
                            st.metric("Sentiment Score", f"{sentiment['score']}/100", help="0=Bearish, 100=Bullish. Weighted by source credibility.")
                            st.progress(sentiment['score']/100)
                            st.caption(f"**Rating:** {sentiment['rating']}")
                        with sc2:
                            st.write("**Market Whispers (Topics):**")
                            st.write(", ".join(sentiment['topics']))
                            st.write("**Community Verdict:**")
                            st.write("Sentiment is derived from financial news outlets and retail discussion forums.")

# --- PAGE 2: IPO ---
elif page == "🚀 IPO Intelligence":
    st.title("🚀 IPO Intelligence Center")
    st.info("Analyze Fundamentals (Peer Compare), GMP, and Social Mood.")
    
    ipo_df = get_ipo_data()
    
    if not ipo_df.empty:
        t_dash, t_dive = st.tabs(["🔥 GMP Dashboard", "🔍 Deep Dive Analysis"])
        
        with t_dash:
            st.dataframe(
                ipo_df[['Company', 'Price', 'GMP', 'Gain%']],
                column_config={
                    "Gain%": st.column_config.ProgressColumn("Listing Gain", format="%.1f%%", min_value=-10, max_value=100),
                    "GMP": st.column_config.NumberColumn("GMP (₹)", help=TOOLTIPS['GMP'])
                }, hide_index=True, use_container_width=True
            )
            
        with t_dive:
            sel_ipo = st.selectbox("Select IPO", ipo_df['Company'].unique())
            if sel_ipo:
                row = ipo_df[ipo_df['Company'] == sel_ipo].iloc[0]
                
                # 1. GMP CARD
                st.subheader("Grey Market Status")
                gc1, gc2 = st.columns(2)
                gc1.metric("Expected Listing Price", f"₹{row['Price_Val'] + row['GMP_Val']}")
                gc2.metric("Listing Gain", f"{row['Gain%']:.1f}%", help="Estimated profit based on current GMP.")
                
                st.markdown("---")
                # 2. SENTIMENT
                st.subheader("🧠 Credible Sentiment Rating")
                with st.spinner("Analyzing Social Mood..."):
                    sent = get_sentiment_report(f"{sel_ipo} IPO")
                
                if sent:
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        st.metric("Hype Score", f"{sent['score']}/100")
                        st.progress(sent['score']/100)
                    with c2:
                        st.write(f"**Verdict:** {sent['rating']}")
                        st.caption("Based on Reddit discussions and Financial News coverage.")
                        
                st.markdown("---")
                # 3. PEER COMPARE (Proxy for Fundamentals)
                st.subheader("🏢 Fundamentals Check (Peer Comparison)")
                peer = st.text_input("Compare with Listed Competitor (e.g. ZOMATO)", placeholder="Symbol...")
                if peer:
                    pdata = get_stock_fundamentals(peer)
                    if pdata:
                        st.success(f"**{peer.upper()}** (Sector Proxy)")
                        st.write(f"Competitor P/E Ratio: **{pdata['metrics']['PE']:.2f}**")
                        st.caption("If the IPO price implies a higher P/E than this competitor, it might be overpriced.")

# --- PAGE 3: MUTUAL FUNDS ---
elif page == "💰 Mutual Funds":
    st.title("Mutual Fund Analyzer")
    st.info("Track long-term returns and recent news updates.")
    
    obj = Mftool()
    schemes = obj.get_scheme_codes()
    s_name = st.selectbox("Select Fund", list(schemes.values()), index=None, placeholder="Search Axis, HDFC, SBI...")
    
    if s_name:
        if st.button("Analyze Fund"):
            code = list(schemes.keys())[list(schemes.values()).index(s_name)]
            with st.spinner("Fetching NAV History & Returns..."):
                df, det, ret = get_mf_deep_dive(code)
                sent = get_sentiment_report(f"{det['fund_house']} Mutual Fund")
            
            if df is not None:
                # 1. RETURNS CARD
                st.subheader("📈 Performance Report")
                rc1, rc2, rc3, rc4 = st.columns(4)
                rc1.metric("1 Year Return", f"{ret['1Y']:.2f}%", help="CAGR for last 1 year")
                rc2.metric("3 Year Return", f"{ret['3Y']:.2f}%", help="CAGR for last 3 years")
                rc3.metric("5 Year Return", f"{ret['5Y']:.2f}%", help="CAGR for last 5 years")
                rc4.metric("Since Inception", f"{ret['All']:.2f}%")
                
                # 2. CHART
                fig = px.line(df.tail(365*3), x='date', y='nav', title="3-Year NAV Trend")
                st.plotly_chart(fig, use_container_width=True)
                
                # 3. NEWS & SENTIMENT
                st.markdown("---")
                st.subheader(f"📰 News & Sentiment: {det['fund_house']}")
                
                sc1, sc2 = st.columns([1,2])
                with sc1:
                    if sent:
                        st.metric("Trust Score", f"{sent['score']}/100")
                        st.caption(sent['rating'])
                with sc2:
                    if sent:
                        st.write("**Recent Headlines:**")
                        for i, r in sent['data'].head(3).iterrows():
                            st.markdown(f"• [{r['Title']}]({r['Link']})")
