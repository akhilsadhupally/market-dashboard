import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- 🎨 PAGE CONFIGURATION (Professional Look) ---
st.set_page_config(page_title="Market Pulse Pro", page_icon="🇮🇳", layout="wide")

# --- 🧹 DATA ENGINE (Clean & Simple) ---
@st.cache_data(ttl=300)
def get_stock_data(ticker):
    try:
        symbol = ticker.upper() if ticker.endswith(".NS") else f"{ticker.upper()}.NS"
        stock = yf.Ticker(symbol)
        history = stock.history(period="1mo")
        
        if history.empty:
            return None, None, "No data (Check Symbol)"
            
        current_price = history['Close'].iloc[-1]
        
        # Calculate Change
        prev_close = history['Close'].iloc[-2] if len(history) > 1 else current_price
        change_val = current_price - prev_close
        change_pct = (change_val / prev_close) * 100
        
        return current_price, change_val, change_pct, history, "Success"

    except Exception as e:
        return None, None, None, None, f"Error: {str(e)}"

# --- 🧠 SENTIMENT ENGINE (Universal) ---
@st.cache_data(ttl=1800)
def get_sentiment(query, count=8):
    # Google News RSS (Reliable & Free)
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    try:
        response = requests.get(url)
        # Parse XML manually to avoid external libraries
        items = response.text.split('<item>')[1:count+1] 
        data = []
        analyzer = SentimentIntensityAnalyzer()
        
        for item in items:
            if '<title>' in item:
                title = item.split('<title>')[1].split('</title>')[0]
                link = item.split('<link>')[1].split('</link>')[0] if '<link>' in item else '#'
                score = analyzer.polarity_scores(title)['compound']
                
                # Tag the sentiment
                if score > 0.05: mood = "Positive 🟢"
                elif score < -0.05: mood = "Negative 🔴"
                else: mood = "Neutral ⚪"
                
                data.append({'Title': title, 'Score': score, 'Link': link, 'Mood': mood})
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# --- 📱 APP LAYOUT ---
# Sidebar Navigation
st.sidebar.title("Market Pulse 🇮🇳")
page = st.sidebar.radio("Navigate", ["📈 Stocks", "🚀 IPO Center", "💰 Mutual Funds"])
st.sidebar.markdown("---")
st.sidebar.caption("v2.0 Professional Edition")

# --- PAGE 1: STOCKS 📈 ---
if page == "📈 Stocks":
    st.title("Equity Research Terminal")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        ticker = st.text_input("Symbol", "RELIANCE")
        if st.button("Analyze Stock", type="primary"):
            run_stock = True
        else:
            run_stock = False
            
    if run_stock:
        with st.spinner(f"Analyzing {ticker}..."):
            price, change, pct, history, status = get_stock_data(ticker)
            
        if status == "Success":
            # 1. METRICS ROW (Professional Header)
            m1, m2, m3 = st.columns(3)
            m1.metric("Current Price", f"₹{price:,.2f}", f"{change:+.2f} ({pct:+.2f}%)")
            
            # Simple 50-Day Moving Average Logic (approx)
            avg_price = history['Close'].mean()
            m2.metric("Monthly Average", f"₹{avg_price:,.2f}")
            
            # Volume
            vol = history['Volume'].iloc[-1]
            m3.metric("Latest Volume", f"{vol:,}")
            
            st.markdown("---")
            
            # 2. CHARTS & NEWS
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("Price Action")
                fig = go.Figure(data=[go.Candlestick(x=history.index,
                                open=history['Open'], high=history['High'],
                                low=history['Low'], close=history['Close'], name="Price")])
                
                # Add Moving Average Line
                fig.add_trace(go.Scatter(x=history.index, y=history['Close'].rolling(window=5).mean(), 
                                         mode='lines', name='5-Day Trend', line=dict(color='orange', width=1)))
                
                fig.update_layout(height=450, margin=dict(l=0, r=0, t=0, b=0), template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
                
            with c2:
                st.subheader("Market Chatter")
                news = get_sentiment(ticker + " stock india")
                if not news.empty:
                    avg = news['Score'].mean()
                    st.metric("Sentiment Score", f"{avg:.2f}", delta="Bullish" if avg > 0 else "Bearish")
                    for i, row in news.iterrows():
                        st.markdown(f"**{row['Mood']}** [{row['Title']}]({row['Link']})")

# --- PAGE 2: IPO CENTER 🚀 ---
elif page == "🚀 IPO Center":
    st.title("IPO Grey Market & Sentiment")
    st.info("💡 Tracks buzz, GMP discussions, and subscription news.")
    
    # Pre-defined hot topics
    ipo_query = st.text_input("Search IPO Name (or leave blank for general buzz)", "IPO GMP India")
    
    if st.button("Scan IPO Market"):
        with st.spinner("Scanning Grey Market discussions..."):
            # We search for "IPO Name + GMP" to find grey market discussions
            query = f"{ipo_query} GMP Subscription" if ipo_query != "IPO GMP India" else "Upcoming IPO GMP India"
            df = get_sentiment(query, count=10)
            
        if not df.empty:
            avg = df['Score'].mean()
            
            # Display Big Sentiment Score
            st.markdown("### Market Sentiment Gauge")
            col1, col2, col3 = st.columns(3)
            col1.metric("Buzz Score", f"{avg:.2f}")
            
            if avg > 0.1:
                col2.success("🔥 High Retail Interest")
                col3.success("📈 GMP Likely Positive")
            elif avg < -0.1:
                col2.error("❄️ Low Retail Interest")
                col3.error("📉 GMP Likely Negative")
            else:
                col2.warning("😐 Moderate Interest")
                col3.info("➡️ GMP Stable/Uncertain")
            
            st.markdown("---")
            st.subheader("Latest GMP & Subscription Headlines")
            
            for i, row in df.iterrows():
                # Highlight GMP specific news
                if "GMP" in row['Title'] or "Premium" in row['Title']:
                    st.markdown(f"💰 **{row['Title']}** \n[Read Source]({row['Link']})")
                else:
                    st.markdown(f"📰 {row['Title']}  \n[Read Source]({row['Link']})")
        else:
            st.warning("No active IPO discussions found right now.")

# --- PAGE 3: MUTUAL FUNDS 💰 ---
elif page == "💰 Mutual Funds":
    st.title("Mutual Fund Analyzer")
    st.caption("Track sentiment for Categories or Specific Funds")
    
    mf_list = ["Quant Small Cap", "HDFC Mid Cap", "Parag Parikh Flexi Cap", "SBI Contra Fund", "Nippon India Small Cap"]
    selected_mf = st.selectbox("Select Popular Fund", mf_list)
    custom_mf = st.text_input("Or type another fund name...")
    
    final_query = custom_mf if custom_mf else selected_mf
    
    if st.button("Analyze Fund"):
        with st.spinner(f"Analyzing sentiment for {final_query}..."):
            # Search for Fund reviews and news
            df = get_sentiment(f"{final_query} mutual fund review performance")
            
        if not df.empty:
            avg = df['Score'].mean()
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.metric("Sentiment Score", f"{avg:.2f}")
                if avg > 0.2:
                    st.success("🌟 Highly Recommended by Media")
                elif avg > 0:
                    st.info("✅ Generally Positive")
                else:
                    st.warning("⚠️ Mixed/Negative Reviews")
                    
            with c2:
                st.subheader("What Investors Are Saying")
                for i, row in df.iterrows():
                    st.markdown(f"• [{row['Title']}]({row['Link']})")
