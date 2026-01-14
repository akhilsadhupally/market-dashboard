import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from mftool import Mftool
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

import pandas as pd
from flask import Flask, jsonify, request

app = Flask(__name__)

# --- NEW CODE START ---

# 1. Load the Master List
# We load this ONCE when the app starts so it's super fast
try:
    # Read the CSV. We only need the Symbol and Company Name.
    # Note: Ensure your CSV has columns roughly named 'SYMBOL' and 'NAME OF COMPANY'
    df = pd.read_csv('stocks.csv')
    
    # Clean up column names just in case (remove spaces)
    df.columns = df.columns.str.strip()
    
    # Create a simple list of dictionaries: [{'symbol': 'TATASTEEL', 'name': 'Tata Steel'}, ...]
    # Adjust 'SYMBOL' and 'NAME OF COMPANY' if your CSV headers are slightly different
    STOCKS_DATA = df[['SYMBOL', 'NAME OF COMPANY']].to_dict(orient='records')
    print("✅ Stock Master List Loaded Successfully!")
    
except Exception as e:
    print(f"⚠️ Error loading stocks.csv: {e}")
    STOCKS_DATA = []

# 2. Create the Search Endpoint
@app.route('/api/search')
def search_stocks():
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])

    # Filter the list for matches (Limit to top 10 results for speed)
    results = [
        stock for stock in STOCKS_DATA 
        if query in stock['SYMBOL'].lower() or query in stock['NAME OF COMPANY'].lower()
    ]
    return jsonify(results[:10])

# --- NEW CODE END ---

# ... (The rest of your existing app.py code goes here) ...

# --- 🎨 CONFIGURATION ---
st.set_page_config(page_title="InvestRight.AI", page_icon="🦁", layout="wide")

# --- 🛠️ HELPER FUNCTIONS (The Engine) ---

# 1. IPO ENGINE (Scraper + News)
@st.cache_data(ttl=3600)
def get_ipo_gmp():
    url = "https://www.investorgain.com/report/live-ipo-gmp/331/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'class': 'table'})
        data = []
        rows = table.find_all('tr')[1:]
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 3:
                ipo_name = cols[0].text.strip()
                gmp = cols[3].text.strip()
                try:
                    gmp_val = float(gmp.replace('₹', '').replace(',', ''))
                except:
                    gmp_val = 0
                data.append({'IPO Name': ipo_name, 'GMP': gmp_val, 'Status': cols[2].text.strip()})
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

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
    ticker = st.text_input("Enter Symbol", "ZOMATO")
    
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
    st.title("IPO Scanner")
    
    # 1. LIVE GMP TABLE
    st.subheader("Live Grey Market Premium (GMP)")
    with st.spinner("Scraping market..."):
        gmp_df = get_ipo_gmp()
        
    if not gmp_df.empty:
        # Show top 5 hottest
        gmp_df = gmp_df.sort_values(by='GMP', ascending=False)
        st.dataframe(gmp_df.head(10), hide_index=True, use_container_width=True)
    else:
        st.warning("Could not fetch GMP data.")
        
    st.markdown("---")
    
    # 2. SENTIMENT SEARCH
    st.subheader("Check IPO Sentiment")
    ipo_search = st.text_input("Enter IPO Name to check buzz (e.g., Hyundai)", "Hyundai")
    
    if st.button("Check Buzz"):
        news = get_ai_sentiment(f"{ipo_search} IPO GMP subscription")
        if not news.empty:
            avg = news['Score'].mean()
            st.metric("Buzz Score", f"{avg:.2f}", delta="High Hype" if avg > 0.1 else "Low Hype")
            
            # Heatmap Chart
            fig = px.bar(news, x=news.index, y='Score', color='Score', 
                         color_continuous_scale=['red', 'yellow', 'green'], title="Sentiment Intensity")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No recent news found for this IPO.")

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

