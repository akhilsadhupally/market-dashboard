import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from mftool import Mftool
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import deprecated 

# --- 🎨 CONFIGURATION ---
st.set_page_config(page_title="InvestRight.AI", page_icon="🦁", layout="wide")

# --- 🛠️ DATA LOADING ---
@st.cache_data
def load_stock_data():
    try:
        # RAW GitHub URL
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

# --- 🛠️ ENGINE ROOM (The Logic) ---

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
        
        # Calculate Percentage
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

# 3. EQUITY ENGINE (Upgraded with Fundamentals)
@st.cache_data(ttl=300)
def get_stock_data(ticker):
    try:
        symbol = ticker.upper() if ticker.endswith(".NS") else f"{ticker.upper()}.NS"
        stock = yf.Ticker(symbol)
        history = stock.history(period="3mo") # Fetched 3 months for better peer comparison
        if history.empty: return None, None, None, None, "No Data"
        
        # Price Data
        current = history['Close'].iloc[-1]
        prev = history['Close'].iloc[-2] if len(history) > 1 else current
        change = ((current - prev) / prev) * 100
        
        # Fundamental Data
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

# 4. SOCIAL BUZZ ENGINE
@st.cache_data(ttl=600)
def get_social_buzz(query_term):
    queries = [
        f"site:reddit.com {query_term} discussion review",
        f"site:twitter.com {query_term} sentiment",
        f"{query_term} news india"
    ]
    
    combined_data = []
    analyzer = SentimentIntensityAnalyzer()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for q in queries:
        url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
        try:
            r = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(r.text, 'xml') 
            items = soup.find_all('item')[:4]
            
            for item in items:
                title = item.title.text
                link = item.link.text
                if "reddit" in q: source = "Reddit 🔴"
                elif "twitter" in q: source = "X (Twitter) ⚫"
                else: source = "News 📰"
                
                score = analyzer.polarity_scores(title)['compound']
                combined_data.append({'Title': title, 'Source': source, 'Score': score, 'Link': link})
        except:
            continue

    return pd.DataFrame(combined_data)

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
            with st.spinner("Analyzing Fundamentals & Sentiment..."):
                price, chg, hist, fund, stat = get_stock_data(ticker)
            
            if stat == "Success":
                st.metric(f"{search_label}", f"₹{price:,.2f}", f"{chg:+.2f}%")
                
                st.subheader("📊 Fundamental Snapshot")
                col1, col2, col3, col4 = st.columns(4)
                
                mcap = fund['Market Cap']
                mcap_str = f"₹{mcap/10000000:.0f} Cr" if isinstance(mcap, (int, float)) and mcap > 10000000 else f"{mcap}"

                col1.metric("Market Cap", mcap_str)
                col1.caption(f"Sector: {fund['Sector']}")
                col2.metric("P/E Ratio", f"{fund['P/E Ratio']}")
                col2.caption("Valuation Check")
                col3.metric("52W High", f"₹{fund['52W High']}")
                col3.caption(f"Low: ₹{fund['52W Low']}")
                col4.metric("Div Yield", f"{fund['Dividend Yield']:.2f}%")
                col4.caption("Annual Return")

                with st.expander("📖 Read Business Summary"):
                    st.write(fund['Business Summary'])

                st.markdown("---")
                c1, c2 = st.columns([2, 1])
                
                with c1:
                    st.subheader("Price Chart (1 Mo)")
                    fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'])])
                    fig.update_layout(height=350, margin=dict(l=0,r=0,t=0,b=0))
                    st.plotly_chart(fig, use_container_width=True)

                with c2:
                    st.subheader("🗣️ Social Buzz")
                    buzz_df = get_social_buzz(ticker)
                    if not buzz_df.empty:
                        for i, row in buzz_df.head(4).iterrows():
                            color = "green" if row['Score'] > 0 else "red" if row['Score'] < 0 else "grey"
                            st.markdown(f"**{row['Source']}** [{row['Title'][:50]}...]({row['Link']}) <span style='color:{color};'>●</span>", unsafe_allow_html=True)
                    else:
                        st.write("No chatter found.")

