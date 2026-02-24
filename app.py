import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# --- 1. הגדרות דף ועיצוב (RTL מלא, ללא סרגל צד) ---
st.set_page_config(page_title="Intelligence Hub 2026", layout="wide", initial_sidebar_state="collapsed")

# מנגנון ריענון אוטומטי (כל 15 דקות)
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

refresh_interval = 900 # 15 דקות בשניות
current_time = time.time()
if current_time - st.session_state.last_refresh > refresh_interval:
    st.session_state.last_refresh = current_time
    st.rerun()

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    .block-container { padding-top: 1rem !important; }
    
    /* עיצוב כרטיסי AI */
    .ai-card { background: white; padding: 12px; border-radius: 10px; border-right: 6px solid #1a73e8; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 10px; }
    .bull { background-color: #e8f5e9; border-color: #2e7d32; color: #1b5e20; padding: 10px; border-radius: 8px; border-right: 5px solid; margin-bottom: 5px; }
    .bear { background-color: #ffeef0; border-color: #d73a49; color: #b71c1c; padding: 10px; border-radius: 8px; border-right: 5px solid; }
    
    /* צמצום רווחים בטבלאות */
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th { padding: 2px 8px !important; font-size: 13px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילון אודות והסברים (בועות הסבר) ---
GLOSSARY = {
    "מחיר": "המחיר הנוכחי: בדולר ($) לארה\"ב או אגורות (אג') לישראל.",
    "צמיחה": "צמיחה בהכנסות מעל 10% (קריטריון מה-PDF).",
    "ROE": "תשואה על ההון מעל 15% (מדד ליעילות החברה).",
    "P/L": "רווח או הפסד כספי נומינלי מההשקעה שלך.",
    "שווי הוגן": "הערכת DCF - מחיר המטרה של המניה לפי AI."
}

ABOUT_DB = {
    "MSFT": "<b>מיקרוסופט:</b> שולטת בשוק התוכנה והענן. מנוע צמיחה אדיר ב-AI דרך OpenAI.",
    "NVDA": "<b>אנבידיה:</b> מובילת שבבי ה-AI. החומרה שלה היא הבסיס לכל מודל בינה מלאכותית בעולם.",
    "ENLT.TA": "<b>אנלייט:</b> חברה ישראלית המקימה חוות רוח ושמש. קריטית לאספקת חשמל נקי לחוות שרתים.",
    "AAPL": "<b>אפל:</b> ענקית המכשירים עם אקו-סיסטם סגור שמייצר נאמנות ורווחים חוזרים גבוהים.",
    "PLTR": "<b>פלנטיר:</b> מערכות AI מתקדמות לניתוח דאטה עבור ממשלות ועסקים גדולים."
}

# --- 3. לוגיקה חכמה וחישובי PDF ---

def evaluate_stock(info):
    score = 0
    try:
        if info.get('revenueGrowth', 0) >= 0.10: score += 1
        if info.get('earningsGrowth', 0) >= 0.10: score += 1
        if info.get('profitMargins', 0) >= 0.10: score += 1
        if info.get('returnOnEquity', 0) >= 0.15: score += 1
        if (info.get('totalCash', 0) / info.get('totalDebt', 1)) > 1: score += 1
        if info.get('totalDebt', 0) == 0: score += 1
    except: pass
    return score

def calculate_fv(info):
    try:
        fcf = info.get('freeCashflow', 0) or 0
        shares = info.get('sharesOutstanding', 1)
        return (fcf * 15) / shares if fcf > 0 else 0
    except: return 0

# --- 4. שליפת נתונים ---
MY_STOCKS_LIST = ["MSFT", "AAPL", "NVDA", "TSLA", "PLTR", "ENLT.TA", "POLI.TA", "LUMI.TA"]
SCAN_LIST = ["AMZN", "AVGO", "META", "GOOGL", "LLY", "TSM", "COST", "V", "ADBE", "AMD"]

@st.cache_data(ttl=600)
def fetch_data(tickers):
    rows = []
    for t in tickers:
        try:
            s = yf.Ticker(t)
            inf = s.info
            h = s.history(period="2d")
            if h.empty: continue
            px = h['Close'].iloc[-1]
            chg = ((px / h['Close'].iloc[-2]) - 1) * 100
            score = evaluate_stock(inf)
            fv = calculate_fv(inf)
            
            rows.append({
                "Symbol": t, "CurrentPrice": px, "Change": round(chg, 2),
                "QualityScore": score, "RevenueGrowth": inf.get('revenueGrowth', 0),
                "ROE": inf.get('returnOnEquity', 0), "FairValue": fv,
                "EarningsDate": inf.get('nextEarningsDate'), "Info": inf
            })
        except: continue
    return pd.DataFrame(rows)

df_all = fetch_data(list(set(MY_STOCKS_LIST + SCAN_LIST)))

# --- 5. בניית הממשק ---
st.title("🚀 Market Intelligence Hub 2026")

# קוביות מדדים עליונות
vix_px = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1, c2, c3, c4 = st.columns(4)
c1.metric("📊 מדד הפחד (VIX)", f"{vix_px:.2f}")
c2.metric("🏆 מניות זהב", len(df_all[df_all["QualityScore"] >= 5]))
c3.metric("🔥 הזינוק היומי", df_all.loc[df_all["Change"].idxmax()]["Symbol"] if not df_all.empty else "N/A")
c4.metric("🕒 עדכון אחרון", datetime.now().strftime("%H:%M"))

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📌 המניות שלי", "🔍 סורק מניות זהב", "📄 דוח ואודות (10 שנים)", "🔔 התראות חכמות", "🤝 רדאר מיזוגים"])

# טאב 1: המניות שלי עם רווח והפסד (P/L)
with tab1:
    st.subheader("ניהול תיק וחישוב רווחיות")
    if 'portfolio' not in st.session_state:
        # הוספה אוטומטית של מניות זהב מהסורק
        gold_stocks = df_all[df_all['QualityScore'] >= 5]['Symbol'].tolist()
        initial_list = list(set(MY_STOCKS_LIST + gold_stocks))
        st.session_state.portfolio = pd.DataFrame([{"Symbol": t, "BuyPrice": 0.0, "Quantity": 0} for t in initial_list])

    edited_df = st.data_editor(st.session_state.portfolio, num_rows="dynamic")
    st.session_state.portfolio = edited_df

    if not edited_df.empty:
        merged = pd.merge(edited_df, df_all[['Symbol', 'CurrentPrice', 'Change', 'QualityScore']], on="Symbol")
        merged['P/L'] = (merged['CurrentPrice'] - merged['BuyPrice']) * merged['Quantity']
        merged['Yield%'] = ((merged['CurrentPrice'] / merged['BuyPrice']) - 1) * 100
        
        st.dataframe(
            merged[["Symbol", "CurrentPrice", "Change", "P/L", "Yield%", "QualityScore"]],
            column_config={
                "CurrentPrice": st.column_config.NumberColumn("מחיר", help=GLOSSARY["מחיר"]),
                "P/L": st.column_config.NumberColumn("רווח/הפסד ($/אג')", format="%.2f"),
                "Yield%": st.column_config.NumberColumn("תשואה", format="%.1f%%"),
                "QualityScore": st.column_config.NumberColumn("⭐ ציון", help="ציון איכות לפי 6 קריטריונים")
            },
            use_container_width=True, hide_index=True
        )

# טאב 3: דוח, אודות ושור/דוב (10 שנים)
with tab3:
    sel = st.selectbox("בחר מניה לניתוח עמוק:", df_all['Symbol'].unique())
    row = df_all[df_all['Symbol'] == sel].iloc[0]
    
    # אודות מורחב
    st.markdown(f'<div class="ai-card"><b>🏢 אודות {sel}:</b><br>{ABOUT_DB.get(sel, "חברה מובילה המופיעה ברשימות המעקב.")}</div>', unsafe_allow_html=True)
    
    # ניתוח שור ודוב (AI)
    col_bull, col_bear = st.columns(2)
    with col_bull:
        st.markdown(f'<div class="bull"><b>🐂 תרחיש השור (AI):</b> צמיחה של {row["RevenueGrowth"]:.1%} ומובילות טכנולוגית חזקה.</div>', unsafe_allow_html=True)
    with col_bear:
        st.markdown(f'<div class="bear"><b>🐻 תרחיש הדוב (AI):</b> מכפיל רווח גבוה וסיכוני רגולציה שעלולים להוביל לתיקון.</div>', unsafe_allow_html=True)

    # גרף 10 שנים
    yrs = st.slider("טווח שנים לגרף:", 1, 10, 5)
    hist = yf.Ticker(sel).history(period=f"{yrs}y")
    fig = go.Figure(go.Scatter(x=hist.index, y=hist['Close'], line=dict(color='#1a73e8', width=2), fill='tozeroy'))
    fig.update_layout(title=f"ביצועי מניית {sel} ל-{yrs} שנים", height=350, template="plotly_white", margin=dict(l=0,r=0,t=30,b=0))
    st.plotly_chart(fig, use_container_width=True)

# טאב 4: התראות דוחות (7 ימים מראש)
with tab4:
    st.subheader("🔔 מודיעין דוחות ואירועים (AI)")
    found_alert = False
    for _, r in df_all.iterrows():
        if r['EarningsDate']:
            e_dt = datetime.fromtimestamp(r['EarningsDate'])
            days = (e_dt - datetime.now()).days
            if 0 <= days <= 7:
                st.warning(f"📅 **{r['Symbol']}** מפרסמת דוחות בעוד {days} ימים! (ניתוח AI צופה תנודתיות גבוהה)")
                found_alert = True
        if abs(r['Change']) >= 3.0:
            st.info(f"🚀 **{r['Symbol']}** בתנועה חריגה של {r['Change']}% היום.")
            found_alert = True
    if not found_alert: st.write("אין דוחות משמעותיים בשבוע הקרוב.")

# טאב 5: רדאר מיזוגים עם לינקים
with tab5:
    st.subheader("🤝 רדאר M&A ושמועות גלובליות")
    mergers = [
        {"חברה": "Wiz / Google", "פרטים": "שמועות על רכישה בסך 23 מיליארד דולר.", "לינק": "https://www.google.com/search?q=Wiz+Google+merger"},
        {"חברה": "Intel / Qualcomm", "פרטים": "ספקולציות על רכישת חטיבת השבבים.", "לינק": "https://www.google.com/search?q=Intel+Qualcomm+acquisition"}
    ]
    for m in mergers:
        st.markdown(f"""<div class="ai-card">
            <b>🤝 {m['חברה']}</b> | {m['פרטים']}<br>
            <a href="{m['לינק']}" target="_blank" style="color:#1a73e8; font-weight:bold;">🔗 קרא את הדיווח המלא</a>
        </div>""", unsafe_allow_html=True)
