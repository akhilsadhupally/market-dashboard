import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- 🔐 CONFIGURATION ---
# I have inserted your valid key below:
API_KEY = "8a6b36ff930547d9bc06d75c20a8ee77"

st.set_page_config(page_title="Akhil's Pro Dashboard", page_icon="🇮🇳", layout="wide")

# --- 📡 REAL DATA ENGINE ---
@st.cache_data(ttl=300)
def get_stock_data(symbol):
    # FIX: Twelve Data wants "TATASTEEL", not "TATASTEEL.NS"
    clean_symbol = symbol.replace(".NS", "")
    
    # We specify "&exchange=NSE" to make sure we get the Indian version
    url = f"https://api.twelvedata.com/time_series?symbol={clean_symbol}&exchange=NSE&interval=1day&outputsize=30&apikey={API_KEY}"
    
    try:
        response = requests.get(url).json()
        
        # Check for API errors
        if 'code' in response and response['code'] == 400:
            return None, None, "Error"
            
        # Parse the data
        if 'values' in response:
            df = pd.DataFrame(response['values'])
            df['datetime'] = pd.to_datetime(df['datetime'])
            
            # Convert text numbers to real floats
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col].astype(float)
                
            current_price = df['close'].iloc[0]
            return current_price, df, "Success"
            
    except Exception as e:
        return None, None, "Error"
    
    return None, None, "Error"

# --- 📰 NEWS ENGINE ---
@st.cache_data(ttl=1800)
def get_news(symbol_query):
    # News works better with just the name (e.g. "Tata Steel")
    clean_query = symbol_query.replace(".NS", "")
    url = f"https://news.google.com/rss/search?q={clean_query}+stock+news+india&hl=en-IN&gl=IN&ceid=IN:en"
    response = requests.get(url)
    
    items = response.text.split('<item>')[1:6]
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
    st.caption("Try: TATASTEEL, RELIANCE, INFY, HDFCBANK")
    
    if st.button("Fetch Live Data", type="primary"):
        run_app = True
    else:
        run_app = False

if run_app:
    # We strip .NS for the API logic to keep it clean
    symbol_input = ticker.upper()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"📊 {symbol_input} (NSE)")
        
        with st.spinner("Connecting to Satellite..."):
            price, history, status = get_stock_data(symbol_input)
        
        if status == "Error":
            st.error(f"❌ Could not find '{symbol_input}' on NSE. Check spelling or API limit.")
        else:
            st.metric("Live Price", f"₹{price:,.2f}")
            
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
        news_df = get_news(symbol_input)
        
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
