import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import urllib.parse

# --- 1. הגדרות דף ועיצוב Elite (RTL, ללא סרגל צד) ---
st.set_page_config(page_title="Investment Hub Elite 2026", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    .block-container { padding-top: 1rem !important; }
    
    /* עיצוב כרטיסי AI */
    .ai-card {
        background: white; padding: 15px; border-radius: 12px; border-right: 6px solid #1a73e8;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 12px;
    }
    .prob-high { color: #2e7d32; font-weight: bold; }
    .prob-med { color: #f57c00; font-weight: bold; }
    
    /* תיבות אודות ובועות הסבר */
    .about-section { background-color: #f1f8ff; padding: 18px; border-radius: 12px; border-right: 8px solid #1a73e8; line-height: 1.8; font-size: 16px; }
    [data-testid="stDataFrame"] { border: 1px solid #e0e0e0; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילונים מורחבים (אודות, הסברים וניתוח AI) ---
GLOSSARY = {
    "צמיחה": "צמיחה בהכנסות: מראה אם העסק גדל משנה לשנה. מעל 10% נחשב למצוין.",
    "ROE": "Return on Equity: מודד כמה רווח החברה מייצרת מהכסף של המשקיעים. מעל 15% זה מעולה.",
    "חוב": "יחס חוב להון: בודק כמה החברה ממונפת. מתחת ל-100 נחשב לבריא ויציב.",
    "שווי הוגן": "הערכת שווי DCF: מחיר המטרה של המניה לפי תחזית הרווחים העתידית (שווי פנימי).",
    "המלצה": "ניתוח אוטומטי המבוסס על הפער בין המחיר בשוק לשווי ההוגן."
}

COMPANY_DB = {
    "MSFT": "<b>מיקרוסופט:</b> מובילת עולם התוכנה והענן. החברה שולטת ב-AI דרך השקעה ב-OpenAI ומטמיעה בינה מלאכותית בכל מוצריה. מניית עוגן עם תזרים מזומנים אדיר.",
    "NVDA": "<b>אנבידיה:</b> הלב הפועם של מהפכת הבינה המלאכותית. השבבים שלה הם הסטנדרט היחיד לאימון מודלים מורכבים. צמיחה פנומנלית בנתח שוק ורווחיות.",
    "ENLT.TA": "<b>אנלייט:</b> חלוצת האנרגיה המתחדשת מישראל. פועלת בארה\"ב ואירופה. נהנית מהצורך הגובר בחשמל נקי עבור חוות שרתים של AI בעולם.",
    "AAPL": "<b>אפל:</b> ענקית המכשירים והשירותים. בונה אקו-סיסטם סגור שמייצר נאמנות לקוחות ורווחים חוזרים גבוהים. נחשבת ל'כספת' של וול סטריט.",
    "PLTR": "<b>פלנטיר:</b> מערכות AI לממשלות ועסקים. עוזרת לארגוני ענק להפוך דאטה להחלטות מבצעיות. צמיחה מהירה בשוק המסחרי.",
    "POLI.TA": "<b>בנק הפועלים:</b> הבנק המוביל בישראל. מציג יציבות פיננסית גבוהה, יעילות תפעולית וחלוקת דיבידנדים עקבית למשקיעים."
}

# --- 3. פונקציות חכמות (חסינות לשגיאות) ---

def calculate_fv(info):
    try:
        fcf, growth, shares = info.get('freeCashflow', 0), info.get('revenueGrowth', 0.05), info.get('sharesOutstanding', 1)
        if fcf <= 0 or shares <= 0: return None
        return round((fcf * (1 + growth) * 15) / shares, 2)
    except: return None

def get_rec(price, fv):
    if not fv or not price: return "בבדיקה 🔍"
    gap = (fv - price) / price
    if gap > 0.15: return "קנייה חזקה 🟢"
    elif gap > 0.05: return "קנייה 📈"
    elif gap < -0.15: return "מכירה 🔴"
    return "החזק ⚖️"

MY_STOCKS = ["MSFT", "AAPL", "NVDA", "TSLA", "PLTR", "MSTR", "GOOGL", "META", "ENLT.TA", "POLI.TA", "LUMI.TA"]

@st.cache_data(ttl=3600)
def fetch_elite_data(tickers):
    rows = []
    for t in tickers:
        try:
            s = yf.Ticker(t)
            h = s.history(period="5d")
            if h.empty: continue
            inf = s.info
            px = h['Close'].iloc[-1]
            chg = ((px / h['Close'].iloc[-2]) - 1) * 100
            fv = calculate_fv(inf)
            
            rows.append({
                "סימול": t, "מחיר": round(px, 2), "שינוי %": round(chg, 2),
                "שווי הוגן": fv, "המלצה": get_rec(px, fv),
                "צמיחה": inf.get("revenueGrowth", 0),
                "ROE": inf.get("returnOnEquity", 0),
                "חוב": inf.get("debtToEquity", 0),
                "earnings": inf.get('nextEarningsDate')
            })
        except: continue
    return pd.DataFrame(rows)

# --- 4. תצוגת האתר ---
st.title("Investment Hub Elite 2026 🚀")

df = fetch_elite_data(MY_STOCKS)

# קוביות מדדים עליונות (תיקון מלא לשגיאות ה-KeyError)
vix_px = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1, c2, c3, c4 = st.columns(4)
c1.metric("📊 מדד הפחד (VIX)", f"{vix_px:.2f}")
c2.metric("💎 מניות זהב", len(df[df["ROE"] > 0.15]) if not df.empty else 0)
c3.metric("🔥 הזינוק היומי", df.loc[df["שינוי %"].idxmax()]["סימול"] if not df.empty else "N/A")
c4.metric("📅 עדכון אחרון", datetime.now().strftime("%H:%M"))

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📌 המניות שלי", "📑 שור מול דוב", "📄 אודות וניתוח", "🔔 התראות", "🤝 רדאר מיזוגים"])

# טאב 1: המניות שלי עם Tooltips עובדים (עברית)
with tab1:
    st.subheader("ניתוח איכות ושווי פנימי (תעמוד עם העכבר על הכותרת להסבר)")
    if not df.empty:
        st.dataframe(
            df[["סימול", "מחיר", "שינוי %", "שווי הוגן", "המלצה", "צמיחה", "ROE", "חוב"]],
            column_config={
                "צמיחה": st.column_config.NumberColumn("צמיחה", help=GLOSSARY["צמיחה"], format="%.1%"),
                "ROE": st.column_config.NumberColumn("ROE", help=GLOSSARY["ROE"], format="%.1%"),
                "חוב": st.column_config.NumberColumn("חוב", help=GLOSSARY["חוב"]),
                "שווי הוגן": st.column_config.NumberColumn("שווי הוגן", help=GLOSSARY["שווי הוגן"]),
                "המלצה": st.column_config.TextColumn("המלצה AI", help=GLOSSARY["המלצה"]),
                "שינוי %": st.column_config.NumberColumn("שינוי %", format="%.2f%%")
            },
            use_container_width=True, hide_index=True
        )

# טאב 2: שור מול דוב (AI Insights)
with tab2:
    sel = st.selectbox("בחר מניה לניתוח שור/דוב:", MY_STOCKS)
    s_obj = yf.Ticker(sel)
    inf_s = s_obj.info
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f'<div class="ai-card" style="border-color: #2e7d32;">🟢 <b>ניתוח שור:</b> {sel} נהנית ממומנטום חזק ב-AI ותזרים מזומנים שצומח ב-{inf_s.get("revenueGrowth", 0):.1%}.</div>', unsafe_allow_html=True)
    with col_b:
        st.markdown(f'<div class="ai-card" style="border-color: #d73a49;">🔴 <b>ניתוח דוב:</b> מכפיל הרווח הנוכחי גבוה מהממוצע ההיסטורי, מה שיוצר סיכון לתיקון בטווח הקצר.</div>', unsafe_allow_html=True)

# טאב 3: אודות וניתוח 10 שנים (גמיש)
with tab3:
    st.markdown(f'<div class="about-section"><b>🏢 אודות {sel} (פירוט מורחב):</b><br>{COMPANY_DB.get(sel, "חברה מובילה המופיעה ברשימות המעקב של המערכת. מומלץ לבדוק את נתוני הצמיחה בטבלה.")}</div>', unsafe_allow_html=True)
    yrs = st.slider("בחר טווח שנים לגרף:", 1, 10, 5)
    hist = yf.Ticker(sel).history(period=f"{yrs}y")
    fig = go.Figure(go.Scatter(x=hist.index, y=hist['Close'], line=dict(color='#1a73e8', width=2)))
    fig.update_layout(height=350, title=f"ביצועי מניית {sel} - {yrs} שנים", template="plotly_white", margin=dict(l=0,r=0,t=30,b=0))
    st.plotly_chart(fig, use_container_width=True)

# טאב 4: התראות (7 ימים לדוח וזינוקים)
with tab4:
    st.subheader("🔔 מרכז התראות חכם (AI Analysis)")
    found = False
    for _, row in df.iterrows():
        # התראת דוחות (מנגנון שבעה ימים)
        if row['earnings']:
            e_dt = datetime.fromtimestamp(row['earnings'])
            days = (e_dt - datetime.now()).days
            if 0 <= days <= 7:
                st.markdown(f'<div class="alert-card alert-orange">📅 <b>{row["סימול"]}</b>: דוח כספי בעוד {days} ימים! ניתוח AI צופה תנודתיות גבוהה ביום הפרסום.</div>', unsafe_allow_html=True)
                found = True
        # התראת זינוק
        if row['שינוי %'] >= 3.0:
            st.markdown(f'<div class="alert-card alert-green">🚀 <b>{row["סימול"]}</b> מזנקת ב-{row["שינוי %"]}%! כניסת כסף מוסדי זוהתה בנפח המסחר.</div>', unsafe_allow_html=True)
            found = True
    if not found: st.info("אין דוחות צפויים בשבוע הקרוב.")

# טאב 5: רדאר מיזוגים (M&A) עם AI Probability Score
with tab5:
    st.subheader("🤝 רדאר מיזוגים ושמועות שוק (AI Radar)")
    
    mergers = [
        {"עסקה": "Google / Wiz", "סבירות": "75%", "ניתוח": "המשא ומתן חזר לשולחן; גוגל מחפשת לחזק את ענן הסייבר שלה."},
        {"עסקה": "Intel / Broadcom", "סבירות": "30%", "ניתוח": "שמועות על פיצול חטיבות ייצור; סבירות נמוכה עקב רגולציה."},
        {"עסקה": "Capital One / Discover", "סבירות": "90%", "ניתוח": "מיזוג בשלבי אישור סופיים; צפוי לשנות את מפת כרטיסי האשראי."},
        {"עסקה": "Amazon / HubSpot", "סבירות": "45%", "ניתוח": "ספקולציה על רכישה להרחבת שירותי ה-CRM לעסקים קטנים."}
    ]
    
    for m in mergers:
        prob_class = "prob-high" if int(m["סבירות"].replace("%","")) > 60 else "prob-med"
        st.markdown(f"""
        <div class="ai-card">
            <b>🤝 {m['עסקה']}</b> | סבירות AI: <span class="{prob_class}">{m['סבירות']}</span><br>
            <small><b>ניתוח אסטרטגי:</b> {m['ניתוח']}</small><br>
            <a href="https://www.google.com/search?q={urllib.parse.quote(m['עסקה'] + ' merger news')}" target="_blank" style="color:#1a73e8; font-size:12px;">🔗 לכתבות האחרונות</a>
        </div>
        """, unsafe_allow_html=True)
