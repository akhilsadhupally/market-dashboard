import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- 🔐 CONFIGURATION ---
# YOUR KEY IS SET BELOW 👇
API_KEY = "8a6b36ff930547d9bc06d75c20a8ee77"

st.set_page_config(page_title="Akhil's Pro Dashboard", page_icon="🇮🇳", layout="wide")

# --- 📡 ROBUST DATA ENGINE (tries 3 methods) ---
@st.cache_data(ttl=300)
def get_stock_data(user_input):
    # Method 1: Clean Symbol + NSE Exchange
    symbol = user_input.upper().replace(".NS", "").strip()
    
    # Try 1: Specific Indian Exchange Request
    url_1 = f"https://api.twelvedata.com/time_series?symbol={symbol}&exchange=NSE&interval=1day&outputsize=30&apikey={API_KEY}"
    
    # Try 2: Global Search (Let API decide)
    url_2 = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1day&outputsize=30&apikey={API_KEY}"
    
    # Try 3: Direct Ticker (e.g. TATASTEEL.NS)
    url_3 = f"https://api.twelvedata.com/time_series?symbol={symbol}.NS&interval=1day&outputsize=30&apikey={API_KEY}"

    for url in [url_1, url_2, url_3]:
        try:
            response = requests.get(url).json()
            
            # CHECK FOR SPECIFIC ERRORS
            if 'code' in response and response['code'] != 200:
                print(f"Attempt failed: {response['message']}")
                continue # Try next URL
                
            if 'values' in response:
                df = pd.DataFrame(response['values'])
                df['datetime'] = pd.to_datetime(df['datetime'])
                for col in ['open', 'high', 'low', 'close']:
                    df[col] = df[col].astype(float)
                current_price = df['close'].iloc[0]
                
                # Success! Return data
                return current_price, df, "Success"
                
        except Exception as e:
            continue

    return None, None, "Could not find stock. API Limit or Symbol Error."

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

# --- 📱 THE DASHBOARD UI ---
st.title("🇮🇳 Akhil's Live Market Terminal")
st.caption("Status: Connected to TwelveData API 🟢")

with st.sidebar:
    ticker = st.text_input("Enter Symbol", "TATASTEEL")
    st.caption("Try: TATASTEEL, RELIANCE, INFY")
    
    if st.button("Fetch Live Data", type="primary"):
        run_app = True
    else:
        run_app = False

if run_app:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"📊 {ticker.upper()}")
        with st.spinner("Connecting to Satellite..."):
            price, history, status = get_stock_data(ticker)
        
        if status != "Success":
            st.error(f"❌ Error: {status}")
            st.info("Note: The Free API allows 8 calls/minute. Wait a moment and try again.")
        else:
            st.metric("Live Price", f"₹{price:,.2f}")
            fig = go.Figure(data=[go.Candlestick(x=history['datetime'],
                            open=history['open'], high=history['high'],
                            low=history['low'], close=history['close'])])
            fig.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
                
    with col2:
        st.subheader("📰 AI Sentiment")
        news_df = get_news(ticker)
        if not news_df.empty:
            avg_score = news_df['Score'].mean()
            if avg_score > 0.05: st.success(f"BULLISH 🚀 ({avg_score:.2f})")
            elif avg_score < -0.05: st.error(f"BEARISH 📉 ({avg_score:.2f})")
            else: st.info(f"NEUTRAL 😐 ({avg_score:.2f})")
            
            for i, row in news_df.iterrows():
                emoji = "🟢" if row['Score'] > 0 else "🔴" if row['Score'] < 0 else "⚪"
                st.markdown(f"{emoji} [{row['Title']}]({row['Link']})")
