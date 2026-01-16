import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from mftool import Mftool
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
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
    </style>
    """, unsafe_allow_html=True)

# --- 📚 EDUCATIONAL TOOLTIPS ---
TOOLTIPS = {
    "PE": "Price-to-Earnings Ratio: Measures if a stock is overvalued. Lower is generally better (cheaper).",
    "DE": "Debt-to-Equity: How much debt the company has vs. shareholder money. >2 is risky.",
    "ROE": "Return on Equity: How efficiently the company uses your money to generate profit. >15% is good.",
    "GMP": "Grey Market Premium: The price unofficial traders are paying before listing. High GMP = High Demand.",
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

# --- 🧠 SENTIMENT ENGINE ---
@st.cache_data(ttl=600)
def get_sentiment_report(query_term):
    queries = [
        f"site:moneycontrol.com {query_term} analysis", 
        f"site:reddit.com {query_term} discussion"
    ]
    
    combined_data = []
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
                weight = 0.6 if "reddit" in q else 1.2 
                score = analyzer.polarity_scores(title)['compound']
                combined_data.append({'Title': title, 'Source': 'News/Social', 'Score': score, 'Link': link, 'Weight': weight})
        except:
            continue
            
    if not combined_data: return None

    df = pd.DataFrame(combined_data)
    weighted_score = (df['Score'] * df['Weight']).sum() / df['Weight'].sum()
    final_score = int((weighted_score + 1) * 50)
    
    if final_score >= 80: rating = "Strong Buy (Bullish) 🟢"
    elif final_score >= 60: rating = "Accumulate (Positive) 📈"
    elif final_score >= 40: rating = "Hold (Neutral) ⚖️"
    elif final_score >= 20: rating = "Reduce (Cautious) ⚠️"
    else: rating = "Sell (Bearish) 🔴"
    
    return {"score": final_score, "rating": rating, "data": df}

# --- 📊 EQUITY ENGINE (ROBUST VERSION) ---
@st.cache_data(ttl=300)
def get_stock_fundamentals(ticker):
    try:
        symbol = ticker.upper() if ticker.endswith(".NS") else f"{ticker.upper()}.NS"
        stock = yf.Ticker(symbol)
        
        # 1. Price Data (Critical)
        hist = stock.history(period="1y")
        if hist.empty: return None # If no price, we can't show anything.
        
        current = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        change_pct = ((current - prev) / prev) * 100
        
        # 2. Fundamentals (Optional - Don't fail if missing)
        metrics = {}
        try:
            info = stock.info
            metrics = {
                "Market Cap": info.get("marketCap", "N/A"),
                "PE": info.get("trailingPE", "N/A"),
                "Div Yield": info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0,
                "52W High": info.get("fiftyTwoWeekHigh", "N/A"),
                "DebtToEquity": info.get("debtToEquity", "N/A"),
                "ROE": info.get("returnOnEquity", 0),
                "Sector": info.get("sector", "N/A"),
                "Summary": info.get("longBusinessSummary", "Summary not available.")
            }
        except:
            # Fallback if Yahoo blocks 'info'
            metrics = {"Summary": "Fundamental data temporarily unavailable."}
            
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
        
        # Calc Gain
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
            with st.spinner(f"Analyzing {ticker}..."):
                data = get_stock_fundamentals(ticker)
                sentiment = get_sentiment_report(f"{ticker} stock")
            
            if data:
                m = data['metrics']
                c1, c2, c3 = st.columns([2,1,1])
                c1.metric(f"{search}", f"₹{data['price']:,.2f}", f"{data['change']:+.2f}%")
                c2.metric("Sector", m.get('Sector', 'N/A'))
                
                tab_fund, tab_news = st.tabs(["📊 Fundamentals", "🧠 Smart Sentiment"])
                
                with tab_fund:
                    # Robust display: Check if data is 'N/A' before formatting
                    fc1, fc2, fc3, fc4 = st.columns(4)
                    
                    pe = m.get('PE')
                    pe_str = f"{pe:.2f}" if isinstance(pe, (int, float)) else "N/A"
                    fc1.metric("P/E Ratio", pe_str, help=TOOLTIPS['PE'])
                    
                    de = m.get('DebtToEquity')
                    de_str = f"{de:.2f}" if isinstance(de, (int, float)) else "N/A"
                    fc2.metric("Debt/Equity", de_str, help=TOOLTIPS['DE'])
                    
                    roe = m.get('ROE')
                    roe_str = f"{roe*100:.2f}%" if isinstance(roe, (int, float)) else "N/A"
                    fc3.metric("ROE %", roe_str, help=TOOLTIPS['ROE'])
                    
                    div = m.get('Div Yield')
                    div_str = f"{div:.2f}%" if isinstance(div, (int, float)) else "N/A"
                    fc4.metric("Div Yield", div_str)
                    
                    st.subheader("Price History (1 Year)")
                    st.line_chart(data['hist']['Close'])
                    st.write(f"**Business Summary:** {m.get('Summary', 'N/A')}")

                with tab_news:
                    if sentiment:
                        st.metric("Sentiment Score", f"{sentiment['score']}/100")
                        st.caption(sentiment['rating'])
                        st.write("Recent Headlines:")
                        for r in sentiment['data'].head(3).to_dict('records'):
                            st.markdown(f"• [{r['Title']}]({r['Link']})")
                    else:
                        st.info("No recent news found.")
            else:
                st.error("Could not fetch data. The stock symbol might be delisted or blocked by the API.")

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
                st.subheader("🏢 Fundamentals Check")
                st.info("Since this IPO is not listed, compare it with a similar LISTED company.")
                
                peer = st.text_input("Type Competitor Symbol (e.g. TATASTEEL)", placeholder="Enter Symbol...")
                
                if peer:
                    with st.spinner(f"Analyzing {peer}..."):
                        pdata = get_stock_fundamentals(peer)
                    if pdata:
                        st.success(f"**{peer.upper()}** (Sector Benchmark)")
                        pe = pdata['metrics'].get('PE')
                        pe_show = f"{pe:.2f}" if isinstance(pe, (int, float)) else "N/A"
                        st.write(f"Competitor P/E Ratio: **{pe_show}**")
                        st.caption("If the IPO's valuation is higher than this, be cautious.")
                    else:
                        st.error("Competitor symbol not found. Try adding '.NS' (e.g. ZOMATO.NS)")

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
                
                else: # SINGLE MODE (FIXED: Added 3Y/5Y Returns here)
                    if df_a is not None:
                        st.subheader(f"📈 Performance: {det_a.get('scheme_name')}")
                        
                        # The requested metrics are now HERE 👇
                        rc1, rc2, rc3, rc4 = st.columns(4)
                        rc1.metric("1Y Return", f"{ret_a['1Y']:.2f}%")
                        rc2.metric("3Y Return", f"{ret_a['3Y']:.2f}%")
                        rc3.metric("5Y Return", f"{ret_a['5Y']:.2f}%")
                        rc4.metric("All Time", f"{ret_a['All']:.2f}%")
                        
                        st.line_chart(df_a.set_index('date')['nav'])
                        st.write(f"**Category:** {det_a.get('scheme_category', 'N/A')}")
                        st.write(f"**Fund House:** {det_a.get('fund_house', 'N/A')}")
