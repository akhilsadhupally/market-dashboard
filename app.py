
import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import plotly.graph_objects as go
import plotly.express as px
from mftool import Mftool
import datetime as dt
import xml.etree.ElementTree as ET

# =========================================================
# INVESTRIGHT.AI - CLEAN PRO VERSION
# =========================================================

st.set_page_config(
    page_title="InvestRight.AI | Market Research Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------
# THEME / CSS
# -------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main {
        background: #F6F8FB;
    }

    h1, h2, h3 {
        color: #111827;
        letter-spacing: -0.03em;
    }

    .block-container {
        padding-top: 1.6rem;
        padding-bottom: 2rem;
        max-width: 1350px;
    }

    [data-testid="stSidebar"] {
        background: #0F172A;
    }

    [data-testid="stSidebar"] * {
        color: #E5E7EB;
    }

    .hero-card {
        padding: 24px;
        border-radius: 20px;
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 55%, #065F46 100%);
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 18px 35px rgba(15, 23, 42, 0.16);
    }

    .hero-title {
        font-size: 34px;
        font-weight: 800;
        margin-bottom: 6px;
        color: white;
    }

    .hero-subtitle {
        font-size: 15px;
        color: #D1D5DB;
        max-width: 900px;
    }

    .soft-card {
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 18px;
        padding: 18px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        margin-bottom: 16px;
    }

    .small-label {
        color: #6B7280;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .insight {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        padding: 14px 16px;
        border-radius: 14px;
        font-size: 14px;
    }

    .positive {
        color: #047857;
        font-weight: 700;
    }

    .negative {
        color: #B91C1C;
        font-weight: 700;
    }

    .neutral {
        color: #374151;
        font-weight: 700;
    }

    .risk-badge {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        background: #FEF3C7;
        color: #92400E;
        font-size: 12px;
        font-weight: 700;
    }

    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        padding: 14px;
        border-radius: 16px;
        box-shadow: 0 5px 14px rgba(15, 23, 42, 0.04);
    }

    .stDataFrame {
        border-radius: 16px;
        overflow: hidden;
    }

    .footer-note {
        font-size: 12px;
        color: #6B7280;
        margin-top: 24px;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------
# CONSTANTS
# -------------------------
TOOLTIPS = {
    "PE": "Price-to-Earnings Ratio. It shows how much investors pay for ₹1 of earnings. Lower is not always better, but very high PE needs growth support.",
    "DE": "Debt-to-Equity. It indicates leverage. Higher debt can increase risk, especially in weak cycles.",
    "ROE": "Return on Equity. It shows how efficiently the company uses shareholder money. Higher is generally better if sustainable.",
    "Sentiment": "A simple news headline sentiment score. Treat this as a market mood indicator, not a buy/sell recommendation.",
    "GMP": "Grey Market Premium is unofficial and can be manipulated. Use only as one signal, never as the main investment reason."
}

DISCLAIMER = "Educational dashboard only. This is not investment advice. Verify financials, risks, RHP, exchange filings and consult a SEBI-registered advisor before investing."

# -------------------------
# HELPERS
# -------------------------
def money(x):
    try:
        return f"₹{float(x):,.2f}"
    except Exception:
        return "N/A"

def pct(x):
    try:
        return f"{float(x):,.2f}%"
    except Exception:
        return "N/A"

def short_text(text, n=220):
    if not text:
        return "Not available."
    text = str(text).strip()
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + "..."

def score_label(score):
    if score >= 70:
        return "Positive"
    if score >= 45:
        return "Neutral"
    return "Cautious"

def style_delta(value):
    try:
        value = float(value)
        return "positive" if value >= 0 else "negative"
    except Exception:
        return "neutral"

def make_line_chart(df, x, y_cols, title, y_title, normalized=False):
    fig = go.Figure()

    for col in y_cols:
        plot_df = df[[x, col]].dropna()
        if normalized and not plot_df.empty:
            base = plot_df[col].iloc[0]
            if base != 0:
                plot_df[col] = (plot_df[col] / base) * 100

        fig.add_trace(
            go.Scatter(
                x=plot_df[x],
                y=plot_df[col],
                mode="lines",
                name=str(col),
                line=dict(width=2.6),
                hovertemplate="%{x}<br>%{y:.2f}<extra></extra>"
            )
        )

    fig.update_layout(
        title=dict(text=title, x=0.02, xanchor="left", font=dict(size=18)),
        height=430,
        margin=dict(l=20, r=20, t=55, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis_title=y_title,
        xaxis_title="",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#EEF2F7")
    return fig

def make_bar_chart(df, x, y, title, y_title, text_auto=True):
    fig = px.bar(df, x=x, y=y, text_auto=".2s" if text_auto else False)
    fig.update_layout(
        title=dict(text=title, x=0.02, xanchor="left", font=dict(size=18)),
        height=360,
        margin=dict(l=20, r=20, t=55, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        yaxis_title=y_title,
        xaxis_title="",
        showlegend=False
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#EEF2F7")
    return fig

def hero(title, subtitle):
    st.markdown(f"""
    <div class="hero-card">
        <div class="hero-title">{title}</div>
        <div class="hero-subtitle">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

# -------------------------
# DATA LAYER
# -------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def load_stock_list():
    """Loads NSE stock list from your GitHub CSV with a small fallback."""
    try:
        url = "https://raw.githubusercontent.com/akhilsadhupally/market-dashboard/refs/heads/main/stocks.csv"
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()

        if {"SYMBOL", "NAME OF COMPANY"}.issubset(df.columns):
            df = df.rename(columns={"SYMBOL": "Symbol", "NAME OF COMPANY": "Company"})
        elif {"Symbol", "Company Name"}.issubset(df.columns):
            df = df.rename(columns={"Company Name": "Company"})

        df["Symbol"] = df["Symbol"].astype(str).str.strip()
        df["Company"] = df["Company"].astype(str).str.strip()
        df["Search_Label"] = df["Symbol"] + " - " + df["Company"]
        return df[["Symbol", "Company", "Search_Label"]].dropna().drop_duplicates()
    except Exception:
        fallback = [
            ("RELIANCE", "Reliance Industries"),
            ("TCS", "Tata Consultancy Services"),
            ("HDFCBANK", "HDFC Bank"),
            ("INFY", "Infosys"),
            ("TATAMOTORS", "Tata Motors"),
            ("SUZLON", "Suzlon Energy"),
            ("KPIGREEN", "KPI Green Energy"),
            ("ZOMATO", "Eternal / Zomato")
        ]
        return pd.DataFrame(fallback, columns=["Symbol", "Company"]).assign(
            Search_Label=lambda d: d["Symbol"] + " - " + d["Company"]
        )

@st.cache_data(ttl=900, show_spinner=False)
def get_google_news_rss(query_term, max_items=8):
    clean_query = str(query_term).replace("Limited", "").replace("Ltd", "").strip()
    rss_url = f"https://news.google.com/rss/search?q={clean_query}+india+business&hl=en-IN&gl=IN&ceid=IN:en"

    items = []
    try:
        r = requests.get(rss_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        root = ET.fromstring(r.content)

        for item in root.findall("./channel/item")[:max_items]:
            title = item.findtext("title", default="").strip()
            link = item.findtext("link", default="").strip()
            pub_date = item.findtext("pubDate", default="").strip()

            lower = title.lower()
            tag = "General"
            if any(k in lower for k in ["dividend", "bonus", "split", "record date", "buyback"]):
                tag = "Corporate action"
            elif any(k in lower for k in ["profit", "loss", "revenue", "quarter", "q1", "q2", "q3", "q4", "results"]):
                tag = "Earnings"
            elif any(k in lower for k in ["order", "contract", "project", "agreement", "mw", "commissioned"]):
                tag = "Order / project"
            elif any(k in lower for k in ["merger", "acquisition", "stake", "deal", "fundraise"]):
                tag = "Deal / M&A"

            source = "News"
            if "moneycontrol" in link.lower():
                source = "Moneycontrol"
            elif "economictimes" in link.lower() or "indiatimes" in link.lower():
                source = "Economic Times"
            elif "livemint" in link.lower():
                source = "Mint"
            elif "bseindia" in link.lower() or "nseindia" in link.lower():
                source = "Exchange"

            items.append({"Title": title, "Source": source, "Tag": tag, "Date": pub_date, "Link": link})

    except Exception:
        return []

    return items

@st.cache_data(ttl=900, show_spinner=False)
def get_news_sentiment(query_term):
    news = get_google_news_rss(query_term)
    if not news:
        return None

    analyzer = SentimentIntensityAnalyzer()
    rows = []
    for item in news:
        compound = analyzer.polarity_scores(item["Title"])["compound"]
        rows.append({**item, "Sentiment": compound})

    df = pd.DataFrame(rows)
    avg = float(df["Sentiment"].mean())
    final_score = int((avg + 1) * 50)
    return {
        "score": final_score,
        "label": score_label(final_score),
        "data": df,
        "count": len(df)
    }

@st.cache_data(ttl=600, show_spinner=False)
def get_stock_fundamentals(ticker, period="5y"):
    symbol = ticker.upper().strip()
    yahoo_symbol = symbol if symbol.endswith(".NS") else f"{symbol}.NS"

    try:
        stock = yf.Ticker(yahoo_symbol)
        hist = stock.history(period=period, auto_adjust=False)

        if hist.empty:
            return None

        hist = hist.reset_index()
        hist["Date"] = pd.to_datetime(hist["Date"]).dt.tz_localize(None)
        hist = hist.rename(columns={"Close": "Close", "Volume": "Volume"})

        current = float(hist["Close"].iloc[-1])
        previous = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
        change_pct = ((current - previous) / previous) * 100 if previous else 0.0

        info = {}
        try:
            info = stock.info or {}
        except Exception:
            info = {}

        def ret_from_days(days):
            if len(hist) > days:
                old = float(hist["Close"].iloc[-days])
                return ((current - old) / old) * 100 if old else np.nan
            return np.nan

        returns = {
            "1M": ret_from_days(21),
            "6M": ret_from_days(126),
            "1Y": ret_from_days(252),
            "3Y": ret_from_days(252 * 3),
            "5Y": ret_from_days(252 * 5),
        }

        hist["MA50"] = hist["Close"].rolling(50).mean()
        hist["MA200"] = hist["Close"].rolling(200).mean()

        metrics = {
            "Market Cap": info.get("marketCap", np.nan),
            "P/E": info.get("trailingPE", np.nan),
            "Forward P/E": info.get("forwardPE", np.nan),
            "Debt/Equity": info.get("debtToEquity", np.nan),
            "ROE": info.get("returnOnEquity", np.nan),
            "Dividend Yield": info.get("dividendYield", np.nan),
            "Sector": info.get("sector", "Not available"),
            "Industry": info.get("industry", "Not available"),
            "Summary": info.get("longBusinessSummary", "Business summary is not available from the data source.")
        }

        return {
            "symbol": yahoo_symbol,
            "price": current,
            "change_pct": change_pct,
            "hist": hist,
            "returns": returns,
            "metrics": metrics
        }
    except Exception:
        return None

@st.cache_data(ttl=3600, show_spinner=False)
def get_mf_schemes():
    obj = Mftool()
    try:
        schemes = obj.get_scheme_codes()
        df = pd.DataFrame(
            [{"Code": str(k), "Fund": v} for k, v in schemes.items()]
        )
        df["Fund"] = df["Fund"].astype(str)
        return df.sort_values("Fund")
    except Exception:
        return pd.DataFrame(columns=["Code", "Fund"])

@st.cache_data(ttl=3600, show_spinner=False)
def get_mf_deep_dive(code):
    obj = Mftool()
    try:
        raw = obj.get_scheme_historical_nav(str(code))
        details = obj.get_scheme_details(str(code)) or {}

        df = pd.DataFrame(raw.get("data", []))
        if df.empty:
            return None, details, None

        df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
        df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
        df = df.dropna(subset=["date", "nav"]).sort_values("date")

        curr = float(df["nav"].iloc[-1])

        def ret_days(days):
            if len(df) > days:
                old = float(df["nav"].iloc[-days])
                return ((curr - old) / old) * 100 if old else np.nan
            return np.nan

        returns = {
            "1Y": ret_days(365),
            "3Y": ret_days(365 * 3),
            "5Y": ret_days(365 * 5),
        }

        return df, details, returns
    except Exception:
        return None, None, None

@st.cache_data(ttl=1800, show_spinner=False)
def load_ipo_data():
    """Demo IPO dataset. Replace this with a proper API/scraper or CSV later."""
    data = [
        {
            "Company": "Shayona Engineering",
            "Type": "SME",
            "Open": "22-Jan-2026",
            "Close": "27-Jan-2026",
            "Listing": "30-Jan-2026",
            "Price": 144,
            "Lot": 1000,
            "GMP": 35,
            "Subscription": "1.34x",
            "Status": "Open",
            "Sector": "Engineering",
            "Summary": "Precision engineering parts manufacturer."
        },
        {
            "Company": "Hannah Joseph Hospital",
            "Type": "SME",
            "Open": "22-Jan-2026",
            "Close": "27-Jan-2026",
            "Listing": "30-Jan-2026",
            "Price": 70,
            "Lot": 2000,
            "GMP": 0,
            "Subscription": "0.55x",
            "Status": "Open",
            "Sector": "Healthcare",
            "Summary": "Specialty hospital focused on neurology and trauma care."
        },
        {
            "Company": "Biopol Chemicals",
            "Type": "SME",
            "Open": "06-Feb-2026",
            "Close": "10-Feb-2026",
            "Listing": "13-Feb-2026",
            "Price": 108,
            "Lot": 1200,
            "GMP": 15,
            "Subscription": "N/A",
            "Status": "Upcoming",
            "Sector": "Chemicals",
            "Summary": "Specialty chemicals and eco-friendly coatings manufacturer."
        },
        {
            "Company": "Shadowfax Technologies",
            "Type": "Mainboard",
            "Open": "20-Jan-2026",
            "Close": "22-Jan-2026",
            "Listing": "28-Jan-2026",
            "Price": 124,
            "Lot": 120,
            "GMP": -4,
            "Subscription": "2.86x",
            "Status": "Closed",
            "Sector": "Logistics",
            "Summary": "Tech-enabled logistics platform for hyperlocal and e-commerce delivery."
        },
        {
            "Company": "Hyundai Motor India",
            "Type": "Mainboard",
            "Open": "02-Feb-2026",
            "Close": "04-Feb-2026",
            "Listing": "10-Feb-2026",
            "Price": 1960,
            "Lot": 7,
            "GMP": -30,
            "Subscription": "1.20x",
            "Status": "Listed",
            "Sector": "Automobile",
            "Summary": "Passenger vehicle manufacturer."
        },
    ]

    df = pd.DataFrame(data)
    df["Est. Listing Price"] = df["Price"] + df["GMP"]
    df["Est. Listing Gain %"] = np.where(df["Price"] > 0, (df["GMP"] / df["Price"]) * 100, np.nan)
    df["Lot Value"] = df["Price"] * df["Lot"]
    df["Est. Profit / Lot"] = df["GMP"] * df["Lot"]
    return df

# -------------------------
# SIDEBAR
# -------------------------
st.sidebar.markdown("## 📊 InvestRight.AI")
st.sidebar.caption("Explore IPOs, mutual funds and Indian stocks with cleaner research views.")

segment = st.sidebar.radio(
    "Choose module",
    ["Overview", "IPO Explorer", "Mutual Funds", "Stocks"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.info(DISCLAIMER)

# =========================================================
# OVERVIEW
# =========================================================
if segment == "Overview":
    hero(
        "InvestRight.AI Market Research Dashboard",
        "A cleaner, beginner-friendly research terminal for IPOs, mutual funds and Indian equities. Built for discovery, comparison and learning, not blind buy/sell calls."
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Modules", "3", "IPO, MF, Stocks")
    c2.metric("Primary data sources", "3", "Yahoo Finance, MF NAV, Google News")
    c3.metric("Best use", "Research", "Not investment advice")

    st.markdown("### What you can do")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="soft-card">
            <div class="small-label">IPO Explorer</div>
            <h3>Compare IPO opportunities</h3>
            <p>View GMP, lot value, estimated listing gain, subscription and risk notes in a cleaner table.</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="soft-card">
            <div class="small-label">Mutual Funds</div>
            <h3>Compare NAV performance</h3>
            <p>Analyze a single fund or compare two funds on 1Y, 3Y and 5Y returns with normalized charts.</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="soft-card">
            <div class="small-label">Stocks</div>
            <h3>Research Indian stocks</h3>
            <p>Check price action, moving averages, returns, valuation metrics, business summary and news.</p>
        </div>
        """, unsafe_allow_html=True)

    st.warning("Important: the IPO data in this version is still demo/manual data. For a serious public product, connect IPO data to a maintained CSV, Google Sheet, NSE/BSE source, or licensed data provider.")

# =========================================================
# IPO EXPLORER
# =========================================================
elif segment == "IPO Explorer":
    hero(
        "IPO Explorer",
        "Track Mainboard and SME IPOs with estimated listing gain, lot value, subscription and simple risk context."
    )

    ipo_df = load_ipo_data()

    left, right = st.columns([1, 1])
    with left:
        type_filter = st.multiselect("IPO type", sorted(ipo_df["Type"].unique()), default=sorted(ipo_df["Type"].unique()))
    with right:
        status_filter = st.multiselect("Status", sorted(ipo_df["Status"].unique()), default=sorted(ipo_df["Status"].unique()))

    filtered = ipo_df[ipo_df["Type"].isin(type_filter) & ipo_df["Status"].isin(status_filter)].copy()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("IPOs shown", len(filtered))
    m2.metric("Avg GMP", f"₹{filtered['GMP'].mean():.1f}" if not filtered.empty else "N/A")
    m3.metric("Highest est. gain", pct(filtered["Est. Listing Gain %"].max()) if not filtered.empty else "N/A")
    m4.metric("Avg lot value", f"₹{filtered['Lot Value'].mean():,.0f}" if not filtered.empty else "N/A")

    st.markdown("### IPO comparison table")
    display_cols = [
        "Company", "Type", "Status", "Sector", "Open", "Close", "Listing", "Price", "Lot",
        "Lot Value", "GMP", "Est. Listing Price", "Est. Listing Gain %", "Est. Profit / Lot", "Subscription"
    ]

    st.dataframe(
        filtered[display_cols].style.format({
            "Price": "₹{:,.0f}",
            "Lot Value": "₹{:,.0f}",
            "GMP": "₹{:,.0f}",
            "Est. Listing Price": "₹{:,.0f}",
            "Est. Listing Gain %": "{:,.2f}%",
            "Est. Profit / Lot": "₹{:,.0f}"
        }),
        use_container_width=True,
        hide_index=True
    )

    if not filtered.empty:
        st.plotly_chart(
            make_bar_chart(
                filtered.sort_values("Est. Listing Gain %", ascending=False),
                x="Company",
                y="Est. Listing Gain %",
                title="Estimated listing gain by IPO",
                y_title="Estimated gain %"
            ),
            use_container_width=True
        )

    st.markdown("### IPO notes")
    selected_ipo = st.selectbox("Select IPO for quick view", filtered["Company"].tolist() if not filtered.empty else [])
    if selected_ipo:
        row = filtered[filtered["Company"] == selected_ipo].iloc[0]
        c1, c2 = st.columns([1, 2])
        with c1:
            st.metric("Issue price", money(row["Price"]))
            st.metric("Lot value", f"₹{row['Lot Value']:,.0f}")
            st.metric("Est. profit / lot", f"₹{row['Est. Profit / Lot']:,.0f}")
        with c2:
            st.markdown(f"""
            <div class="soft-card">
                <div class="small-label">{row['Type']} IPO | {row['Sector']}</div>
                <h3>{row['Company']}</h3>
                <p>{row['Summary']}</p>
                <p><span class="risk-badge">GMP is unofficial. Verify RHP and fundamentals.</span></p>
            </div>
            """, unsafe_allow_html=True)

            sentiment = get_news_sentiment(row["Company"])
            if sentiment:
                st.metric("News mood", f"{sentiment['score']}/100", sentiment["label"], help=TOOLTIPS["Sentiment"])
                st.dataframe(sentiment["data"][["Tag", "Source", "Title", "Date", "Link"]], use_container_width=True, hide_index=True)

# =========================================================
# MUTUAL FUNDS
# =========================================================
elif segment == "Mutual Funds":
    hero(
        "Mutual Fund Explorer",
        "Compare NAV trends, trailing returns and SIP outcomes. Use this to shortlist funds for deeper research."
    )

    schemes_df = get_mf_schemes()

    tab1, tab2, tab3 = st.tabs(["Compare funds", "SIP calculator", "MF basics"])

    with tab1:
        if schemes_df.empty:
            st.error("Unable to load mutual fund scheme list right now.")
        else:
            fund_names = schemes_df["Fund"].tolist()

            c1, c2 = st.columns(2)
            with c1:
                fund_a = st.selectbox("Fund A", fund_names, index=None, placeholder="Search a fund")
            with c2:
                fund_b = st.selectbox("Fund B optional", fund_names, index=None, placeholder="Search another fund")

            analyze = st.button("Analyze funds", type="primary", use_container_width=True)

            if analyze and fund_a:
                code_a = schemes_df.loc[schemes_df["Fund"] == fund_a, "Code"].iloc[0]

                with st.spinner("Fetching fund NAV history..."):
                    df_a, det_a, ret_a = get_mf_deep_dive(code_a)

                if df_a is None:
                    st.error("Could not fetch Fund A data.")
                else:
                    if fund_b:
                        code_b = schemes_df.loc[schemes_df["Fund"] == fund_b, "Code"].iloc[0]
                        df_b, det_b, ret_b = get_mf_deep_dive(code_b)

                        if df_b is None:
                            st.error("Could not fetch Fund B data.")
                        else:
                            st.markdown("### Head-to-head comparison")

                            comparison = pd.DataFrame({
                                "Metric": ["1Y return", "3Y return", "5Y return", "Risk", "Category", "Fund house"],
                                "Fund A": [
                                    pct(ret_a.get("1Y")),
                                    pct(ret_a.get("3Y")),
                                    pct(ret_a.get("5Y")),
                                    det_a.get("scheme_risk", "N/A"),
                                    det_a.get("scheme_category", "N/A"),
                                    det_a.get("fund_house", "N/A")
                                ],
                                "Fund B": [
                                    pct(ret_b.get("1Y")),
                                    pct(ret_b.get("3Y")),
                                    pct(ret_b.get("5Y")),
                                    det_b.get("scheme_risk", "N/A"),
                                    det_b.get("scheme_category", "N/A"),
                                    det_b.get("fund_house", "N/A")
                                ]
                            })
                            st.dataframe(comparison, use_container_width=True, hide_index=True)

                            merged = pd.merge(
                                df_a[["date", "nav"]].rename(columns={"nav": "Fund A"}),
                                df_b[["date", "nav"]].rename(columns={"nav": "Fund B"}),
                                on="date",
                                how="inner"
                            )

                            st.plotly_chart(
                                make_line_chart(
                                    merged,
                                    x="date",
                                    y_cols=["Fund A", "Fund B"],
                                    title="Normalized NAV comparison",
                                    y_title="Growth of ₹100",
                                    normalized=True
                                ),
                                use_container_width=True
                            )
                    else:
                        st.markdown(f"### {det_a.get('scheme_name', fund_a)}")
                        r1, r2, r3, r4 = st.columns(4)
                        r1.metric("Current NAV", f"₹{df_a['nav'].iloc[-1]:,.2f}")
                        r2.metric("1Y return", pct(ret_a.get("1Y")))
                        r3.metric("3Y return", pct(ret_a.get("3Y")))
                        r4.metric("5Y return", pct(ret_a.get("5Y")))

                        info = pd.DataFrame({
                            "Field": ["Fund house", "Category", "Risk", "Launch date"],
                            "Value": [
                                det_a.get("fund_house", "N/A"),
                                det_a.get("scheme_category", "N/A"),
                                det_a.get("scheme_risk", "N/A"),
                                det_a.get("scheme_start_date", {}).get("date", "N/A") if isinstance(det_a.get("scheme_start_date"), dict) else "N/A",
                            ]
                        })
                        st.dataframe(info, use_container_width=True, hide_index=True)

                        st.plotly_chart(
                            make_line_chart(
                                df_a.rename(columns={"nav": "NAV", "date": "Date"}),
                                x="Date",
                                y_cols=["NAV"],
                                title="NAV history",
                                y_title="NAV"
                            ),
                            use_container_width=True
                        )

                        fund_house = det_a.get("fund_house")
                        if fund_house:
                            sentiment = get_news_sentiment(fund_house)
                            if sentiment:
                                st.markdown("### Fund house news")
                                s1, s2 = st.columns([1, 3])
                                s1.metric("News mood", f"{sentiment['score']}/100", sentiment["label"])
                                s2.dataframe(sentiment["data"][["Tag", "Source", "Title", "Date", "Link"]], use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("### SIP calculator")

        c1, c2 = st.columns([1, 1])
        with c1:
            monthly = st.number_input("Monthly SIP", min_value=500, value=10000, step=500)
            annual_return = st.slider("Expected annual return", 5.0, 25.0, 12.0, 0.5)
            years = st.slider("Investment period in years", 1, 30, 10)

        months = years * 12
        monthly_rate = annual_return / 12 / 100
        future_value = monthly * ((((1 + monthly_rate) ** months) - 1) / monthly_rate) * (1 + monthly_rate)
        invested = monthly * months
        gain = future_value - invested

        with c2:
            st.metric("Total invested", f"₹{invested:,.0f}")
            st.metric("Estimated gain", f"₹{gain:,.0f}", pct((gain / invested) * 100 if invested else 0))
            st.metric("Estimated final value", f"₹{future_value:,.0f}")

        yearly_rows = []
        for y in range(1, years + 1):
            m = y * 12
            fv = monthly * ((((1 + monthly_rate) ** m) - 1) / monthly_rate) * (1 + monthly_rate)
            inv = monthly * m
            yearly_rows.append({"Year": y, "Invested": inv, "Estimated value": fv})

        sip_df = pd.DataFrame(yearly_rows)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=sip_df["Year"], y=sip_df["Invested"], name="Invested"))
        fig.add_trace(go.Scatter(x=sip_df["Year"], y=sip_df["Estimated value"], name="Estimated value", mode="lines+markers"))
        fig.update_layout(
            title="SIP growth over time",
            height=420,
            margin=dict(l=20, r=20, t=55, b=20),
            paper_bgcolor="white",
            plot_bgcolor="white",
            yaxis_title="Amount in ₹",
            xaxis_title="Year",
            hovermode="x unified"
        )
        fig.update_yaxes(gridcolor="#EEF2F7")
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.markdown("""
        ### Mutual fund basics

        **Direct vs Regular:** Direct funds usually have lower expense ratios because there is no distributor commission.

        **Growth vs IDCW:** Growth reinvests profits. IDCW may distribute payouts but your NAV adjusts.

        **Equity funds:** Better suited for 5+ year goals. They can fall sharply in the short term.

        **Debt funds:** Usually lower risk than equity, but not risk-free. Check credit quality and duration.

        **Index funds:** Simple, low-cost funds that track an index like Nifty 50 or Sensex.
        """)

# =========================================================
# STOCKS
# =========================================================
elif segment == "Stocks":
    hero(
        "Equity Research Terminal",
        "Search Indian listed companies, check price action, returns, key fundamentals, business summary and recent news."
    )

    stock_df = load_stock_list()

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        search = st.selectbox("Search company", stock_df["Search_Label"].unique(), index=None, placeholder="Example: RELIANCE, HDFCBANK, TCS")
    with c2:
        period = st.selectbox("Chart period", ["1y", "2y", "5y", "10y"], index=2)
    with c3:
        show_ma = st.toggle("Show moving averages", value=True)

    if search:
        ticker = search.split(" - ")[0].strip()
        company_name = search.split(" - ", 1)[1].strip() if " - " in search else ticker

        if st.button("Analyze stock", type="primary", use_container_width=True):
            with st.spinner(f"Fetching market data for {ticker}..."):
                data = get_stock_fundamentals(ticker, period=period)
                sentiment = get_news_sentiment(company_name)
                news = get_google_news_rss(company_name)

            if data is None:
                st.error("Could not fetch stock data. Try another ticker or check if the symbol exists on Yahoo Finance.")
            else:
                m = data["metrics"]
                returns = data["returns"]
                hist = data["hist"]

                st.markdown(f"### {company_name} ({data['symbol']})")

                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Last price", money(data["price"]), pct(data["change_pct"]))
                k2.metric("Sector", m.get("Sector", "N/A"))
                k3.metric("1Y return", pct(returns.get("1Y")))
                k4.metric("5Y return", pct(returns.get("5Y")))

                metric_df = pd.DataFrame([
                    {"Metric": "Market cap", "Value": f"₹{m.get('Market Cap', np.nan) / 1e7:,.0f} Cr" if pd.notna(m.get("Market Cap", np.nan)) else "N/A"},
                    {"Metric": "P/E", "Value": pct(m.get("P/E")).replace("%", "")},
                    {"Metric": "Forward P/E", "Value": pct(m.get("Forward P/E")).replace("%", "")},
                    {"Metric": "Debt/Equity", "Value": pct(m.get("Debt/Equity")).replace("%", "")},
                    {"Metric": "ROE", "Value": pct(m.get("ROE") * 100) if pd.notna(m.get("ROE", np.nan)) else "N/A"},
                    {"Metric": "Dividend yield", "Value": pct(m.get("Dividend Yield") * 100) if pd.notna(m.get("Dividend Yield", np.nan)) else "N/A"},
                    {"Metric": "Industry", "Value": m.get("Industry", "N/A")},
                ])

                st.markdown("### Fundamentals snapshot")
                st.dataframe(metric_df, use_container_width=True, hide_index=True)

                chart_df = hist[["Date", "Close", "MA50", "MA200"]].copy()
                y_cols = ["Close"]
                if show_ma:
                    y_cols += ["MA50", "MA200"]

                st.plotly_chart(
                    make_line_chart(
                        chart_df,
                        x="Date",
                        y_cols=y_cols,
                        title="Price chart with moving averages",
                        y_title="Price in ₹"
                    ),
                    use_container_width=True
                )

                returns_df = pd.DataFrame({
                    "Period": list(returns.keys()),
                    "Return": [returns[k] for k in returns.keys()]
                }).dropna()

                if not returns_df.empty:
                    st.plotly_chart(
                        make_bar_chart(returns_df, x="Period", y="Return", title="Trailing returns", y_title="Return %"),
                        use_container_width=True
                    )

                st.markdown("### Business summary")
                st.markdown(f"<div class='insight'>{short_text(m.get('Summary'), 700)}</div>", unsafe_allow_html=True)

                st.markdown("### News and corporate radar")
                col1, col2 = st.columns([1, 3])
                with col1:
                    if sentiment:
                        st.metric("News mood", f"{sentiment['score']}/100", sentiment["label"], help=TOOLTIPS["Sentiment"])
                    else:
                        st.metric("News mood", "N/A")
                with col2:
                    if news:
                        news_df = pd.DataFrame(news)
                        st.dataframe(news_df[["Tag", "Source", "Title", "Date", "Link"]], use_container_width=True, hide_index=True)
                    else:
                        st.info("No recent news found from Google News RSS.")

st.markdown(f"<div class='footer-note'>{DISCLAIMER}</div>", unsafe_allow_html=True)
