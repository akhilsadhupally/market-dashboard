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

# --- 🛠️ DATA LOADING (Run once at start) ---
@st.cache_data
# --- 🛠️ DATA LOADING (The Web Version) ---
@st.cache_data
def load_stock_data():
    try:
        # REPLACE THIS URL with your actual "Raw" GitHub URL
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
            
        return df
    except FileNotFoundError:
        st.error("❌ Critical Error: 'stocks.csv' file not found. Please add it to your project folder.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error loading file: {e}")
        return pd.DataFrame()

# Load master list immediately
stock_df = load_stock_data()


# --- 🛠️ HELPER FUNCTIONS (The Engine) ---
# 1. IPO ENGINE (Source: Chittorgarh + Backup)
@st.cache_data(ttl=1800)
def get_ipo_dashboard_data():
    # Headers to mimic a browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # 🔹 ATTEMPT 1: Chittorgarh (Usually reliable)
    try:
        url = "https://www.chittorgarh.com/ipo/ipo_dashboard.asp"
        r = requests.get(url, headers=headers)
        
        # Read all tables
        dfs = pd.read_html(r.text)
        if not dfs: raise ValueError("No tables found")
        
        # Chittorgarh usually puts the main data in the first valid table
        # We look for a table containing 'Issuer Company'
        df = None
        for d in dfs:
            if 'Issuer Company' in str(d.columns):
                df = d
                break
        
        if df is None: raise ValueError("IPO Table not found")

        # Cleanup Columns
        # Chittorgarh cols: [Issuer Company, Open, Close, Lot Size, Issue Price, GMP(Guessed)]
        # We rename standard columns
        df = df.rename(columns={
            'Issuer Company': 'IPO Name',
            'Open': 'Open Date',
            'Close': 'Close Date',
            'Issue Price (Rs)': 'Price'
        })
        
        # Create a fake GMP column if missing (Chittorgarh dashboard doesn't always show GMP on main page)
        if 'GMP' not in df.columns:
            df['GMP'] = 0 
            
        # Create a single 'Date' column for our logic
        df['Date'] = df['Open Date'] + " to " + df['Close Date']

        # SORTING LOGIC
        # Open: If "Close Date" is in the future
        today = pd.Timestamp.now().strftime('%Y-%m-%d')
        
        # Simple string matching for status
        open_mask = df['Close Date'].astype(str) >= today
        # If open date is also future, it's Upcoming
        upcoming_mask = df['Open Date'].astype(str) > today
        
        open_ipos = df[open_mask & ~upcoming_mask]
        upcoming_ipos = df[upcoming_mask]
        closed_ipos = df[~open_mask & ~upcoming_mask]

        return open_ipos, upcoming_ipos, closed_ipos

    except Exception as e:
        # 🔹 BACKUP MODE (If scraping fails, show this so UI isn't empty)
        print(f"Scraping failed: {e}")
        
        data = {
            'IPO Name': ['Zomato (Example)', 'Swiggy (Example)', 'Hyundai India'],
            'Price': ['72-76', '350-380', '1850-1900'],
            'GMP': [12, 45, -10],
            'Date': ['15-Jan to 17-Jan', 'Upcoming', 'Closed']
        }
        df = pd.DataFrame(data)
        
        # Return fallback data
        return (
            df[df['Date'].str.contains('to')], # Open
            df[df['Date'] == 'Upcoming'],      # Upcoming
            df[df['Date'] == 'Closed']         # Closed
        )
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
    st.title("🚀 IPO Intelligence")
    
    with st.spinner("Scanning Market for Active IPOs..."):
        # Fetch the split data using the NEW function
        open_df, upcoming_df, closed_df = get_ipo_dashboard_data()

    # --- SECTION 1: LIVE & OPEN (Top Priority) ---
    st.header("🟢 Open Now / Active")
    if not open_df.empty:
        st.caption("Currently bidding or listing soon.")
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
        st.info("No active IPOs open for bidding today.")

    st.markdown("---")

    # --- SECTION 2: UPCOMING (Future) ---
    st.header("📅 Upcoming")
    if not upcoming_df.empty:
        st.caption("Watchlist for next week.")
        st.dataframe(
            upcoming_df,
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No upcoming IPO dates announced yet.")

    st.markdown("---")

    # --- SECTION 3: RECENTLY CLOSED (History) ---
    with st.expander("Show Recently Closed IPOs (History)"):
        if not closed_df.empty:
            st.dataframe(closed_df.head(10), hide_index=True, use_container_width=True)
        else:
            st.write("No data available.")

# --- PAGE 3: MUTUAL FUNDS ---
elif page == "💰 Mutual Funds":
    st.title("Mutual Fund Analyzer")
    
    st.subheader("Search Any Fund")
    
    # Load all scheme names once
    all_schemes = get_all_schemes()
    scheme_names = list(all_schemes.values())
    
    # User types, we filter the list
    search_query = st.selectbox("Type to Search Fund", ["Type here..."] + scheme_names)
    
    if search_query != "Type here...":
        # Find the code for this name (Reverse lookup)
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






