import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import urllib.parse

# --- 1. הגדרות דף ועיצוב CSS (RTL, ללא סרגל צד) ---
st.set_page_config(page_title="Investment Hub Elite 2026", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    .block-container { padding-top: 1rem !important; }
    
    /* עיצוב קוביות מדדים */
    .metric-card {
        background: white; padding: 12px; border-radius: 10px;
        border-right: 5px solid #1a73e8; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center; margin-bottom: 15px;
    }
    
    /* תיבות מידע */
    .about-box { background-color: #f1f8ff; padding: 15px; border-radius: 10px; border-right: 6px solid #1a73e8; line-height: 1.6; margin-bottom: 15px; }
    .alert-card { padding: 10px; border-radius: 8px; margin-bottom: 8px; border-right: 5px solid; font-size: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .alert-green { background-color: #e8f5e9; border-color: #2e7d32; color: #1b5e20; }
    .alert-orange { background-color: #fff3e0; border-color: #ef6c00; color: #e65100; }
    
    /* עיצוב טבלה אינטראקטיבית */
    [data-testid="stDataFrame"] { border: 1px solid #e0e0e0; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילונים והסברים (בועות הסבר) ---
GLOSSARY = {
    "צמיחה": "צמיחה בהכנסות: מראה אם העסק גדל משנה לשנה. מעל 10% זה מצוין.",
    "ROE": "תשואה על ההון: מודד כמה רווח החברה מייצרת מהכסף של המשקיעים. מעל 15% זה מעולה.",
    "חוב": "יחס חוב להון: בודק כמה החברה ממונפת. מתחת ל-100 נחשב לבריא.",
    "שווי הוגן": "הערכת שווי DCF: מחיר המטרה של המניה לפי תחזית הרווחים העתידית.",
    "המלצה": "ניתוח אוטומטי: משווה בין המחיר בשוק לשווי ההוגן וממליץ על פעולה."
}

ABOUT_DB = {
    "MSFT": "<b>מיקרוסופט:</b> מובילת עולם התוכנה והענן. מנוע צמיחה אדיר ב-AI.",
    "NVDA": "<b>אנבידיה:</b> הלב של מהפכת הבינה המלאכותית. צמיחה פנומנלית בשבבים.",
    "AAPL": "<b>אפל:</b> ענקית המכשירים עם קופת המזומנים הגדולה בעולם.",
    "TSLA": "<b>טסלה:</b> מובילת הרכבים החשמליים והרובוטיקה. השקעה על העתיד האוטונומי.",
    "ENLT.TA": "<b>אנלייט:</b> חברה ישראלית המקימה פרויקטים של אנרגיה ירוקה בעולם.",
    "PLTR": "<b>פלנטיר:</b> מערכות AI מתקדמות לניתוח דאטה עבור ממשלות ועסקים."
}

# --- 3. פונקציות לוגיקה וחישוב ---

def get_recommendation(price, fair_value):
    if fair_value == "N/A" or not isinstance(fair_value, (int, float)): return "בבדיקה 🔍"
    gap = (fair_value - price) / price
    if gap > 0.15: return "קנייה חזקה 🟢"
    elif gap > 0.05: return "קנייה 📈"
    elif gap < -0.15: return "מכירה 🔴"
    elif gap < -0.05: return "הפחתה 📉"
    return "החזק ⚖️"

def calculate_fair_value_numeric(info):
    try:
        fcf = info.get('freeCashflow', 0)
        growth = info.get('revenueGrowth', 0.05)
        shares = info.get('sharesOutstanding', 1)
        if fcf <= 0 or shares <= 0: return "N/A"
        val = (fcf * (1 + growth) * 15) / shares
        return round(val, 2)
    except: return "N/A"

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
            px = hist['Close'].iloc[-1]
            chg = ((px / hist['Close'].iloc[-2]) - 1) * 100
            
            fv = calculate_fair_value_numeric(info)
            rec = get_recommendation(px, fv)
            
            rows.append({
                "סימול": t, "מחיר": round(px, 2), "שינוי %": round(chg, 2),
                "שווי הוגן": fv, "המלצה": rec,
                "צמיחה": info.get("revenueGrowth", 0),
                "ROE": info.get("returnOnEquity", 0),
                "חוב": info.get("debtToEquity", 0),
                "earnings": info.get('nextEarningsDate')
            })
        except: continue
    return pd.DataFrame(rows)

# --- 4. תצוגת האתר ---
st.title("Investment Hub Elite 2026 🚀")

df = fetch_elite_data(list(set(MY_STOCKS + SCAN_LIST)))

# קוביות מדדים עליונות
c1, c2, c3, c4 = st.columns(4)
vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1.markdown(f'<div class="metric-card"><div class="m-lbl">📊 מדד הפחד (VIX)</div><div class="m-val">{vix:.2f}</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-card"><div class="m-lbl">💎 מניות ב"קנייה"</div><div class="m-val">{len(df[df["המלצה"].str.contains("קנייה")]) if not df.empty else 0}</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="metric-card"><div class="m-lbl">🚀 המזנקת היומית</div><div class="m-val" style="color:green;">{df.loc[df["שינוי %"].idxmax()]["סימol"] if not df.empty else "N/A"}</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="metric-card"><div class="m-lbl">🕒 עדכון</div><div class="m-val">{datetime.now().strftime("%H:%M")}</div></div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📌 המניות שלי", "🔍 סורק איכות", "📄 אודות וניתוח עשור", "🔔 התראות חכמות", "🤝 רדאר מיזוגים"])

# טאב 1: המניות שלי עם Tooltips (בועות הסבר)
with tab1:
    st.subheader("ניתוח החזקות ושווי הוגן")
    my_df = df[df['סימול'].isin(MY_STOCKS)]
    
    st.dataframe(
        my_df[["סימול", "מחיר", "שינוי %", "שווי הוגן", "המלצה", "צמיחה", "ROE"]],
        column_config={
            "צמיחה": st.column_config.NumberColumn("צמיחה", help=GLOSSARY["צמיחה"], format="%.1%"),
            "ROE": st.column_config.NumberColumn("ROE", help=GLOSSARY["ROE"], format="%.1%"),
            "שווי הוגן": st.column_config.NumberColumn("שווי הוגן", help=GLOSSARY["שווי הוגן"]),
            "המלצה": st.column_config.TextColumn("המלצה AI", help=GLOSSARY["המלצה"]),
            "שינוי %": st.column_config.NumberColumn("שינוי %", format="%.2f%%")
        },
        use_container_width=True,
        hide_index=True
    )
    st.caption("💡 **טיפ:** העבר את העכבר מעל כותרות העמודות בטבלה להסבר בעברית.")

# טאב 3: אודות וניתוח 10 שנים
with tab3:
    sel = st.selectbox("בחר מניה לניתוח:", MY_STOCKS + SCAN_LIST)
    st.markdown(f'<div class="about-box"><b>🏢 אודות {sel}:</b><br>{ABOUT_DB.get(sel, "חברה מובילה המופיעה ברשימות המעקב.")}</div>', unsafe_allow_html=True)
    
    yrs = st.slider("בחר שנים לגרף היסטורי:", 1, 10, 5)
    hist_10 = yf.Ticker(sel).history(period=f"{yrs}y")
    if not hist_10.empty:
        fig = go.Figure(go.Scatter(x=hist_10.index, y=hist_10['Close'], line=dict(color='#1a73e8', width=2)))
        fig.update_layout(height=350, title=f"ביצועי המניה ל-{yrs} שנים", template="plotly_white", margin=dict(l=0,r=0,t=30,b=0))
        st.plotly_chart(fig, use_container_width=True)

# טאב 4: התראות חכמות
with tab4:
    st.subheader("🔔 מרכז התראות")
    found_alert = False
    for _, row in df.iterrows():
        if row['earnings']:
            e_dt = datetime.fromtimestamp(row['earnings'])
            days = (e_dt - datetime.now()).days
            if 0 <= days <= 7:
                st.markdown(f'<div class="alert-card alert-orange">📅 <b>{row["סימול"]}</b>: דוח כספי בעוד {days} ימים ({e_dt.strftime("%d/%m")})</div>', unsafe_allow_html=True)
                found_alert = True
        if row['שינוי %'] >= 3.5:
            st.markdown(f'<div class="alert-card alert-green">🚀 <b>{row["סימול"]}</b> בזינוק חריג של {row["שינוי %"]:.1f}% היום!</div>', unsafe_allow_html=True)
            found_alert = True
    if not found_alert: st.info("אין התראות חריגות כרגע.")

# טאב 5: רדאר מיזוגים (עם קישורים לחדשות)
with tab5:
    st.subheader("🤝 רדאר M&A ושמועות שוק")
    mergers = [
        {"חברה": "Wiz / Google", "סטטוס": "שמועות רכישה", "חיפוש": "Wiz Google merger news"},
        {"חברה": "Intel", "סטטוס": "ספקולציה", "חיפוש": "Intel acquisition rumors"},
        {"חברה": "Capital One", "סטטוס": "מיזוג רשמי", "חיפוש": "Capital One Discover merger update"}
    ]
    
    for m in mergers:
        url = f"https://www.google.com/search?q={urllib.parse.quote(m['חיפוש'])}"
        st.markdown(f"""
        <div style="background: white; padding: 12px; border-radius: 8px; border: 1px solid #eee; margin-bottom: 8px;">
            <b>{m['חברה']}</b> | סטטוס: {m['סטטוס']}<br>
            <a href="{url}" target="_blank" style="color: #1a73e8; text-decoration: none; font-weight: bold;">🔗 לכתבות האחרונות בנושא</a>
        </div>
        """, unsafe_allow_html=True)
