import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- 🔐 CONFIGURATION ---
# 👇 PASTE YOUR KEY INSIDE THESE QUOTES 👇
API_KEY = "8a6b36ff930547d9bc06d75c20a8ee77" 

st.set_page_config(page_title="Akhil's Pro Dashboard", page_icon="🇮🇳", layout="wide")

# --- 📡 REAL DATA ENGINE ---
@st.cache_data(ttl=300)
def get_stock_data(symbol):
    # Twelve Data uses .NS for Indian stocks (e.g., TATASTEEL.NS)
    # We fetch 30 days of data for the chart
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1day&outputsize=30&apikey={API_KEY}"
    
    try:
        response = requests.get(url).json()
        
        # Check if the API gave us an error
        if 'code' in response and response['code'] == 400:
            return None, None, "Error"
            
        # Parse the data
        if 'values' in response:
            df = pd.DataFrame(response['values'])
            df['datetime'] = pd.to_datetime(df['datetime'])
            # Convert text numbers to real numbers
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col].astype(float)
                
            current_price = df['close'].iloc[0] # The first row is the newest data
            return current_price, df, "Success"
            
    except Exception as e:
        return None, None, "Error"
    
    return None, None, "Error"

# --- 📰 NEWS ENGINE ---
@st.cache_data(ttl=1800)
def get_news(symbol_query):
    # We use RSS feed which is reliable and free
    url = f"https://news.google.com/rss/search?q={symbol_query}+stock+news+india&hl=en-IN&gl=IN&ceid=IN:en"
    response = requests.get(url)
    
    # Simple XML parsing to find titles and links
    items = response.text.split('<item>')[1:6] # Get top 5 stories
    news_data = []
    analyzer = SentimentIntensityAnalyzer()
    
    for item in items:
        try:
            if '<title>' in item and '<link>' in item:
                title = item.split('<title>')[1].split('</title>')[0]
                link = item.split('<link>')[1].split('</link>')[0]
                score = analyzer.polarity_scores(title)['compound']
                news_data.append({'Title': title, 'Score': score, 'Link': link})
        except:
            continue
            
    return pd.DataFrame(news_data)

# --- 📱 THE DASHBOARD UI ---
st.title("🇮🇳 Akhil's Live Market Terminal")
st.markdown("**Status:** Connected to TwelveData API 🟢")

with st.sidebar:
    ticker = st.text_input("Enter Symbol", "TATASTEEL")
    st.caption("Examples: TATASTEEL, RELIANCE, INFY")
    
    if st.button("Fetch Live Data", type="primary"):
        run_app = True
    else:
        run_app = False

if run_app:
    # Ensure it has .NS for India
    clean_symbol = ticker.upper().replace(".NS", "").strip()
    search_symbol = f"{clean_symbol}.NS"
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"📊 {search_symbol}")
        
        with st.spinner("Connecting to Satellite..."):
            price, history, status = get_stock_data(search_symbol)
        
        if status == "Error":
            st.error(f"❌ Could not find '{search_symbol}'. Check spelling or API Key.")
        else:
            st.metric("Live Price", f"₹{price:,.2f}")
            
            # Draw Real Chart with Plotly
            if history is not None:
                fig = go.Figure(data=[go.Candlestick(x=history['datetime'],
                                open=history['open'],
                                high=history['high'],
                                low=history['low'],
                                close=history['close'])])
                fig.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig, use_container_width=True)
                
    with col2:
        st.subheader("📰 AI Sentiment")
        news_df = get_news(clean_symbol)
        
        if not news_df.empty:
            avg_score = news_df['Score'].mean()
            
            if avg_score > 0.05:
                st.success(f"BULLISH 🚀 ({avg_score:.2f})")
            elif avg_score < -0.05:
                st.error(f"BEARISH 📉 ({avg_score:.2f})")
            else:
                st.info(f"NEUTRAL 😐 ({avg_score:.2f})")
                
            for i, row in news_df.iterrows():
                emoji = "🟢" if row['Score'] > 0 else "🔴" if row['Score'] < 0 else "⚪"
                st.markdown(f"{emoji} [{row['Title']}]({row['Link']})")
        else:
            st.warning("No recent news found.")
