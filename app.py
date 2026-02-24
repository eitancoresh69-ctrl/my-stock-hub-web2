import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. הגדרות דף ועיצוב CSS (RTL מלא, ללא סרגל צד) ---
st.set_page_config(page_title="Investment Hub PRO 2026", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    .block-container { padding-top: 1rem !important; }
    
    /* קוביות מדדים */
    .metric-card {
        background: white; padding: 15px; border-radius: 12px;
        border-right: 5px solid #1a73e8; box-shadow: 0 4px 6px rgba(0,0,0,0.07);
        text-align: center; margin-bottom: 15px;
    }
    .m-val { font-size: 24px; font-weight: bold; color: #1a73e8; }
    .m-lbl { font-size: 14px; color: #5f6368; }

    /* תיבות מידע ואודות */
    .about-box { background-color: #f1f8ff; padding: 15px; border-radius: 10px; border-right: 6px solid #1a73e8; line-height: 1.6; margin-bottom: 15px; }
    .alert-card { padding: 12px; border-radius: 8px; margin-bottom: 8px; border-right: 5px solid; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .alert-green { background-color: #e8f5e9; border-color: #2e7d32; color: #1b5e20; }
    .alert-orange { background-color: #fff3e0; border-color: #ef6c00; color: #e65100; }
    
    /* צמצום טבלאות */
    [data-testid="stTable"] td, [data-testid="stTable"] th { padding: 5px 10px !important; font-size: 14px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילון מונחים ואודות מפורט ---
GLOSSARY = {
    "צמיחה": "אחוז השינוי בהכנסות בשנה האחרונה. מעל 10% נחשב לצמיחה טובה.",
    "ROE": "Return on Equity: כמה רווח החברה מייצרת מההון העצמי. מעל 15% זה מצוין.",
    "חוב": "Debt to Equity: בודק את המינוף. מתחת ל-100 נחשב ליציב ובטוח.",
    "שוליים": "שולי רווח נקי: כמה נשאר לחברה בכיס מכל דולר של הכנסה."
}

ABOUT_DETAILS = {
    "MSFT": "ענקית התוכנה והענן. מובילה ב-AI דרך השקעה ב-OpenAI ומטמיעה בינה מלאכותית בכל מוצריה. מניית עוגן יציבה מאוד.",
    "NVDA": "הלב של מהפכת ה-AI. מייצרת את השבבים שבלעדיהם אי אפשר לאמן מודלים. צמיחה פנומנלית ויתרון טכנולוגי אדיר.",
    "AAPL": "חברת המכשירים והשירותים המצליחה בעולם. בונה אקו-סיסטם סגור שמייצר נאמנות לקוחות ורווחים חוזרים גבוהים.",
    "TSLA": "מובילת הרכבים החשמליים, אנרגיה ורובוטיקה. מהמרת על עתיד של נהיגה אוטונומית מלאה.",
    "ENLT.TA": "חלוצת האנרגיה המתחדשת מישראל. פועלת בארה\"ב ואירופה. נהנית מהביקוש לחשמל נקי עבור חוות שרתים.",
    "PLTR": "מתמחה בניתוח דאטה מורכב לממשלים וחברות ענק. הופכת למובילה ב-AI ארגוני."
}

# --- 3. פונקציות שליפה חסינות שגיאות ---
MY_STOCKS = ["MSFT", "AAPL", "NVDA", "TSLA", "PLTR", "MSTR", "GOOGL", "META", "ENLT.TA", "POLI.TA", "LUMI.TA"]
SCAN_CANDIDATES = ["AMZN", "AVGO", "COST", "MA", "V", "LLY", "TSM", "ADBE", "NFLX", "ORCL", "ASML", "SBUX"]

@st.cache_data(ttl=3600)
def fetch_robust_data(tickers):
    rows = []
    for t in tickers:
        try:
            stock = yf.Ticker(t)
            hist = stock.history(period="5d")
            if hist.empty: continue
            info = stock.info
            curr, prev = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
            
            # שליפה בטוחה של נתוני איכות
            rev_g = info.get("revenueGrowth", 0) or 0
            margin = info.get("profitMargins", 0) or 0
            roe = info.get("returnOnEquity", 0) or 0
            debt = info.get("debtToEquity", 150)
            
            score = sum([rev_g >= 0.1, margin >= 0.12, roe >= 0.15, debt < 100])
            
            rows.append({
                "סימול": t, "מחיר": round(curr, 2), "שינוי %": round(((curr/prev)-1)*100, 2),
                "צמיחה": rev_g, "ROE": roe, "חוב": debt, "שוליים": margin,
                "ציון (4)": score, "זהב": "🏆" if score >= 3 else "",
                "earnings_raw": info.get('nextEarningsDate')
            })
        except: continue
    return pd.DataFrame(rows)

# --- 4. תצוגת האתר ---
st.title("Investment Hub PRO 2026 🚀")

all_tickers = list(set(MY_STOCKS + SCAN_CANDIDATES))
df_data = fetch_robust_data(all_tickers)

# קוביות מדדים עליונות (תיקון השגיאה מהצילום)
vix_px = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1, c2, c3, c4 = st.columns(4)
c1.metric("📊 מדד הפחד (VIX)", f"{vix_px:.2f}")
c2.metric("🏆 מניות זהב", len(df_data[df_data["זהב"] == "🏆"]))
c3.metric("🔥 הזינוק היומי", df_data.loc[df_data["שינוי %"].idxmax()]["סימול"] if not df_data.empty else "N/A")
c4.metric("📅 עדכון אחרון", datetime.now().strftime("%H:%M"))

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📌 המניות שלי", "🔍 סורק איכות", "📄 אודות וניתוח עשור", "🔔 התראות חכמות", "🤝 רדאר מיזוגים"])

# טאב 1: המניות שלי (החזרתי את הטבלה!)
with tab1:
    st.subheader("החזקות ומעקב אישי")
    my_df = df_data[df_data['סימול'].isin(MY_STOCKS)]
    st.table(my_df[["סימול", "מחיר", "שינוי %", "צמיחה", "ROE", "חוב", "זהב"]])

# טאב 2: סורק איכות
with tab2:
    st.subheader("חיפוש הזדמנויות בשוק")
    scan_df = df_data[df_data['סימול'].isin(SCAN_CANDIDATES)].sort_values(by="ציון (4)", ascending=False)
    st.table(scan_df[["סימול", "מחיר", "שינוי %", "ציון (4)", "זהב"]])

# טאב 3: אודות וניתוח 10 שנים (גמיש)
with tab3:
    sel = st.selectbox("בחר מניה לניתוח עומק:", all_tickers)
    st.markdown(f'<div class="about-box"><b>🏢 אודות {sel} (למשקיע המתחיל):</b><br>{ABOUT_DETAILS.get(sel, "חברה מובילה בסקטור שלה, נסחרת במדדים המרכזים.")}</div>', unsafe_allow_html=True)
    
    st.divider()
    yrs = st.slider("בחר טווח שנים לניתוח היסטורי:", 1, 10, 5)
    hist_10 = yf.Ticker(sel).history(period=f"{yrs}y")
    if not hist_10.empty:
        fig = go.Figure(go.Scatter(x=hist_10.index, y=hist_10['Close'], line=dict(color='#1a73e8', width=2)))
        fig.update_layout(height=350, title=f"ביצועי מניית {sel} - {yrs} שנים אחרונות", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

# טאב 4: התראות חכמות (מתוקן!)
with tab4:
    st.subheader("🔔 מרכז התראות בזמן אמת")
    
    # התראת דוחות - 7 ימים מראש
    found_e = False
    for _, row in df_data.iterrows():
        if row['earnings_raw']:
            e_dt = datetime.fromtimestamp(row['earnings_raw'])
            days_to = (e_dt - datetime.now()).days
            if 0 <= days_to <= 7:
                st.markdown(f'<div class="alert-card alert-orange">📅 <b>{row["סימול"]}</b>: דוח קרוב ב-{e_dt.strftime("%d/%m")} (בעוד {days_to} ימים)</div>', unsafe_allow_html=True)
                found_e = True
    
    # התראת זינוקים
    for _, row in df_data.iterrows():
        if row['שינוי %'] >= 3.0:
            st.markdown(f'<div class="alert-card alert-green">🚀 <b>{row["סימול"]}</b> בזינוק של {row["שינוי %"]}% היום!</div>', unsafe_allow_html=True)
            found_e = True
            
    if not found_e: st.info("אין התראות מיוחדות כרגע.")

# טאב 5: רדאר מיזוגים
with tab5:
    st.subheader("🤝 רדאר מיזוגים (M&A) ושמועות")
    mergers = [
        {"חברה": "Wiz / Google", "סטטוס": "שמועות רכישה", "פרטים": "דיווחים על חידוש המגעים לרכישה הגדולה ביותר של גוגל."},
        {"חברה": "Intel", "סטטוס": "ספקולציה", "פרטים": "שמועות על פיצול חטיבות הייצור והעיצוב להגברת ערך."},
        {"חברה": "Discover / Capital One", "סטטוס": "מיזוג רשמי", "פרטים": "ממתין לאישורים רגולטוריים סופיים."},
    ]
    st.table(pd.DataFrame(mergers))
