import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. הגדרות דף ועיצוב CSS (RTL מלא וצמצום רווחים) ---
st.set_page_config(page_title="Investment Hub PRO 2026", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    .block-container { padding-top: 1rem !important; }
    
    /* קוביות מדדים עליונות */
    .metric-container {
        background: white; padding: 15px; border-radius: 12px;
        border-right: 5px solid #1a73e8; box-shadow: 0 4px 6px rgba(0,0,0,0.07);
        text-align: center; margin-bottom: 15px;
    }
    .m-val { font-size: 24px; font-weight: bold; color: #1a73e8; }
    .m-lbl { font-size: 14px; color: #5f6368; }

    /* תיבות מידע */
    .about-box { background-color: #f1f8ff; padding: 15px; border-radius: 10px; border-right: 6px solid #1a73e8; line-height: 1.6; margin-bottom: 15px; }
    .alert-card { padding: 10px; border-radius: 8px; margin-bottom: 8px; border-right: 5px solid; font-size: 14px; }
    .alert-up { background-color: #e8f5e9; border-color: #2e7d32; color: #1b5e20; }
    .alert-info { background-color: #fff3e0; border-color: #ef6c00; color: #e65100; }
    </style>
""", unsafe_allow_html=True)

# --- 2. נתונים ואודות למתחילים ---
MY_STOCKS = ["MSFT", "AAPL", "NVDA", "TSLA", "PLTR", "MSTR", "GOOGL", "META", "ENLT.TA", "POLI.TA", "LUMI.TA"]
SCAN_CANDIDATES = ["AMZN", "AVGO", "COST", "MA", "V", "LLY", "TSM", "ADBE", "NFLX", "ORCL", "ASML", "SBUX", "AMD"]

ABOUT_GUIDE = {
    "MSFT": "מיקרוסופט היא ענקית התוכנה והענן. היא מרוויחה מכל מחשב בעולם (Windows) ומהבינה המלאכותית (ChatGPT). נחשבת למניה בטוחה ויציבה.",
    "NVDA": "אנבידיה מייצרת את ה'מוח' של הבינה המלאכותית. בלעדיה העולם הטכנולוגי לא יכול להתקדם. היא הצומחת ביותר כרגע.",
    "AAPL": "אפל היא מלכת המותג. היא בונה מוצרים שאנשים לא יכולים לעזוב (iPhone), מה שמייצר לה רווחים אדירים.",
    "TSLA": "טסלה היא חברת טכנולוגיה במסווה של רכב. היא מהמרת על נהיגה אוטונומית ורובוטים.",
    "ENLT.TA": "אנלייט היא חברה ישראלית שבונה חוות רוח ושדות סולאריים. היא נהנית מהמעבר העולמי לחשמל נקי."
}

# --- 3. פונקציות שליפה חסינות (בלי KeyError) ---
@st.cache_data(ttl=3600)
def fetch_safe_data(tickers):
    rows = []
    for t in tickers:
        try:
            obj = yf.Ticker(t)
            hist = obj.history(period="5d")
            if hist.empty: continue
            info = obj.info
            curr, prev = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
            
            # בדיקת איכות (מניית זהב)
            rev_g = info.get("revenueGrowth", 0) or 0
            margin = info.get("profitMargins", 0) or 0
            score = sum([rev_g >= 0.1, margin >= 0.12, info.get("returnOnEquity", 0) >= 0.15])
            
            rows.append({
                "סימול": t, "מחיר": round(curr, 2), "שינוי %": round(((curr/prev)-1)*100, 2),
                "צמיחה": f"{rev_g:.1%}", "שוליים": f"{margin:.1%}",
                "ציון (3)": score, "זהב": "🏆" if score >= 2 else "",
                "earnings_date": info.get('nextEarningsDate', None)
            })
        except: continue
    return pd.DataFrame(rows)

# --- 4. בניית הממשק ---
st.title("Investment Hub PRO 2026 🚀")

all_tickers = list(set(MY_STOCKS + SCAN_CANDIDATES))
df_data = fetch_safe_data(all_tickers)

# וידוא עמודות קיימות למניעת קריסה
for col in ["זהב", "earnings_date", "שינוי %", "סימול"]:
    if col not in df_data.columns: df_data[col] = None

# קוביות מדדים
vix_px = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(f'<div class="metric-container"><div class="m-lbl">📊 מדד הפחד (VIX)</div><div class="m-val">{vix_px:.2f}</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="metric-container"><div class="m-lbl">💎 מניות זהב</div><div class="m-val">{len(df_data[df_data["זהב"] == "🏆"])}</div></div>', unsafe_allow_html=True)
with c3:
    top_s = df_data.loc[df_data["שינוי %"].idxmax()]["סימול"] if not df_data.empty else "N/A"
    st.markdown(f'<div class="metric-container"><div class="m-lbl">🔥 זינוק יומי</div><div class="m-val" style="color:green;">{top_s}</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="metric-container"><div class="m-lbl">🕒 עדכון</div><div class="m-val">{datetime.now().strftime("%H:%M")}</div></div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📌 המניות שלי", "🔍 סורק זהב", "📄 דוח חברה ואודות", "🔔 התראות", "🤝 רדאר מיזוגים"])

# טאב 1: המניות שלי
with tab1:
    my_df = df_data[df_data['סימול'].isin(MY_STOCKS)]
    # הסרת עמודות בבטחה
    cols_to_drop = [c for c in ["earnings_date", "זהב"] if c in my_df.columns]
    st.table(my_df.drop(columns=cols_to_drop))

# טאב 3: אודות וניתוח 10 שנים
with tab3:
    sel = st.selectbox("בחר מניה לניתוח:", all_tickers)
    st.markdown(f'<div class="about-box"><b>🏢 אודות {sel}:</b><br>{ABOUT_GUIDE.get(sel, "חברה מובילה בסקטור שלה.")}</div>', unsafe_allow_html=True)
    
    yrs = st.slider("בחר שנים לגרף:", 1, 10, 5)
    hist_10 = yf.Ticker(sel).history(period=f"{yrs}y")
    if not hist_10.empty:
        fig = go.Figure(go.Scatter(x=hist_10.index, y=hist_10['Close'], line=dict(color='#1a73e8')))
        fig.update_layout(height=350, title=f"ביצועי מניית {sel} - {yrs} שנים", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

# טאב 4: התראות (תיקון ה-KeyError לחדשות)
with tab4:
    st.subheader("🔔 מרכז התראות")
    
    # בדיקת דוחות
    for _, row in df_data.iterrows():
        if row['earnings_date']:
            e_dt = datetime.fromtimestamp(row['earnings_date'])
            if (e_dt - datetime.now()).days <= 7:
                st.markdown(f'<div class="alert-card alert-info">📅 <b>{row["סימול"]}</b>: דוח קרוב ב-{e_dt.strftime("%d/%m")}</div>', unsafe_allow_html=True)

    # הצגת חדשות בבטחה
    st.divider()
    st.write("📰 **מבזקים אחרונים:**")
    for t in MY_STOCKS[:3]:
        news = yf.Ticker(t).news
        for n in news[:2]:
            title = n.get('title', 'אין כותרת זמינה') # שימוש ב-.get() מונע KeyError
            st.write(f"🔔 **{t}**: {title}")

# טאב 5: רדאר מיזוגים
with tab5:
    st.subheader("🤝 רדאר מיזוגים ושמועות (M&A)")
    mergers = [
        {"חברה": "Wiz / Google", "סטטוס": "שמועות רכישה", "פרטים": "דיווחים על חידוש המגעים."},
        {"חברה": "Intel", "סטטוס": "ספקולציה", "פרטים": "שמועות על פיצול חטיבות."},
    ]
    st.table(pd.DataFrame(mergers))
