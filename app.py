import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from mftool import Mftool
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


# ... (The rest of your existing app.py code goes here) ...

# --- 🎨 CONFIGURATION ---
st.set_page_config(page_title="InvestRight.AI", page_icon="🦁", layout="wide")
# --- 🛠️ LOAD MASTER STOCK LIST (New Feature) ---
@st.cache_data
def load_stock_data():
    try:
        # Load the CSV file you saved
        df = pd.read_csv('stocks.csv')
        
        # Clean up column names (remove extra spaces)
        df.columns = df.columns.str.strip()
        
        # Create a "Search Label" so users see "TATASTEEL - Tata Steel Ltd"
        # Adjust column names 'SYMBOL' or 'NAME OF COMPANY' if your CSV is slightly different
        df['Search_Label'] = df['SYMBOL'] + " - " + df['NAME OF COMPANY']
        
        return df
    except Exception as e:
        # If file is missing, return empty so app doesn't crash
        return pd.DataFrame()

# Load data once when app starts
stock_df = load_stock_data()
# --- 🛠️ HELPER FUNCTIONS (The Engine) ---

# 1. IPO ENGINE (Scraper + News)
# 1. IPO ENGINE (Scraper + News)
@st.cache_data(ttl=1800)
def get_ipo_dashboard_data():
    url = "https://www.investorgain.com/report/live-ipo-gmp/331/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        # Method: Use Pandas to automatically find the table
        r = requests.get(url, headers=headers)
        # Use lxml to read tables (make sure lxml is in requirements.txt)
        dfs = pd.read_html(r.text)
        
        if not dfs:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
            
        df = dfs[0] # The first table is usually the correct one
        
        # CLEANUP: Keep only useful columns (Name, GMP, Listing %, Date)
        # We select by index to be safe: 0=Name, 2=Price, 5=GMP, 6=Listing%
        # Note: Websites change layouts, so we try to be generic
        df = df.iloc[:, [0, 2, 5, 7]] 
        df.columns = ['IPO Name', 'Price', 'GMP', 'Date']
        
        # Clean numeric GMP data
        def clean_gmp(x):
            try:
                return float(str(x).replace('₹', '').replace(',', ''))
            except:
                return 0.0

        df['GMP'] = df['GMP'].apply(clean_gmp)
        
        # LOGIC: Sort into Open, Upcoming, Closed
        # "Open" usually has a date range like "14-Jan to 16-Jan"
        open_ipos = df[df['Date'].str.contains('to', case=False, na=False)]
        
        # "Upcoming" usually has a single future date or "Upcoming" text
        upcoming_ipos = df[df['Date'].str.contains('Upcoming', case=False, na=False)]
        
        # Everything else is Closed/Past
        closed_ipos = df[~df.index.isin(open_ipos.index) & ~df.index.isin(upcoming_ipos.index)]
        
        return open_ipos, upcoming_ipos, closed_ipos

    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
# 2. MUTUAL FUND ENGINE (Smart Search)
@st.cache_data(ttl=86400) # Cache list for 24 hours
def get_all_schemes():
    obj = Mftool()
    return obj.get_scheme_codes() # Returns a huge dict {code: name}

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

# 3. EQUITY ENGINE (Yahoo + Sentiment)
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

@st.cache_data(ttl=1800)
def get_ai_sentiment(query):
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        response = requests.get(url)
        items = response.text.split('<item>')[1:10]
        data = []
        analyzer = SentimentIntensityAnalyzer()
        for item in items:
            if '<title>' in item:
                title = item.split('<title>')[1].split('</title>')[0]
                link = item.split('<link>')[1].split('</link>')[0] if '<link>' in item else '#'
                score = analyzer.polarity_scores(title)['compound']
                data.append({'Title': title, 'Score': score, 'Link': link})
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# --- 📱 APP UI ---
st.sidebar.title("🦁 InvestRight.AI")
page = st.sidebar.radio("Go to", ["📈 Equity Research", "🚀 IPO & GMP", "💰 Mutual Funds"])

