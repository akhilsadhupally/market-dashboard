import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from mftool import Mftool
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- 🎨 CONFIGURATION ---
st.set_page_config(page_title="InvestRight.AI", page_icon="🦁", layout="wide")

# --- 🛠️ DATA LOADING (GitHub Version) ---
@st.cache_data
def load_stock_data():
    try:
        # RAW GitHub URL (Correct)
        url = "https://raw.githubusercontent.com/akhilsadhupally/market-dashboard/refs/heads/main/stocks.csv"
        
        # Read directly from the internet
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        
        if 'SYMBOL' in df.columns:
            df['Search_Label'] = df['SYMBOL'] + " - " + df['NAME OF COMPANY']
        elif 'Symbol' in df.columns:
            df['Search_Label'] = df['Symbol'] + " - " + df['Company Name']
        else:
            return pd.DataFrame()
        return df

    except Exception as e:
        # Fallback if internet fails
        st.warning(f"⚠️ Could not load file from GitHub: {e}")
        data = {
            'Search_Label': [
                'TATASTEEL - Tata Steel Ltd', 
                'TATAMOTORS - Tata Motors Ltd', 
                'RELIANCE - Reliance Industries', 
                'ZOMATO - Zomato Ltd'
            ]
        }
        return pd.DataFrame(data)

# Load master list immediately
stock_df = load_stock_data()


# --- 🛠️ HELPER FUNCTIONS (The Engine) ---
# 1. IPO ENGINE (Google Sheet Bridge)
@st.cache_data(ttl=300)
def get_ipo_dashboard_data():
    try:
        # 🟢 YOUR LINK IS INSERTED HERE 👇
        sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSrY-WLkphYTFIp9FffqR_WfXE_Ta9E0SId-pKqF10ZaUXTZEW1rHY96ilINOkrA6IDaASwWiQl9TMI/pub?output=csv"
        
        # Read the CSV directly
        df = pd.read_csv(sheet_url)
        
        # --- CLEANUP ---
        # Normalize columns (lowercase) to avoid case errors
        df.columns = [c.lower() for c in df.columns]
        
        new_df = pd.DataFrame()
        
        # Map columns dynamically (Find 'name', 'price', 'gmp')
        # We look for columns containing these keywords
        col_name = next((c for c in df.columns if 'ipo' in c or 'company' in c), None)
        col_price = next((c for c in df.columns if 'price' in c), None)
        col_gmp = next((c for c in df.columns if 'gmp' in c or 'premium' in c), None)
        
        if not col_name: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        new_df['IPO Name'] = df[col_name]
        new_df['Price'] = df[col_price] if col_price else "N/A"
        new_df['GMP'] = df[col_gmp] if col_gmp else 0

        # Clean GMP Values
        def clean_gmp(val):
            try:
                # Remove '₹', commas, percentages
                clean = str(val).split('(')[0].replace('₹', '').replace(',', '').replace('%', '').strip()
                return float(clean)
            except:
                return 0.0
        
        new_df['GMP_Value'] = new_df['GMP'].apply(clean_gmp)
        
        # SORT: Highest GMP first
        new_df = new_df.sort_values(by='GMP_Value', ascending=False)
        
        # SPLIT into Categories
        # Top 10 = Active/Hot
        open_ipos = new_df.head(10)
        # Next 10 = Upcoming
        upcoming_ipos = new_df.iloc[10:20]
        # Rest = Closed/History
        closed_ipos = new_df.iloc[20:]
        
        return open_ipos, upcoming_ipos, closed_ipos

    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
# 2. MUTUAL FUND ENGINE
@st.cache_data(ttl=86400)
def get_all_schemes():
    obj = Mftool()
    return obj.get_scheme_codes()

@st.cache_data(ttl=3600)
def get_mf_data(code):
    obj = Mftool()
    try:
        data = obj.get_scheme_historical_nav(code)
        df = pd.DataFrame(data['data'])
        df['nav'] = df['nav'].astype(float)
        df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
        df = df.sort_values('date')
        details = obj.get_scheme_details(code)
        return df, details
    except:
        return None, None

# 3. EQUITY ENGINE
@st.cache_data(ttl=300)
def get_stock_data(ticker):
    try:
        symbol = ticker.upper() if ticker.endswith(".NS") else f"{ticker.upper()}.NS"
        stock = yf.Ticker(symbol)
        history = stock.history(period="1mo")
        if history.empty: return None, None, None, None, "No Data"
        
        current = history['Close'].iloc[-1]
        prev = history['Close'].iloc[-2] if len(history) > 1 else current
        change = ((current - prev) / prev) * 100
        return current, change, history, stock.info, "Success"
    except Exception as e:
        return None, None, None, None, str(e)

# 4. SOCIAL BUZZ ENGINE (Reddit & X via Google)
@st.cache_data(ttl=600)
def get_social_buzz(ticker):
    # We search Google News specifically for Reddit and Twitter threads
    queries = [
        f"site:reddit.com {ticker} stock discussion",
        f"site:twitter.com {ticker} stock analysis",
        f"{ticker} stock news india"
    ]
    
    combined_data = []
    analyzer = SentimentIntensityAnalyzer()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    for q in queries:
        url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
        try:
            r = requests.get(url, headers=headers)
            soup = BeautifulSoup(r.text, 'xml') # XML parser for RSS
            items = soup.find_all('item')[:5]   # Top 5 per source
            
            for item in items:
                title = item.title.text
                link = item.link.text
                
                # Determine Source based on query
                if "reddit" in q: source = "Reddit 🔴"
                elif "twitter" in q: source = "X (Twitter) ⚫"
                else: source = "News 📰"
                
                # Sentiment Score
                score = analyzer.polarity_scores(title)['compound']
                
                combined_data.append({
                    'Title': title,
                    'Source': source,
                    'Score': score,
                    'Link': link
                })
        except:
            continue

    return pd.DataFrame(combined_data)


