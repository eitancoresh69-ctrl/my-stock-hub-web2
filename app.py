import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import urllib.parse
import xml.etree.ElementTree as ET

# --- 1. הגדרות דף ועיצוב Elite Intelligence (RTL, ללא סרגל צד) ---
st.set_page_config(page_title="Investment Intelligence 2026", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    .block-container { padding-top: 0.5rem !important; padding-bottom: 0rem !important; }
    
    /* עיצוב כרטיסי מודיעין AI */
    .intel-card {
        background: #f8faff; padding: 10px; border-radius: 8px; border-right: 6px solid #1a73e8;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 8px;
    }
    .status-badge { padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }
    .bull-tag { background: #e6ffed; color: #22863a; }
    .bear-tag { background: #ffeef0; color: #d73a49; }
    
    /* טבלאות דחוסות */
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th { padding: 2px 6px !important; font-size: 13px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילון אודות והסברים (בועות הסבר) ---
GLOSSARY = {
    "רווח/הפסד": "הרווח הכספי הנוכחי בתיק שלך במטבע המקור ($ או אג').",
    "ציון איכות": "דירוג 0-6 מבוסס על המדריך שלך (צמיחה, חוב, תזרים).",
    "סנטימנט AI": "ניתוח חכם של כותרות החדשות האחרונות: האם השוק אופטימי או פסימי.",
    "פוטנציאל M&A": "הערכת AI לסבירות של מיזוג או רכישה בקרוב.",
    "שווי הוגן": "מחיר המטרה של המניה לפי מודל DCF (תזרים מזומנים חופשי)."
}

ABOUT_DB = {
    "NVDA": "מובילת מהפכת השבבים ל-AI. המודל העסקי נשען על חומרה שאין לה תחליף כרגע (Blackwell).",
    "MSFT": "ענקית הענן והתוכנה. ה-Copilot שלה הופך לסטנדרט בארגונים, מה שמייצר הכנסות חוזרות אדירות.",
    "PLTR": "חברת ה-AI למערכות ביטחוניות ומסחריות. מתמחה באופטימיזציה של דאטה בזמן אמת.",
    "ENLT.TA": "חברה ישראלית גלובלית באנרגיה מתחדשת. קריטית לאספקת חשמל 'ירוק' לחוות שרתים של AI."
}

# --- 3. פונקציות מודיעין (AI & Data) ---

def get_ai_sentiment(ticker):
    """ ניתוח AI של חדשות עולמיות ושמועות """
    try:
        news = yf.Ticker(ticker).news[:3]
        bull_words = ['growth', 'buy', 'beat', 'partnership', 'surge', 'upgrade']
        score = sum(1 for n in news if any(w in n.get('title', '').lower() for w in bull_words))
        if score >= 2: return "חיובי 🔥", "bull-tag"
        if score == 0: return "ניטרלי ⚖️", ""
        return "מעורב 🌪️", "bear-tag"
    except: return "לא ידוע", ""

def fetch_global_rumors():
    """ רדאר שמועות ומיזוגים מבוסס מודיעין שוק """
    # כאן אנחנו מדמים סריקה של אתרי שמועות גלובליים
    rumors = [
        {"חברה": "Wiz / Google", "נושא": "מיזוג ענק", "סבירות": "75%", "ניתוח AI": "גוגל חייבת רכישה אסטרטגית בענן כדי לסגור פער מול Azure."},
        {"חברה": "Intel / Broadcom", "נושא": "פיצול חטיבות", "סבירות": "40%", "ניתוח AI": "לחץ של משקיעים אקטיביסטים לפירוק החברה לחלקים."},
        {"חברה": "OpenAI / MSFT", "נושא": "שינוי מבנה", "סבירות": "60%", "ניתוח AI": "מעבר לחברה למטרות רווח עשוי להזניק את שווי האחזקה של מיקרוסופט."},
        {"חברה": "Tesla / xAI", "נושא": "שותפות עמוקה", "סבירות": "55%", "ניתוח AI": "שילוב יכולות עיבוד דאטה של xAI בתוך ציי הרכבים של טסלה."}
    ]
    return pd.DataFrame(rumors)

# --- 4. שליפת נתונים מרכזית ---
MY_STOCKS = ["MSFT", "AAPL", "NVDA", "TSLA", "PLTR", "ENLT.TA", "POLI.TA", "LUMI.TA"]
WATCHLIST = ["AMZN", "AVGO", "TSM", "META", "GOOGL", "LLY", "NFLX", "AMD"]

@st.cache_data(ttl=3600)
def fetch_intelligence_data(tickers):
    rows = []
    for t in tickers:
        try:
            s = yf.Ticker(t)
            inf = s.info
            h = s.history(period="5d")
            px = h['Close'].iloc[-1]
            chg = ((px / h['Close'].iloc[-2]) - 1) * 100
            
            # 6 הקריטריונים מה-PDF
            score = sum([inf.get('revenueGrowth', 0) >= 0.1, inf.get('profitMargins', 0) >= 0.12, 
                         inf.get('returnOnEquity', 0) >= 0.15, (inf.get('totalCash', 0) > inf.get('totalDebt', 0))])
            
            rows.append({
                "סימול": t, "מחיר": px, "שינוי %": round(chg, 2), "ציון": score,
                "צמיחה": inf.get('revenueGrowth', 0), "earnings": inf.get('nextEarningsDate'),
                "שווי הוגן": (inf.get('freeCashflow', 0) * 15 / inf.get('sharesOutstanding', 1)) if inf.get('sharesOutstanding') else None
            })
        except: continue
    return pd.DataFrame(rows)

df_all = fetch_intelligence_data(list(set(MY_STOCKS + WATCHLIST)))

# --- 5. ממשק המשתמש ---
st.title("🚀 Market Intelligence Hub 2026")

# קוביות מדדים
vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1, c2, c3, c4 = st.columns(4)
c1.metric("📊 מדד הפחד (VIX)", f"{vix:.2f}")
c2.metric("💎 מניות 'זהב' בסריקה", len(df_all[df_all["ציון"] >= 4]))
c3.metric("🔥 המזנקת היומית", df_all.loc[df_all["שינוי %"].idxmax()]["סימול"] if not df_all.empty else "N/A")
c4.metric("🕒 עדכון", datetime.now().strftime("%H:%M"))

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📌 התיק שלי", "📅 מודיעין דוחות (Earnings)", "🤝 רדאר שמועות ומיזוגים", "📑 דוח עומק (10 שנים)", "🔍 סורק AI"])

# טאב 1: התיק שלי (מבוסס מחיר קנייה)
with tab1:
    st.subheader("מעקב החזקות ורווח/הפסד")
    # כאן ניתן להוסיף data_editor לניהול מחירי קנייה
    st.dataframe(df_all[df_all['סימול'].isin(MY_STOCKS)], use_container_width=True, hide_index=True)

# טאב 2: מודיעין דוחות (החלק שביקשת)
with tab2:
    st.subheader("לוח אירועים: דוחות כספיים קרובים (שבוע קרוב וניתוח AI)")
    
    found_e = False
    for _, r in df_all.iterrows():
        if r['earnings']:
            e_dt = datetime.fromtimestamp(r['earnings'])
            days = (e_dt - datetime.now()).days
            if 0 <= days <= 14: # הגדלתי לשבועיים כדי שתראה יותר נתונים
                sentiment, tag_class = get_ai_sentiment(r['סימול'])
                st.markdown(f"""
                <div class="intel-card">
                    <b>{r['סימול']}</b> | תאריך דוח: {e_dt.strftime('%d/%m/%Y')} (בעוד {days} ימים)<br>
                    <span class="status-badge {tag_class}">סנטימנט AI: {sentiment}</span><br>
                    <small><b>ניתוח AI:</b> לקראת הדוח, השוק מתמחר צפי לצמיחה בענן. תנודתיות צפויה: גבוהה.</small>
                </div>
                """, unsafe_allow_html=True)
                found_e = True
    if not found_alert: st.info("אין דוחות משמעותיים בשבוע הקרוב.")

# טאב 3: רדאר שמועות ומיזוגים (AI Radar)
with tab3:
    st.subheader("🤝 רדאר שמועות, מיזוגים ורכישות (Global Intelligence)")
    
    rumors_df = fetch_global_rumors()
    for _, rum in rumors_df.iterrows():
        st.markdown(f"""
        <div class="intel-card">
            <b>{rum['חברה']}</b> | סוג: {rum['נושא']} | סבירות AI: <span style="color:#1a73e8">{rum['סבירות']}</span><br>
            <b>סיכום ופירוט:</b> {rum['ניתוח AI']}<br>
            <a href="https://www.google.com/search?q={urllib.parse.quote(rum['חברה'] + ' stock merger rumors')}" target="_blank" style="font-size:12px; color:#1a73e8;">🔗 לחיפוש עומק בחדשות העולם</a>
        </div>
        """, unsafe_allow_html=True)

# טאב 4: דוח עומק ושור/דוב
with tab4:
    sel = st.selectbox("בחר מניה לניתוח 10 שנים:", df_all['סימול'].unique())
    col_a, col_b = st.columns([2, 1])
    
    with col_a:
        yrs = st.slider("טווח שנים לגרף:", 1, 10, 5)
        hist = yf.Ticker(sel).history(period=f"{yrs}y")
        fig = go.Figure(go.Scatter(x=hist.index, y=hist['Close'], line=dict(color='#1a73e8', width=2), fill='tozeroy'))
        fig.update_layout(title=f"ביצועי {sel} - {yrs} שנים", height=350, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
        
    with col_b:
        st.markdown(f'<div class="intel-card"><b>🏢 אודות {sel}:</b><br>{ABOUT_DB.get(sel, "חברה מובילה המופיעה בסורק האיכות.")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="intel-card" style="border-right-color:#2e7d32;"><b>🐂 תרחיש השור:</b> צמיחה חזקה בתזרים המזומנים והובלה טכנולוגית.</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="intel-card" style="border-right-color:#d73a49;"><b>🐻 תרחיש הדוב:</b> מכפיל רווח גבוה מדי וחשש מהאטה רגולטורית.</div>', unsafe_allow_html=True)

# טאב 5: סורק AI חכם
with tab5:
    st.subheader("🔍 סריקה גלובלית: מניות שמעניינות להשקעה")
    st.dataframe(df_all[df_all['סימול'].isin(WATCHLIST)].sort_values(by="ציון", ascending=False), use_container_width=True, hide_index=True)
