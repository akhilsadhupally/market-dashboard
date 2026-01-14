import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- 🎨 CONFIGURATION (Dark Mode Friendly) ---
st.set_page_config(page_title="Market Pulse Platinum", page_icon="💎", layout="wide")

# --- 🧹 DATA ENGINE ---
@st.cache_data(ttl=300)
def get_stock_data(ticker):
    try:
        symbol = ticker.upper() if ticker.endswith(".NS") or ticker.endswith(".BO") else f"{ticker.upper()}.NS"
        stock = yf.Ticker(symbol)
        history = stock.history(period="1mo")
        
        if history.empty: return None, None, None, None, "No data"
            
        current_price = history['Close'].iloc[-1]
        prev_close = history['Close'].iloc[-2] if len(history) > 1 else current_price
        change_val = current_price - prev_close
        change_pct = (change_val / prev_close) * 100
        
        return current_price, change_val, change_pct, history, "Success"
    except Exception as e: return None, None, None, None, str(e)

# --- 🧠 SENTIMENT ENGINE ---
@st.cache_data(ttl=1800)
def get_sentiment(query, count=10):
    # Google News RSS
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        response = requests.get(url)
        items = response.text.split('<item>')[1:count+1]
        data = []
        analyzer = SentimentIntensityAnalyzer()
        
        for item in items:
            if '<title>' in item:
                title = item.split('<title>')[1].split('</title>')[0]
                link = item.split('<link>')[1].split('</link>')[0] if '<link>' in item else '#'
                score = analyzer.polarity_scores(title)['compound']
                
                if score > 0.05: mood = "Positive"
                elif score < -0.05: mood = "Negative"
                else: mood = "Neutral"
                
                data.append({'Title': title, 'Score': score, 'Link': link, 'Mood': mood})
        return pd.DataFrame(data)
    except: return pd.DataFrame()

# --- 🏦 MUTUAL FUND MAP ---
MF_MAP = {
    "Quant Small Cap Direct Growth": "0P0000XW91.BO",
    "HDFC Mid-Cap Opportunities": "0P00005WLZ.BO",
    "Parag Parikh Flexi Cap": "0P0000XW8F.BO",
    "Nippon India Small Cap": "0P0000XVAA.BO",
    "SBI Contra Fund": "0P00009J3J.BO"
}

@st.cache_data(ttl=3600)
def get_mf_history(ticker_code):
    try:
        mf = yf.Ticker(ticker_code)
        return mf.history(period="6mo")
    except: return pd.DataFrame()

# --- 📱 SIDEBAR ---
st.sidebar.title("💎 Market Pulse")
page = st.sidebar.radio("Go to", ["📈 Stocks", "🚀 IPO Center", "💰 Mutual Funds"])
st.sidebar.markdown("---")
st.sidebar.caption("Wall Street Edition v4.0")

# --- PAGE 1: STOCKS ---
if page == "📈 Stocks":
    st.title("Equity Research Terminal")
    ticker = st.text_input("Symbol", "ZOMATO")
    
    if st.button("Analyze Stock"):
        with st.spinner("Crunching numbers..."):
            price, chg, pct, hist, stat = get_stock_data(ticker)
        
        if stat == "Success":
            # Top Metrics
            c1, c2, c3 = st.columns(3)
            c1.metric("Current Price", f"₹{price:,.2f}", f"{pct:+.2f}%")
            c2.metric("High (1M)", f"₹{hist['High'].max():,.2f}")
            c3.metric("Low (1M)", f"₹{hist['Low'].min():,.2f}")
            
            # Chart & Sentiment Split
            col_chart, col_news = st.columns([2, 1])
            
            with col_chart:
                st.subheader("Price Action")
                # Professional Candlestick
                fig = go.Figure(data=[go.Candlestick(x=hist.index,
                                open=hist['Open'], high=hist['High'],
                                low=hist['Low'], close=hist['Close'])])
                fig.update_layout(height=400, margin=dict(l=0,r=0,t=0,b=0), template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
            
            with col_news:
                st.subheader("AI Sentiment Analysis")
                news = get_sentiment(ticker + " stock india")
                
                if not news.empty:
                    # FIX: Explicitly Calculate Average Score
                    avg_score = news['Score'].mean()
                    
                    # Display Big Score Metric
                    if avg_score > 0.05:
                        st.success(f"BULLISH 🚀 ({avg_score:.2f})")
                    elif avg_score < -0.05:
                        st.error(f"BEARISH 📉 ({avg_score:.2f})")
                    else:
                        st.info(f"NEUTRAL 😐 ({avg_score:.2f})")
                    
                    # Show Headlines
                    st.markdown("---")
                    for i, row in news.head(5).iterrows():
                        emoji = "🟢" if row['Score'] > 0 else "🔴" if row['Score'] < 0 else "⚪"
                        st.markdown(f"{emoji} [{row['Title'][:60]}...]({row['Link']})")

# --- PAGE 2: IPO CENTER ---
elif page == "🚀 IPO Center":
    st.title("IPO Grey Market & Sentiment")
    ipo_name = st.text_input("Enter IPO Name", "IPO GMP")
    
    if st.button("Scan Buzz"):
        with st.spinner("Analyzing Grey Market..."):
            df = get_sentiment(f"{ipo_name} GMP subscription review", count=15)
            
        if not df.empty:
            avg = df['Score'].mean()
            st.metric("Hype Score", f"{avg:.2f}", delta="High Demand" if avg > 0.1 else "Low Demand")
            
            # 📊 NEW POLISHED CHART
            st.subheader("Sentiment Heatmap")
            
            # We map colors: Red (-1) -> Yellow (0) -> Green (1)
            fig = px.bar(df, x=df.index, y='Score',
                         color='Score',
                         color_continuous_scale=['#FF4B4B', '#FFD700', '#2ECC71'], # Red-Yellow-Green
                         range_y=[-1, 1], # Fix y-axis to show full range
                         labels={'index': 'Article #', 'Score': 'Sentiment Intensity'},
                         title=f"News Sentiment Pattern for {ipo_name}")
            
            fig.update_layout(showlegend=False, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Headlines")
            for i, row in df.iterrows():
                st.markdown(f"[{row['Title']}]({row['Link']})")
        else:
            st.warning("No data found.")

# --- PAGE 3: MUTUAL FUNDS ---
elif page == "💰 Mutual Funds":
    st.title("Mutual Fund Tracker")
    fund_name = st.selectbox("Select Fund", list(MF_MAP.keys()))
    
    if st.button("Get Performance"):
        code = MF_MAP[fund_name]
        with st.spinner(f"Fetching NAV for {fund_name}..."):
            hist = get_mf_history(code)
            
        if not hist.empty:
            curr = hist['Close'].iloc[-1]
            start = hist['Close'].iloc[0]
            ret = ((curr - start) / start) * 100
            
            st.metric("Current NAV", f"₹{curr:.2f}", f"{ret:+.2f}% (6 Months)")
            
            # Green Line Chart for Growth
            fig = px.line(hist, y='Close', title="6-Month Growth Trajectory")
            fig.update_traces(line_color='#2ecc71', line_width=3)
            fig.update_layout(template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
