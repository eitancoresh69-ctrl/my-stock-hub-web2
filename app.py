import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. הגדרות דף ועיצוב Elite (RTL + Tooltips) ---
st.set_page_config(page_title="Investment Hub Elite 2026", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    
    .block-container { padding-top: 1rem !important; }
    
    /* עיצוב תיבות שור/דוב */
    .opinion-box { padding: 15px; border-radius: 10px; margin-bottom: 10px; border-right: 6px solid; }
    .bull-box { background-color: #e8f5e9; border-color: #2e7d32; color: #1b5e20; }
    .bear-box { background-color: #ffeef0; border-color: #d73a49; color: #b71c1c; }
    
    /* עיצוב כללי */
    .metric-card { background: white; padding: 12px; border-radius: 10px; border-right: 5px solid #1a73e8; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; }
    .about-box { background-color: #f1f8ff; padding: 15px; border-radius: 10px; border-right: 6px solid #1a73e8; line-height: 1.6; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילון מונחים ובועות הסבר (המדריך החי) ---
GLOSSARY = {
    "צמיחה": "צמיחה בהכנסות: מראה אם העסק גדל ומוכר יותר משנה לשנה. צמיחה מעל 10% נחשבת למצוינת.",
    "ROE": "תשואה על ההון: כמה רווח החברה מייצרת על כל שקל שבעלי המניות השקיעו. ככל שזה גבוה יותר, החברה יעילה יותר.",
    "שוליים": "שולי רווח נקי: כמה אחוזים נשארים לחברה בכיס מכל שקל של הכנסה אחרי כל ההוצאות.",
    "חוב": "יחס חוב להון: בודק כמה החברה חייבת לעומת מה שיש לה. יחס מתחת ל-100 נחשב לבריא ושמרני.",
    "שווי הוגן": "הערכת שווי DCF: המחיר התיאורטי שהמניה שווה לפי תחזית הרווחים העתידית שלה. עוזר לדעת אם המחיר בשוק זול או יקר."
}

# --- 3. פונקציות לוגיקה ---

def get_bull_bear(info, ticker):
    """ ניתוח שור מול דוב מבוסס נתונים חצי-AI """
    bull_reasons = []
    bear_reasons = []
    
    # לוגיקת שור (חיובי)
    if info.get('revenueGrowth', 0) > 0.15: bull_reasons.append("צמיחה מהירה בהכנסות המעידה על השתלטות על השוק.")
    if info.get('returnOnEquity', 0) > 0.20: bull_reasons.append("יעילות אדירה בייצור רווח מהון עצמי.")
    if info.get('freeCashflow', 0) > 0: bull_reasons.append("תזרים מזומנים חופשי חיובי המאפשר השקעות ודיבידנדים.")
    
    # לוגיקת דוב (סיכונים)
    if info.get('trailingPE', 0) > 40: bear_reasons.append("מכפיל רווח גבוה מאוד - המניה עלולה להיות בבועה.")
    if info.get('debtToEquity', 0) > 150: bear_reasons.append("רמת חוב גבוהה שעלולה להכביד בתקופות של ריבית עולה.")
    if info.get('profitMargins', 0) < 0.10: bear_reasons.append("שולי רווח נמוכים המשאירים מעט מקום לטעויות.")

    return bull_reasons, bear_reasons

# --- 4. תצוגת המערכת ---

# Sidebar
st.sidebar.title("⚙️ הגדרות ורשימות")
MY_STOCKS = st.sidebar.multiselect("המניות שלי:", ["MSFT", "AAPL", "NVDA", "TSLA", "PLTR", "MSTR", "ENLT.TA"], default=["MSFT", "NVDA", "AAPL"])
SCAN_LIST = ["AMZN", "AVGO", "COST", "MA", "V", "LLY", "TSM", "ADBE", "NFLX"]

@st.cache_data(ttl=3600)
def fetch_data(tickers):
    rows = []
    for t in tickers:
        try:
            s = yf.Ticker(t)
            inf = s.info
            h = s.history(period="5d")
            px = h['Close'].iloc[-1]
            chg = ((px / h['Close'].iloc[-2]) - 1) * 100
            
            rows.append({
                "סימול": t, "מחיר": round(px, 2), "שינוי %": round(chg, 2),
                "צמיחה": inf.get('revenueGrowth', 0), "ROE": inf.get('returnOnEquity', 0),
                "שוליים": inf.get('profitMargins', 0), "חוב": inf.get('debtToEquity', 0),
                "earnings": inf.get('nextEarningsDate')
            })
        except: continue
    return pd.DataFrame(rows)

df = fetch_data(list(set(MY_STOCKS + SCAN_LIST)))

st.title("🚀 Investment Hub Elite 2026")

# קוביות מדדים עליונות
c1, c2, c3, c4 = st.columns(4)
vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1.metric("📊 מדד הפחד (VIX)", f"{vix:.2f}", help="מראה את רמת התנודתיות בשוק. מעל 25 מעיד על פחד.")
c2.metric("💎 מניות איכות", len(df[df["ROE"] > 0.15]))
c3.metric("🔥 הזינוק היומי", df.loc[df["שינוי %"].idxmax()]["סימול"])
c4.metric("📅 עדכון", datetime.now().strftime("%H:%M"))

tab1, tab2, tab3, tab4 = st.tabs(["📌 טבלת איכות (עם הסברים)", "📑 דוח שור/דוב", "🔔 התראות דוחות", "🤝 רדאר מיזוגים"])

with tab1:
    st.subheader("ניתוח איכות עם המדריך החי")
    # שימוש ב-column_config להצגת בועות הסבר בעברית
    st.dataframe(
        df[["סימול", "מחיר", "שינוי %", "צמיחה", "ROE", "שוליים", "חוב"]],
        column_config={
            "צמיחה": st.column_config.NumberColumn("צמיחה", help=GLOSSARY["צמיחה"], format="%.1%"),
            "ROE": st.column_config.NumberColumn("ROE", help=GLOSSARY["ROE"], format="%.1%"),
            "שוליים": st.column_config.NumberColumn("שוליים", help=GLOSSARY["שוליים"], format="%.1%"),
            "חוב": st.column_config.NumberColumn("חוב", help=GLOSSARY["חוב"]),
        },
        use_container_width=True,
        hide_index=True
    )
    st.caption("💡 טיפ: העבר את העכבר מעל שמות העמודות בטבלה כדי לראות מה כל מדד אומר.")

with tab2:
    sel = st.selectbox("בחר מניה לניתוח שור/דוב:", MY_STOCKS)
    s_obj = yf.Ticker(sel)
    
    col_bull, col_bear = st.columns(2)
    bulls, bears = get_bull_bear(s_obj.info, sel)
    
    with col_bull:
        st.markdown("### 🐂 תרחיש השור (למה לקנות?)")
        for b in bulls: st.markdown(f'<div class="opinion-box bull-box">✅ {b}</div>', unsafe_allow_html=True)
    
    with col_bear:
        st.markdown("### 🐻 תרחיש הדוב (ממה להיזהר?)")
        for br in bears: st.markdown(f'<div class="opinion-box bear-box">⚠️ {br}</div>', unsafe_allow_html=True)
        
    

[Image of bull and bear market concepts]


with tab3:
    st.subheader("🔔 התראת דוחות (7 ימים מראש)")
    found_alert = False
    for _, row in df.iterrows():
        if row['earnings']:
            e_date = datetime.fromtimestamp(row['earnings'])
            days = (e_date - datetime.now()).days
            if 0 <= days <= 7:
                st.warning(f"📅 המניה **{row['סימול']}** מפרסמת דוח בעוד {days} ימים! ({e_date.strftime('%d/%m')})")
                found_alert = True
    if not found_alert: st.write("אין דוחות קרובים בשבוע הקרוב.")

with tab4:
    st.subheader("🤝 רדאר מיזוגים ושמועות חמות")
    st.markdown("""
    * **שמועה:** Broadcom בוחנת רכישה של חברת שבבים בתחום האופטיקה.
    * **דיווח:** OpenAI שוקלת להפוך לחברה למטרות רווח, מה שעשוי להשפיע על מיקרוסופט.
    """)