# --- PAGE 2: IPO ---
elif page == "🚀 IPO & GMP":
    st.title("🚀 IPO Intelligence")
    
    with st.spinner("Fetching Live GMP Data..."):
        ipo_df = get_ipo_dashboard_data()

    if not ipo_df.empty:
        st.subheader("🔥 Live GMP Dashboard")
        st.dataframe(
            ipo_df[['IPO Name', 'Price', 'GMP', 'GMP %']],
            column_config={
                "GMP %": st.column_config.ProgressColumn("Expected Gain", format="%.1f%%", min_value=-10, max_value=100),
                "GMP": st.column_config.NumberColumn("GMP (₹)")
            },
            hide_index=True,
            use_container_width=True
        )

        st.markdown("---")

        # --- DEEP DIVE SECTION ---
        st.header("🔍 IPO Deep Dive & Peer Comparison")
        selected_ipo = st.selectbox("Select IPO to Analyze:", options=ipo_df['IPO Name'].unique())
        
        if selected_ipo:
            row = ipo_df[ipo_df['IPO Name'] == selected_ipo].iloc[0]
            
            # 1. IPO METRICS
            c1, c2, c3 = st.columns(3)
            c1.metric("GMP Value", f"₹{row['GMP_Value']}")
            c2.metric("Est. Listing Price", f"₹{row['Price_Value'] + row['GMP_Value']}")
            c3.metric("Listing Gain %", f"{row['GMP %']:.1f}%")
            
            # 2. SECTOR / PEER REPORT (NEW FEATURE)
            st.markdown("---")
            st.subheader("🏢 Sector & Peer Context")
            st.info(f"Since '{selected_ipo}' is not listed yet, compare it with a listed competitor to understand the sector mood.")
            
            # User inputs a peer
            col_peer, col_info = st.columns([1, 2])
            with col_peer:
                peer_ticker = st.text_input("Type a Listed Competitor (Symbol)", placeholder="e.g. ZOMATO, TATASTEEL")
            
            if peer_ticker:
                with st.spinner(f"Analyzing Peer: {peer_ticker}..."):
                    pprice, pchg, phist, pfund, pstat = get_stock_data(peer_ticker)
                
                if pstat == "Success":
                    with col_info:
                        st.success(f"**Sector Proxy: {peer_ticker.upper()}**")
                        st.write(f"The sector is currently trading at a P/E of **{pfund['P/E Ratio']}**. Use this to check if the IPO is overpriced.")
                        st.metric("Peer 3-Month Trend", f"{pchg:+.2f}% (Recent Performance)")
                    
                    # Peer Chart
                    st.caption(f"Performance of {peer_ticker.upper()} (Sector Benchmark)")
                    st.line_chart(phist['Close'], height=250)
                else:
                    st.error("Could not find that competitor. Check the symbol.")

            # 3. SOCIAL BUZZ
            st.markdown("---")
            st.subheader(f"🗣️ Public Sentiment: {selected_ipo}")
            ipo_buzz = get_social_buzz(f"{selected_ipo} IPO")
            
            if not ipo_buzz.empty:
                for i, r in ipo_buzz.iterrows():
                    st.markdown(f"**{r['Source']}**: [{r['Title']}]({r['Link']})")
            else:
                st.warning("No specific discussions found yet.")

# --- PAGE 3: MUTUAL FUNDS ---
elif page == "💰 Mutual Funds":
    st.title("Mutual Fund Comparator ⚔️")
    
    all_schemes = get_all_schemes()
    scheme_names = list(all_schemes.values())
    
    st.info("Select two funds to compare their performance side-by-side.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fund_a_name = st.selectbox("Select Fund A", ["Type to search..."] + scheme_names, key="f1")
    
    with col2:
        fund_b_name = st.selectbox("Select Fund B (Optional)", ["Type to search..."] + scheme_names, key="f2")
    
    # LOGIC: If Fund A is picked
    if fund_a_name != "Type to search...":
        # Get Code A
        code_a = list(all_schemes.keys())[list(all_schemes.values()).index(fund_a_name)]
        
        # If Fund B is ALSO picked -> COMPARE MODE
        if fund_b_name != "Type to search...":
            code_b = list(all_schemes.keys())[list(all_schemes.values()).index(fund_b_name)]
            
            if st.button("Compare Funds 🚀"):
                with st.spinner("Crunching numbers..."):
                    hist_a, det_a = get_mf_data(code_a)
                    hist_b, det_b = get_mf_data(code_b)
                
                if hist_a is not None and hist_b is not None:
                    # 1. COMPARISON TABLE
                    st.subheader("📊 Head-to-Head Stats")
                    comp_data = {
                        "Metric": ["Current NAV", "Fund House", "Category", "Risk Level"],
                        f"{det_a['scheme_name'][:20]}...": [f"₹{hist_a['nav'].iloc[-1]}", det_a['fund_house'], det_a['scheme_category'], det_a['scheme_risk']],
                        f"{det_b['scheme_name'][:20]}...": [f"₹{hist_b['nav'].iloc[-1]}", det_b['fund_house'], det_b['scheme_category'], det_b['scheme_risk']]
                    }
                    st.dataframe(pd.DataFrame(comp_data), hide_index=True, use_container_width=True)
                    
                    # 2. COMPARISON CHART
                    st.subheader("📈 Performance War (1 Year)")
                    
                    # Align Data
                    df_a = hist_a.tail(365)[['date', 'nav']].rename(columns={'nav': 'Fund A'})
                    df_b = hist_b.tail(365)[['date', 'nav']].rename(columns={'nav': 'Fund B'})
                    
                    # Merge on Date to plot together
                    merged = pd.merge(df_a, df_b, on='date', how='inner')
                    
                    # Plot
                    fig = px.line(merged, x='date', y=['Fund A', 'Fund B'], title="NAV Trajectory")
                    st.plotly_chart(fig, use_container_width=True)
                    
        # If ONLY Fund A picked -> SINGLE MODE
        else:
            if st.button("Analyze Fund A"):
                with st.spinner("Fetching Data..."):
                    hist, details = get_mf_data(code_a)
                if hist is not None:
                    curr = hist['nav'].iloc[-1]
                    st.subheader(f"{details['scheme_name']}")
                    st.metric("Current NAV", f"₹{curr}", f"Risk: {details.get('scheme_risk', 'N/A')}")
                    fig = px.line(hist.tail(365), x='date', y='nav', title="1-Year Performance")
                    fig.update_traces(line_color='#8e44ad', line_width=3)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Social Buzz
                    st.markdown("---")
                    st.subheader("🗣️ Community Sentiment")
                    mf_buzz = get_social_buzz(f"{details['fund_house']} Mutual Fund")
                    if not mf_buzz.empty:
                        for i, r in mf_buzz.iterrows():
                            st.markdown(f"**{r['Source']}**: [{r['Title']}]({r['Link']})")
