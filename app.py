import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

# --- 1. הגדרות דף ועיצוב CSS "דחוס" (מניעת רווחים לבנים) ---
st.set_page_config(page_title="Investment Hub Elite 2026", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    
    /* ביטול רווחים לבנים ענקיים */
    .block-container { padding-top: 0.5rem !important; padding-bottom: 0rem !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 5px; }
    .stTabs [data-baseweb="tab"] { padding: 5px 10px; font-size: 14px; }
    
    /* קוביות מדדים קומפקטיות */
    .metric-card {
        background: white; padding: 10px; border-radius: 8px;
        border-right: 5px solid #1a73e8; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        text-align: center; margin-bottom: 10px;
    }
    .m-val { font-size: 20px; font-weight: bold; color: #1a73e8; }
    .m-lbl { font-size: 12px; color: #666; }

    /* אודות מורחב והתראות */
    .about-section { background-color: #f1f8ff; padding: 15px; border-radius: 10px; border-right: 8px solid #1a73e8; line-height: 1.8; font-size: 15px; }
    .alert-card { padding: 10px; border-radius: 8px; margin-bottom: 8px; border-right: 5px solid; font-size: 14px; }
    .alert-up { background-color: #e8f5e9; border-color: #2e7d32; color: #1b5e20; }
    .alert-earnings { background-color: #fff3e0; border-color: #ef6c00; color: #e65100; }
    
    /* טבלאות צפופות */
    [data-testid="stTable"] td, [data-testid="stTable"] th { padding: 4px 8px !important; font-size: 13px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילון אודות מפורט למשקיע המתחיל ---
ABOUT_DB = {
    "MSFT": "<b>מיקרוסופט:</b> חברת הטכנולוגיה המגוונת בעולם. היא מרוויחה משירותי ענן (Azure), תוכנות אופיס, וגיימינג (Xbox). היא נחשבת למובילה בבינה מלאכותית בזכות השקעה ב-ChatGPT. למתחילים: מניה יציבה עם צמיחה עקבית וביטחון גבוה.",
    "NVDA": "<b>אנבידיה:</b> הלב של מהפכת ה-AI. היא מייצרת שבבים שמאפשרים למחשבים 'לחשוב'. כל חברת ענק בעולם צריכה את השבבים שלה. למתחילים: מניה עם תנודות חדות (וולטיליות) אך צמיחה מהירה מאוד.",
    "AAPL": "<b>אפל:</b> ענקית המכשירים. הכוח שלה הוא ב'אקו-סיסטם' - מי שקונה אייפון בדרך כלל יקנה גם שירותי ענן ואפליקציות של אפל. למתחילים: נחשבת למניה בטוחה עם קופת מזומנים ענקית שמגנה עליה במשברים.",
    "TSLA": "<b>טסלה:</b> לא רק מכוניות, אלא חברת רובוטיקה ואנרגיה. היא מפתחת בינה מלאכותית לנהיגה עצמית. למתחילים: השקעה בטכנולוגיית העתיד, אך תלויה מאוד בחדשנות ובאילון מאסק.",
    "ENLT.TA": "<b>אנלייט:</b> חברה ישראלית שבונה פרויקטים של אנרגיה ירוקה (רוח ושמש) בישראל ובארה\"ב. למתחילים: דרך טובה להשקיע בעתיד כדור הארץ ובצורך הגובר בחשמל נקי.",
    "PLTR": "<b>פלנטיר:</b> מתמחה בניתוח נתונים מורכבים עבור צבאות וממשלות. המערכת שלהם מאפשרת לקבל החלטות מבוססות AI בזמן אמת. למתחילים: חברת תוכנה אסטרטגית שצומחת בשוק המסחרי."
}

# --- 3. פונקציות שליפה חכמות ---
MY_STOCKS = ["MSFT", "AAPL", "NVDA", "TSLA", "PLTR", "MSTR", "GOOGL", "META", "ENLT.TA", "POLI.TA", "LUMI.TA"]
SCAN_LIST = ["AMZN", "AVGO", "COST", "MA", "V", "LLY", "TSM", "ADBE", "NFLX", "ORCL", "ASML", "SBUX"]

@st.cache_data(ttl=3600)
def fetch_elite_data(tickers):
    rows = []
    for t in tickers:
        try:
            stock = yf.Ticker(t)
            hist = stock.history(period="5d")
            if hist.empty: continue
            info = stock.info
            curr, prev = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
            
            # קריטריונים מה-PDF (ציון איכות 0-5)
            score = sum([
                info.get('revenueGrowth', 0) > 0.1,
                info.get('profitMargins', 0) > 0.12,
                info.get('returnOnEquity', 0) > 0.15,
                info.get('debtToEquity', 100) < 100,
                info.get('earningsGrowth', 0) > 0.1
            ])
            
            rows.append({
                "סימול": t, "מחיר": round(curr, 2), "שינוי %": round(((curr/prev)-1)*100, 2),
                "צמיחה": f"{info.get('revenueGrowth', 0):.1%}", "ROE": f"{info.get('returnOnEquity', 0):.1%}",
                "חוב": info.get('debtToEquity', 'N/A'), "ציון": ("⭐" * score), "score_num": score,
                "earnings_raw": info.get('nextEarningsDate')
            })
        except: continue
    return pd.DataFrame(rows)

# --- 4. בניית הממשק ---
st.title("Investment Hub Elite 2026 🚀")

df_data = fetch_elite_data(list(set(MY_STOCKS + SCAN_LIST)))

# קוביות מדדים עליונות
vix_px = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="metric-card"><div class="m-lbl">📊 מדד הפחד (VIX)</div><div class="m-val">{vix_px:.2f}</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-card"><div class="m-lbl">💎 מניות זהב (4+)</div><div class="m-val">{len(df_data[df_data["score_num"] >= 4])}</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="metric-card"><div class="m-lbl">🚀 זינוק יומי</div><div class="m-val" style="color:green;">{df_data.loc[df_data["שינוי %"].idxmax()]["סימול"]}</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="metric-card"><div class="m-lbl">🕒 עדכון</div><div class="m-val" style="font-size:16px;">{datetime.now().strftime("%H:%M")}</div></div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📌 המניות שלי", "🔍 סורק איכות", "📄 אודות וניתוח עשור", "🔔 התראות חכמות", "🤝 רדאר מיזוגים"])

with tab1:
    st.table(df_data[df_data['סימול'].isin(MY_STOCKS)].drop(columns=["score_num", "earnings_raw"]))

with tab2:
    st.table(df_data[df_data['סימול'].isin(SCAN_LIST)].sort_values(by="score_num", ascending=False).drop(columns=["score_num", "earnings_raw"]))

with tab3:
    sel = st.selectbox("בחר מניה לניתוח עומק:", MY_STOCKS + SCAN_LIST)
    
    # אודות מורחב למשקיע מתחיל
    st.markdown(f'<div class="about-section"><b>🏢 אודות החברה (פירוט מורחב):</b><br>{ABOUT_DB.get(sel, "חברה מובילה המופיעה ברשימות המעקב של המערכת. מומלץ לבדוק את נתוני הצמיחה והרווחיות בטבלאות האיכות.")}</div>', unsafe_allow_html=True)
    
    # ניתוח 10 שנים גמיש
    st.divider()
    years = st.slider("בחר טווח שנים לגרף ההיסטורי:", 1, 10, 5)
    hist_10 = yf.Ticker(sel).history(period=f"{years}y")
    if not hist_10.empty:
        fig = go.Figure(go.Scatter(x=hist_10.index, y=hist_10['Close'], line=dict(color='#1a73e8', width=2)))
        fig.update_layout(height=350, title=f"ביצועי המניה ל-{years} שנים", template="plotly_white", margin=dict(l=0,r=0,t=30,b=0))
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("📢 לוח התראות חכם")
    
    # 1. התראת דוחות (7 ימים מראש)
    found_e = False
    for _, row in df_data.iterrows():
        if row['earnings_raw']:
            e_dt = datetime.fromtimestamp(row['earnings_raw'])
            days_to = (e_dt - datetime.now()).days
            if 0 <= days_to <= 7:
                st.markdown(f'<div class="alert-card alert-earnings">📅 <b>{row["סימול"]}</b>: מפרסמת דוחות ב-{e_dt.strftime("%d/%m/%Y")} (בעוד {days_to} ימים)</div>', unsafe_allow_html=True)
                found_e = True
    
    # 2. התראת מניות עולות (מעל 3% היום)
    for _, row in df_data.iterrows():
        if row['שינוי %'] >= 3.0:
            st.markdown(f'<div class="alert-card alert-up">🚀 <b>{row["סימול"]}</b> בזינוק של {row["שינוי %"]}% היום!</div>', unsafe_allow_html=True)
            found_e = True
    
    if not found_e: st.info("אין התראות מיוחדות כרגע.")

with tab5:
    st.subheader("🤝 רדאר מיזוגים ושמועות (M&A)")
    mergers = [
        {"חברה": "Wiz / Google", "סטטוס": "שמועות רכישה", "פרטים": "דיווחים על חידוש המשא ומתן לרכישת ענק."},
        {"חברה": "Intel", "סטטוס": "ספקולציה", "פרטים": "אנליסטים צופים פיצול של חטיבת הייצור מהעיצוב."},
        {"חברה": "Discover", "סטטוס": "מיזוג רשמי", "פרטים": "ממתין לאישורים רגולטוריים אחרונים."}
    ]
    st.table(pd.DataFrame(mergers))
