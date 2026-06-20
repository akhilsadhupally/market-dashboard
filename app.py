import datetime as dt
import re
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf
from mftool import Mftool
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# =========================================================
# INVESTRIGHT.AI
# Beginner Investment Intelligence Platform
# =========================================================

st.set_page_config(
    page_title="InvestRight.AI | Understand Before You Invest",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_NAME = "InvestRight.AI"
TAGLINE = "Understand before you invest."
DISCLAIMER = (
    "InvestRight.AI is an education and research tool. It does not provide investment advice, "
    "buy or sell recommendations, target prices or guaranteed returns. Always verify data from official sources "
    "and consult a SEBI registered professional before making investment decisions."
)

# =========================================================
# DESIGN SYSTEM
# =========================================================

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.block-container {
    padding-top: 1.35rem;
    padding-bottom: 2.2rem;
    max-width: 1380px;
}

[data-testid="stSidebar"] {
    background: #0B1220;
}
[data-testid="stSidebar"] * {
    color: #E5E7EB !important;
}

h1, h2, h3 {
    color: #0F172A;
    letter-spacing: -0.03em;
}

.hero {
    border-radius: 24px;
    padding: 28px;
    margin-bottom: 20px;
    background: radial-gradient(circle at top left, #1D4ED8 0%, #0F172A 45%, #064E3B 100%);
    color: white;
    box-shadow: 0 24px 50px rgba(15, 23, 42, 0.20);
}
.hero h1 {
    color: white;
    font-size: 40px;
    font-weight: 800;
    margin: 0 0 6px 0;
}
.hero p {
    color: #D1D5DB;
    max-width: 920px;
    font-size: 16px;
    margin-bottom: 0;
}

.card {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 20px;
    padding: 18px;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.055);
    margin-bottom: 16px;
}

.card-title {
    font-weight: 800;
    color: #111827;
    font-size: 18px;
    margin-bottom: 6px;
}

.card-copy {
    color: #4B5563;
    font-size: 14px;
    line-height: 1.55;
}

.kicker {
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: #64748B;
    font-size: 12px;
    font-weight: 800;
    margin-bottom: 6px;
}

.pill {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    background: #EEF2FF;
    color: #3730A3;
    font-size: 12px;
    font-weight: 700;
    margin: 3px 4px 3px 0;
}

.pill-green { background: #ECFDF5; color: #047857; }
.pill-red { background: #FEF2F2; color: #B91C1C; }
.pill-yellow { background: #FFFBEB; color: #92400E; }
.pill-gray { background: #F3F4F6; color: #374151; }

.explain-box {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 16px;
    padding: 15px 16px;
    color: #334155;
    font-size: 14px;
    line-height: 1.55;
}

.safe-note {
    background: #FFFBEB;
    border: 1px solid #FDE68A;
    color: #78350F;
    border-radius: 14px;
    padding: 12px 14px;
    font-size: 13px;
    line-height: 1.5;
}

.footer-note {
    margin-top: 26px;
    padding: 14px 16px;
    color: #64748B;
    font-size: 12px;
    border-top: 1px solid #E5E7EB;
}

[data-testid="stMetric"] {
    background: white;
    border: 1px solid #E5E7EB;
    border-radius: 16px;
    padding: 14px;
    box-shadow: 0 6px 20px rgba(15, 23, 42, 0.045);
}

.stDataFrame {
    border-radius: 16px;
    overflow: hidden;
}

hr {
    border: none;
    border-top: 1px solid #E5E7EB;
    margin: 1.5rem 0;
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# COPY AND EXPLANATIONS
# =========================================================

TOOLTIPS = {
    "PE": "Price to Earnings ratio. It shows how expensive the stock is compared with its current earnings.",
    "ROE": "Return on Equity. It shows how efficiently the company uses shareholder money to generate profit.",
    "DE": "Debt to Equity. It shows how much debt the company has compared with shareholder funds.",
    "Mood": "A simple score based on recent headlines and public market chatter. This is not a recommendation.",
    "Clarity": "A research score that combines data availability, trend, mood and risk flags. It is not a buy or sell signal.",
}

LEARN_CONTENT = {
    "IPO": "An IPO is when a private company sells shares to the public for the first time. Beginners usually look at GMP and subscription, but they should also study the business, valuation, risks and whether demand is genuine or just hype.",
    "Stock": "A stock represents ownership in a company. Before studying a stock, understand what the business does, how it makes money, whether it is profitable, whether debt is high and what recent news says.",
    "Mutual Fund": "A mutual fund pools money from investors and invests it in stocks, bonds or other assets. Beginners should compare fund category, risk level, 3Y/5Y returns and consistency before choosing.",
    "GMP": "GMP means Grey Market Premium. It is an unofficial estimate of IPO listing demand. It can be manipulated, so never treat GMP as final truth.",
    "SIP": "SIP means Systematic Investment Plan. It lets you invest a fixed amount regularly, usually monthly, so you do not need to time the market.",
}

INSTITUTIONAL_SOURCES = [
    "business standard",
    "economic times",
    "economictimes",
    "moneycontrol",
    "livemint",
    "mint",
    "bloomberg",
    "reuters",
    "cnbc",
    "ndtv profit",
    "financial express",
    "bq prime",
    "the hindu businessline",
    "businessline",
    "crisil",
    "icra",
    "care ratings",
    "jpmorgan",
    "jp morgan",
    "morgan stanley",
    "goldman sachs",
    "jefferies",
    "nomura",
    "motilal oswal",
    "kotak",
    "nuvama",
]

EVENT_KEYWORDS = {
    "Results": ["profit", "loss", "revenue", "earnings", "q1", "q2", "q3", "q4", "results", "ebitda"],
    "Large order": ["order", "contract", "project", "commission", "wins", "bagged", "supply", "mw", "epc"],
    "Corporate action": ["dividend", "bonus", "split", "buyback", "rights issue"],
    "M&A or stake": ["acquisition", "merger", "stake", "sells stake", "buys stake", "acquires", "divest"],
    "Regulatory": ["sebi", "rbi", "penalty", "fine", "notice", "approval", "probe", "investigation"],
}

# =========================================================
# HELPER FUNCTIONS
# =========================================================

def money(value, currency="₹"):
    if value is None or pd.isna(value):
        return "N/A"
    try:
        if abs(value) >= 1e7:
            return f"{currency}{value / 1e7:,.1f} Cr"
        return f"{currency}{value:,.2f}"
    except Exception:
        return "N/A"


def pct(value, decimals=2):
    if value is None or pd.isna(value):
        return "N/A"
    try:
        return f"{value:,.{decimals}f}%"
    except Exception:
        return "N/A"


def number(value, decimals=2):
    if value is None or pd.isna(value):
        return "N/A"
    try:
        return f"{value:,.{decimals}f}"
    except Exception:
        return "N/A"


def safe_text(value, max_len=380):
    if value is None or pd.isna(value) or str(value).strip() == "":
        return "No summary available from the current source."
    value = re.sub(r"\s+", " ", str(value)).strip()
    return value if len(value) <= max_len else value[:max_len].rsplit(" ", 1)[0] + "..."


def score_band(score):
    if score is None or pd.isna(score):
        return "Data not enough", "pill-gray"
    if score >= 75:
        return "Strong positive signal", "pill-green"
    if score >= 60:
        return "Positive but study further", "pill-green"
    if score >= 45:
        return "Mixed signals", "pill-yellow"
    if score >= 30:
        return "Caution signals", "pill-yellow"
    return "Weak or negative signal", "pill-red"


def mood_label(score):
    if score is None or pd.isna(score):
        return "Not enough data"
    if score >= 70:
        return "Very positive mood"
    if score >= 58:
        return "Positive mood"
    if score >= 43:
        return "Mixed mood"
    if score >= 30:
        return "Cautious mood"
    return "Negative mood"


def render_hero(title, subtitle):
    st.markdown(
        f"""
        <div class="hero">
            <div class="kicker">{APP_NAME}</div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_card(title, copy, pills=None):
    pills_html = ""
    if pills:
        pills_html = "".join([f"<span class='pill'>{p}</span>" for p in pills])
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">{title}</div>
            <div class="card-copy">{copy}</div>
            <div style="margin-top:10px;">{pills_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_safe_note():
    st.markdown(f"<div class='safe-note'>{DISCLAIMER}</div>", unsafe_allow_html=True)


def extract_source_from_google_title(title):
    if not title:
        return "News"
    if " - " in title:
        return title.rsplit(" - ", 1)[-1].strip()
    return "News"


def clean_google_title(title):
    if not title:
        return ""
    if " - " in title:
        return title.rsplit(" - ", 1)[0].strip()
    return title.strip()


def event_tag(title):
    lower = title.lower()
    for tag, keywords in EVENT_KEYWORDS.items():
        if any(k in lower for k in keywords):
            return tag
    return "General"


def classify_source(source):
    source_l = source.lower()
    if any(s in source_l for s in INSTITUTIONAL_SOURCES):
        return "Institutional or business media"
    return "Public news"


def create_line_chart(df, x_col, y_cols, title, y_title, normalize=False):
    fig = go.Figure()
    data = df.copy()
    if normalize:
        for col in y_cols:
            first_valid = data[col].dropna().iloc[0] if not data[col].dropna().empty else np.nan
            if pd.notna(first_valid) and first_valid != 0:
                data[col] = (data[col] / first_valid) * 100
        y_title = "Growth of ₹100 invested"

    for col in y_cols:
        if col in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data[x_col],
                    y=data[col],
                    mode="lines",
                    name=col,
                    line=dict(width=2.4),
                )
            )
    fig.update_layout(
        title=dict(text=title, x=0.02, xanchor="left"),
        height=430,
        margin=dict(l=20, r=20, t=55, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="",
        yaxis_title=y_title,
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#EEF2F7")
    fig.update_yaxes(showgrid=True, gridcolor="#EEF2F7")
    return fig


def create_bar_chart(df, x_col, y_col, title, y_title, suffix=""):
    fig = px.bar(df, x=x_col, y=y_col, text=y_col)
    fig.update_traces(texttemplate=f"%{{text:.2f}}{suffix}", textposition="outside")
    fig.update_layout(
        title=dict(text=title, x=0.02, xanchor="left"),
        height=360,
        margin=dict(l=20, r=20, t=55, b=20),
        xaxis_title="",
        yaxis_title=y_title,
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#EEF2F7")
    return fig


def create_donut(labels, values, title):
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.62,
                textinfo="label+percent",
                sort=False,
            )
        ]
    )
    fig.update_layout(
        title=dict(text=title, x=0.02, xanchor="left"),
        height=340,
        margin=dict(l=20, r=20, t=55, b=20),
        paper_bgcolor="white",
    )
    return fig

# =========================================================
# DATA SOURCES
# =========================================================

@st.cache_data(ttl=24 * 3600, show_spinner=False)
def load_stock_list():
    fallback = pd.DataFrame(
        {
            "SYMBOL": ["RELIANCE", "TCS", "HDFCBANK", "INFY", "TATASTEEL", "SUZLON", "KPIGREEN", "ZOMATO"],
            "NAME OF COMPANY": [
                "Reliance Industries Limited",
                "Tata Consultancy Services Limited",
                "HDFC Bank Limited",
                "Infosys Limited",
                "Tata Steel Limited",
                "Suzlon Energy Limited",
                "KPI Green Energy Limited",
                "Zomato Limited",
            ],
        }
    )
    try:
        url = "https://raw.githubusercontent.com/akhilsadhupally/market-dashboard/refs/heads/main/stocks.csv"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        from io import StringIO
        df = pd.read_csv(StringIO(response.text))
        df.columns = df.columns.str.strip()
        if "SYMBOL" not in df.columns:
            if "Symbol" in df.columns:
                df = df.rename(columns={"Symbol": "SYMBOL"})
            else:
                return fallback.assign(Search_Label=lambda x: x["SYMBOL"] + " - " + x["NAME OF COMPANY"])
        if "NAME OF COMPANY" not in df.columns:
            if "Company Name" in df.columns:
                df = df.rename(columns={"Company Name": "NAME OF COMPANY"})
            else:
                df["NAME OF COMPANY"] = df["SYMBOL"]
        df = df.dropna(subset=["SYMBOL"]).copy()
        df["SYMBOL"] = df["SYMBOL"].astype(str).str.strip()
        df["NAME OF COMPANY"] = df["NAME OF COMPANY"].astype(str).str.strip()
        df["Search_Label"] = df["SYMBOL"] + " - " + df["NAME OF COMPANY"]
        return df[["SYMBOL", "NAME OF COMPANY", "Search_Label"]].drop_duplicates()
    except Exception:
        fallback["Search_Label"] = fallback["SYMBOL"] + " - " + fallback["NAME OF COMPANY"]
        return fallback


@st.cache_data(ttl=900, show_spinner=False)
def get_google_news_rss(query_term, max_items=10):
    if not query_term:
        return []
    clean_query = str(query_term).replace("Limited", "").replace("Ltd", "").strip()
    query = quote_plus(f"{clean_query} India business stock market")
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    items = []
    try:
        response = requests.get(rss_url, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        for item in root.findall("./channel/item")[:max_items]:
            raw_title = item.findtext("title", default="")
            source = extract_source_from_google_title(raw_title)
            title = clean_google_title(raw_title)
            link = item.findtext("link", default="")
            date = item.findtext("pubDate", default="")
            items.append(
                {
                    "Title": title,
                    "Source": source,
                    "Source Type": classify_source(source),
                    "Tag": event_tag(title),
                    "Date": date,
                    "Link": link,
                }
            )
        return items
    except Exception:
        return []


@st.cache_data(ttl=900, show_spinner=False)
def get_sentiment_pack(query_term):
    news = get_google_news_rss(query_term, max_items=12)
    if not news:
        return None
    analyzer = SentimentIntensityAnalyzer()
    rows = []
    for item in news:
        score = analyzer.polarity_scores(item["Title"])["compound"]
        rows.append({**item, "Sentiment": score})
    df = pd.DataFrame(rows)
    avg = df["Sentiment"].mean()
    mood_score = int((avg + 1) * 50)

    positive = df[df["Sentiment"] > 0.12].sort_values("Sentiment", ascending=False).head(3)
    negative = df[df["Sentiment"] < -0.12].sort_values("Sentiment").head(3)
    institutional = df[df["Source Type"] == "Institutional or business media"]
    event_df = df[df["Tag"] != "General"]

    institutional_score = None
    if not institutional.empty:
        institutional_score = int((institutional["Sentiment"].mean() + 1) * 50)

    return {
        "mood_score": mood_score,
        "mood_label": mood_label(mood_score),
        "institutional_score": institutional_score,
        "institutional_label": mood_label(institutional_score) if institutional_score is not None else "Not enough institutional data",
        "data": df,
        "positive": positive,
        "negative": negative,
        "institutional": institutional,
        "events": event_df,
    }


@st.cache_data(ttl=600, show_spinner=False)
def get_stock_data(ticker, period="5y"):
    if not ticker:
        return None
    symbol = ticker.upper().strip()
    if not symbol.endswith(".NS"):
        symbol = f"{symbol}.NS"
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)
        if hist is None or hist.empty:
            return None
        hist = hist.reset_index()
        hist["Date"] = pd.to_datetime(hist["Date"]).dt.tz_localize(None)
        hist["MA50"] = hist["Close"].rolling(50).mean()
        hist["MA200"] = hist["Close"].rolling(200).mean()
        hist["Return"] = hist["Close"].pct_change() * 100
        current = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
        change_pct = ((current - prev) / prev) * 100 if prev else 0
        try:
            info = stock.info or {}
        except Exception:
            info = {}

        def ret_from_days(days):
            if len(hist) > days:
                start_price = hist["Close"].iloc[-days]
                if start_price and not pd.isna(start_price):
                    return ((current - start_price) / start_price) * 100
            return np.nan

        returns = {
            "1M": ret_from_days(22),
            "6M": ret_from_days(126),
            "1Y": ret_from_days(252),
            "3Y": ret_from_days(756),
            "5Y": ret_from_days(1260),
        }

        metrics = {
            "Sector": info.get("sector", "N/A"),
            "Industry": info.get("industry", "N/A"),
            "Market Cap": info.get("marketCap", np.nan),
            "P/E": info.get("trailingPE", np.nan),
            "Forward P/E": info.get("forwardPE", np.nan),
            "Debt/Equity": info.get("debtToEquity", np.nan),
            "ROE": info.get("returnOnEquity", np.nan),
            "Dividend Yield": info.get("dividendYield", np.nan),
            "Summary": info.get("longBusinessSummary", ""),
        }
        return {
            "symbol": symbol,
            "price": current,
            "change_pct": change_pct,
            "hist": hist,
            "metrics": metrics,
            "returns": returns,
        }
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_mf_schemes():
    try:
        obj = Mftool()
        schemes = obj.get_scheme_codes()
        if isinstance(schemes, dict) and schemes:
            return schemes
    except Exception:
        pass
    return {
        "120503": "HDFC Flexi Cap Fund - Direct Plan - Growth Option",
        "119551": "ICICI Prudential Bluechip Fund - Direct Plan - Growth",
        "120716": "Parag Parikh Flexi Cap Fund - Direct Plan - Growth",
        "118550": "Nippon India Small Cap Fund - Direct Plan - Growth Plan",
    }


@st.cache_data(ttl=3600, show_spinner=False)
def get_mf_data(code):
    try:
        obj = Mftool()
        nav_data = obj.get_scheme_historical_nav(code)
        details = obj.get_scheme_details(code)
        df = pd.DataFrame(nav_data.get("data", []))
        if df.empty:
            return None
        df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
        df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
        df = df.dropna(subset=["date", "nav"]).sort_values("date")
        current_nav = df["nav"].iloc[-1]

        def ret_days(days):
            target_date = df["date"].max() - pd.Timedelta(days=days)
            older = df[df["date"] <= target_date]
            if not older.empty:
                base = older["nav"].iloc[-1]
                if base:
                    return ((current_nav - base) / base) * 100
            return np.nan

        returns = {
            "1Y": ret_days(365),
            "3Y": ret_days(365 * 3),
            "5Y": ret_days(365 * 5),
        }
        return {"df": df, "details": details or {}, "returns": returns, "current_nav": current_nav}
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def load_ipo_data():
    # MVP note: Replace this with a Google Sheet or paid IPO API later.
    data = [
        {
            "Company": "Tata Capital",
            "Type": "Mainboard",
            "Status": "Upcoming",
            "Sector": "Financial Services",
            "Open": "TBA",
            "Close": "TBA",
            "Listing": "TBA",
            "Price": np.nan,
            "Lot": np.nan,
            "GMP": np.nan,
            "Subscription": "TBA",
            "Summary": "Financial services company from the Tata Group. Add official RHP details when available.",
            "Risk Flags": "Awaiting price band, valuation and RHP details",
        },
        {
            "Company": "National Securities Depository Limited",
            "Type": "Mainboard",
            "Status": "Upcoming",
            "Sector": "Market Infrastructure",
            "Open": "TBA",
            "Close": "TBA",
            "Listing": "TBA",
            "Price": np.nan,
            "Lot": np.nan,
            "GMP": np.nan,
            "Subscription": "TBA",
            "Summary": "Depository infrastructure business. Add official issue details when available.",
            "Risk Flags": "Awaiting price band and valuation details",
        },
        {
            "Company": "Demo SME Engineering IPO",
            "Type": "SME",
            "Status": "Demo",
            "Sector": "Engineering",
            "Open": "TBA",
            "Close": "TBA",
            "Listing": "TBA",
            "Price": 120,
            "Lot": 1000,
            "GMP": 8,
            "Subscription": "2.1x",
            "Summary": "Demo entry to show SME IPO layout. Replace with verified data before public use.",
            "Risk Flags": "SME IPOs can have lower liquidity and higher lot size",
        },
    ]
    return pd.DataFrame(data)

# =========================================================
# SCORING LAYER
# =========================================================

def stock_clarity_score(stock_data, sentiment_pack):
    if stock_data is None:
        return np.nan, ["Market data unavailable"]
    score = 50
    flags = []
    returns = stock_data["returns"]
    metrics = stock_data["metrics"]

    one_year = returns.get("1Y", np.nan)
    if pd.notna(one_year):
        if one_year > 20:
            score += 10
        elif one_year < -15:
            score -= 10
            flags.append("1Y price trend is weak")
    else:
        flags.append("1Y return data is not enough")

    pe = metrics.get("P/E", np.nan)
    if pd.notna(pe):
        if pe > 80:
            score -= 8
            flags.append("P/E looks very high, compare with peers")
        elif 8 <= pe <= 35:
            score += 5
    else:
        flags.append("P/E is unavailable")

    de = metrics.get("Debt/Equity", np.nan)
    if pd.notna(de):
        # Yahoo often reports this as percentage for Indian stocks. Treat very high value as high debt signal.
        if de > 200:
            score -= 8
            flags.append("Debt to equity appears high")
        elif de < 80:
            score += 4

    roe = metrics.get("ROE", np.nan)
    if pd.notna(roe):
        roe_pct = roe * 100 if abs(roe) < 2 else roe
        if roe_pct > 15:
            score += 6
        elif roe_pct < 5:
            score -= 4
            flags.append("ROE appears low")

    if sentiment_pack:
        mood = sentiment_pack["mood_score"]
        if mood >= 65:
            score += 8
        elif mood < 40:
            score -= 8
            flags.append("Recent news mood is cautious")
        if not sentiment_pack["events"].empty:
            score += 3
    else:
        flags.append("Recent news mood unavailable")

    score = max(0, min(100, int(score)))
    if not flags:
        flags = ["No major beginner-level red flag detected from available data"]
    return score, flags


def ipo_clarity_score(row, sentiment_pack):
    score = 45
    flags = []
    gmp = row.get("GMP", np.nan)
    price = row.get("Price", np.nan)
    if pd.notna(gmp) and pd.notna(price) and price:
        gmp_pct = (gmp / price) * 100
        if gmp_pct > 15:
            score += 15
        elif gmp_pct < 0:
            score -= 10
            flags.append("GMP is negative or weak")
    else:
        flags.append("GMP or price band not available")

    sub = str(row.get("Subscription", "")).lower()
    sub_num = np.nan
    match = re.search(r"([0-9]+\.?[0-9]*)", sub)
    if match:
        sub_num = float(match.group(1))
    if pd.notna(sub_num):
        if sub_num > 10:
            score += 15
        elif sub_num > 2:
            score += 7
        elif sub_num < 1:
            score -= 8
            flags.append("Subscription demand looks weak so far")
    else:
        flags.append("Subscription data not available")

    if sentiment_pack:
        mood = sentiment_pack["mood_score"]
        if mood >= 65:
            score += 8
        elif mood < 40:
            score -= 8
            flags.append("News mood is cautious")

    if row.get("Type") == "SME":
        score -= 5
        flags.append("SME IPOs usually have higher lot size and liquidity risk")

    score = max(0, min(100, int(score)))
    if row.get("Risk Flags"):
        flags.append(row.get("Risk Flags"))
    return score, flags


def fund_clarity_score(mf_pack, sentiment_pack=None):
    if mf_pack is None:
        return np.nan, ["Fund data unavailable"]
    score = 50
    flags = []
    r = mf_pack["returns"]
    r3 = r.get("3Y", np.nan)
    r5 = r.get("5Y", np.nan)
    if pd.notna(r5):
        if r5 > 15:
            score += 14
        elif r5 < 5:
            score -= 8
            flags.append("5Y return appears weak")
    else:
        flags.append("5Y return data not enough")
    if pd.notna(r3):
        if r3 > 12:
            score += 8
        elif r3 < 4:
            score -= 5
            flags.append("3Y return appears weak")
    if sentiment_pack:
        mood = sentiment_pack["mood_score"]
        if mood >= 65:
            score += 5
        elif mood < 40:
            score -= 5
            flags.append("Fund house news mood is cautious")
    score = max(0, min(100, int(score)))
    if not flags:
        flags = ["No major beginner-level red flag detected from available data"]
    return score, flags

# =========================================================
# PAGE COMPONENTS
# =========================================================

def render_mood_section(sentiment_pack, title="What people are saying"):
    st.markdown(f"### {title}")
    if not sentiment_pack:
        st.info("No recent public news found. This does not mean the company or fund is good or bad. It only means the current source did not return enough data.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Public mood", f"{sentiment_pack['mood_score']}/100", sentiment_pack["mood_label"], help=TOOLTIPS["Mood"])
    inst_score = sentiment_pack.get("institutional_score")
    c2.metric("Institutional signal", f"{inst_score}/100" if inst_score is not None else "N/A", sentiment_pack["institutional_label"])
    c3.metric("Items scanned", len(sentiment_pack["data"]))

    st.markdown("#### Simple summary")
    col_pos, col_neg = st.columns(2)
    with col_pos:
        st.markdown("<div class='kicker'>Positive reasons found</div>", unsafe_allow_html=True)
        if sentiment_pack["positive"].empty:
            st.caption("No strong positive headline detected.")
        else:
            for _, row in sentiment_pack["positive"].iterrows():
                st.markdown(f"<span class='pill pill-green'>{row['Source']}</span> {row['Title']}", unsafe_allow_html=True)
    with col_neg:
        st.markdown("<div class='kicker'>Concerns found</div>", unsafe_allow_html=True)
        if sentiment_pack["negative"].empty:
            st.caption("No strong negative headline detected.")
        else:
            for _, row in sentiment_pack["negative"].iterrows():
                st.markdown(f"<span class='pill pill-red'>{row['Source']}</span> {row['Title']}", unsafe_allow_html=True)

    with st.expander("View scanned news and source links"):
        show_df = sentiment_pack["data"][["Tag", "Source", "Source Type", "Title", "Date", "Link", "Sentiment"]].copy()
        st.dataframe(show_df, use_container_width=True, hide_index=True)


def render_event_radar(sentiment_pack):
    st.markdown("### Big money and company update radar")
    if not sentiment_pack or sentiment_pack["events"].empty:
        st.info("No major event headline detected from the current news source. Later we should connect NSE corporate announcements, bulk deals and block deals here.")
        return
    event_df = sentiment_pack["events"][["Tag", "Source", "Title", "Date", "Link"]].copy()
    st.dataframe(event_df, use_container_width=True, hide_index=True)


def render_risk_flags(flags):
    st.markdown("### Beginner risk flags")
    for flag in flags[:6]:
        st.markdown(f"<span class='pill pill-yellow'>{flag}</span>", unsafe_allow_html=True)

# =========================================================
# PAGES
# =========================================================

def page_home():
    render_hero(
        "Understand stocks, IPOs and mutual funds before you invest.",
        "A beginner-friendly research platform that explains market data, public mood, institutional signals, risk flags and comparisons without making you feel dumb.",
    )
    render_safe_note()

    st.markdown("## What this product is trying to solve")
    a, b, c = st.columns(3)
    with a:
        render_card("For curious beginners", "Most finance websites assume users already understand investing. This platform explains the meaning behind the data.", ["Simple language", "No judgement"])
    with b:
        render_card("For quick research", "A user should understand the basics of a stock, IPO or fund in two minutes before deciding whether to study deeper.", ["Mood", "Risk", "Events"])
    with c:
        render_card("For safer discovery", "The app avoids buy/sell calls and focuses on education, comparison and research signals.", ["Not advice", "Research-first"])

    st.markdown("## Product modules")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_card("IPOs", "Track price band, GMP, subscription, public mood and issue risks.", ["GMP", "Demand", "Risk"])
    with m2:
        render_card("Stocks", "Understand what a company does, price trend, fundamentals, mood and big events.", ["Price", "News", "Fundamentals"])
    with m3:
        render_card("Mutual Funds", "Compare funds by NAV trend, 1Y/3Y/5Y returns, risk and SIP growth.", ["NAV", "SIP", "Compare"])
    with m4:
        render_card("Learn", "Explain finance terms in plain English for new investors.", ["IPO", "PE", "SIP"])

    st.markdown("## 10-day demo goal")
    st.markdown(
        """
        <div class='explain-box'>
        The first version should not try to become Moneycontrol. It should become the cleanest beginner layer on top of market information. The chairman demo should show one IPO, one stock and one mutual fund journey where a user can understand public mood, institutional signal, risk and comparison without confusion.
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_ipos():
    render_hero(
        "IPO Explorer",
        "Understand IPO demand, GMP, public mood and key risks without getting lost in heavy finance tables.",
    )
    render_safe_note()
    ipo_df = load_ipo_data()

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        ipo_type = st.selectbox("IPO type", ["All"] + sorted(ipo_df["Type"].dropna().unique().tolist()))
    with c2:
        status = st.selectbox("Status", ["All"] + sorted(ipo_df["Status"].dropna().unique().tolist()))
    filtered = ipo_df.copy()
    if ipo_type != "All":
        filtered = filtered[filtered["Type"] == ipo_type]
    if status != "All":
        filtered = filtered[filtered["Status"] == status]

    table = filtered.copy()
    table["Est. listing gain %"] = np.where(
        table["Price"].notna() & table["GMP"].notna() & (table["Price"] != 0),
        (table["GMP"] / table["Price"]) * 100,
        np.nan,
    )
    st.dataframe(
        table[["Company", "Type", "Status", "Sector", "Open", "Close", "Price", "GMP", "Subscription", "Est. listing gain %"]],
        use_container_width=True,
        hide_index=True,
    )

    selected = st.selectbox("Study an IPO", filtered["Company"].tolist(), index=0 if not filtered.empty else None)
    if selected:
        row = filtered[filtered["Company"] == selected].iloc[0]
        sentiment_pack = get_sentiment_pack(selected)
        clarity, flags = ipo_clarity_score(row, sentiment_pack)
        label, pill_class = score_band(clarity)

        st.markdown(f"## {selected}")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Clarity score", f"{clarity}/100", label, help=TOOLTIPS["Clarity"])
        k2.metric("IPO type", row["Type"])
        k3.metric("GMP", money(row["GMP"]) if pd.notna(row["GMP"]) else "TBA")
        k4.metric("Subscription", row["Subscription"])

        st.markdown("### Plain English summary")
        st.markdown(f"<div class='explain-box'>{safe_text(row['Summary'], 700)}</div>", unsafe_allow_html=True)
        render_risk_flags(flags)
        render_mood_section(sentiment_pack)
        render_event_radar(sentiment_pack)

        st.markdown("### Beginner explanation")
        st.markdown(
            """
            <div class='explain-box'>
            For IPOs, do not look only at GMP. First check what the company does, whether the valuation is reasonable, whether subscription is broad-based and what risks are mentioned in the RHP. GMP can be useful, but it is unofficial and can change quickly.
            </div>
            """,
            unsafe_allow_html=True,
        )


def page_stocks():
    render_hero(
        "Stock Explorer",
        "Search a company and quickly understand price trend, fundamentals, public mood, institutional signal and recent events.",
    )
    render_safe_note()
    stock_df = load_stock_list()

    c1, c2, c3 = st.columns([2.2, 0.9, 0.9])
    with c1:
        search = st.selectbox("Search company", stock_df["Search_Label"].unique(), index=None, placeholder="Example: RELIANCE, TCS, HDFCBANK")
    with c2:
        period = st.selectbox("Chart period", ["1y", "2y", "5y", "10y"], index=2)
    with c3:
        show_ma = st.toggle("Show moving averages", value=True)

    if not search:
        st.info("Select a company to start. The page is designed for beginners, so the first output is a simple scorecard, not a complex terminal.")
        return

    ticker = search.split(" - ")[0].strip()
    company_name = search.split(" - ", 1)[1].strip() if " - " in search else ticker

    with st.spinner(f"Fetching data for {company_name}..."):
        stock_data = get_stock_data(ticker, period=period)
        sentiment_pack = get_sentiment_pack(company_name)

    if not stock_data:
        st.error("Could not fetch stock data for this ticker. Try another company or check the Yahoo Finance symbol.")
        return

    metrics = stock_data["metrics"]
    returns = stock_data["returns"]
    clarity, flags = stock_clarity_score(stock_data, sentiment_pack)
    label, _ = score_band(clarity)

    st.markdown(f"## {company_name} ({stock_data['symbol']})")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Last price", money(stock_data["price"]), pct(stock_data["change_pct"]))
    c2.metric("Clarity score", f"{clarity}/100", label, help=TOOLTIPS["Clarity"])
    c3.metric("1Y return", pct(returns.get("1Y")))
    c4.metric("Sector", metrics.get("Sector", "N/A"))

    st.markdown("### What this company does")
    st.markdown(f"<div class='explain-box'>{safe_text(metrics.get('Summary'), 850)}</div>", unsafe_allow_html=True)

    metric_rows = [
        {"Metric": "Market cap", "Value": money(metrics.get("Market Cap"))},
        {"Metric": "P/E", "Value": number(metrics.get("P/E")), "Meaning": "Higher can mean expensive, but compare with peers."},
        {"Metric": "Forward P/E", "Value": number(metrics.get("Forward P/E")), "Meaning": "Market expectation based on future earnings."},
        {"Metric": "Debt/Equity", "Value": number(metrics.get("Debt/Equity")), "Meaning": "High value may indicate higher financial risk."},
        {"Metric": "ROE", "Value": pct(metrics.get("ROE") * 100) if pd.notna(metrics.get("ROE", np.nan)) else "N/A", "Meaning": "Shows efficiency of shareholder capital."},
        {"Metric": "Dividend yield", "Value": pct(metrics.get("Dividend Yield") * 100) if pd.notna(metrics.get("Dividend Yield", np.nan)) else "N/A", "Meaning": "Income from dividends as a percentage of price."},
        {"Metric": "Industry", "Value": metrics.get("Industry", "N/A")},
    ]
    st.markdown("### Beginner scorecard")
    st.dataframe(pd.DataFrame(metric_rows), use_container_width=True, hide_index=True)

    chart_cols = ["Close"]
    if show_ma:
        chart_cols += ["MA50", "MA200"]
    st.plotly_chart(
        create_line_chart(stock_data["hist"], "Date", chart_cols, "Price trend", "Price in ₹"),
        use_container_width=True,
    )

    ret_df = pd.DataFrame({"Period": list(returns.keys()), "Return": list(returns.values())}).dropna()
    if not ret_df.empty:
        st.plotly_chart(create_bar_chart(ret_df, "Period", "Return", "Trailing returns", "Return %", "%"), use_container_width=True)

    render_risk_flags(flags)
    render_mood_section(sentiment_pack)
    render_event_radar(sentiment_pack)


def page_mutual_funds():
    render_hero(
        "Mutual Fund Explorer",
        "Compare funds by returns, NAV growth, risk category and SIP outcomes without needing heavy finance knowledge.",
    )
    render_safe_note()
    schemes = get_mf_schemes()
    scheme_items = sorted([(name, code) for code, name in schemes.items()], key=lambda x: x[0])
    names = [x[0] for x in scheme_items]
    name_to_code = {name: code for name, code in scheme_items}

    tab1, tab2, tab3 = st.tabs(["Explore and compare", "SIP calculator", "How to choose"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            fund_a = st.selectbox("Fund A", names, index=None, placeholder="Search a mutual fund")
        with c2:
            fund_b = st.selectbox("Fund B optional", names, index=None, placeholder="Choose another fund to compare")

        if not fund_a:
            st.info("Select one fund to explore. Select two funds to compare them head-to-head.")
        else:
            with st.spinner("Fetching mutual fund data..."):
                pack_a = get_mf_data(name_to_code[fund_a])
                sent_a = get_sentiment_pack(fund_a.split("-")[0])
                pack_b = get_mf_data(name_to_code[fund_b]) if fund_b else None

            if not pack_a:
                st.error("Could not fetch mutual fund NAV data.")
            else:
                clarity, flags = fund_clarity_score(pack_a, sent_a)
                label, _ = score_band(clarity)
                details = pack_a["details"]
                st.markdown(f"## {details.get('scheme_name', fund_a)}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Current NAV", money(pack_a["current_nav"]))
                c2.metric("Clarity score", f"{clarity}/100", label)
                c3.metric("3Y return", pct(pack_a["returns"].get("3Y")))
                c4.metric("5Y return", pct(pack_a["returns"].get("5Y")))

                info_df = pd.DataFrame(
                    [
                        {"Metric": "Fund house", "Value": details.get("fund_house", "N/A")},
                        {"Metric": "Category", "Value": details.get("scheme_category", "N/A")},
                        {"Metric": "Scheme type", "Value": details.get("scheme_type", "N/A")},
                        {"Metric": "Launch date", "Value": details.get("scheme_start_date", {}).get("date", "N/A") if isinstance(details.get("scheme_start_date"), dict) else details.get("scheme_start_date", "N/A")},
                    ]
                )
                st.dataframe(info_df, use_container_width=True, hide_index=True)

                if pack_b:
                    details_b = pack_b["details"]
                    compare = pd.DataFrame(
                        [
                            {"Metric": "1Y return", "Fund A": pct(pack_a["returns"].get("1Y")), "Fund B": pct(pack_b["returns"].get("1Y"))},
                            {"Metric": "3Y return", "Fund A": pct(pack_a["returns"].get("3Y")), "Fund B": pct(pack_b["returns"].get("3Y"))},
                            {"Metric": "5Y return", "Fund A": pct(pack_a["returns"].get("5Y")), "Fund B": pct(pack_b["returns"].get("5Y"))},
                            {"Metric": "Category", "Fund A": details.get("scheme_category", "N/A"), "Fund B": details_b.get("scheme_category", "N/A")},
                            {"Metric": "Fund house", "Fund A": details.get("fund_house", "N/A"), "Fund B": details_b.get("fund_house", "N/A")},
                        ]
                    )
                    st.markdown("### Head-to-head comparison")
                    st.dataframe(compare, use_container_width=True, hide_index=True)
                    merged = pd.merge(
                        pack_a["df"][["date", "nav"]].rename(columns={"nav": "Fund A"}),
                        pack_b["df"][["date", "nav"]].rename(columns={"nav": "Fund B"}),
                        on="date",
                        how="inner",
                    )
                    st.plotly_chart(create_line_chart(merged, "date", ["Fund A", "Fund B"], "NAV growth comparison", "NAV", normalize=True), use_container_width=True)
                else:
                    st.plotly_chart(create_line_chart(pack_a["df"], "date", ["nav"], "NAV trend", "NAV"), use_container_width=True)

                render_risk_flags(flags)
                render_mood_section(sent_a, title="Fund house news mood")

    with tab2:
        st.markdown("### SIP calculator")
        c1, c2 = st.columns([1, 1.2])
        with c1:
            monthly = st.number_input("Monthly SIP amount", min_value=500, max_value=500000, value=5000, step=500)
            annual_return = st.slider("Expected annual return", min_value=4.0, max_value=25.0, value=12.0, step=0.5)
            years = st.slider("Investment period", min_value=1, max_value=35, value=10)
        months = years * 12
        monthly_rate = annual_return / 12 / 100
        if monthly_rate == 0:
            future_value = monthly * months
        else:
            future_value = monthly * ((((1 + monthly_rate) ** months) - 1) / monthly_rate) * (1 + monthly_rate)
        invested = monthly * months
        gain = future_value - invested
        with c2:
            k1, k2, k3 = st.columns(3)
            k1.metric("Total invested", money(invested))
            k2.metric("Estimated gain", money(gain))
            k3.metric("Estimated value", money(future_value))
            st.plotly_chart(create_donut(["Invested", "Estimated gain"], [invested, gain], "SIP value split"), use_container_width=True)
        timeline = []
        for y in range(1, years + 1):
            m = y * 12
            val = monthly * ((((1 + monthly_rate) ** m) - 1) / monthly_rate) * (1 + monthly_rate) if monthly_rate else monthly * m
            timeline.append({"Year": y, "Invested": monthly * m, "Estimated value": val})
        st.plotly_chart(create_line_chart(pd.DataFrame(timeline), "Year", ["Invested", "Estimated value"], "SIP growth over time", "Amount in ₹"), use_container_width=True)

    with tab3:
        st.markdown("### How a beginner should choose a mutual fund")
        st.markdown(
            """
            <div class='explain-box'>
            First decide the goal and time period. For long-term wealth creation, equity funds may suit some investors but carry higher risk. For short-term money, debt or liquid funds may be safer. Compare funds within the same category, not randomly. A small cap fund should not be compared directly with a liquid fund.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("#### Simple checklist")
        checklist = pd.DataFrame(
            [
                {"Question": "Is it Direct or Regular?", "Beginner meaning": "Direct usually has lower cost than regular."},
                {"Question": "What category is it?", "Beginner meaning": "Large cap, flexi cap, small cap, debt etc. Risk changes by category."},
                {"Question": "How consistent is 3Y and 5Y return?", "Beginner meaning": "One good year is not enough."},
                {"Question": "What is the risk level?", "Beginner meaning": "Higher return funds often fluctuate more."},
                {"Question": "Does it match my time period?", "Beginner meaning": "Equity is usually better studied for longer periods."},
            ]
        )
        st.dataframe(checklist, use_container_width=True, hide_index=True)


def page_compare():
    render_hero(
        "Compare Center",
        "Compare two stocks, funds or IPOs side by side using beginner-friendly signals instead of confusing raw data.",
    )
    render_safe_note()
    mode = st.radio("What do you want to compare?", ["Stocks", "Mutual Funds", "IPOs"], horizontal=True)

    if mode == "Stocks":
        stock_df = load_stock_list()
        c1, c2 = st.columns(2)
        with c1:
            a = st.selectbox("Stock A", stock_df["Search_Label"].unique(), index=None)
        with c2:
            b = st.selectbox("Stock B", stock_df["Search_Label"].unique(), index=None)
        if a and b:
            ticker_a, name_a = a.split(" - ", 1)
            ticker_b, name_b = b.split(" - ", 1)
            da = get_stock_data(ticker_a, "5y")
            db = get_stock_data(ticker_b, "5y")
            sa = get_sentiment_pack(name_a)
            sb = get_sentiment_pack(name_b)
            if da and db:
                ca, fa = stock_clarity_score(da, sa)
                cb, fb = stock_clarity_score(db, sb)
                comp = pd.DataFrame(
                    [
                        {"Metric": "Clarity score", "Stock A": ca, "Stock B": cb},
                        {"Metric": "Last price", "Stock A": money(da["price"]), "Stock B": money(db["price"])},
                        {"Metric": "1Y return", "Stock A": pct(da["returns"].get("1Y")), "Stock B": pct(db["returns"].get("1Y"))},
                        {"Metric": "5Y return", "Stock A": pct(da["returns"].get("5Y")), "Stock B": pct(db["returns"].get("5Y"))},
                        {"Metric": "P/E", "Stock A": number(da["metrics"].get("P/E")), "Stock B": number(db["metrics"].get("P/E"))},
                        {"Metric": "Public mood", "Stock A": sa["mood_score"] if sa else "N/A", "Stock B": sb["mood_score"] if sb else "N/A"},
                    ]
                )
                st.dataframe(comp, use_container_width=True, hide_index=True)
                merged = pd.merge(
                    da["hist"][["Date", "Close"]].rename(columns={"Close": name_a[:24]}),
                    db["hist"][["Date", "Close"]].rename(columns={"Close": name_b[:24]}),
                    on="Date",
                    how="inner",
                )
                st.plotly_chart(create_line_chart(merged, "Date", [name_a[:24], name_b[:24]], "Price growth comparison", "Growth", normalize=True), use_container_width=True)
            else:
                st.error("Could not fetch both stocks.")

    elif mode == "Mutual Funds":
        schemes = get_mf_schemes()
        items = sorted([(name, code) for code, name in schemes.items()], key=lambda x: x[0])
        names = [i[0] for i in items]
        mapping = {name: code for name, code in items}
        c1, c2 = st.columns(2)
        with c1:
            a = st.selectbox("Fund A", names, index=None)
        with c2:
            b = st.selectbox("Fund B", names, index=None)
        if a and b:
            pa = get_mf_data(mapping[a])
            pb = get_mf_data(mapping[b])
            if pa and pb:
                comp = pd.DataFrame(
                    [
                        {"Metric": "1Y return", "Fund A": pct(pa["returns"].get("1Y")), "Fund B": pct(pb["returns"].get("1Y"))},
                        {"Metric": "3Y return", "Fund A": pct(pa["returns"].get("3Y")), "Fund B": pct(pb["returns"].get("3Y"))},
                        {"Metric": "5Y return", "Fund A": pct(pa["returns"].get("5Y")), "Fund B": pct(pb["returns"].get("5Y"))},
                        {"Metric": "Category", "Fund A": pa["details"].get("scheme_category", "N/A"), "Fund B": pb["details"].get("scheme_category", "N/A")},
                    ]
                )
                st.dataframe(comp, use_container_width=True, hide_index=True)
            else:
                st.error("Could not fetch both mutual funds.")

    else:
        ipo_df = load_ipo_data()
        c1, c2 = st.columns(2)
        with c1:
            a = st.selectbox("IPO A", ipo_df["Company"].tolist(), index=None)
        with c2:
            b = st.selectbox("IPO B", ipo_df["Company"].tolist(), index=None)
        if a and b:
            ra = ipo_df[ipo_df["Company"] == a].iloc[0]
            rb = ipo_df[ipo_df["Company"] == b].iloc[0]
            sa = get_sentiment_pack(a)
            sb = get_sentiment_pack(b)
            ca, _ = ipo_clarity_score(ra, sa)
            cb, _ = ipo_clarity_score(rb, sb)
            comp = pd.DataFrame(
                [
                    {"Metric": "Clarity score", "IPO A": ca, "IPO B": cb},
                    {"Metric": "Type", "IPO A": ra["Type"], "IPO B": rb["Type"]},
                    {"Metric": "Sector", "IPO A": ra["Sector"], "IPO B": rb["Sector"]},
                    {"Metric": "GMP", "IPO A": money(ra["GMP"]) if pd.notna(ra["GMP"]) else "TBA", "IPO B": money(rb["GMP"]) if pd.notna(rb["GMP"]) else "TBA"},
                    {"Metric": "Subscription", "IPO A": ra["Subscription"], "IPO B": rb["Subscription"]},
                ]
            )
            st.dataframe(comp, use_container_width=True, hide_index=True)


def page_learn():
    render_hero(
        "Learn Investing Without Feeling Dumb",
        "Plain-English explainers for people who are curious, scared or just starting with investing.",
    )
    render_safe_note()
    topic = st.selectbox("Choose a topic", list(LEARN_CONTENT.keys()))
    st.markdown(f"## {topic}")
    st.markdown(f"<div class='explain-box'>{LEARN_CONTENT[topic]}</div>", unsafe_allow_html=True)

    st.markdown("## Beginner glossary")
    glossary = pd.DataFrame(
        [
            {"Term": "P/E", "Simple meaning": "How expensive a stock is compared with its earnings."},
            {"Term": "ROE", "Simple meaning": "How efficiently the company uses shareholder money."},
            {"Term": "Debt/Equity", "Simple meaning": "How much debt the company has compared with its own funds."},
            {"Term": "GMP", "Simple meaning": "Unofficial IPO premium before listing. Useful but risky."},
            {"Term": "NAV", "Simple meaning": "Price of one unit of a mutual fund."},
            {"Term": "SIP", "Simple meaning": "Fixed amount invested regularly in a mutual fund."},
            {"Term": "Bulk deal", "Simple meaning": "A large market transaction by an investor or institution."},
            {"Term": "Market cap", "Simple meaning": "Total market value of a listed company."},
        ]
    )
    st.dataframe(glossary, use_container_width=True, hide_index=True)

    st.markdown("## What InvestRight should never do")
    st.markdown(
        """
        <div class='explain-box'>
        This product should not say buy this, sell this, guaranteed return or best stock today. The clean direction is research, education, comparison, risk flags and explainability.
        </div>
        """,
        unsafe_allow_html=True,
    )

# =========================================================
# NAVIGATION
# =========================================================

st.sidebar.markdown("## 📊 InvestRight.AI")
st.sidebar.caption(TAGLINE)

page = st.sidebar.radio(
    "Menu",
    ["Home", "IPOs", "Stocks", "Mutual Funds", "Compare", "Learn"],
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Product principle")
st.sidebar.caption("We do not tell users what to buy. We help them understand what they are looking at.")
st.sidebar.markdown("---")
st.sidebar.caption(DISCLAIMER)

if page == "Home":
    page_home()
elif page == "IPOs":
    page_ipos()
elif page == "Stocks":
    page_stocks()
elif page == "Mutual Funds":
    page_mutual_funds()
elif page == "Compare":
    page_compare()
elif page == "Learn":
    page_learn()

st.markdown(f"<div class='footer-note'>{DISCLAIMER}</div>", unsafe_allow_html=True)
