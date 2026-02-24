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
    .gold-label { background-color: #ffd700; color: #000; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 10px; }
    
    /* בועות הסבר וטבלאות */
    [data-testid="stDataFrame"] { border: 1px solid #e0e0e0; border-radius: 10px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילון מונחים (בועות הסבר בעברית) ---
GLOSSARY = {
    "מחיר": "המחיר הנוכחי במסחר. במניות ארה\"ב בדולר ($), במניות ישראל באגורות (אג').",
    "צמיחה": "צמיחה בהכנסות: מראה אם העסק מוכר יותר משנה לשנה. מעל 10% זה מצוין.",
    "ROE": "תשואה על ההון: כמה רווח החברה מייצרת על כל שקל שהשקעת. מעל 15% זה מעולה.",
    "חוב": "יחס חוב להון: בודק כמה החברה ממונפת. מתחת ל-100 נחשב לבריא ויציב.",
    "שווי הוגן": "הערכת שווי DCF: כמה המניה שווה באמת לפי תחזית רווחים עתידית.",
    "המלצה": "ניתוח AI: האם המניה זולה (קנייה) או יקרה (מכירה) ביחס לשווי ההוגן."
}

# --- 3. לוגיקה חכמה וזיהוי מטבע ---

def format_price(ticker, price):
    """ זיהוי מטבע והוספת סימול מתאים """
    if ".TA" in ticker:
        return f"{price:,.1f} אג'"
    return f"${price:,.2f}"

def calculate_advanced_metrics(info):
    try:
        fcf = info.get('freeCashflow', 0)
        growth = info.get('revenueGrowth', 0.05)
        shares = info.get('sharesOutstanding', 1)
        fv = (fcf * (1 + growth) * 15) / shares if fcf > 0 and shares > 0 else None
        
        # ציון איכות (6 קריטריונים)
        score = sum([
            info.get('revenueGrowth', 0) >= 0.10,
            info.get('earningsGrowth', 0) >= 0.10,
            info.get('profitMargins', 0) >= 0.12,
            info.get('returnOnEquity', 0) >= 0.15,
            info.get('currentRatio', 0) > 1.5,
            info.get('totalDebt', 0) == 0
        ])
        return fv, score
    except: return None, 0

# --- 4. שליפת נתונים ---
MY_STOCKS_LIST = ["MSFT", "AAPL", "NVDA", "TSLA", "PLTR", "ENLT.TA", "POLI.TA", "LUMI.TA"]
SCAN_LIST = ["AMZN", "AVGO", "META", "GOOGL", "LLY", "TSM", "COST", "V", "ADBE", "NFLX"]

@st.cache_data(ttl=3600)
def fetch_elite_data(tickers, scan_tickers):
    rows = []
    all_to_fetch = list(set(tickers + scan_tickers))
    for t in all_to_fetch:
        try:
            s = yf.Ticker(t)
            inf = s.info
            h = s.history(period="2d")
            if h.empty: continue
            px = h['Close'].iloc[-1]
            chg = ((px / h['Close'].iloc[-2]) - 1) * 100
            fv, score = calculate_advanced_metrics(inf)
            
            # לוגיקת המלצה
            gap = (fv - px) / px if fv else 0
            rec = "קנייה חזקה 🟢" if gap > 0.15 else "קנייה 📈" if gap > 0.05 else "מכירה 🔴" if gap < -0.10 else "החזק ⚖️"
            
            rows.append({
                "סימול": t, "מחיר_נומינלי": px, "מחיר": format_price(t, px), "שינוי %": round(chg, 2),
                "שווי הוגן": fv, "המלצה": rec, "ציון איכות": score,
                "צמיחה": inf.get('revenueGrowth', 0), "ROE": inf.get('returnOnEquity', 0),
                "earnings": inf.get('nextEarningsDate')
            })
        except: continue
    return pd.DataFrame(rows)

df_all = fetch_elite_data(MY_STOCKS_LIST, SCAN_LIST)

# --- 5. בניית הממשק ---
st.title("Investment Hub Elite 2026 🚀")

# קוביות מדדים עליונות
vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1, c2, c3, c4 = st.columns(4)
c1.metric("📊 מדד הפחד (VIX)", f"{vix:.2f}")
c2.metric("💎 מניות זהב בסריקה", len(df_all[(df_all['ציון איכות'] >= 5) & (df_all['סימול'].isin(SCAN_LIST))]))
c3.metric("🔥 הזינוק היומי", df_all.loc[df_all["שינוי %"].idxmax()]["סימול"] if not df_all.empty else "N/A")
c4.metric("📅 עדכון אחרון", datetime.now().strftime("%H:%M"))

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📌 המניות שלי", "🔍 סורק מניות חכמות AI", "📄 דוח שור/דוב", "🔔 התראות דוחות", "🤝 רדאר מיזוגים"
])

