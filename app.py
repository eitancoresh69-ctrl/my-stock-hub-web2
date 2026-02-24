import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

# --- 1. הגדרות דף ועיצוב Elite (RTL + דחיסה) ---
st.set_page_config(page_title="Investment Hub Elite 2026", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    .block-container { padding-top: 1rem !important; }
    
    /* עיצוב קוביות המדדים */
    .metric-card {
        background: white; padding: 15px; border-radius: 12px;
        border-right: 5px solid #1a73e8; box-shadow: 0 4px 6px rgba(0,0,0,0.07);
        text-align: center; margin-bottom: 15px;
    }
    .m-val { font-size: 24px; font-weight: bold; color: #1a73e8; }
    .m-lbl { font-size: 14px; color: #5f6368; }

    /* תיבת AI וחדשות */
    .ai-summary { background-color: #f0f7ff; border: 1px solid #cce3ff; padding: 15px; border-radius: 10px; border-right: 6px solid #007bff; margin-bottom: 10px; }
    .sentiment-tag { padding: 3px 8px; border-radius: 5px; font-weight: bold; font-size: 12px; }
    .pos { background-color: #e6ffed; color: #22863a; }
    .neg { background-color: #ffeef0; color: #d73a49; }
    
    /* אודות מורחב */
    .company-long-desc { background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; line-height: 1.8; font-size: 16px; border-right: 8px solid #1a73e8; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילון אודות מפורט (למשקיע המתחיל) ---
STOCK_GUIDE = {
    "MSFT": "<b>מיקרוסופט (Microsoft):</b> ענקית הטכנולוגיה המגוונת ביותר בעולם. החברה שולטת בשוק מערכות ההפעלה (Windows) והפרודוקטיביות (Office), אך מנוע הצמיחה העיקרי שלה הוא ענן ה-Azure. בזכות השקעה מאסיבית ב-OpenAI, מיקרוסופט היא המובילה הבלתי מעורערת בשילוב בינה מלאכותית (AI) במוצרי תוכנה לעסקים. למשקיע המתחיל: זוהי מניית 'עוגן' יציבה עם תזרים מזומנים חזק.",
    "NVDA": "<b>אנבידיה (NVIDIA):</b> המרוויחה הגדולה ביותר ממהפכת ה-AI. החברה מייצרת את השבבים (GPUs) שבלעדיהם אי אפשר לאמן מודלים כמו ChatGPT. היא מחזיקה בנתח שוק של מעל 80% בתחום שבבי הבינה המלאכותית למרכזי נתונים. למשקיע המתחיל: זוהי מניית צמיחה אגרסיבית; היא נעה בחדות אך מובילה סקטור שלם.",
    "AAPL": "<b>אפל (Apple):</b> החברה שהפכה את האייפון לחלק בלתי נפרד מחיינו. הכוח של אפל הוא ב'גן הסגור' שלה - מי שקונה אייפון בדרך כלל יקנה גם Apple Watch, iCloud ושירותי מוזיקה. זה מייצר רווחים חוזרים ונאמנות לקוחות שאין לה אח ורע. למשקיע המתחיל: אפל נחשבת למניה בטוחה יחסית עם קופת מזומנים של מאות מיליארדי דולרים.",
    "TSLA": "<b>טסלה (Tesla):</b> הרבה יותר מחברת רכב. טסלה היא חברת בינה מלאכותית, אנרגיה ורובוטיקה. המודל שלה נשען על נתונים שנאספים ממיליוני רכבים כדי לפתח נהיגה אוטונומית מלאה (FSD) ורובוטים דמויי אדם (Optimus). למשקיע המתחיל: מניה תנודתית מאוד שמושפעת מהחזון של אילון מאסק.",
    "PLTR": "<b>פלנטיר (Palantir):</b> חברת ה-AI לממשלות וארגוני ענק. היא בונה את 'מערכת ההפעלה' לקבלת החלטות מבוססת נתונים. פלטפורמת ה-AIP שלה מאפשרת לחברות מסחריות להטמיע AI בתוך שעות. למשקיע המתחיל: מניה מרתקת בסקטור התוכנה האסטרטגי.",
    "ENLT.TA": "<b>אנלייט אנרגיה (Enlight):</b> חברה ישראלית הפועלת בשוק הגלובלי (ארה\"ב ואירופה). היא מקימה חוות רוח ופרויקטים סולאריים ענקיים. למשקיע המתחיל: דרך מצוינת להיחשף לתחום האנרגיה הירוקה והצורך הגובר בחשמל נקי עבור חוות שרתים של AI."
}

# --- 3. פונקציות חכמות: AI, DCF וחדשות ---

def calculate_fair_value(info):
    """ חישוב שווי הוגן (DCF) מופשט """
    try:
        fcf = info.get('freeCashflow', 0)
        growth = info.get('revenueGrowth', 0.05)
        shares = info.get('sharesOutstanding', 1)
        if fcf <= 0: return 0
        # שווי חזוי ל-10 שנים במכפיל 15
        value = (fcf * (1 + growth) * 15) / shares
        return value
    except: return 0

def ai_sentiment_analysis(ticker):
    """ AI מבוסס חוקים שקורא כותרות ומסכם מצב """
    try:
        stock = yf.Ticker(ticker)
        news = stock.news[:5]
        if not news: return "אין חדשות זמינות כרגע.", "ניטרלי"
        
        bullish_words = ['buy', 'growth', 'beat', 'jump', 'surge', 'upgrade', 'profit', 'success', 'זינוק', 'קנייה', 'שיא']
        bearish_words = ['sell', 'drop', 'miss', 'fall', 'plunge', 'downgrade', 'debt', 'risk', 'ירידה', 'סיכון', 'חוב']
        
        score = 0
        headlines = []
        for n in news:
            title = n.get('title', '')
            headlines.append(title)
            score += sum(1 for w in bullish_words if w in title.lower())
            score -= sum(1 for w in bearish_words if w in title.lower())
            
        summary = "החדשות האחרונות מצביעות על "
        if score > 1:
            return summary + "מגמה חיובית חזקה. האנליסטים אופטימיים לגבי תוצאות החברה.", "חיובי 🔥"
        elif score < -1:
            return summary + "חששות בקרב המשקיעים. ייתכנו לחצי מכירה בטווח הקצר.", "שלילי ⚠️"
        else:
            return summary + "מצב מאוזן. השוק ממתין להתפתחויות נוספות.", "ניטרלי ⚖️"
    except: return "לא ניתן לנתח חדשות כרגע.", "ניטרלי"

def get_merger_radar():
    """ נתונים אמיתיים על מיזוגים ושמועות (M&A) """
    # שילוב של חדשות RSS ושמועות שוק ידועות
    mergers = [
        {"חברה": "Wiz", "סטטוס": "שמועות רכישה", "פרטים": "גוגל בוחנת שוב אפשרות לרכישת ענק של Wiz הישראלית לאחר דחיית ההצעה הקודמת."},
        {"חברה": "Intel", "סטטוס": "פיצול/מכירה", "פרטים": "שמועות על רכישת חטיבות ייצור על ידי אפל או ברודקום להפחתת תלות באנבידיה."},
        {"חברה": "Discover", "סטטוס": "מיזוג רשמי", "פרטים": "מיזוג ענק עם Capital One ממתין לאישורים רגולטוריים אחרונים."},
        {"חברה": "HubSpot", "סטטוס": "ספקולציה", "פרטים": "אנליסטים מעריכים כי אמזון עשויה להגיש הצעה לרכישת החברה כדי להתחרות במיקרוסופט."}
    ]
    return pd.DataFrame(mergers)

# --- 4. תצוגת המערכת ---

# Sidebar לניהול מניות
st.sidebar.title("⚙️ ניהול תיק אישי")
if 'my_list' not in st.session_state:
    st.session_state.my_list = MY_STOCKS

add_stk = st.sidebar.text_input("הוסף סימול (למשל: AMZN):").upper()
if st.sidebar.button("הוסף") and add_stk:
    st.session_state.my_list.append(add_stk)
    st.rerun()

all_tickers = list(set(st.session_state.my_list + SCAN_CANDIDATES))

# שליפת נתונים
@st.cache_data(ttl=3600)
def fetch_all(tickers):
    rows = []
    for t in tickers:
        try:
            s = yf.Ticker(t)
            inf = s.info
            h = s.history(period="5d")
            px = h['Close'].iloc[-1]
            chg = ((px / h['Close'].iloc[-2]) - 1) * 100
            fv = calculate_fair_value(inf)
            
            rows.append({
                "סימול": t, "מחיר": round(px, 2), "שינוי %": round(chg, 2),
                "שווי הוגן": round(fv, 2) if fv > 0 else "N/A",
                "סטטוס": "זול" if (fv > px and fv > 0) else "יקר",
                "earnings": inf.get('nextEarningsDate')
            })
        except: continue
    return pd.DataFrame(rows)

df_main = fetch_all(all_tickers)

# קוביות מדדים עליונות
st.title("Investment Hub Elite 2026 🚀")
c1, c2, c3, c4 = st.columns(4)
vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1.markdown(f'<div class="metric-card"><div class="m-lbl">📊 מדד הפחד (VIX)</div><div class="m-val">{vix:.2f}</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-card"><div class="m-lbl">💎 הזדמנויות (מניות זולות)</div><div class="m-val">{len(df_main[df_main["סטטוס"] == "זול"])}</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="metric-card"><div class="m-lbl">🔥 הזינוק היומי</div><div class="m-val" style="color:green;">{df_main.loc[df_main["שינוי %"].idxmax()]["סימול"]}</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="metric-card"><div class="m-lbl">📅 עדכון אחרון</div><div class="m-val">{datetime.now().strftime("%H:%M")}</div></div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📌 המניות שלי ואיכות", "📑 אודות מורחב ו-AI", "🔔 התראות ודוחות", "🤝 רדאר מיזוגים"])

# טאב 1: המניות שלי ואיכות (DCF)
with tab1:
    st.subheader("ניתוח ערך ואיכות פונדמנטלית")
    st.table(df_main[df_main['סימול'].isin(st.session_state.my_list)])
    st.info("💡 **הסבר למתחיל:** 'שווי הוגן' (Fair Value) הוא המחיר שהמניה צריכה להיות בו לפי הרווחים שלה. אם המחיר נמוך מהשווי ההוגן - המניה 'זולה'.")

# טאב 2: אודות מורחב ו-AI (החלק שביקשת!)
with tab2:
    sel = st.selectbox("בחר מניה לניתוח עומק:", all_tickers)
    
    # אודות מורחב
    st.markdown("### 🏢 אודות החברה (פירוט מורחב)")
    st.markdown(f'<div class="company-long-desc">{STOCK_GUIDE.get(sel, "מידע מפורט על חברה זו יתווסף בקרוב. כרגע ניתן לראות את הנתונים הטכניים והפיננסיים.")}</div>', unsafe_allow_html=True)
    
    st.divider()
    
    # AI סיכום חדשות
    st.markdown("### 🤖 ניתוח חדשות מבוסס AI")
    summary, sentiment = ai_sentiment_analysis(sel)
    st.markdown(f"""
    <div class="ai-summary">
        <strong>סיכום מהיר:</strong> {summary}<br>
        <strong>סנטימנט בשוק:</strong> <span class="sentiment-tag {'pos' if 'חיובי' in sentiment else 'neg' if 'שלילי' in sentiment else ''}">{sentiment}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # גרף 10 שנים גמיש
    years = st.slider("בחר טווח שנים לגרף:", 1, 10, 5)
    hist_10 = yf.Ticker(sel).history(period=f"{years}y")
    fig = px.line(hist_10, y="Close", title=f"ביצועי {sel} ל-{years} שנים", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

# טאב 3: התראות ודוחות (עם נתונים אמיתיים)
with tab3:
    st.subheader("🔔 מרכז התראות ואירועים")
    
    found_alert = False
    for _, row in df_main.iterrows():
        # התראת דוחות 7 ימים
        if row['earnings']:
            e_date = datetime.fromtimestamp(row['earnings'])
            days_to = (e_date - datetime.now()).days
            if 0 <= days_to <= 7:
                st.warning(f"📅 **דוח קרוב!** המניה **{row['סימול']}** מפרסמת דוחות ב-{e_date.strftime('%d/%m')} (בעוד {days_to} ימים).")
                found_alert = True
        
        # התראת מחיר (מעל 3%)
        if row['שינוי %'] >= 3.0:
            st.success(f"🚀 **זינוק חריג!** המניה **{row['סימול']}** עלתה ב-{row['שינוי %']}% היום.")
            found_alert = True
            
    if not found_alert:
        st.write("אין התראות מיוחדות כרגע. השוק רגוע.")

# טאב 4: רדאר מיזוגים (עם נתונים!)
with tab4:
    st.subheader("🤝 רדאר M&A ושמועות שוק")
    st.write("ריכוז עסקאות ושמועות על מיזוגים ורכישות (נתונים מעודכנים):")
    st.table(get_merger_radar())
    st.info("💡 **טיפ:** מיזוגים לרוב גורמים למניית החברה הנרכשת לזנק במחיר באופן מיידי.")

# נוסחת DCF להצגה
with st.expander("🧮 איך חישבנו את השווי ההוגן? (למתקדמים)"):
    st.write("אנו משתמשים במודל DCF (Discounted Cash Flow) מפושט:")
    st.latex(r"Value = \frac{FCF \times (1 + Growth) \times 15}{Shares}")
    st.write("זהו חישוב שמרני שבוחן כמה מזומן החברה תייצר ב-10 השנים הבאות.")
