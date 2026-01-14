import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- 🎨 CONFIGURATION ---
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
                pubDate = item.split('<pubDate>')[1].split('</pubDate>')[0] if '<pubDate>' in item else 'Recent'
                score = analyzer.polarity_scores(title)['compound']
                
                if score > 0.05: mood = "Positive"
                elif score < -0.05: mood = "Negative"
                else: mood = "Neutral"
                
                data.append({'Title': title, 'Score': score, 'Link': link, 'Mood': mood, 'Date': pubDate})
        return pd.DataFrame(data)
    except: return pd.DataFrame()

# --- 🏦 MUTUAL FUND ENGINE (Special Tickers) ---
# Map common names to Yahoo's weird codes
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
        # Get 6 months of NAV history
        hist = mf.history(period="6mo")
        return hist
    except: return pd.DataFrame()

# --- 📱 SIDEBAR ---
st.sidebar.title("💎 Market Pulse")
page = st.sidebar.radio("Go to", ["📈 Stocks", "🚀 IPO Center", "💰 Mutual Funds"])
st.sidebar.markdown("---")
st.sidebar.info("Platinum Edition v3.0")

# --- PAGE 1: STOCKS ---
if page == "📈 Stocks":
    st.title("Equity Terminal")
    ticker = st.text_input("Symbol", "ZOMATO")
    
    if st.button("Analyze"):
        with st.spinner("Fetching data..."):
            price, chg, pct, hist, stat = get_stock_data(ticker)
        
        if stat == "Success":
            c1, c2, c3 = st.columns(3)
            c1.metric("Price", f"₹{price:,.2f}", f"{pct:+.2f}%")
            c2.metric("52W High", f"₹{hist['High'].max():,.2f}")
            c3.metric("Volume", f"{hist['Volume'].iloc[-1]:,}")
            
            st.subheader("Price Action")
            fig = go.Figure(data=[go.Candlestick(x=hist.index,
                            open=hist['Open'], high=hist['High'],
                            low=hist['Low'], close=hist['Close'])])
            fig.update_layout(height=400, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("News Sentiment")
            news = get_sentiment(ticker + " stock india")
            if not news.empty:
                st.dataframe(news[['Mood', 'Title']], hide_index=True)

# --- PAGE 2: IPO CENTER ---
elif page == "🚀 IPO Center":
    st.title("IPO Analyzer")
    st.caption("Visualizing the Grey Market Buzz")
    
    ipo_name = st.text_input("Enter IPO Name", "IPO GMP")
    
    if st.button("Scan Buzz"):
        with st.spinner(f"Analyzing sentiment patterns for {ipo_name}..."):
            df = get_sentiment(f"{ipo_name} GMP subscription review", count=15)
            
        if not df.empty:
            avg = df['Score'].mean()
            st.metric("Aggregate Buzz Score", f"{avg:.2f}", 
                      delta="High Hype" if avg > 0.15 else "Low Hype")
            
            # 📊 NEW CHART: Sentiment Pattern
            st.subheader("Sentiment Intensity Pattern")
            st.caption("Each bar represents a news headline. Higher Green = Stronger Positive Hype.")
            
            # Create a bar chart of scores
            fig = px.bar(df, x=df.index, y='Score', color='Score',
                         color_continuous_scale=['red', 'yellow', 'green'],
                         labels={'index': 'Article #', 'Score': 'Sentiment Intensity'},
                         range_y=[-1, 1])
            st.plotly_chart(fig, use_container_width=True)
            
            # Headlines
            st.subheader("Headlines Scanned")
            for i, row in df.iterrows():
                emoji = "🟢" if row['Score'] > 0 else "🔴" if row['Score'] < 0 else "⚪"
                st.markdown(f"{emoji} [{row['Title']}]({row['Link']})")
        else:
            st.warning("No active buzz found.")

# --- PAGE 3: MUTUAL FUNDS ---
elif page == "💰 Mutual Funds":
    st.title("Mutual Fund Tracker")
    
    # Dropdown with specific codes
    fund_name = st.selectbox("Select Fund", list(MF_MAP.keys()))
    
    if st.button("Get Performance"):
        code = MF_MAP[fund_name]
        
        with st.spinner(f"Fetching NAV History for {fund_name}..."):
            hist = get_mf_history(code)
            news = get_sentiment(fund_name + " mutual fund review")
            
        if not hist.empty:
            curr_nav = hist['Close'].iloc[-1]
            prev_nav = hist['Close'].iloc[0]
            returns = ((curr_nav - prev_nav) / prev_nav) * 100
            
            c1, c2 = st.columns(2)
            c1.metric("Current NAV", f"₹{curr_nav:.2f}")
            c2.metric("6-Month Return", f"{returns:+.2f}%")
            
            # 📈 NEW CHART: Historical Returns
            st.subheader("6-Month Performance Trend")
            fig = px.line(hist, y='Close', title=f"{fund_name} NAV Trend")
            fig.update_traces(line_color='#2ecc71', line_width=3) # Green line
            st.plotly_chart(fig, use_container_width=True)
            
            # Sentiment
            if not news.empty:
                st.subheader("What Analysts Are Saying")
                avg = news['Score'].mean()
                st.info(f"Market Sentiment Score: {avg:.2f}")
                for i, row in news.iterrows():
                    st.markdown(f"• [{row['Title']}]({row['Link']})")
        else:
            st.error("Could not fetch data. Try again later.")
