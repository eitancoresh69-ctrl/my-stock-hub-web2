import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import urllib.parse

# --- 1. הגדרות דף ועיצוב Elite (צמצום רווחים קיצוני ו-RTL) ---
st.set_page_config(page_title="Investment Hub Elite 2026", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    .block-container { padding-top: 0.5rem !important; padding-bottom: 0rem !important; }
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th { padding: 2px 5px !important; font-size: 13px !important; }
    .ai-card { background: white; padding: 10px; border-radius: 10px; border-right: 5px solid #1a73e8; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 8px; }
    .bull { background-color: #e8f5e9; border-color: #2e7d32; color: #1b5e20; padding: 10px; border-radius: 8px; border-right: 5px solid; }
    .bear { background-color: #ffeef0; border-color: #d73a49; color: #b71c1c; padding: 10px; border-radius: 8px; border-right: 5px solid; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילונים (אודות, הסברים וסימולציה) ---
GLOSSARY = {
    "צמיחה": "צמיחה בהכנסות מעל 10% (קריטריון 1 מה-PDF).",
    "ROE": "תשואה על ההון מעל 15% (קריטריון 4 מה-PDF).",
    "שווי הוגן": "הערכת DCF - המחיר שהמניה שווה באמת.",
    "ציון": "שקלול 6 הקריטריונים מהמדריך שלך."
}

ABOUT_DB = {
    "MSFT": "ענקית התוכנה והענן. מובילה ב-AI דרך OpenAI. מניית עוגן עם תזרים חזק.",
    "NVDA": "הלב של מהפכת ה-AI. שבבי ה-GPU שלה הם הסטנדרט היחיד בשוק. צמיחה אדירה.",
    "PLTR": "מערכות AI לממשלות ועסקים. עוזרת להפוך דאטה להחלטות מבצעיות.",
    "ENLT.TA": "אנרגיה ירוקה מישראל. בונה חוות רוח ושמש בעולם. קריטית לצורך בחשמל ל-AI."
}

# --- 3. לוגיקה פיננסית חכמה ---

def get_currency_symbol(ticker):
    return "אג'" if ".TA" in ticker else "$"

def evaluate_stock_pdf(info):
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

# --- 4. טעינת נתונים ---
MY_STOCKS_LIST = ["MSFT", "AAPL", "NVDA", "TSLA", "PLTR", "ENLT.TA", "POLI.TA", "LUMI.TA"]
SCAN_LIST = ["AMZN", "AVGO", "META", "GOOGL", "LLY", "TSM", "COST", "V", "MA", "ADBE"]

@st.cache_data(ttl=3600)
def fetch_all_data(tickers):
    rows = []
    for t in tickers:
        try:
            s = yf.Ticker(t)
            inf = s.info
            h = s.history(period="2d")
            px = h['Close'].iloc[-1]
            chg = ((px / h['Close'].iloc[-2]) - 1) * 100
            score = evaluate_stock_pdf(inf)
            
            # חישוב שווי הוגן בסיסי
            fcf = inf.get('freeCashflow', 0) or 0
            shares = inf.get('sharesOutstanding', 1)
            fv = (fcf * 15) / shares if fcf > 0 else None
            
            rows.append({
                "סימול": t, "מחיר_נומינלי": px, "שינוי %": round(chg, 2),
                "ציון איכות": score, "צמיחה %": inf.get('revenueGrowth', 0),
                "ROE %": inf.get('returnOnEquity', 0), "שווי הוגן": fv,
                "earnings": inf.get('nextEarningsDate'), "info": inf,
                "זהב": "🏆" if score >= 5 else ""
            })
        except: continue
    return pd.DataFrame(rows)

df_all = fetch_all_data(list(set(MY_STOCKS_LIST + SCAN_LIST)))

# --- 5. ממשק המשתמש ---
st.title("Investment Hub Elite 2026 🚀")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📌 המניות שלי (P/L)", "🔍 סורק מניות זהב", "📄 דוח ואודות (10 שנים)", "🔔 התראות חכמות", "🤝 רדאר מיזוגים"])

# טאב 1: המניות שלי עם עריכת מחיר קנייה ורווח/הפסד
with tab1:
    st.subheader("ניהול תיק אישי - עדכן מחירי קנייה לחישוב רווח")
    
    # יצירת טבלה לעריכה
    if 'portfolio' not in st.session_state:
        # הוספה אוטומטית של מניות זהב מהסורק לתיק
        gold_stocks = df_all[(df_all['ציון איכות'] >= 5) & (df_all['סימול'].isin(SCAN_LIST))]['סימול'].tolist()
        initial_list = list(set(MY_STOCKS_LIST + gold_stocks))
        st.session_state.portfolio = pd.DataFrame([{"סימול": t, "מחיר קניה": 0.0, "כמות": 0} for t in initial_list])

    edited_df = st.data_editor(st.session_state.portfolio, num_rows="dynamic")
    st.session_state.portfolio = edited_df

    # חיבור נתונים וחישוב P/L
    if not edited_df.empty:
        merged = pd.merge(edited_df, df_all[['סימול', 'מחיר_נומינלי', 'שינוי %', 'ציון איכות', 'זהב']], on="סימול")
        merged['רווח/הפסד'] = (merged['מחיר_נומינלי'] - merged['מחיר קניה']) * merged['כמות']
        merged['תשואה %'] = ((merged['מחיר_נומינלי'] / merged['מחיר קניה']) - 1) * 100
        merged['מחיר'] = merged.apply(lambda r: f"{get_currency_symbol(r['סימול'])}{r['מחיר_נומינלי']:,.2f}", axis=1)
        
        st.dataframe(
            merged[["סימול", "מחיר", "שינוי %", "רווח/הפסד", "תשואה %", "ציון איכות", "זהב"]],
            column_config={
                "תשואה %": st.column_config.NumberColumn("תשואה", format="%.1f%%"),
                "רווח/הפסד": st.column_config.NumberColumn("רווח/הפסד", format="%.2f"),
                "ציון איכות": st.column_config.NumberColumn("⭐ ציון", help=GLOSSARY["ציון"])
            },
            use_container_width=True, hide_index=True
        )

# טאב 2: סורק מניות חכמות
with tab2:
    st.subheader("🔍 סריקה לפי 6 קריטריונים מה-PDF")
    scan_df = df_all[df_all['סימול'].isin(SCAN_LIST)].sort_values(by="ציון איכות", ascending=False)
    st.dataframe(
        scan_df[["סימול", "מחיר_נומינלי", "ציון איכות", "צמיחה %", "ROE %", "זהב"]],
        column_config={
            "מחיר_נומינלי": st.column_config.NumberColumn("מחיר"),
            "צמיחה %": st.column_config.NumberColumn("צמיחה", format="%.1%"),
            "ROE %": st.column_config.NumberColumn("ROE", format="%.1%")
        },
        use_container_width=True, hide_index=True
    )

# טאב 3: דוח, אודות ושור/דוב
with tab3:
    sel = st.selectbox("בחר מניה לניתוח עמוק:", df_all['סימול'].unique())
    row = df_all[df_all['סימול'] == sel].iloc[0]
    
    st.markdown(f'<div class="ai-card"><b>🏢 אודות {sel} (מורחב):</b><br>{ABOUT_DB.get(sel, "חברה מובילה המופיעה ברשימת המעקב.")}</div>', unsafe_allow_html=True)
    
    c_bull, c_bear = st.columns(2)
    with c_bull:
        st.markdown(f'<div class="bull"><b>🐂 תרחיש השור (Bull):</b> צמיחה של {row["צמיחה %"]:.1%} והובלה בסקטור ה-AI.</div>', unsafe_allow_html=True)
    with c_bear:
        st.markdown(f'<div class="bear"><b>🐻 תרחיש הדוב (Bear):</b> רמת חוב או מכפיל רווח שעלולים להוביל לתיקון.</div>', unsafe_allow_html=True)

    yrs = st.slider("טווח שנים לגרף (עד 10 שנים):", 1, 10, 5)
    hist = yf.Ticker(sel).history(period=f"{yrs}y")
    fig = go.Figure(go.Scatter(x=hist.index, y=hist['Close'], line=dict(color='#1a73e8', width=2), fill='tozeroy'))
    fig.update_layout(title=f"ביצועי מניית {sel} ל-{yrs} שנים", height=350, template="plotly_white", margin=dict(l=0,r=0,t=30,b=0))
    st.plotly_chart(fig, use_container_width=True)

# טאב 4: התראות חכמות AI (7 ימים)
with tab4:
    st.subheader("🔔 מודיעין שוק והתראות")
    found = False
    for _, r in df_all.iterrows():
        if r['earnings']:
            e_dt = datetime.fromtimestamp(r['earnings'])
            days = (e_dt - datetime.now()).days
            if 0 <= days <= 7:
                st.warning(f"📅 **{r['סימול']}** מפרסמת דוח בעוד {days} ימים! (ניתוח AI צופה תנודתיות גבוהה)")
                found = True
        if abs(r['שינוי %']) >= 3.0:
            st.info(f"🚀 **{r['סימול']}** בתנועה חריגה של {r['שינוי %']}% היום. כדאי לבדוק חדשות!")
            found = True
    if not found: st.write("אין התראות דחופות ל-7 הימים הקרובים.")

# טאב 5: רדאר מיזוגים עם לינקים
with tab5:
    mergers = [
        {"חברה": "Wiz / Google", "פרטים": "שמועות רכישה ב-23 מיליארד דולר.", "לינק": "https://www.google.com/search?q=Wiz+Google+merger"},
        {"חברה": "Intel / Qualcomm", "פרטים": "ספקולציות על רכישת חטיבת השבבים.", "לינק": "https://www.google.com/search?q=Intel+Qualcomm+rumors"}
    ]
    for m in mergers:
        st.markdown(f"""<div class="ai-card">
            <b>🤝 {m['חברה']}</b> | {m['פרטים']}<br>
            <a href="{m['לינק']}" target="_blank" style="color:#1a73e8; font-weight:bold;">🔗 קרא עוד בחדשות</a>
        </div>""", unsafe_allow_html=True)