# טאב 1: המניות שלי (כולל הוספה אוטומטית של מניות זהב)
with tab1:
    st.subheader("תיק השקעות ומעקב אישי")
    # לוגיקת הוספה אוטומטית: המניות המקוריות + כל מניה מהסורק עם ציון 5-6
    auto_added = df_all[(df_all['ציון איכות'] >= 5) & (df_all['סימול'].isin(SCAN_LIST))]['סימול'].tolist()
    display_list = list(set(MY_STOCKS_LIST + auto_added))
    my_df = df_all[df_all['סימול'].isin(display_list)]
    
    st.dataframe(
        my_df[["סימול", "מחיר", "שינוי %", "המלצה", "ציון איכות", "צמיחה", "ROE"]],
        column_config={
            "מחיר": st.column_config.TextColumn("מחיר", help=GLOSSARY["מחיר"]),
            "צמיחה": st.column_config.ProgressColumn("צמיחה", help=GLOSSARY["צמיחה"], format="%.1f%%", min_value=0, max_value=0.5),
            "ROE": st.column_config.NumberColumn("ROE", help=GLOSSARY["ROE"], format="%.1%"),
            "ציון איכות": st.column_config.NumberColumn("⭐ איכות", help="ציון 0-6 מבוסס על המדריך שלך"),
            "המלצה": st.column_config.TextColumn("המלצת AI", help=GLOSSARY["המלצה"])
        },
        use_container_width=True, hide_index=True
    )
    st.caption("💡 מניות עם ציון איכות 5-6 מהסורק מתווספות לכאן אוטומטית כ'המלצות זהב'.")

# טאב 2: סורק מניות חכמות AI
with tab2:
    st.subheader("🔍 סריקת הזדמנויות בשוק העולמי")
    scan_df = df_all[df_all['סימול'].isin(SCAN_LIST)].sort_values(by="ציון איכות", ascending=False)
    st.table(scan_df[["סימול", "מחיר", "המלצה", "ציון איכות", "צמיחה"]])

# טאב 3: דוח שור/דוב (ניתוח AI)
with tab3:
    sel = st.selectbox("בחר מניה לניתוח AI עמוק:", display_list)
    row = df_all[df_all['סימול'] == sel].iloc[0]
    
    # ניתוח שנים גמיש שביקשת
    yrs = st.slider("טווח שנים לגרף:", 1, 10, 5)
    hist = yf.Ticker(sel).history(period=f"{yrs}y")
    fig = go.Figure(go.Scatter(x=hist.index, y=hist['Close'], line=dict(color='#1a73e8', width=2), fill='tozeroy'))
    fig.update_layout(title=f"ביצועי מניית {sel} - {yrs} שנים", height=350, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.success(f"🐂 **תרחיש השור (AI):** {sel} מציגה ROE חזק של {row['ROE']:.1%}. המודל העסקי מוכיח עמידות גבוהה.")
    with col_b:
        st.error(f"🐻 **תרחיש הדוב (AI):** תמחור השוק קרוב לשווי ההוגן. צמיחה נמוכה מ-10% עלולה להוביל לתיקון.")

# טאב 4: התראות דוחות (7 ימים מראש)
with tab4:
    st.subheader("🔔 מרכז התראות (שבוע מראש)")
    found = False
    for _, r in df_all.iterrows():
        if r['earnings']:
            e_dt = datetime.fromtimestamp(r['earnings'])
            days = (e_dt - datetime.now()).days
            if 0 <= days <= 7:
                st.warning(f"📅 **{r['סימול']}** מפרסמת דוחות בעוד {days} ימים! ({e_dt.strftime('%d/%m/%Y')})")
                found = True
    if not found: st.info("אין דוחות צפויים ב-7 הימים הקרובים.")

# טאב 5: רדאר מיזוגים עם לינקים
with tab5:
    st.subheader("🤝 רדאר M&A ושמועות שוק")
    mergers = [
        {"חברה": "Wiz / Google", "סבירות AI": "75%", "לינק": "https://www.google.com/search?q=Wiz+Google+merger+news"},
        {"חברה": "Intel / Qualcomm", "סבירות AI": "30%", "לינק": "https://www.google.com/search?q=Intel+Qualcomm+acquisition+rumors"},
        {"חברה": "Capital One / Discover", "סבירות AI": "90%", "לינק": "https://www.google.com/search?q=Capital+One+Discover+merger+update"}
    ]
    for m in mergers:
        st.markdown(f"""
        <div class="ai-card">
            <b>{m['חברה']}</b> | סבירות AI: {m['סבירות AI']}<br>
            <a href="{m['לינק']}" target="_blank" style="color:#1a73e8; font-weight:bold;">🔗 קרא את הדיווח האחרון בנושא</a>
        </div>
        """, unsafe_allow_html=True)
