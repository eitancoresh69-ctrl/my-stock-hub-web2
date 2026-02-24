import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import urllib.parse

# --- 1. הגדרות דף ועיצוב Elite (RTL, ללא סרגל צד, עיצוב גרפי) ---
st.set_page_config(page_title="Investment Hub Elite 2026", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    .block-container { padding-top: 1rem !important; }
    
    /* עיצוב כרטיסי AI מודרניים */
    .ai-insight-box {
        background: linear-gradient(135deg, #f0f7ff 0%, #ffffff 100%);
        padding: 15px; border-radius: 12px; border-right: 6px solid #1a73e8;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 15px;
    }
    
    /* התראות מעוצבות */
    .alert-banner { padding: 12px; border-radius: 8px; margin-bottom: 8px; border-right: 5px solid; font-size: 14px; font-weight: 500; }
    .alert-green { background-color: #e8f5e9; border-color: #2e7d32; color: #1b5e20; }
    .alert-orange { background-color: #fff3e0; border-color: #ef6c00; color: #e65100; }
    
    /* כותרות דגש */
    .section-header { color: #1a73e8; border-bottom: 2px solid #e1e4e8; padding-bottom: 5px; margin-bottom: 15px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילון מונחים (בועות הסבר בעברית) ---
GLOSSARY = {
    "revenueGrowth": "צמיחה בהכנסות: מראה אם החברה מוכרת יותר משנה לשנה. מעל 10% מעיד על עסק צומח ובריא.",
    "returnOnEquity": "תשואה על ההון (ROE): מודד כמה רווח החברה מייצרת על כל שקל שהשקעת. מעל 15% נחשב למעולה.",
    "debtToEquity": "יחס חוב להון: בודק אם החברה ממונפת מדי. מתחת ל-100 נחשב לרמה בטוחה ושמרנית.",
    "fairValue": "שווי הוגן (DCF): המחיר התיאורטי שהמניה שווה באמת לפי תחזית רווחים. עוזר לזהות מציאות.",
    "qualityScore": "ציון איכות: שקלול של 6 קריטריונים מהמדריך. 5-6 כוכבים מעידים על חברת 'זהב'.",
    "recommendation": "המלצת AI: ניתוח אוטומטי של הפער בין המחיר הנוכחי לשווי ההוגן."
}

# --- 3. לוגיקה פיננסית חכמה (AI & Calculations) ---

def calculate_advanced_metrics(info):
    """ חישוב מורחב של שווי וציון איכות """
    try:
        fcf = info.get('freeCashflow', 0)
        growth = info.get('revenueGrowth', 0.05)
        shares = info.get('sharesOutstanding', 1)
        fv = (fcf * (1 + growth) * 15) / shares if fcf > 0 and shares > 0 else None
        
        # ציון איכות (6 קריטריונים)
        score = sum([
            info.get('revenueGrowth', 0) >= 0.10,
            info.get('earningsGrowth', 0) >= 0.10,
            info.get('profitMargins', 0) >= 0.10,
            info.get('returnOnEquity', 0) >= 0.15,
            (info.get('totalCash', 0) / info.get('totalDebt', 1)) > 1,
            info.get('totalDebt', 0) == 0
        ])
        return fv, score
    except: return None, 0

def get_ai_rec(price, fv):
    if not fv or not price: return "בבדיקה 🔍"
    gap = (fv - price) / price
    if gap > 0.15: return "קנייה חזקה 💎"
    elif gap > 0.05: return "קנייה 📈"
    elif gap < -0.15: return "מכירה 🔴"
    return "החזק ⚖️"

# --- 4. שליפת נתונים מרכזית ---
MY_STOCKS = ["MSFT", "AAPL", "NVDA", "TSLA", "PLTR", "MSTR", "ENLT.TA", "POLI.TA", "LUMI.TA"]
SCAN_LIST = ["AMZN", "AVGO", "META", "GOOGL", "LLY", "TSM", "COST", "V", "MA", "ADBE"]

@st.cache_data(ttl=3600)
def fetch_hub_data(tickers):
    rows = []
    for t in tickers:
        try:
            s = yf.Ticker(t)
            inf = s.info
            h = s.history(period="5d")
            if h.empty: continue
            px = h['Close'].iloc[-1]
            chg = ((px / h['Close'].iloc[-2]) - 1) * 100
            fv, score = calculate_advanced_metrics(inf)
            
            rows.append({
                "סימול": t, "מחיר": round(px, 2), "שינוי %": round(chg, 2),
                "שווי הוגן": fv, "המלצה": get_ai_rec(px, fv),
                "ציון איכות": score, "צמיחה": inf.get('revenueGrowth', 0),
                "ROE": inf.get('returnOnEquity', 0), "חוב": inf.get('debtToEquity', 0),
                "earnings_date": inf.get('nextEarningsDate')
            })
        except: continue
    return pd.DataFrame(rows)

# --- 5. בניית הממשק הגרפי ---
st.title("Investment Hub Elite 2026 🚀")

df_full = fetch_hub_data(list(set(MY_STOCKS + SCAN_LIST)))

# דשבורד עליון צבעוני
vix_px = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1, c2, c3, c4 = st.columns(4)
c1.metric("📊 מדד הפחד (VIX)", f"{vix_px:.2f}", help="מראה את רמת הלחץ בשוק.")
c2.metric("🏆 מניות זהב (5-6)", len(df_full[df_full["ציון איכות"] >= 5]))
c3.metric("🔥 הזינוק היומי", df_full.loc[df_full["שינוי %"].idxmax()]["סימול"] if not df_full.empty else "N/A")
c4.metric("📅 עדכון אחרון", datetime.now().strftime("%H:%M"))

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📌 המניות שלי", "🔍 סורק מניות חכמות AI", "📄 אודות וניתוח עומק", "🔔 התראות חכמות", "🤝 רדאר מיזוגים"
])

# --- טאב 1: המניות שלי (גרפי וצבעוני) ---
with tab1:
    st.markdown('<div class="section-header">ניתוח תיק השקעות ואיכות פנימית</div>', unsafe_allow_html=True)
    my_df = df_full[df_full['סימול'].isin(MY_STOCKS)]
    
    st.dataframe(
        my_df[["סימול", "מחיר", "שינוי %", "המלצה", "ציון איכות", "צמיחה", "ROE"]],
        column_config={
            "צמיחה": st.column_config.ProgressColumn("צמיחה", help=GLOSSARY["revenueGrowth"], format="%.1f%%", min_value=0, max_value=0.5),
            "ROE": st.column_config.NumberColumn("ROE", help=GLOSSARY["returnOnEquity"], format="%.1%"),
            "ציון איכות": st.column_config.NumberColumn("⭐ ציון", help=GLOSSARY["qualityScore"]),
            "שינוי %": st.column_config.NumberColumn("שינוי %", format="%.2f%%"),
            "המלצה": st.column_config.TextColumn("המלצת AI", help=GLOSSARY["recommendation"])
        },
        use_container_width=True, hide_index=True
    )

# --- טאב 2: סורק מניות חכמות (החלק שביקשת) ---
with tab2:
    st.markdown('<div class="section-header">🔍 סורק הזדמנויות AI (לפי 6 קריטריונים)</div>', unsafe_allow_html=True)
    scan_df = df_full[df_full['סימול'].isin(SCAN_LIST)].sort_values(by="ציון איכות", ascending=False)
    
    col_filters, col_results = st.columns([1, 4])
    with col_filters:
        min_score = st.slider("ציון איכות מינימלי", 0, 6, 4)
        only_buy = st.checkbox("הצג רק המלצות 'קנייה'")
    
    filtered_scan = scan_df[scan_df["ציון איכות"] >= min_score]
    if only_buy:
        filtered_scan = filtered_scan[filtered_scan["המלצה"].str.contains("קנייה")]
        
    st.dataframe(
        filtered_scan[["סימול", "מחיר", "המלצה", "ציון איכות", "שווי הוגן", "חוב"]],
        column_config={
            "שווי הוגן": st.column_config.NumberColumn("שווי הוגן", help=GLOSSARY["fairValue"], format="$%.2f"),
            "ציון איכות": st.column_config.NumberColumn("ציון איכות (6)", help="מספר הקריטריונים החיוביים שעמדו בבדיקה."),
            "חוב": st.column_config.NumberColumn("יחס חוב", help=GLOSSARY["debtToEquity"])
        },
        use_container_width=True, hide_index=True
    )

# --- טאב 3: אודות וניתוח (10 שנים גמיש) ---
with tab3:
    sel = st.selectbox("בחר מניה לניתוח עומק:", list(df_full['סימול']))
    row = df_full[df_full['סימול'] == sel].iloc[0]
    
    st.markdown(f"""
    <div class="ai-insight-box">
        <strong>🏢 אודות {sel} (במילים פשוטות):</strong><br>
        החברה נסחרת בציון איכות של {row['ציון איכות']} מתוך 6. 
        המלצת ה-AI שלנו היא <b>{row['המלצה']}</b> לאור הפער בין המחיר הנוכחי לשווי המעורך.
    </div>
    """, unsafe_allow_html=True)
    
    yrs = st.slider("בחר טווח שנים לגרף:", 1, 10, 5)
    hist = yf.Ticker(sel).history(period=f"{yrs}y")
    fig = go.Figure(go.Scatter(x=hist.index, y=hist['Close'], line=dict(color='#1a73e8', width=2), fill='tozeroy'))
    fig.update_layout(title=f"ביצועי המניה ל-{yrs} שנים", height=400, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

# --- טאב 4: התראות חכמות (דוחות 7 ימים) ---
with tab4:
    st.markdown('<div class="section-header">📢 התראות ודיווחים קרובים</div>', unsafe_allow_html=True)
    found_alert = False
    for _, row in df_full.iterrows():
        # 1. התראת דוחות שבוע מראש
        if row['earnings_date']:
            e_dt = datetime.fromtimestamp(row['earnings_date'])
            days = (e_dt - datetime.now()).days
            if 0 <= days <= 7:
                st.markdown(f'<div class="alert-banner alert-orange">📅 <b>{row["סימול"]}</b>: דוח כספי בעוד {days} ימים! ({e_dt.strftime("%d/%m")})</div>', unsafe_allow_html=True)
                found_alert = True
        # 2. התראת זינוק
        if row['שינוי %'] >= 3.0:
            st.markdown(f'<div class="alert-banner alert-green">🚀 <b>{row["סימול"]}</b> בזינוק חריג של {row["שינוי %"]}% היום!</div>', unsafe_allow_html=True)
            found_alert = True
    if not found_alert: st.info("אין התראות דחופות כרגע.")

# --- טאב 5: רדאר מיזוגים (M&A) ---
with tab5:
    st.markdown('<div class="section-header">🤝 רדאר מיזוגים ושמועות (AI Radar)</div>', unsafe_allow_html=True)
    mergers = [
        {"עסקה": "Google / Wiz", "סבירות": "75%", "ניתוח AI": "המשא ומתן חזר לשולחן; פוטנציאל לחיזוק ענן הסייבר."},
        {"עסקה": "Intel / Broadcom", "סבירות": "30%", "ניתוח AI": "שמועות על פיצול חטיבות; סבירות נמוכה עקב רגולציה."},
        {"עסקה": "Capital One / Discover", "סבירות": "90%", "ניתוח AI": "מיזוג בשלבי אישור סופיים."}
    ]
    for m in mergers:
        st.markdown(f"""
        <div class="ai-insight-box">
            <b>{m['עסקה']}</b> | סבירות: <span style="color:#1a73e8">{m['סבירות']}</span><br>
            <small>{m['ניתוח AI']}</small>
        </div>
        """, unsafe_allow_html=True)

# כפתור רענון
if st.button("🔄 רענון נתונים"):
    st.cache_data.clear()
    st.rerun()
