import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from mftool import Mftool
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from collections import Counter
import re
import deprecated 

# --- 🎨 CONFIGURATION ---
st.set_page_config(
    page_title="InvestRight.AI", 
    page_icon="🦁", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 🛠️ DATA LOADING ---
@st.cache_data
def load_stock_data():
    try:
        url = "https://raw.githubusercontent.com/akhilsadhupally/market-dashboard/refs/heads/main/stocks.csv"
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
        data = {'Search_Label': ['TATASTEEL - Tata Steel Ltd', 'RELIANCE - Reliance Industries', 'ZOMATO - Zomato Ltd']}
        return pd.DataFrame(data)

stock_df = load_stock_data()

# --- 🧠 INTELLIGENT SENTIMENT ENGINE (The Core Upgrade) ---
@st.cache_data(ttl=600)
def get_sentiment_report(query_term):
    """
    Scrapes news/social media, analyzes sentiment, AND summarizes the conversation.
    Returns a dictionary with Score, Rating, Summary, and Raw Links.
    """
    queries = [
        f"site:reddit.com {query_term} discussion",
        f"site:twitter.com {query_term} sentiment",
        f"{query_term} market news india",
        f"{query_term} analysis review"
    ]
    
    combined_data = []
    all_titles = []
    analyzer = SentimentIntensityAnalyzer()
    headers = {"User-Agent": "Mozilla/5.0"}

    # 1. FETCH DATA
    for q in queries:
        url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
        try:
            r = requests.get(url, headers=headers, timeout=4)
            soup = BeautifulSoup(r.text, 'xml') 
            items = soup.find_all('item')[:5] # Fetch top 5 per source
            for item in items:
                title = item.title.text
                link = item.link.text
                pub_date = item.pubDate.text if item.pubDate else ""
                
                # Identify Source
                if "reddit" in q: source = "Reddit"
                elif "twitter" in q: source = "X (Twitter)"
                else: source = "News Media"
                
                # Score
                score = analyzer.polarity_scores(title)['compound']
                combined_data.append({'Title': title, 'Source': source, 'Score': score, 'Link': link, 'Date': pub_date})
                all_titles.append(title)
        except:
            continue
            
    if not combined_data:
        return None

    df = pd.DataFrame(combined_data)
    
    # 2. CALCULATE AGGREGATE SCORES
    avg_score = df['Score'].mean() # Range -1 to 1
    
    # Convert to 0-100 Scale for UI
    # -1 becomes 0, 0 becomes 50, +1 becomes 100
    sentiment_score = int((avg_score + 1) * 50)
    
    # Determine Professional Rating
    if sentiment_score >= 75: rating = "Strong Buy / Bullish 🚀"
    elif sentiment_score >= 60: rating = "Positive Accumulate 📈"
    elif sentiment_score >= 40: rating = "Neutral / Hold ⚖️"
    elif sentiment_score >= 25: rating = "Weak / Cautious ⚠️"
    else: rating = "Strong Sell / Bearish 🩸"

    # 3. GENERATE "TALKING POINTS" SUMMARY
    # Extract keywords to see what people are talking about
    text_blob = " ".join(all_titles).lower()
    # Remove common useless words
    ignore_words = ['stock', 'share', 'price', 'market', 'india', 'news', 'analysis', 'review', 'target', 'today', 'latest', 'for', 'the', 'and', 'with', 'ipo', 'fund', 'mutual']
    words = re.findall(r'\w+', text_blob)
    filtered_words = [w for w in words if w not in ignore_words and len(w) > 3]
    
    # Find most common topics (e.g., "profit", "debt", "growth")
    common_topics = [word for word, count in Counter(filtered_words).most_common(5)]
    topic_str = ", ".join(common_topics).title()
    
    summary_text = f"Market discourse is currently focused on **{topic_str}**. "
    if avg_score > 0.2:
        summary_text += "Overall tone is optimistic, driven by positive news coverage and community support."
    elif avg_score < -0.2:
        summary_text += "Sentiment is weighed down by negative headlines or caution in community discussions."
    else:
        summary_text += "Opinions are mixed, indicating a period of consolidation or uncertainty."

    return {
        "score_val": sentiment_score, # 0-100
        "rating": rating,
        "summary": summary_text,
        "topics": common_topics,
        "data": df
    }

# --- 🛠️ OTHER ENGINES (IPO & MF) ---

# 1. IPO ENGINE (Google Sheet Bridge)
@st.cache_data(ttl=300)
def get_ipo_dashboard_data():
    try:
        # 🟢 YOUR GOOGLE SHEET LINK
        sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSrY-WLkphYTFIp9FffqR_WfXE_Ta9E0SId-pKqF10ZaUXTZEW1rHY96ilINOkrA6IDaASwWiQl9TMI/pub?output=csv"
        df = pd.read_csv(sheet_url)
        df.columns = [c.lower() for c in df.columns]
        
        new_df = pd.DataFrame()
        col_name = next((c for c in df.columns if 'ipo' in c or 'company' in c), None)
        col_price = next((c for c in df.columns if 'price' in c), None)
        col_gmp = next((c for c in df.columns if 'gmp' in c or 'premium' in c), None)
        
        if not col_name: return pd.DataFrame()
        
        new_df['IPO Name'] = df[col_name]
        new_df['Price'] = df[col_price] if col_price else "0"
        new_df['GMP'] = df[col_gmp] if col_gmp else 0

        def clean_val(val):
            try:
                return float(str(val).split('(')[0].replace('₹', '').replace(',', '').replace('%', '').strip())
            except:
                return 0.0
        
        new_df['GMP_Value'] = new_df['GMP'].apply(clean_val)
        new_df['Price_Value'] = new_df['Price'].apply(clean_val)
        
        def calc_perc(row):
            if row['Price_Value'] > 0:
                return (row['GMP_Value'] / row['Price_Value']) * 100
            return 0.0
            
        new_df['GMP %'] = new_df.apply(calc_perc, axis=1)
        new_df = new_df.sort_values(by='GMP_Value', ascending=False)
        return new_df

    except Exception as e:
        return pd.DataFrame()

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
        history = stock.history(period="3mo")
        if history.empty: return None, None, None, None, "No Data"
        
        current = history['Close'].iloc[-1]
        prev = history['Close'].iloc[-2] if len(history) > 1 else current
        change = ((current - prev) / prev) * 100
        
        i = stock.info
        fundamentals = {
            "Market Cap": i.get("marketCap", "N/A"),
            "Sector": i.get("sector", "N/A"),
            "P/E Ratio": i.get("trailingPE", "N/A"),
            "Dividend Yield": i.get("dividendYield", 0) * 100 if i.get("dividendYield") else 0,
            "52W High": i.get("fiftyTwoWeekHigh", 0),
            "52W Low": i.get("fiftyTwoWeekLow", 0),
            "Business Summary": i.get("longBusinessSummary", "No summary available.")
        }
        
        return current, change, history, fundamentals, "Success"
    except Exception as e:
        return None, None, None, None, str(e)

# --- 📱 APP UI START ---
st.sidebar.title("🦁 InvestRight.AI")
page = st.sidebar.radio("Go to", ["📈 Equity Research", "🚀 IPO & GMP", "💰 Mutual Funds"])

# --- PAGE 1: EQUITY RESEARCH ---
if page == "📈 Equity Research":
    st.title("Equity Intelligence")
    
    search_label = st.selectbox(
        "Search Stock", 
        options=stock_df['Search_Label'].unique() if not stock_df.empty else [],
        index=None, 
        placeholder="Type to search (e.g., Tata Motors)..."
    )

    if search_label:
        ticker = search_label.split(" - ")[0] 
        if st.button("Analyze Stock"):
            with st.spinner("Compiling Intelligence Report..."):
                price, chg, hist, fund, stat = get_stock_data(ticker)
                # Fetch INTELLIGENT SENTIMENT
                sentiment = get_sentiment_report(f"{ticker} stock")
            
            if stat == "Success":
                # Header
                st.metric(f"{search_label}", f"₹{price:,.2f}", f"{chg:+.2f}%")
                
                # TABS UI
                tab1, tab2, tab3 = st.tabs(["📊 Fundamentals", "📈 Technicals", "🧠 Sentiment Intelligence"])
                
                with tab1:
                    c1, c2, c3, c4 = st.columns(4)
                    mcap = fund['Market Cap']
                    mcap_str = f"₹{mcap/10000000:.0f} Cr" if isinstance(mcap, (int, float)) and mcap > 10000000 else f"{mcap}"
                    c1.metric("Market Cap", mcap_str)
                    c2.metric("P/E Ratio", f"{fund['P/E Ratio']}")
                    c3.metric("52W High", f"₹{fund['52W High']}")
                    c4.metric("Div Yield", f"{fund['Dividend Yield']:.2f}%")
                    st.caption(f"Sector: {fund['Sector']}")
                    with st.expander("Business Summary"):
                        st.write(fund['Business Summary'])

                with tab2:
                    fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'])])
                    fig.update_layout(height=400, margin=dict(l=0,r=0,t=0,b=0))
                    st.plotly_chart(fig, use_container_width=True)

                with tab3:
                    if sentiment:
                        # 1. SCORECARD
                        st.subheader(f"Rating: {sentiment['rating']}")
                        st.progress(sentiment['score_val'] / 100)
                        st.caption(f"Confidence Score: {sentiment['score_val']}/100")
                        
                        st.markdown("---")
                        
                        # 2. AI SUMMARY
                        st.info(f"**💡 AI Summary:** {sentiment['summary']}")
                        
                        # 3. DETAILS
                        c_buzz, c_feed = st.columns([1, 2])
                        with c_buzz:
                            st.write("**Top Talking Points:**")
                            for topic in sentiment['topics']:
                                st.code(topic)

                        with c_feed:
                            st.write("**Source Feeds:**")
                            for i, row in sentiment['data'].head(5).iterrows():
                                icon = "🔴" if row['Source'] == "Reddit" else "⚫" if row['Source'] == "X (Twitter)" else "📰"
                                st.markdown(f"{icon} [{row['Title']}]({row['Link']})")
                    else:
                        st.warning("Not enough data to generate a reliable sentiment rating.")

# --- PAGE 2: IPO ---
elif page == "🚀 IPO & GMP":
    st.title("🚀 IPO Intelligence")
    
    with st.spinner("Fetching Live GMP Data..."):
        ipo_df = get_ipo_dashboard_data()

    if not ipo_df.empty:
        tab_main, tab_dive = st.tabs(["🔥 Active Dashboard", "🔍 Deep Dive & Sentiment"])
        
        with tab_main:
            st.dataframe(
                ipo_df[['IPO Name', 'Price', 'GMP', 'GMP %']],
                column_config={
                    "GMP %": st.column_config.ProgressColumn("Gain %", format="%.1f%%", min_value=-10, max_value=100),
                    "GMP": st.column_config.NumberColumn("GMP (₹)")
                },
                hide_index=True,
                use_container_width=True
            )
        
        with tab_dive:
            selected_ipo = st.selectbox("Select IPO:", options=ipo_df['IPO Name'].unique(), index=None, placeholder="Pick an IPO to analyze...")
            
            if selected_ipo:
                # Fetch Sentiment for IPO
                with st.spinner(f"Analyzing Market Mood for {selected_ipo}..."):
                    row = ipo_df[ipo_df['IPO Name'] == selected_ipo].iloc[0]
                    sentiment = get_sentiment_report(f"{selected_ipo} IPO")
                
                # METRICS
                c1, c2, c3 = st.columns(3)
                c1.metric("GMP Value", f"₹{row['GMP_Value']}")
                c2.metric("Est. Listing", f"₹{row['Price_Value'] + row['GMP_Value']}")
                c3.metric("Gain %", f"{row['GMP %']:.1f}%")
                
                st.markdown("---")
                
                # SENTIMENT REPORT
                st.subheader("🧠 Public Sentiment & Rating")
                
                if sentiment:
                    col_score, col_text = st.columns([1, 2])
                    
                    with col_score:
                        st.metric("Sentiment Score", f"{sentiment['score_val']}/100")
                        st.caption(sentiment['rating'])
                        st.progress(sentiment['score_val'] / 100)
                    
                    with col_text:
                        st.success(f"**Analysis:** {sentiment['summary']}")
                        st.write("Recent Discussions:")
                        for i, r in sentiment['data'].head(3).iterrows():
                            st.markdown(f"- [{r['Title']}]({r['Link']})")
                else:
                    st.info("No sufficient public discussion data found for this IPO yet.")

# --- PAGE 3: MUTUAL FUNDS ---
elif page == "💰 Mutual Funds":
    st.title("Mutual Fund Comparator ⚔️")
    
    all_schemes = get_all_schemes()
    scheme_names = list(all_schemes.values())
    
    st.info("Select a fund to see its Smart Sentiment Rating.")
    
    col1, col2 = st.columns(2)
    with col1:
        fund_a_name = st.selectbox("Select Fund A", options=scheme_names, index=None, placeholder="Search Fund A...", key="f1")
    with col2:
        fund_b_name = st.selectbox("Select Fund B (Optional)", options=scheme_names, index=None, placeholder="Search Fund B...", key="f2")
    
    # LOGIC
    if fund_a_name:
        # Determine mode
        mode = "Compare" if fund_b_name else "Analyze"
        btn_label = "Compare Funds 🚀" if mode == "Compare" else "Analyze Fund A"
        
        if st.button(btn_label, type="primary"):
            with st.spinner("Analyzing Performance & Sentiment..."):
                code_a = list(all_schemes.keys())[list(all_schemes.values()).index(fund_a_name)]
                hist_a, det_a = get_mf_data(code_a)
                
                # Fetch Sentiment for Fund A
                fh_a = det_a.get('fund_house', '')
                sent_a = get_sentiment_report(f"{fh_a} Mutual Fund")

                if mode == "Compare":
                    code_b = list(all_schemes.keys())[list(all_schemes.values()).index(fund_b_name)]
                    hist_b, det_b = get_mf_data(code_b)
            
            if hist_a is not None:
                # TABS
                tabs = st.tabs(["📊 Overview", "🧠 Smart Sentiment", "📈 Performance"])
                
                with tabs[0]:
                    # Overview Table
                    if mode == "Compare" and hist_b is not None:
                        comp_data = {
                            "Metric": ["NAV", "Risk", "Fund House"],
                            f"Fund A": [f"₹{hist_a['nav'].iloc[-1]}", det_a.get('scheme_risk', 'N/A'), det_a.get('fund_house', 'N/A')],
                            f"Fund B": [f"₹{hist_b['nav'].iloc[-1]}", det_b.get('scheme_risk', 'N/A'), det_b.get('fund_house', 'N/A')]
                        }
                        st.dataframe(pd.DataFrame(comp_data), hide_index=True, use_container_width=True)
                    else:
                        st.metric("NAV", f"₹{hist_a['nav'].iloc[-1]}")
                        st.write(f"**Fund House:** {det_a.get('fund_house')}")
                        st.write(f"**Category:** {det_a.get('scheme_category')}")
                
                with tabs[1]:
                    # SENTIMENT TAB (The New Feature)
                    st.subheader(f"Sentiment for: {det_a.get('fund_house')}")
                    
                    if sent_a:
                        c1, c2 = st.columns([1, 2])
                        with c1:
                            st.metric("Trust Score", f"{sent_a['score_val']}/100")
                            st.progress(sent_a['score_val'] / 100)
                            st.caption(sent_a['rating'])
                        with c2:
                            st.info(f"**Community Verdict:** {sent_a['summary']}")
                            st.write("**Key Topics:** " + ", ".join(sent_a['topics']))
                    else:
                        st.warning("No sentiment data available.")

                with tabs[2]:
                    # Chart Logic
                    if mode == "Compare" and hist_b is not None:
                        df_a = hist_a.tail(365)[['date', 'nav']].rename(columns={'nav': 'Fund A'})
                        df_b = hist_b.tail(365)[['date', 'nav']].rename(columns={'nav': 'Fund B'})
                        merged = pd.merge(df_a, df_b, on='date', how='inner')
                        fig = px.line(merged, x='date', y=['Fund A', 'Fund B'], title="Comparative Returns")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        fig = px.line(hist_a.tail(365), x='date', y='nav', title="1-Year Trend")
                        st.plotly_chart(fig, use_container_width=True)
