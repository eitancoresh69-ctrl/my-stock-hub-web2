import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# =====================================================
# הגדרות דף
# =====================================================

st.set_page_config(
    page_title="Investment Hub Elite PRO",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# CSS משופר
# =====================================================

st.markdown("""
<style>
html, body, [class*="css"]  {
    direction: rtl;
    text-align: right;
}

.metric-card {
    background: white;
    padding: 12px;
    border-radius: 10px;
    border-right: 5px solid #1a73e8;
}

.bull-box {
    background-color: #e8f5e9;
    padding: 10px;
    border-radius: 8px;
    border-right: 5px solid #2e7d32;
}

.bear-box {
    background-color: #ffebee;
    padding: 10px;
    border-radius: 8px;
    border-right: 5px solid #c62828;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# Sidebar
# =====================================================

st.sidebar.title("⚙️ הגדרות")

DEFAULT_STOCKS = ["MSFT","NVDA","AAPL"]
ALL_STOCKS = ["MSFT","AAPL","NVDA","TSLA","PLTR","MSTR","ENLT.TA"]

MY_STOCKS = st.sidebar.multiselect(
    "המניות שלי:",
    ALL_STOCKS,
    default=DEFAULT_STOCKS
)

SCAN_LIST = ["AMZN","AVGO","COST","MA","V","LLY","TSM","ADBE","NFLX"]

# =====================================================
# פונקציית ניקוי ערכים
# =====================================================

def safe(val, default=0):
    return val if val is not None else default

# =====================================================
# חישוב ציון איכות
# =====================================================

def quality_score(info):
    score = 0

    if safe(info.get("revenueGrowth")) > 0.10:
        score += 1
    if safe(info.get("returnOnEquity")) > 0.15:
        score += 1
    if safe(info.get("profitMargins")) > 0.15:
        score += 1
    if safe(info.get("freeCashflow")) > 0:
        score += 1
    if safe(info.get("debtToEquity")) < 100:
        score += 1

    return score

# =====================================================
# Bull / Bear משופר
# =====================================================

def get_bull_bear(info):

    bulls, bears = [], []

    if safe(info.get("revenueGrowth")) > 0.20:
        bulls.append("צמיחה חריגה בהכנסות (מעל 20%).")

    if safe(info.get("returnOnEquity")) > 0.20:
        bulls.append("ROE גבוה במיוחד — יעילות ניהולית חזקה.")

    if safe(info.get("freeCashflow")) > 0:
        bulls.append("תזרים מזומנים חיובי ויציב.")

    if safe(info.get("trailingPE")) > 40:
        bears.append("מכפיל רווח גבוה מאוד.")

    if safe(info.get("debtToEquity")) > 150:
        bears.append("רמת חוב גבוהה.")

    if safe(info.get("profitMargins")) < 0.10:
        bears.append("שולי רווח נמוכים.")

    return bulls, bears

# =====================================================
# שליפת נתונים חכמה
# =====================================================

@st.cache_data(ttl=1800)
def fetch_data(tickers):

    rows = []

    for t in tickers:
        try:
            stock = yf.Ticker(t)
            info = stock.info
            hist = stock.history(period="5d")

            if hist.empty:
                continue

            price = hist["Close"].iloc[-1]
            change = ((price / hist["Close"].iloc[-2]) - 1) * 100

            rows.append({
                "סימול": t,
                "מחיר": round(price,2),
                "שינוי %": round(change,2),
                "צמיחה": safe(info.get("revenueGrowth")),
                "ROE": safe(info.get("returnOnEquity")),
                "שוליים": safe(info.get("profitMargins")),
                "חוב": safe(info.get("debtToEquity")),
                "דירוג איכות": quality_score(info),
                "earnings": info.get("nextEarningsDate")
            })

        except:
            continue

    return pd.DataFrame(rows)

# =====================================================
# טעינת נתונים
# =====================================================

df = fetch_data(list(set(MY_STOCKS + SCAN_LIST)))

# =====================================================
# כותרת
# =====================================================

st.title("🚀 Investment Hub Elite PRO")

# =====================================================
# מדדי על
# =====================================================

col1, col2, col3, col4 = st.columns(4)

try:
    vix = yf.Ticker("^VIX").history(period="1d")["Close"].iloc[-1]
except:
    vix = 0

risk_mode = "🟢 רגוע" if vix < 20 else "🟠 תנודתי" if vix < 30 else "🔴 פחד"

col1.metric("מדד הפחד (VIX)", f"{vix:.2f}")
col2.metric("מצב שוק", risk_mode)
col3.metric("מניות איכות (4+)", len(df[df["דירוג איכות"] >= 4]))

if not df.empty:
    top = df.loc[df["שינוי %"].idxmax()]
    col4.metric("הזינוק היומי", f"{top['סימול']} ({top['שינוי %']}%)")

# =====================================================
# טאבים
# =====================================================

tab1, tab2, tab3 = st.tabs(["📊 טבלת איכות", "🐂 שור / 🐻 דוב", "🔔 דוחות קרובים"])

# =====================================================
# טאב 1
# =====================================================

with tab1:

    styled = df.style.applymap(
        lambda x: "color: green" if isinstance(x, (int,float)) and x > 0 else "",
        subset=["שינוי %"]
    )

    st.dataframe(styled, use_container_width=True, hide_index=True)

# =====================================================
# טאב 2
# =====================================================

with tab2:

    sel = st.selectbox("בחר מניה", MY_STOCKS)

    info = yf.Ticker(sel).info
    bulls, bears = get_bull_bear(info)

    col_bull, col_bear = st.columns(2)

    with col_bull:
        st.subheader("🐂 תרחיש שור")
        for b in bulls:
            st.markdown(f"<div class='bull-box'>✅ {b}</div>", unsafe_allow_html=True)

    with col_bear:
        st.subheader("🐻 תרחיש דוב")
        for br in bears:
            st.markdown(f"<div class='bear-box'>⚠️ {br}</div>", unsafe_allow_html=True)

# =====================================================
# טאב 3
# =====================================================

with tab3:

    found = False

    for _, row in df.iterrows():

        e = row["earnings"]

        if isinstance(e, list):
            e = e[0]

        if e:
            try:
                e_date = datetime.fromtimestamp(e)
                days = (e_date - datetime.now()).days

                if 0 <= days <= 7:
                    st.warning(f"{row['סימול']} מפרסמת דוח בעוד {days} ימים")
                    found = True
            except:
                pass

    if not found:
        st.success("אין דוחות בשבוע הקרוב.")
