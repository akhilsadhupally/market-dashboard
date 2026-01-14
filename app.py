import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- 🔐 CONFIGURATION ---
API_KEY = "8a6b36ff930547d9bc06d75c20a8ee77"

st.set_page_config(page_title="Akhil's Market Terminal", page_icon="🇮🇳", layout="wide")

# --- 📡 PRECISE DATA ENGINE ---
def get_stock_data(symbol):
    # 1. Clean the symbol (Remove .NS because we specify exchange=NSE)
    clean_symbol = symbol.replace(".NS", "").strip()
    
    # 2. The ONE correct URL for Indian Stocks
    url = f"https://api.twelvedata.com/time_series?symbol={clean_symbol}&exchange=NSE&interval=1day&outputsize=30&apikey={API_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()

        # 🚨 DEBUGGER: If it fails, return the EXACT error message from the server
        if data.get("status") == "error":
            return None, None, f"Server Said: {data.get('message')}"

        # If success, process data
        if "values" in data:
            df = pd.DataFrame(data['values'])
            df['datetime'] = pd.to_datetime(df['datetime'])
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col].astype(float)
            return df['close'].iloc[0], df, "Success"
            
    except Exception as e:
        return None, None, f"Crash Error: {str(e)}"
    
    return None, None, "Unknown Error"

# --- 📰 NEWS ENGINE ---
@st.cache_data(ttl=1800)
def get_news(symbol_query):
    clean_query = symbol_query.replace(".NS", "")
    url = f"https://news.google.com/rss/search?q={clean_query}+stock+news+india&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        response = requests.get(url)
        items = response.text.split('<item>')[1:6]
        news_data = []
        analyzer = SentimentIntensityAnalyzer()
        
        for item in items:
            if '<title>' in item:
                title = item.split('<title>')[1].split('</title>')[0]
                link = item.split('<link>')[1].split('</link>')[0] if '<link>' in item else '#'
                score = analyzer.polarity_scores(title)['compound']
                news_data.append({'Title': title, 'Score': score, 'Link': link})
        return pd.DataFrame(news_data)
    except:
        return pd.DataFrame()

# --- 📱 APP UI ---
st.title("🇮🇳 Akhil's Live Terminal (Safe Mode)")
st.caption("Status: Connected to TwelveData API 🟢")

with st.sidebar:
    ticker = st.text_input("Symbol", "TATASTEEL")
    if st.button("Fetch Data"):
        run_app = True
    else:
        run_app = False

if run_app:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"📊 {ticker.upper()}")
        with st.spinner("Connecting..."):
            price, history, status = get_stock_data(ticker)
        
        if status != "Success":
            # 🛑 This will show us the REAL problem
            st.error(f"❌ {status}")
            st.info("💡 If it says 'limit reached', wait 1 minute.")
        else:
            st.metric("Live Price", f"₹{price:,.2f}")
            fig = go.Figure(data=[go.Candlestick(x=history['datetime'],
                            open=history['open'], high=history['high'],
                            low=history['low'], close=history['close'])])
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📰 Sentiment")
        news_df = get_news(ticker)
        if not news_df.empty:
            avg = news_df['Score'].mean()
            st.info(f"Sentiment Score: {avg:.2f}")
            for i, row in news_df.iterrows():
                st.markdown(f"• [{row['Title']}]({row['Link']})")