# --- 📱 APP UI START ---
st.sidebar.title("🦁 InvestRight.AI")
page = st.sidebar.radio("Go to", ["📈 Equity Research", "🚀 IPO & GMP", "💰 Mutual Funds"])

# --- PAGE 1: EQUITY RESEARCH ---
if page == "📈 Equity Research":
    st.title("Equity Intelligence")
    
    # 1. AUTOCOMPLETE SEARCH BAR
    search_label = st.selectbox(
        "Search Stock (Type 'Tata', 'HDFC', etc.)", 
        options=stock_df['Search_Label'].unique() if not stock_df.empty else [],
        index=None, 
        placeholder="Type to search..."
    )

    if search_label:
        ticker = search_label.split(" - ")[0] 
    else:
        ticker = "ZOMATO" 
    
    if st.button("Analyze Stock"):
        with st.spinner("Fetching fundamentals & sentiment..."):
            price, chg, hist, info, stat = get_stock_data(ticker)
        
        if stat == "Success":
            # 1. METRICS
            c1, c2, c3 = st.columns(3)
            c1.metric("Price", f"₹{price:,.2f}", f"{chg:+.2f}%")
            if info:
                c2.metric("52W High", f"₹{info.get('fiftyTwoWeekHigh', 0)}")
                c3.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A')}")
            
            # 2. CHART
            st.subheader("Price Chart")
            fig = go.Figure(data=[go.Candlestick(x=hist.index,
                            open=hist['Open'], high=hist['High'],
                            low=hist['Low'], close=hist['Close'])])
            fig.update_layout(height=400, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig, use_container_width=True)
            
            # 3. COMMUNITY SENTIMENT (New!)
            st.subheader("Community & Social Buzz")
            st.caption("Discussions from Reddit, X (Twitter), and News.")
            
            with st.spinner("Analyzing social discussions..."):
                buzz_df = get_social_buzz(ticker)
            
            if not buzz_df.empty:
                avg_score = buzz_df['Score'].mean()
                
                if avg_score > 0.15: 
                    st.success(f"🔥 Market Mood: BULLISH (Score: {avg_score:.2f})")
                elif avg_score < -0.15: 
                    st.error(f"🩸 Market Mood: BEARISH (Score: {avg_score:.2f})")
                else: 
                    st.info(f"⚖️ Market Mood: NEUTRAL (Score: {avg_score:.2f})")
                
                for i, row in buzz_df.iterrows():
                    icon = row['Source']
                    color = "green" if row['Score'] > 0 else "red" if row['Score'] < 0 else "grey"
                    st.markdown(f"**{icon}** [{row['Title']}]({row['Link']}) <span style='color:{color};'>({row['Score']})</span>", unsafe_allow_html=True)
            else:
                st.write("No recent social discussions found.")

# --- PAGE 2: IPO ---
elif page == "🚀 IPO & GMP":
    st.title("🚀 IPO Intelligence")
    
    with st.spinner("Scanning Market for Active IPOs..."):
        open_df, upcoming_df, closed_df = get_ipo_dashboard_data()

    # SECTION 1: HOT / OPEN
    st.header("🔥 Hot / Active GMP")
    if not open_df.empty:
        st.caption("Top IPOs by GMP Value (Implied Profit)")
        st.dataframe(
            open_df,
            column_config={
                "IPO Name": st.column_config.TextColumn("Company"),
                "GMP": st.column_config.NumberColumn("GMP (₹)", format="₹%d"),
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No active IPOs found.")

    st.markdown("---")

    # SECTION 2: UPCOMING
    st.header("📅 Upcoming Watchlist")
    if not upcoming_df.empty:
        st.dataframe(upcoming_df, hide_index=True, use_container_width=True)
    else:
        st.info("No upcoming IPOs found.")

    st.markdown("---")

    # SECTION 3: HISTORY
    with st.expander("Show All Other IPOs"):
        if not closed_df.empty:
            st.dataframe(closed_df.head(20), hide_index=True, use_container_width=True)
        else:
            st.write("No data available.")

# --- PAGE 3: MUTUAL FUNDS ---
elif page == "💰 Mutual Funds":
    st.title("Mutual Fund Analyzer")
    st.subheader("Search Any Fund")
    
    all_schemes = get_all_schemes()
    scheme_names = list(all_schemes.values())
    
    search_query = st.selectbox("Type to Search Fund", ["Type here..."] + scheme_names)
    
    if search_query != "Type here...":
        code = list(all_schemes.keys())[list(all_schemes.values()).index(search_query)]
        
        if st.button("Fetch Data"):
            with st.spinner("Fetching from AMFI..."):
                hist, details = get_mf_data(code)
                
            if hist is not None:
                curr = hist['nav'].iloc[-1]
                st.markdown(f"### {details['scheme_name']}")
                st.metric("Current NAV", f"₹{curr}", f"Risk: {details.get('scheme_risk', 'N/A')}")
                
                fig = px.line(hist.tail(365), x='date', y='nav', title="1-Year Performance")
                fig.update_traces(line_color='#2ecc71', line_width=3)
                st.plotly_chart(fig, use_container_width=True)
                
                st.info(f"**Fund House:** {details['fund_house']} | **Category:** {details['scheme_category']}")



