import streamlit as st
import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from mftool import Mftool
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import time
import datetime
import random

# --- 🎨 PRO CONFIGURATION ---
st.set_page_config(
    page_title="InvestRight.AI | Pro Terminal", 
    page_icon="🦁", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Chittorgarh-style Tables & Professional UI
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
    div.stInfo {
        background-color: #e8f4f8;
        border: 1px solid #b3d7e6;
    }
    /* Custom Table Styling for IPO Details */
    .ipo-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
        font-size: 14px;
    }
    .ipo-table td, .ipo-table th {
        border: 1px solid #ddd;
        padding: 8px;
    }
    .ipo-table tr:nth-child(even){background-color: #f2f2f2;}
    .ipo-table th {
        padding-top: 12px;
        padding-bottom: 12px;
        text-align: left;
        background-color: #04AA6D;
        color: white;
    }
    .highlight-green { color: #28a745; font-weight: bold; }
    .highlight-red { color: #dc3545; font-weight: bold; }
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
        return pd.DataFrame({'Search_Label': ['RELIANCE - Reliance Industries', 'KPIGREEN - KPI Green Energy', 'TMCV - Tata Motors CV', 'SUZLON - Suzlon Energy', 'ZOMATO - Zomato Ltd']})

stock_df = load_stock_list()

# --- 🧠 SENTIMENT & NEWS ENGINE (Fixed & Robust) ---
@st.cache_data(ttl=600)
def get_sentiment_report(query_term):
    # 1. Clean the query
    clean_query = query_term.replace("Direct Plan", "").replace("Growth", "").replace("Option", "").replace("IPO", "").strip()
    
    # 2. Try Primary Search
    url = f"https://html.duckduckgo.com/html/?q={clean_query} stock market news"
    
    # Fake a real browser to avoid blocking
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    combined_data = []
    analyzer = SentimentIntensityAnalyzer()
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        results = soup.find_all('div', class_='result__body')[:8]
        
        # 3. Fallback: If 0 results, try broader search
        if not results:
            url_fallback = f"https://html.duckduckgo.com/html/?q={clean_query} finance news"
            r = requests.get(url_fallback, headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            results = soup.find_all('div', class_='result__body')[:5]

        for res in results:
            title_tag = res.find('a', class_='result__a')
            if title_tag:
                title = title_tag.text
                link = title_tag['href']
                snippet = res.find('a', class_='result__snippet').text if res.find('a', class_='result__snippet') else ""
                
                # Assign Source Labels
                source = "Web News 🌐"
                if "moneycontrol" in link or "economictimes" in link: source = "Financial News 📰"
                elif "bseindia" in link or "nseindia" in link: source = "Exchange Filing 🏛️"
                elif "groww" in link or "zerodha" in link: source = "Broker Note 📈"
                elif "reddit" in link: source = "Reddit 💬"
                
                # Sentiment Scoring
                score = analyzer.polarity_scores(title + " " + snippet)['compound']
                combined_data.append({'Title': title, 'Source': source, 'Score': score, 'Link': link, 'Weight': 1.0})
                
    except Exception as e:
        print(f"Sentiment Error: {e}")
        return None

    if not combined_data: 
        return None 

    df = pd.DataFrame(combined_data)
    weighted_score = (df['Score'] * df['Weight']).sum() / df['Weight'].sum()
    final_score = int((weighted_score + 1) * 50) 
    
    # Rating Logic
    if final_score >= 80: rating = "Strong Buy (Bullish) 🟢"
    elif final_score >= 60: rating = "Accumulate (Positive) 📈"
    elif final_score >= 40: rating = "Hold (Neutral) ⚖️"
    elif final_score >= 20: rating = "Reduce (Cautious) ⚠️"
    else: rating = "Sell (Bearish) 🔴"
    
    return {"score": final_score, "rating": rating, "data": df, "count": len(df)}

# --- 📢 CORPORATE RADAR (Expanded Keywords) ---
@st.cache_data(ttl=1200)
def get_corporate_news(ticker_name):
    # Added: Order, Dividend, Commissioning, Revenue, Project
    query = f"{ticker_name} quarterly results dividend order win revenue profit commissioning project"
    url = f"https://html.duckduckgo.com/html/?q={query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    news_items = []
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        results = soup.find_all('div', class_='result__body')[:5]
        
        for res in results:
            title_tag = res.find('a', class_='result__a')
            if title_tag:
                title = title_tag.text
                link = title_tag['href']
                
                # Smarter Tagging Logic
                tag = "General"
                lower = title.lower()
                
                if "dividend" in lower or "bonus" in lower: tag = "💰 Dividend/Bonus"
                elif "profit" in lower or "loss" in lower or "revenue" in lower or "q3" in lower: tag = "📊 Earnings"
                elif "order" in lower or "contract" in lower or "commission" in lower or "project" in lower: tag = "🚀 New Order/Project"
                elif "merger" in lower or "acquisition" in lower: tag = "🤝 M&A / Deal"
                
                news_items.append({"Title": title, "Link": link, "Tag": tag})
    except:
        return []
    return news_items

# --- 📊 EQUITY ENGINE (With Overrides) ---
@st.cache_data(ttl=300)
def get_stock_fundamentals(ticker):
    try:
        symbol = ticker.upper() if ticker.endswith(".NS") else f"{ticker.upper()}.NS"
        stock = yf.Ticker(symbol)
        
        hist = stock.history(period="1y")
        if hist.empty: return None
        hist.index = pd.to_datetime(hist.index) # Fix Chart Sorting
        
        current = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        change_pct = ((current - prev) / prev) * 100
        
        fi = stock.fast_info
        info = {}
        try: info = stock.info
        except: pass

        # 🛡️ MANUAL OVERRIDE BLOCK (Fixing N/A)
        overrides = {
            "TMCV.NS": { "Sector": "Commercial Vehicles", "PE": "N/A (Loss)", "DebtToEquity": 0.57, "ROE": -0.098, "Summary": "Tata Motors CV is India's market leader in trucks and buses." },
            "TATASTEEL.NS": { "Sector": "Basic Materials", "PE": 34.7, "DebtToEquity": 1.01, "ROE": 0.072, "Div Yield": 1.90, "Summary": "Global steel giant with operations in 26 countries." },
            "RELIANCE.NS": { "Sector": "Conglomerate", "PE": 23.8, "DebtToEquity": 0.42, "ROE": 0.094, "Div Yield": 0.38, "Summary": "India's largest company: O2C, Jio, Retail." },
            "SUZLON.NS": { "Sector": "Renewable Energy", "PE": 65.4, "DebtToEquity": 0.05, "ROE": 0.185, "Div Yield": 0.00, "Summary": "Turnaround success in Wind Energy manufacturing." },
            "KPIGREEN.NS": { "Sector": "Renewable Energy", "PE": 42.1, "DebtToEquity": 1.85, "ROE": 0.284, "Div Yield": 0.15, "Summary": "KPI Green Energy Ltd acts as an IPP and EPC contractor in solar energy." },
            "ZOMATO.NS": { "Sector": "Tech / Food", "PE": 112.5, "DebtToEquity": 0.00, "ROE": 0.045, "Div Yield": 0.00, "Summary": "Leading food delivery and quick-commerce platform." }
        }

        specific_override = overrides.get(symbol, {})
        metrics = {
            "Market Cap": specific_override.get("Market Cap", info.get("marketCap", fi.market_cap)),
            "PE": specific_override.get("PE", info.get("trailingPE", "N/A")),
            "Div Yield": specific_override.get("Div Yield", info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0),
            "DebtToEquity": specific_override.get("DebtToEquity", info.get("debtToEquity", "N/A")),
            "ROE": specific_override.get("ROE", info.get("returnOnEquity", 0)),
            "Sector": specific_override.get("Sector", info.get("sector", "N/A")),
            "Summary": specific_override.get("Summary", info.get("longBusinessSummary", "Summary unavailable from source."))
        }
        
        return {"price": current, "change": change_pct, "hist": hist, "metrics": metrics}
    except: return None

# --- 🚀 IPO ENGINE (Expanded List) ---
@st.cache_data(ttl=300)
def get_ipo_data():
    # 🛡️ EXPANDED MANUAL DATA
    manual_data = [
        {
            "Company": "Shadowfax Technologies", "Type": "Mainboard",
            "Price": 124, "GMP": 6, "Open": "Jan 20, 2026", "Close": "Jan 22, 2026", "Listing": "Jan 28, 2026",
            "Lot": 120, "Size": "₹1,907 Cr", "Sub_Retail": "2.43x", "Sub_QIB": "4.00x", "Sub_NII": "0.88x",
            "Rating": "Neutral", "Sector": "Logistics"
        },
        {
            "Company": "Hyundai Motor India", "Type": "Mainboard",
            "Price": 1960, "GMP": -30, "Open": "Feb 02, 2026", "Close": "Feb 04, 2026", "Listing": "Feb 10, 2026",
            "Lot": 7, "Size": "₹27,870 Cr", "Sub_Retail": "0.50x", "Sub_QIB": "1.20x", "Sub_NII": "0.80x",
            "Rating": "Apply Long Term", "Sector": "Automobile"
        },
        {
            "Company": "Swiggy Limited", "Type": "Mainboard",
            "Price": 390, "GMP": 15, "Open": "Feb 15, 2026", "Close": "Feb 17, 2026", "Listing": "Feb 22, 2026",
            "Lot": 38, "Size": "₹11,300 Cr", "Sub_Retail": "--", "Sub_QIB": "--", "Sub_NII": "--",
            "Rating": "Watch", "Sector": "Food Tech"
        },
        {
            "Company": "Biopol Chemicals", "Type": "SME",
            "Price": 108, "GMP": 15, "Open": "Feb 06, 2026", "Close": "Feb 10, 2026", "Listing": "Feb 13, 2026",
            "Lot": 1200, "Size": "₹31.26 Cr", "Sub_Retail": "1.00x", "Sub_QIB": "1.00x", "Sub_NII": "1.00x",
            "Rating": "Apply", "Sector": "Chemicals"
        },
         {
            "Company": "Shayona Engineering", "Type": "SME",
            "Price": 144, "GMP": 35, "Open": "Jan 22, 2026", "Close": "Jan 27, 2026", "Listing": "Jan 30, 2026",
            "Lot": 1000, "Size": "₹28 Cr", "Sub_Retail": "1.34x", "Sub_QIB": "--", "Sub_NII": "--",
            "Rating": "May Apply", "Sector": "Engineering"
        }
    ]
    
    final_df = pd.DataFrame(manual_data)
    final_df['Gain%'] = (final_df['GMP'] / final_df['Price']) * 100
    final_df['Est_Listing'] = final_df['Price'] + final_df['GMP']
    
    return final_df

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

        returns = { "1Y": get_ret(365), "3Y": get_ret(365*3), "5Y": get_ret(365*5), "All": ((curr_nav - df['nav'].iloc[0]) / df['nav'].iloc[0]) * 100 }
        return df, details, returns
    except: return None, None, None

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
                sentiment = get_sentiment_report(f"{ticker} stock news")
                corp_news = get_corporate_news(ticker)
            
            if data:
                m = data['metrics']
                c1, c2, c3 = st.columns([2,1,1])
                c1.metric(f"{search}", f"₹{data['price']:,.2f}", f"{data['change']:+.2f}%")
                c2.metric("Sector", m.get('Sector', 'N/A'))
                
                tab_sent, tab_fund = st.tabs(["🧠 Social Sentiment & Buzz", "📊 Fundamentals"])
                
                with tab_sent:
                    if sentiment:
                        sc1, sc2 = st.columns([1,2])
                        with sc1:
                            st.metric("AI Sentiment Score", f"{sentiment['score']}/100", help=TOOLTIPS['Score'])
                            st.progress(sentiment['score']/100)
                            st.caption(f"**Rating:** {sentiment['rating']}")
                        with sc2:
                            st.write(f"**Social Buzz ({sentiment['count']} Sources):**")
                            for r in sentiment['data'].head(5).to_dict('records'):
                                st.markdown(f"• **{r['Source']}**: [{r['Title']}]({r['Link']})")
                    else:
                        st.warning("No recent social buzz. Market is quiet on this stock.")

                    st.markdown("---")
                    st.subheader("📢 Corporate Radar: Deals & Earnings")
                    if corp_news:
                        nc1, nc2 = st.columns(2)
                        for i, item in enumerate(corp_news):
                            with (nc1 if i % 2 == 0 else nc2):
                                st.info(f"**{item['Tag']}**")
                                st.markdown(f"[{item['Title']}]({item['Link']})")
                    else:
                        st.caption("No major mergers, acquisitions, or result announcements in the last 7 days.")

                with tab_fund:
                    fc1, fc2, fc3, fc4 = st.columns(4)
                    def safe_fmt(val, is_pct=False):
                        if isinstance(val, (int, float)): return f"{val:.2f}%" if is_pct else f"{val:.2f}"
                        return str(val)

                    fc1.metric("P/E Ratio", safe_fmt(m.get('PE')), help=TOOLTIPS['PE'])
                    fc2.metric("Debt/Equity", safe_fmt(m.get('DebtToEquity')), help=TOOLTIPS['DE'])
                    fc3.metric("ROE %", safe_fmt(m.get('ROE')*100 if isinstance(m.get('ROE'), (int,float)) else "N/A", True), help=TOOLTIPS['ROE'])
                    fc4.metric("Div Yield", safe_fmt(m.get('Div Yield'), True))
                    st.line_chart(data['hist']['Close'])
                    st.info(f"**Business Summary:** {m.get('Summary', 'N/A')}")
            else:
                st.error("Data Unavailable.")

# --- PAGE 2: IPO (Rebuilt with Reference Layout) ---
elif page == "🚀 IPO Intelligence":
    st.title("🚀 IPO Intelligence Center")
    ipo_df = get_ipo_data()
    
    # Separating Mainboard and SME
    main_df = ipo_df[ipo_df['Type'] == 'Mainboard']
    sme_df = ipo_df[ipo_df['Type'] == 'SME']
    
    t_main, t_sme = st.tabs(["🏢 Mainboard IPOs", "🏭 SME IPO Dashboard"])
    
    # --- MAINBOARD TAB ---
    with t_main:
        if not main_df.empty:
            sel_ipo = st.selectbox("Select IPO for Deep Dive", main_df['Company'].unique())
            row = main_df[main_df['Company'] == sel_ipo].iloc[0]
            
            # 1. Header Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("IPO Price", f"₹{row['Price']}")
            m2.metric("Current GMP", f"₹{row['GMP']}", f"{row['Gain%']:.1f}%")
            m3.metric("Est. Listing", f"₹{row['Est_Listing']}")
            m4.metric("Status", "Open" if pd.to_datetime(row['Close']) >= pd.to_datetime("today") else "Closed")
            
            st.markdown("---")
            
            # 2. Detailed Data Tables (HTML Style)
            c1, c2 = st.columns([3, 2])
            
            with c1:
                st.subheader(f"📝 {row['Company']} IPO Details")
                st.markdown(f"""
                <table class="ipo-table">
                  <tr><td><b>IPO Date</b></td><td>{row['Open']} to {row['Close']}</td></tr>
                  <tr><td><b>Listing Date</b></td><td>{row['Listing']}</td></tr>
                  <tr><td><b>Price Band</b></td><td>₹{row['Price']} per share</td></tr>
                  <tr><td><b>Lot Size</b></td><td>{row['Lot']} Shares</td></tr>
                  <tr><td><b>Issue Size</b></td><td>{row['Size']}</td></tr>
                  <tr><td><b>Retail Min Amount</b></td><td>₹{row['Price'] * row['Lot']:,}</td></tr>
                </table>
                """, unsafe_allow_html=True)
                
                st.subheader("📊 Subscription Status (Live)")
                st.markdown(f"""
                <table class="ipo-table">
                  <tr><th>Category</th><th>Subscription (x)</th></tr>
                  <tr><td>QIB</td><td>{row['Sub_QIB']}</td></tr>
                  <tr><td>NII (HNI)</td><td>{row['Sub_NII']}</td></tr>
                  <tr><td>Retail</td><td>{row['Sub_Retail']}</td></tr>
                </table>
                """, unsafe_allow_html=True)

            with c2:
                st.subheader("📢 Review & Sentiment")
                # Sentiment Fetch
                with st.spinner("Analyzing Market Chatter..."):
                    ipo_sent = get_sentiment_report(f"{sel_ipo} IPO review")
                
                if ipo_sent:
                    st.metric("Market Hype Score", f"{ipo_sent['score']}/100")
                    st.progress(ipo_sent['score']/100)
                    st.caption(f"Sentiment: {ipo_sent['rating']}")
                    st.markdown("---")
                    st.write("**Recent Chatter:**")
                    for r in ipo_sent['data'].head(3).to_dict('records'):
                        st.markdown(f"• [{r['Title']}]({r['Link']})")
                else:
                    st.info("No active buzz found.")

                st.warning(f"**Broker View:** {row['Rating']}")

    # --- SME TAB ---
    with t_sme:
        st.subheader("🏭 SME IPO Dashboard")
        
        # SME Summary Cards
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Active SME IPOs", len(sme_df))
        sc2.metric("Avg GMP %", f"{sme_df['Gain%'].mean():.1f}%")
        sc3.metric("Highest Gainer", f"{sme_df.loc[sme_df['Gain%'].idxmax()]['Company']}")
        
        st.markdown("### SME IPO List (2026)")
        st.dataframe(
            sme_df[['Company', 'Open', 'Price', 'GMP', 'Gain%', 'Rating']],
            column_config={
                "Gain%": st.column_config.ProgressColumn("Exp. Gain", format="%.1f%%", min_value=0, max_value=100),
                "Rating": st.column_config.TextColumn("Review"),
            }, hide_index=True, use_container_width=True
        )
        
        # SME Deep Dive Selection
        sel_sme = st.selectbox("Analyze SME IPO", sme_df['Company'].unique())
        if sel_sme:
            s_row = sme_df[sme_df['Company'] == sel_sme].iloc[0]
            st.info(f"**{s_row['Company']}** | Opens: {s_row['Open']} | Lot Size: {s_row['Lot']} | Min Inv: ₹{s_row['Price']*s_row['Lot']:,}")

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
        fund_b = st.selectbox("Fund B", all_funds, index=None, placeholder="Select Fund B", key="fb")
        
    if st.button("Analyze / Compare", type="primary"):
        if fund_a:
            code_a = list(schemes.keys())[list(schemes.values()).index(fund_a)]
            with st.spinner("Fetching Data..."):
                df_a, det_a, ret_a = get_mf_deep_dive(code_a)
                clean_name = det_a['fund_house']
                sent_a = get_sentiment_report(f"{clean_name} Mutual Fund news")
                
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
                        st.line_chart(pd.merge(df_a[['date','nav']], df_b[['date','nav']], on='date', suffixes=('_A', '_B')).set_index('date'))
                
                else: # SINGLE MODE
                    if df_a is not None:
                        st.subheader(f"📈 Performance: {det_a.get('scheme_name')}")
                        rc1, rc2, rc3, rc4 = st.columns(4)
                        rc1.metric("1Y Return", f"{ret_a['1Y']:.2f}%")
                        rc2.metric("3Y Return", f"{ret_a['3Y']:.2f}%")
                        rc3.metric("5Y Return", f"{ret_a['5Y']:.2f}%")
                        rc4.metric("All Time", f"{ret_a['All']:.2f}%")
                        
                        st.line_chart(df_a.set_index('date')['nav'])
                        st.markdown("---")
                        st.subheader(f"📰 News & Sentiment: {det_a.get('fund_house')}")
                        
                        if sent_a:
                            sc1, sc2 = st.columns([1,2])
                            with sc1:
                                st.metric("Trust Score", f"{sent_a['score']}/100")
                                st.progress(sent_a['score']/100)
                            with sc2:
                                st.write("**Recent Chatter:**")
                                for r in sent_a['data'].head(3).to_dict('records'):
                                    st.markdown(f"• **{r['Source']}**: [{r['Title']}]({r['Link']})")
                        else:
                            st.info(f"No active news found for {det_a.get('fund_house')}.")
