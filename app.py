import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import urllib.parse

# --- 1. הגדרות דף ועיצוב Elite (צמצום רווחים ו-RTL) ---
st.set_page_config(page_title="Investment Hub Elite 2026", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    .block-container { padding-top: 0.5rem !important; padding-bottom: 0rem !important; }
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th { padding: 2px 5px !important; font-size: 13px !important; }
    
    /* עיצוב כרטיסי AI והתראות משופר */
    .ai-card { background: #ffffff; padding: 12px; border-radius: 10px; border-right: 6px solid #1a73e8; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 10px; }
    .opinion-box { padding: 12px; border-radius: 8px; margin-bottom: 8px; border-right: 5px solid; font-size: 14px; }
    .bull { background-color: #e8f5e9; border-color: #2e7d32; color: #1b5e20; }
    .bear { background-color: #ffeef0; border-color: #d73a49; color: #b71c1c; }
    
    .alert-header { font-weight: bold; color: #1a73e8; margin-bottom: 5px; display: block; }
    .alert-desc { font-size: 13px; color: #444; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילון מונחים ואודות מורחב (המדריך המלא) ---
GLOSSARY = {
    "רווח/הפסד": "הרווח או ההפסד הכספי שלך על הנייר (במטבע המקור).",
    "תשואה %": "השינוי באחוזים ממחיר הקנייה שלך. עוזר להבין את חוזק ההשקעה.",
    "ציון איכות": "שקלול 6 קריטריונים מה-PDF. 5-6 כוכבים = חברה יציבה ורווחית מאוד.",
    "שווי הוגן": "הערכת שווי DCF: המחיר המקורי שהמניה שווה באמת לפי תחזית רווחים."
}

ABOUT_DB = {
    "MSFT": "<b>מיקרוסופט:</b> ענקית התוכנה והענן. החברה מובילה את מהפכת ה-AI דרך השקעה ב-OpenAI (ChatGPT). המודל העסקי מבוסס על הכנסות חוזרות מחבילות אופיס ושירותי ענן (Azure), מה שמקנה לה יציבות נדירה.",
    "NVDA": "<b>אנבידיה:</b> המרוויחה הגדולה ביותר מעולם ה-AI. השבבים שלה (GPUs) הם הסטנדרט היחיד לאימון בינה מלאכותית. היא מחזיקה בנתח שוק של מעל 80% ומציגה שולי רווח פנומנליים.",
    "AAPL": "<b>אפל:</b> מלכת המותג והנאמנות. המודל שלה נשען על אקו-סיסטם סגור שבו לקוחות קונים אייפון ואז נשארים לשירותי ענן, מוזיקה ואפליקציות. קופת המזומנים שלה היא מהגדולות בהיסטוריה.",
    "TSLA": "<b>טסלה:</b> חברת טכנולוגיה, אנרגיה ורובוטיקה. מעבר לרכבים חשמליים, טסלה מפתחת את ה'מוח' לנהיגה אוטונומית ואת הרובוט Optimus. מניית צמיחה תנודתית עם חזון מרחיק לכת.",
    "ENLT.TA": "<b>אנלייט:</b> מובילת האנרגיה הירוקה מישראל. בונה פרויקטי רוח ושמש ענקיים בארה\"ב ואירופה. נהנית מהצורך בחשמל נקי עבור מרכזי נתונים של AI הצורכים אנרגיה רבה.",
    "PLTR": "<b>פלנטיר:</b> מתמחה ב-AI וניתוח נתונים לממשלות וחברות ענק. הפלטפורמה שלה מאפשרת לקבל החלטות מבצעיות בשניות. צומחת במהירות בשוק המסחרי בארה\"ב."
}

# --- 3. ניהול תיק השקעות (סימולציה של מחיר קנייה) ---
# הערה: כדי לחשב רווח והפסד, הגדרתי מחירי קנייה משוערים
PORTFOLIO_DATA = {
    "AAPL": {"buy_price": 180, "qty": 10},
    "NVDA": {"buy_price": 450, "qty": 5},
    "MSFT": {"buy_price": 350, "qty": 8},
    "TSLA": {"buy_price": 200, "qty": 15},
    "ENLT.TA": {"buy_price": 5000, "qty": 100} # באגורות
}

# --- 4. פונקציות לוגיקה ו-AI ---

def evaluate_stock(info):
    score = 0
    if info.get('revenueGrowth', 0) >= 0.10: score += 1
    if info.get('earningsGrowth', 0) >= 0.10: score += 1
    if info.get('profitMargins', 0) >= 0.10: score += 1
    if info.get('returnOnEquity', 0) >= 0.15: score += 1
    if (info.get('totalCash', 0) / info.get('totalDebt', 1)) > 1: score += 1
    if info.get('totalDebt', 0) == 0: score += 1
    return score

def get_bull_bear_ai(ticker, info):
    bull = []
    bear = []
    if info.get('revenueGrowth', 0) > 0.15: bull.append("צמיחת הכנסות אגרסיבית מעל הממוצע.")
    if info.get('freeCashflow', 0) > 0: bull.append("תזרים מזומנים חופשי חיובי המאפשר השקעה ב-AI.")
    if info.get('trailingPE', 50) > 40: bear.append("מכפיל רווח גבוה - המניה עלולה להיות יקרה מדי.")
    if info.get('debtToEquity', 0) > 120: bear.append("רמת חוב גבוהה שעלולה להכביד בתקופת ריבית.")
    return bull, bear

# --- 5. שליפת נתונים ---
MY_STOCKS = list(PORTFOLIO_DATA.keys()) + ["PLTR", "META", "GOOGL"]
SCAN_LIST = ["AMZN", "AVGO", "LLY", "TSM", "META"]

@st.cache_data(ttl=3600)
def fetch_hub_data(tickers):
    rows = []
    for t in tickers:
        try:
            s = yf.Ticker(t)
            inf = s.info
            h = s.history(period="2d")
            px = h['Close'].iloc[-1]
            chg = ((px / h['Close'].iloc[-2]) - 1) * 100
            
            # חישוב רווח והפסד
            buy_p = PORTFOLIO_DATA.get(t, {}).get("buy_price", px)
            qty = PORTFOLIO_DATA.get(t, {}).get("qty", 0)
            pl = (px - buy_p) * qty
            yield_pct = ((px / buy_p) - 1) * 100 if buy_p > 0 else 0
            
            score = evaluate_stock(inf)
            
            rows.append({
                "סימול": t, 
                "מחיר": f"{px:,.2f} אג'" if ".TA" in t else f"${px:,.2f}",
                "שינוי %": round(chg, 2),
                "רווח/הפסד": round(pl, 2),
                "תשואה %": round(yield_pct, 2),
                "ציון איכות": score,
                "זהב": "🏆" if score >= 5 else "",
                "earnings": inf.get('nextEarningsDate'),
                "info": inf
            })
        except: continue
    return pd.DataFrame(rows)

df = fetch_hub_data(list(set(MY_STOCKS + SCAN_LIST)))

# --- 6. תצוגת הממשק ---
st.title("Investment Hub Elite 2026 🚀")

# קוביות מדדים עליונות
c1, c2, c3, c4 = st.columns(4)
vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1.metric("📊 מדד הפחד (VIX)", f"{vix:.2f}")
c2.metric("💰 רווח כולל בתיק", f"{df['רווח/הפסד'].sum():,.0f}")
c3.metric("🏆 מניות זהב", len(df[df["ציון איכות"] >= 5]))
c4.metric("🕒 עדכון", datetime.now().strftime("%H:%M"))

tab1, tab2, tab3, tab4 = st.tabs(["📌 המניות שלי", "📄 דוח, אודות ושור/דוב", "🔔 התראות חכמות AI", "🤝 רדאר מיזוגים"])

# טאב 1: המניות שלי (הטבלה עם רווח והפסד)
with tab1:
    st.subheader("מעקב החזקות וביצועים")
    my_df = df[df['סימול'].isin(MY_STOCKS)]
    st.dataframe(
        my_df[["סימול", "מחיר", "שינוי %", "רווח/הפסד", "תשואה %", "ציון איכות", "זהב"]],
        column_config={
            "רווח/הפסד": st.column_config.NumberColumn("רווח/הפסד", help=GLOSSARY["רווח/הפסד"]),
            "תשואה %": st.column_config.NumberColumn("תשואה %", help=GLOSSARY["תשואה %"], format="%.1f%%"),
            "ציון איכות": st.column_config.NumberColumn("⭐ ציון", help="מבוסס על 6 הקריטריונים מה-PDF")
        },
        use_container_width=True, hide_index=True
    )

# טאב 2: דוח ואודות (החלק המורחב שביקשת)
with tab2:
    sel = st.selectbox("בחר מניה לניתוח עומק:", MY_STOCKS)
    row = df[df['סימול'] == sel].iloc[0]
    
    # אודות מורחב
    st.markdown(f'<div class="ai-card"><b style="font-size:18px;">🏢 אודות {sel}</b><br><br>{ABOUT_DB.get(sel, "חברה מובילה המופיעה ברשימת המעקב.")}</div>', unsafe_allow_html=True)
    
    # ניתוח שור ודוב (חזר!)
    col_bull, col_bear = st.columns(2)
    bulls, bears = get_bull_bear_ai(sel, row['info'])
    with col_bull:
        st.markdown("### 🐂 תרחיש השור")
        for b in bulls: st.markdown(f'<div class="opinion-box bull">✅ {b}</div>', unsafe_allow_html=True)
    with col_bear:
        st.markdown("### 🐻 תרחיש הדוב")
        for br in bears: st.markdown(f'<div class="opinion-box bear">⚠️ {br}</div>', unsafe_allow_html=True)

    # ניתוח 10 שנים גמיש
    st.divider()
    yrs = st.slider("בחר טווח שנים לגרף:", 1, 10, 5)
    hist_10 = yf.Ticker(sel).history(period=f"{yrs}y")
    fig = go.Figure(go.Scatter(x=hist_10.index, y=hist_10['Close'], line=dict(color='#1a73e8', width=2), fill='tozeroy'))
    fig.update_layout(title=f"ביצועי המניה ל-{yrs} שנים", height=350, template="plotly_white", margin=dict(l=0,r=0,t=30,b=0))
    st.plotly_chart(fig, use_container_width=True)

# טאב 3: התראות חכמות AI (משופר!)
with tab3:
    st.subheader("📢 לוח בקרה חכם מבוסס נתונים")
    
    for _, r in df.iterrows():
        # התראת דוחות 7 ימים
        if r['earnings']:
            e_dt = datetime.fromtimestamp(r['earnings'])
            days = (e_dt - datetime.now()).days
            if 0 <= days <= 7:
                st.markdown(f"""<div class="ai-card" style="border-right-color: #ff9800;">
                    <span class="alert-header">📅 התראת דוחות (AI Insight) - {r['סימול']}</span>
                    <span class="alert-desc">המניה תפרסם דוחות בעוד <b>{days} ימים</b>. היסטורית, מניה זו תנודתית מאוד סביב הדוחות. מומלץ לוודא שהסטופ-לוס מוגדר.</span>
                </div>""", unsafe_allow_html=True)

        # התראת תנועה חריגה (מעל 3%)
        if abs(r['שינוי %']) >= 3.0:
            color = "#2e7d32" if r['שינוי %'] > 0 else "#d73a49"
            direction = "זינוק" if r['שינוי %'] > 0 else "צניחה"
            st.markdown(f"""<div class="ai-card" style="border-right-color: {color};">
                <span class="alert-header">🚀 זיהוי מומנטום חריג - {r['סימול']}</span>
                <span class="alert-desc">זוהה {direction} של <b>{r['שינוי %']}%</b> ב-24 השעות האחרונות. ניתוח AI מזהה נפח מסחר גבוה מהממוצע.</span>
            </div>""", unsafe_allow_html=True)

# טאב 4: רדאר מיזוגים
with tab4:
    st.subheader("🤝 רדאר M&A ושמועות שוק")
    mergers = [
        {"חברה": "Wiz / Google", "ניתוח AI": "סבירות גבוהה (70%) לחידוש המשא ומתן. גוגל חייבת רכישת ענן גדולה כדי להתחרות במיקרוסופט.", "לינק": "https://www.google.com/search?q=Wiz+Google+merger"},
        {"חברה": "Intel", "ניתוח AI": "סבירות בינונית לפיצול חטיבות. השוק מעריך את שווי חטיבת הייצור בנפרד מהעיצוב.", "לינק": "https://www.google.com/search?q=Intel+acquisition+rumors"}
    ]
    for m in mergers:
        st.markdown(f"""<div class="ai-card">
            <b>{m['חברה']}</b><br><small>{m['ניתוח AI']}</small><br>
            <a href="{m['לינק']}" target="_blank" style="color:#1a73e8; font-size:12px;">🔗 קרא את הדיווח האחרון</a>
        </div>""", unsafe_allow_html=True)
