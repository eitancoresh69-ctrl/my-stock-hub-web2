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
    
    /* צמצום רווחים במיכל הראשי */
    .block-container { padding-top: 0.5rem !important; padding-bottom: 0rem !important; padding-right: 1rem !important; padding-left: 1rem !important; }
    
    /* צמצום רווחים בתוך הטבלה */
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th { padding: 2px 5px !important; font-size: 13px !important; }
    
    /* עיצוב כרטיסי AI והתראות */
    .ai-card { background: white; padding: 10px; border-radius: 8px; border-right: 5px solid #1a73e8; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 8px; }
    .alert-banner { padding: 8px; border-radius: 6px; margin-bottom: 5px; border-right: 4px solid; font-size: 13px; }
    .alert-green { background-color: #e8f5e9; border-color: #2e7d32; color: #1b5e20; }
    .alert-orange { background-color: #fff3e0; border-color: #ef6c00; color: #e65100; }
    
    /* הקטנת רווחים בין אלמנטים */
    .stTabs [data-baseweb="tab"] { padding-top: 5px; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילון מונחים (בועות הסבר בעברית - Tooltips) ---
GLOSSARY = {
    "מחיר": "המחיר הנוכחי: במניות ארה\"ב בדולר ($), בישראל באגורות (אג').",
    "צמיחת מכירות": "קריטריון 1: צמיחה בהכנסות מעל 10% מעידה על עסק מתרחב.",
    "צמיחת רווחים": "קריטריון 2: צמיחה ברווח הנקי מעל 10% מראה יעילות עסקית.",
    "שולי רווח": "קריטריון 3: אחוז הרווח שנשאר מההכנסות. יעד: מעל 10%.",
    "ROE": "קריטריון 4: תשואה על ההון מעל 15% מראה ניצול יעיל של כספי המשקיעים.",
    "יחס מזומן/חוב": "קריטריון 5: האם יש לחברה יותר מזומן מחוב? (Cash > Debt).",
    "חוב אפס": "קריטריון 6: חברות ללא חוב בכלל מקבלות נקודת בונוס על יציבות.",
    "ציון איכות": "שקלול 6 הקריטריונים מה-PDF. ציון 5-6 נחשב ל'זהב'.",
    "המלצה": "ניתוח AI המבוסס על הפער בין המחיר לשווי ההוגן (DCF)."
}

# --- 3. לוגיקה פיננסית (6 הקריטריונים מה-PDF) ---

def format_price(ticker, price):
    if ".TA" in ticker: return f"{price:,.0f} אג'"
    return f"${price:,.2f}"

def evaluate_by_pdf(info):
    """ חישוב ציון לפי 6 הקריטריונים מהמדריך """
    score = 0
    rev_g = info.get('revenueGrowth', 0) or 0
    earn_g = info.get('earningsGrowth', 0) or 0
    margin = info.get('profitMargins', 0) or 0
    roe = info.get('returnOnEquity', 0) or 0
    cash = info.get('totalCash', 0) or 0
    debt = info.get('totalDebt', 0) or 0
    
    if rev_g >= 0.10: score += 1      # 1. צמיחת מכירות
    if earn_g >= 0.10: score += 1     # 2. צמיחת רווחים
    if margin >= 0.10: score += 1     # 3. שולי רווח
    if roe >= 0.15: score += 1        # 4. תשואה על ההון
    if cash > debt: score += 1        # 5. מזומן מול חוב
    if debt == 0: score += 1          # 6. חוב אפס (בונוס יציבות)
    
    # חישוב שווי הוגן (DCF מופשט)
    shares = info.get('sharesOutstanding', 1)
    fcf = info.get('freeCashflow', 0) or 0
    fv = (fcf * 15) / shares if fcf > 0 else None
    
    return score, fv, rev_g, earn_g, margin, roe

# --- 4. שליפת נתונים ועיבוד ---
MY_STOCKS_BASE = ["MSFT", "AAPL", "NVDA", "TSLA", "PLTR", "ENLT.TA", "POLI.TA", "LUMI.TA"]
SCAN_LIST = ["AMZN", "AVGO", "META", "GOOGL", "LLY", "TSM", "COST", "V", "MA", "ADBE", "NFLX"]

@st.cache_data(ttl=3600)
def fetch_hub_data(base_list, scan_list):
    rows = []
    all_tickers = list(set(base_list + scan_list))
    for t in all_tickers:
        try:
            s = yf.Ticker(t)
            inf = s.info
            h = s.history(period="2d")
            if h.empty: continue
            px = h['Close'].iloc[-1]
            chg = ((px / h['Close'].iloc[-2]) - 1) * 100
            
            score, fv, rev_g, earn_g, margin, roe = evaluate_by_pdf(inf)
            
            # המלצת AI
            gap = (fv - px) / px if fv else 0
            rec = "קנייה חזקה 💎" if gap > 0.15 else "קנייה 📈" if gap > 0.05 else "מכירה 🔴" if gap < -0.10 else "החזק ⚖️"
            
            rows.append({
                "סימול": t, "מחיר_נקי": px, "מחיר": format_price(t, px), "שינוי %": round(chg, 2),
                "ציון איכות": score, "המלצה": rec, "צמיחה %": rev_g, "רווח %": earn_g,
                "שוליים %": margin, "ROE %": roe, "שווי הוגן": fv, "earnings": inf.get('nextEarningsDate')
            })
        except: continue
    return pd.DataFrame(rows)

df_all = fetch_hub_data(MY_STOCKS_BASE, SCAN_LIST)

# --- 5. ממשק המשתמש ---
st.title("Investment Hub Elite 2026 🚀")

# קוביות מדדים עליונות (VIX + מניות זהב)
try:
    vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📊 מדד הפחד (VIX)", f"{vix:.2f}")
    c2.metric("🏆 מניות זהב (5-6)", len(df_all[df_all["ציון איכות"] >= 5]))
    c3.metric("🔥 הזינוק היומי", df_all.loc[df_all["שינוי %"].idxmax()]["סימול"])
    c4.metric("🕒 עדכון אחרון", datetime.now().strftime("%H:%M"))
except: pass

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📌 המניות שלי", "🔍 סורק מניות", "📄 דוח ואודות", "🔔 התראות", "🤝 רדאר מיזוגים"])

# טאב 1: המניות שלי (כולל הוספה אוטומטית של מניות זהב)
with tab1:
    # לוגיקת הוספה אוטומטית: בסיס + מניות מסורק שקיבלו ציון 5-6
    gold_from_scan = df_all[(df_all['ציון איכות'] >= 5) & (df_all['סימול'].isin(SCAN_LIST))]['סימול'].tolist()
    my_display_list = list(set(MY_STOCKS_BASE + gold_from_scan))
    my_df = df_all[df_all['סימול'].isin(my_display_list)].sort_values(by="ציון איכות", ascending=False)
    
    st.dataframe(
        my_df[["סימול", "מחיר", "שינוי %", "המלצה", "ציון איכות", "צמיחה %", "ROE %"]],
        column_config={
            "מחיר": st.column_config.TextColumn("מחיר", help=GLOSSARY["מחיר"]),
            "ציון איכות": st.column_config.NumberColumn("⭐ ציון", help=GLOSSARY["ציון איכות"]),
            "צמיחה %": st.column_config.NumberColumn("מכירות", help=GLOSSARY["צמיחת מכירות"], format="%.1%"),
            "ROE %": st.column_config.NumberColumn("ROE", help=GLOSSARY["ROE"], format="%.1%"),
            "המלצה": st.column_config.TextColumn("המלצת AI", help=GLOSSARY["המלצה"]),
            "שינוי %": st.column_config.NumberColumn("שינוי", format="%.2f%%")
        },
        use_container_width=True, hide_index=True
    )
    st.caption("💡 מניות זהב (5-6) מהסורק נוספו לכאן אוטומטית.")

# טאב 2: סורק מניות
with tab2:
    scan_df = df_all[df_all['סימול'].isin(SCAN_LIST)].sort_values(by="ציון איכות", ascending=False)
    st.dataframe(scan_df[["סימול", "מחיר", "ציון איכות", "צמיחה %", "שוליים %", "המלצה"]], use_container_width=True, hide_index=True)

# טאב 3: דוח ואודות (10 שנים גמיש)
with tab3:
    sel = st.selectbox("בחר מניה לניתוח:", my_display_list)
    
    # אודות מפורט
    about_dict = {
        "NVDA": "מובילת מהפכת הבינה המלאכותית. השבבים שלה הם היחידים שמסוגלים להריץ מודלים מורכבים.",
        "MSFT": "ענקית הענן והתוכנה. שולטת ב-AI דרך OpenAI ומערכת Copilot.",
        "ENLT.TA": "חברה ישראלית המקימה חוות רוח ושדות סולאריים בעולם. קריטית לצורך בחשמל נקי.",
        "PLTR": "מערכות הפעלה ל-AI עבור ממשלות ועסקים גדולים. צומחת במהירות בשוק המסחרי."
    }
    st.markdown(f'<div class="ai-card"><b>🏢 אודות {sel}:</b><br>{about_dict.get(sel, "חברה מובילה המופיעה ברשימות המעקב.")}</div>', unsafe_allow_html=True)
    
    # ניתוח 10 שנים
    yrs = st.slider("טווח שנים לגרף:", 1, 10, 5)
    hist = yf.Ticker(sel).history(period=f"{yrs}y")
    fig = go.Figure(go.Scatter(x=hist.index, y=hist['Close'], line=dict(color='#1a73e8', width=2), fill='tozeroy'))
    fig.update_layout(title=f"ביצועי מניית {sel} - {yrs} שנים", height=300, template="plotly_white", margin=dict(l=0,r=0,t=30,b=0))
    st.plotly_chart(fig, use_container_width=True)

# טאב 4: התראות חכמות (7 ימים מראש)
with tab4:
    found_alert = False
    for _, r in df_all.iterrows():
        # התראת דוחות
        if r['earnings']:
            e_dt = datetime.fromtimestamp(r['earnings'])
            days = (e_dt - datetime.now()).days
            if 0 <= days <= 7:
                st.markdown(f'<div class="alert-banner alert-orange">📅 <b>{r["סימול"]}</b>: דוח כספי בעוד {days} ימים! ({e_dt.strftime("%d/%m")})</div>', unsafe_allow_html=True)
                found_alert = True
        # התראת זינוק
        if r['שינוי %'] >= 3.0:
            st.markdown(f'<div class="alert-banner alert-green">🚀 <b>{r["סימול"]}</b> מזנקת ב-{r["שינוי %"]}% היום!</div>', unsafe_allow_html=True)
            found_alert = True
    if not found_alert: st.info("אין התראות דחופות כרגע.")

# טאב 5: רדאר מיזוגים עם לינקים
with tab5:
    mergers = [
        {"חברה": "Wiz / Google", "פרטים": "שמועות על רכישה בסך 23 מיליארד דולר.", "חיפוש": "Wiz Google merger news"},
        {"חברה": "Intel / Qualcomm", "פרטים": "ספקולציות על רכישת חטיבת השבבים.", "חיפוש": "Intel Qualcomm acquisition rumors"},
        {"חברה": "Capital One / Discover", "פרטים": "מיזוג ענק בשלבי אישור רגולטורי.", "חיפוש": "Capital One Discover merger update"}
    ]
    for m in mergers:
        url = f"https://www.google.com/search?q={urllib.parse.quote(m['חיפוש'])}"
        st.markdown(f"""
        <div class="ai-card">
            <b>🤝 {m['חברה']}</b> | {m['פרטים']}<br>
            <a href="{url}" target="_blank" style="color:#1a73e8; font-weight:bold;">🔗 קרא את הדיווח האחרון</a>
        </div>
        """, unsafe_allow_html=True)
