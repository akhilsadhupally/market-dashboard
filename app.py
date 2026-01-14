import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- PAGE CONFIG ---
st.set_page_config(page_title="Akhil's Market Terminal", page_icon="🇮🇳", layout="wide")

# --- 🕵️‍♂️ STEALTH SESSION (The Anti-Block Trick) ---
def get_session():
    session = requests.Session()
    # This 'User-Agent' makes us look like a real Chrome browser, not a bot
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    return session

# --- 📡 DATA ENGINE (Yahoo Finance) ---
@st.cache_data(ttl=300)
def get_stock_data(ticker):
    try:
        # Force the .NS suffix for India
        symbol = ticker.upper() if ticker.endswith(".NS") else f"{ticker.upper()}.NS"
        
        # Use our stealth session
        session = get_session()
        stock = yf.Ticker(symbol, session=session)
        
        # 1. Get History (1 Month)
        # We handle the "No Data" error explicitly
        history = stock.history(period="1mo")
        
        if history.empty:
            return None, None, "No data found (Yahoo might be blocking)"
            
        current_price = history['Close'].iloc[-1]
        return current_price, history, "Success"

    except Exception as e:
        return None, None, f"Error: {str(e)}"

# --- 📰 NEWS ENGINE ---
@st.cache_data(ttl=1800)
def get_news(ticker):
    # Search Google News
    clean_ticker = ticker.replace(".NS", "")
    url = f"https://news.google.com/rss/search?q={clean_ticker}+stock+news+india&hl=en-IN&gl=IN&ceid=IN:en"
    
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
st.title("🇮🇳 Akhil's Stealth Terminal")
st.caption("Powered by Yahoo Finance (Stealth Mode)")

with st.sidebar:
    ticker_input = st.text_input("Symbol", "TATASTEEL")
    if st.button("Fetch Data", type="primary"):
        run_app = True
    else:
        run_app = False

if run_app:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"📊 {ticker_input.upper()}")
        
        with st.spinner("Talking to Yahoo..."):
            price, history, status = get_stock_data(ticker_input)
        
        if status != "Success":
            st.error(f"❌ {status}")
            st.warning("⚠️ If this fails repeatedly, Yahoo is blocking the Cloud IP. (Works 100% on Local Laptop).")
        else:
            st.metric("Live Price", f"₹{price:,.2f}")
            
            # Draw Chart
            fig = go.Figure(data=[go.Candlestick(x=history.index,
                            open=history['Open'], high=history['High'],
                            low=history['Low'], close=history['Close'])])
            fig.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📰 Sentiment")
        news_df = get_news(ticker_input)
        if not news_df.empty:
            avg = news_df['Score'].mean()
            if avg > 0.05: st.success(f"BULLISH 🚀 ({avg:.2f})")
            elif avg < -0.05: st.error(f"BEARISH 📉 ({avg:.2f})")
            else: st.info(f"NEUTRAL 😐 ({avg:.2f})")
            
            for i, row in news_df.iterrows():
                emoji = "🟢" if row['Score'] > 0 else "🔴" if row['Score'] < 0 else "⚪"
                st.markdown(f"{emoji} [{row['Title']}]({row['Link']})")
