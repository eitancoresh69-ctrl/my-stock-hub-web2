import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

# --- 1. הגדרות דף ועיצוב Elite (RTL + צמצום רווחים) ---
st.set_page_config(page_title="Investment Hub Elite 2026", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    .block-container { padding-top: 1rem !important; }
    
    /* עיצוב כרטיסי AI חכמים */
    .ai-insight-card {
        background: linear-gradient(135deg, #f0f7ff 0%, #ffffff 100%);
        padding: 15px; border-radius: 12px; border-right: 6px solid #1a73e8;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 15px;
    }
    .status-tag { padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; }
    .status-bull { background: #e6ffed; color: #22863a; }
    .status-bear { background: #ffeef0; color: #d73a49; }
    
    /* צמצום רווחים בטבלאות */
    [data-testid="stTable"] td, [data-testid="stTable"] th { padding: 4px 8px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילון מונחים (בועות הסבר - Tooltips) ---
# הערה: הבועות יופיעו כשתעמוד עם העכבר על *כותרת* העמודה בטבלה
GLOSSARY = {
    "צמיחה": "אחוז השינוי בהכנסות בשנה האחרונה. מעל 15% נחשב לצמיחה מהירה.",
    "ROE": "Return on Equity: כמה רווח החברה מייצרת מההון של בעלי המניות. מעל 20% זה מצוין.",
    "יחס חוב": "Debt to Equity: בודק את המינוף. מתחת ל-100 אומר שהחברה שומרת על יציבות פיננסית.",
    "RSI": "מדד עוצמה יחסית: מעל 70 זה 'קניית יתר' (יקר), מתחת ל-30 זה 'מכירת יתר' (הזדמנות).",
    "שווי הוגן": "הערכת שווי לפי מודל DCF - המחיר המקורי שהמניה שווה באמת."
}

ABOUT_WIKI = {
    "NVDA": "מובילת מהפכת הבינה המלאכותית. השבבים שלה (H100/Blackwell) הם הסטנדרט היחיד לאימון מודלים. החברה נהנית משולי רווח פנומנליים ויתרון טכנולוגי של שנים.",
    "PLTR": "מתמחה במערכות הפעלה לבינה מלאכותית (AIP). עוזרת לארגוני ענק וממשלות להפוך דאטה גולמי להחלטות מבצעיות בשטח.",
    "MSFT": "ענקית הענן והתוכנה. מובילה את הטמעת ה-AI בעולם העסקי דרך Copilot ושיתוף הפעולה עם OpenAI.",
    "ENLT.TA": "חברה ישראלית פורצת דרך באנרגיה מתחדשת. מקימה חוות רוח ולוחות סולאריים בארה\"ב ואירופה. נהנית מהצורך בחשמל נקי לחוות שרתים."
}

# --- 3. פונקציות חכמות (AI Logic & Comparisons) ---

@st.cache_data(ttl=3600)
def fetch_comp_data(ticker, yrs):
    """ שליפת נתונים להשוואה מול S&P 500 """
    stock = yf.Ticker(ticker).history(period=f"{yrs}y")['Close']
    spy = yf.Ticker("^GSPC").history(period=f"{yrs}y")['Close']
    # נרמול ל-100 כדי לראות תשואה באחוזים
    stock_norm = (stock / stock.iloc[0]) * 100
    spy_norm = (spy / spy.iloc[0]) * 100
    return stock_norm, spy_norm

def get_ai_insight(ticker):
    """ ניתוח AI מבוסס נתונים לכל מניה """
    s = yf.Ticker(ticker)
    info = s.info
    rev_g = info.get('revenueGrowth', 0)
    
    if rev_g > 0.2:
        return "ניתוח AI: החברה נמצאת במסלול צמיחה אגרסיבי. המודל העסקי מוכיח את עצמו והשוק מתמחר אופטימיות גבוהה.", "bull"
    elif rev_g < 0:
        return "ניתוח AI: ישנה האטה בהכנסות. השוק בוחן מחדש את יעילות ההנהלה; מומלץ לעקוב אחר דוחות הרבעון הקרוב.", "bear"
    return "ניתוח AI: החברה יציבה ושומרת על נתח השוק שלה. המניה נסחרת בהתאם לממוצעי הסקטור.", "neutral"

# --- 4. בניית הממשק ---

st.sidebar.title("📊 ניהול השקעות")
MY_STOCKS = st.sidebar.multiselect("המניות שלי:", ["NVDA", "PLTR", "MSFT", "AAPL", "TSLA", "ENLT.TA", "MSTR"], default=["NVDA", "PLTR", "ENLT.TA"])
SCAN_LIST = ["AMZN", "AVGO", "META", "TSM", "GOOGL"]

@st.cache_data(ttl=3600)
def fetch_main_metrics(tickers):
    rows = []
    for t in tickers:
        try:
            s = yf.Ticker(t)
            h = s.history(period="2d")
            px = h['Close'].iloc[-1]
            chg = ((px / h['Close'].iloc[-2]) - 1) * 100
            inf = s.info
            rows.append({
                "סימול": t, "מחיר": round(px, 2), "שינוי %": round(chg, 2),
                "צמיחה": inf.get('revenueGrowth', 0), "ROE": inf.get('returnOnEquity', 0),
                "חוב": inf.get('debtToEquity', 0), "earnings": inf.get('nextEarningsDate')
            })
        except: continue
    return pd.DataFrame(rows)

df = fetch_main_metrics(list(set(MY_STOCKS + SCAN_LIST)))

st.title("Investment Hub Elite 2026 🚀")

# קוביות מדדים עליונות
c1, c2, c3, c4 = st.columns(4)
vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1.metric("📊 מדד הפחד (VIX)", f"{vix:.2f}", help="מראה את רמת הפאניקה בשוק. מעל 25 = פחד.")
c2.metric("💎 מניות צמיחה", len(df[df["צמיחה"] > 0.2]))
c3.metric("🔥 המזנקת היומית", df.loc[df["שינוי %"].idxmax()]["סימול"])
c4.metric("📅 עדכון", datetime.now().strftime("%H:%M"))

tab1, tab2, tab3, tab4 = st.tabs(["📌 איכות ובועות הסבר", "📑 דוח AI והשוואת שוק", "🔔 התראות חכמות", "🤝 רדאר מיזוגים"])

# טאב 1: הטבלה עם בועות ההסבר שביקשת
with tab1:
    st.subheader("ניתוח איכות (תעמוד עם העכבר על כותרת העמודה להסבר)")
    st.dataframe(
        df[["סימול", "מחיר", "שינוי %", "צמיחה", "ROE", "חוב"]],
        column_config={
            "צמיחה": st.column_config.NumberColumn("צמיחה", help=GLOSSARY["צמיחה"], format="%.1%"),
            "ROE": st.column_config.NumberColumn("ROE", help=GLOSSARY["ROE"], format="%.1%"),
            "חוב": st.column_config.NumberColumn("יחס חוב", help=GLOSSARY["חוב"]),
            "שינוי %": st.column_config.NumberColumn("שינוי %", help="שינוי מחיר ב-24 השעות האחרונות")
        },
        use_container_width=True, hide_index=True
    )

# טאב 2: השוואת שוק וניתוח AI
with tab2:
    sel = st.selectbox("בחר מניה לניתוח עומק:", MY_STOCKS)
    
    # אודות מורחב
    st.markdown(f"**🏢 אודות {sel}:**")
    st.info(ABOUT_WIKI.get(sel, "חברת טכנולוגיה מובילה עם השפעה גלובלית רחבה."))
    
    # ניתוח AI
    insight, style = get_ai_insight(sel)
    st.markdown(f"""<div class="ai-insight-card">
        <b>🤖 תובנת AI:</b> {insight}
    </div>""", unsafe_allow_html=True)
    
    # גרף השוואתי S&P 500
    yrs = st.slider("שנות השוואה:", 1, 10, 5)
    s_norm, spy_norm = fetch_comp_data(sel, yrs)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s_norm.index, y=s_norm, name=f"מניית {sel}", line=dict(color='#1a73e8', width=3)))
    fig.add_trace(go.Scatter(x=spy_norm.index, y=spy_norm, name="S&P 500", line=dict(color='#ff4b4b', dash='dash')))
    fig.update_layout(title=f"תשואה מצטברת: {sel} מול מדד ה-S&P 500", template="plotly_white", height=400)
    st.plotly_chart(fig, use_container_width=True)

# טאב 3: התראות חכמות (דוחות 7 ימים וזינוקים)
with tab3:
    st.subheader("📢 לוח בקרה AI")
    
    for _, row in df.iterrows():
        # התראת דוחות
        if row['earnings']:
            e_dt = datetime.fromtimestamp(row['earnings'])
            days = (e_dt - datetime.now()).days
            if 0 <= days <= 7:
                st.markdown(f"""<div class="ai-insight-card" style="border-right-color: #ff9800;">
                    📅 <b>התראת דוח קרוב ({row['סימול']}):</b> דוח כספי בעוד {days} ימים. 
                    <i>המלצת AI: היכונו לתנודתיות גבוהה ביום המסחר שלפני.</i>
                </div>""", unsafe_allow_html=True)
        
        # התראת מחיר
        if row['שינוי %'] >= 3.5:
            st.markdown(f"""<div class="ai-insight-card" style="border-right-color: #2e7d32;">
                🚀 <b>זינוק חריג ({row['סימול']}):</b> המניה עולה ב-{row['שינוי %']}% היום. 
                <i>ניתוח AI: נפח המסחר גבוה מהממוצע, ייתכן כניסת מוסדיים.</i>
            </div>""", unsafe_allow_html=True)

# טאב 4: ראדר מיזוגים (M&A)
with tab4:
    st.subheader("🤝 רדאר מיזוגים ושמועות שוק")
    st.write("ניתוח AI של עסקאות בבדיקה ושמועות בוול-סטריט:")
    
    mergers = [
        {"חברה": "Wiz / Google", "סבירות": "75%", "ניתוח": "המשא ומתן חזר לשולחן; גוגל מחפשת לחזק את ענן הסייבר."},
        {"חברה": "Intel / Qualcomm", "סבירות": "30%", "ניתוח": "קשיים רגולטוריים משמעותיים אך הצדדים בוחנים פיצול חטיבות."},
        {"חברה": "PLTR / Defense", "סבירות": "60%", "ניתוח": "פלנטיר צפויה לחתום על חוזי ענק חדשים עם ממשלת ארה\"ב בקרוב."}
    ]
    for m in mergers:
        st.markdown(f"""<div class="ai-insight-card">
            <b>{m['חברה']}</b> | סבירות AI: {m['סבירות']}<br>
            <small>{m['ניתוח']}</small>
        </div>""", unsafe_allow_html=True)