# --- PAGE 1: EQUITY RESEARCH ---
if page == "📈 Equity Research":
    st.title("Equity Intelligence")
    
    # 1. AUTOCOMPLETE SEARCH BAR
    # This uses the stock_df we loaded at the top
    search_label = st.selectbox(
        "Search Stock (Type 'Tata', 'HDFC', etc.)", 
        options=stock_df['Search_Label'].unique() if not stock_df.empty else [],
        index=None, 
        placeholder="Type to search..."
    )

    # Logic: If user picks something, extract symbol. If not, default to Zomato.
    if search_label:
        ticker = search_label.split(" - ")[0] # Extracts "TATASTEEL" from the string
    else:
        ticker = "ZOMATO" # Default fallback
    
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
            
            # 3. SENTIMENT
            st.subheader("Market Sentiment")
            news = get_ai_sentiment(f"{ticker} stock news india")
            if not news.empty:
                avg = news['Score'].mean()
                if avg > 0.05: st.success(f"Market Mood: BULLISH 🚀 ({avg:.2f})")
                elif avg < -0.05: st.error(f"Market Mood: BEARISH 📉 ({avg:.2f})")
                else: st.info(f"Market Mood: NEUTRAL 😐 ({avg:.2f})")
                
                for i, row in news.head(3).iterrows():
                    st.markdown(f"• [{row['Title']}]({row['Link']})")

# --- PAGE 2: IPO ---
elif page == "🚀 IPO & GMP":
    st.title("🚀 IPO Intelligence Dashboard")
    
    # Create Tabs: One for Prices (GMP), One for Demand (Subscription)
    tab1, tab2 = st.tabs(["💰 Grey Market Premium (GMP)", "📊 Live Subscription Status"])
    
    # --- TAB 1: PRICES ---
    with tab1:
        st.subheader("Market Expectations (GMP)")
        with st.spinner("Fetching latest GMP..."):
            gmp_df = get_ipo_gmp() # Calls your existing function
            
        if not gmp_df.empty:
            # Add status colors
            st.dataframe(gmp_df, use_container_width=True, hide_index=True)
        else:
            st.warning("Could not fetch GMP data.")

    # --- TAB 2: DEMAND (New Feature) ---
    with tab2:
        st.subheader("Real-Time Bidding Status")
        st.caption("Retail (x) = How many times the public applied for 1 share.")
        
        with st.spinner("Checking subscription levels..."):
            sub_df = get_ipo_subscription_status() # Calls the NEW function you added in Step 1
            
        if not sub_df.empty:
            # Highlight Hot IPOs
            st.dataframe(
                sub_df,
                column_config={
                    "IPO Name": st.column_config.TextColumn("Company"),
                    "Retail (x)": st.column_config.ProgressColumn(
                        "Retail Interest", 
                        format="%.2fx",
                        min_value=0, max_value=50, # Sets the progress bar scale
                    ),
                    "Total Subscription (x)": st.column_config.NumberColumn("Total Demand", format="%.2fx")
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.error("Could not fetch Subscription data.")
# --- PAGE 3: MUTUAL FUNDS ---
elif page == "💰 Mutual Funds":
    st.title("Mutual Fund Analyzer")
    
    # 1. SMART SEARCH (The key fix!)
    st.subheader("Search Any Fund")
    
    # Load all scheme names once
    all_schemes = get_all_schemes()
    scheme_names = list(all_schemes.values())
    
    # User types, we filter the list
    search_query = st.selectbox("Type to Search Fund", ["Type here..."] + scheme_names)
    
    if search_query != "Type here...":
        # Find the code for this name
        # (Reverse lookup: Value -> Key)
        code = list(all_schemes.keys())[list(all_schemes.values()).index(search_query)]
        
        if st.button("Fetch Data"):
            with st.spinner("Fetching from AMFI..."):
                hist, details = get_mf_data(code)
                
            if hist is not None:
                # Metrics
                curr = hist['nav'].iloc[-1]
                st.markdown(f"### {details['scheme_name']}")
                st.metric("Current NAV", f"₹{curr}", f"Risk: {details.get('scheme_risk', 'N/A')}")
                
                # Chart
                fig = px.line(hist.tail(365), x='date', y='nav', title="1-Year Performance")
                fig.update_traces(line_color='#2ecc71', line_width=3)
                st.plotly_chart(fig, use_container_width=True)
                
                # Fund Manager
                st.info(f"**Fund House:** {details['fund_house']} | **Category:** {details['scheme_category']}")





