import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. הגדרות דף ועיצוב (RTL, ללא סרגל צד, צמצום רווחים) ---
st.set_page_config(page_title="Investment Hub Elite 2026", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    .block-container { padding-top: 1rem !important; }
    
    /* עיצוב קוביות מדדים עליונות */
    .metric-card {
        background: white; padding: 12px; border-radius: 10px;
        border-right: 5px solid #1a73e8; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center; margin-bottom: 15px;
    }
    
    /* תיבות אודות והתראות */
    .about-box { background-color: #f1f8ff; padding: 15px; border-radius: 10px; border-right: 6px solid #1a73e8; line-height: 1.6; margin-bottom: 15px; }
    .alert-card { padding: 10px; border-radius: 8px; margin-bottom: 8px; border-right: 5px solid; font-size: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .alert-green { background-color: #e8f5e9; border-color: #2e7d32; color: #1b5e20; }
    .alert-orange { background-color: #fff3e0; border-color: #ef6c00; color: #e65100; }
    
    /* הפיכת הטבלה לצפופה יותר */
    [data-testid="stDataFrame"] { border: 1px solid #e0e0e0; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילון מונחים ובועות הסבר (עברית) ---
GLOSSARY = {
    "צמיחה": "צמיחה בהכנסות: מראה אם העסק מוכר יותר משנה לשנה. מעל 10% זה מצוין.",
    "ROE": "תשואה על ההון: כמה רווח החברה מייצרת על כל שקל של בעלי המניות. מעל 15% זה מעולה.",
    "חוב": "יחס חוב להון: בודק כמה החברה ממונפת. מתחת ל-100 נחשב לשמרני ובטוח.",
    "שווי הוגן": "הערכת שווי DCF: כמה המניה שווה באמת לפי תחזית הרווחים שלה.",
    "המלצה": "ניתוח אוטומטי: האם המניה זולה (קנייה), יקרה (מכירה) או במחיר הוגן (החזק)."
}

ABOUT_DB = {
    "MSFT": "<b>מיקרוסופט:</b> חברת הענן והתוכנה המובילה בעולם. שולטת ב-AI דרך OpenAI ומציגה רווחיות פנומנלית.",
    "NVDA": "<b>אנבידיה:</b> המנוע של מהפכת ה-AI. מייצרת את השבבים הכי מבוקשים בעולם. צמיחה אדירה.",
    "AAPL": "<b>אפל:</b> ענקית המכשירים עם קופת מזומנים עצומה. מניה שנחשבת ל'חוף מבטחים' למשקיעים.",
    "TSLA": "<b>טסלה:</b> מובילת הרכבים החשמליים והרובוטיקה. הימור על עתיד הנהיגה האוטונומית.",
    "ENLT.TA": "<b>אנלייט:</b> חברה ישראלית שבונה פרויקטים של אנרגיה נקייה בעולם. נכס אסטרטגי לצורך בחשמל.",
    "PLTR": "<b>פלנטיר:</b> מערכות הפעלה מבוססות AI לממשלות ועסקים. צומחת במהירות בשוק המסחרי."
}

# --- 3. פונקציות לוגיקה וחישוב ---

def get_recommendation(price, fair_value):
    """ נותן המלצה אוטומטית לפי הפער מהשווי ההוגן """
    if fair_value == "N/A" or not isinstance(fair_value, float): return "בבדיקה 🔍"
    gap = (fair_value - price) / price
    if gap > 0.15: return "קנייה חזקה 🟢"
    elif gap > 0.05: return "קנייה 📈"
    elif gap < -0.15: return "מכירה 🔴"
    elif gap < -0.05: return "הפחתה 📉"
    return "החזק ⚖️"

def calculate_fair_value_numeric(info):
    """ מחשב שווי הוגן ומחזיר מספר (Float) לחישובים """
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
c2.markdown(f'<div class="metric-card"><div class="m-lbl">💎 מניות ב"קנייה"</div><div class="m-val">{len(df["המלצה"].str.contains("קנייה")) if not df.empty else 0}</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="metric-card"><div class="m-lbl">🚀 המזנקת היומית</div><div class="m-val" style="color:green;">{df.loc[df["שינוי %"].idxmax()]["סימול"] if not df.empty else "N/A"}</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="metric-card"><div class="m-lbl">🕒 עדכון</div><div class="m-val">{datetime.now().strftime("%H:%M")}</div></div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📌 המניות שלי", "🔍 סורק איכות", "📄 אודות וניתוח עשור", "🔔 התראות חכמות", "🤝 רדאר מיזוגים"])

# טאב 1: המניות שלי עם בועות הסבר (Help)
with tab1:
    st.subheader("ניתוח החזקות ושווי הוגן")
    my_df = df[df['סימול'].isin(MY_STOCKS)]
    
    # שימוש ב-st.dataframe כדי לאפשר את ה-Tooltips (help)
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
    st.caption("💡 **טיפ:** העבר את העכבר מעל כותרות העמודות (כמו צמיחה או ROE) כדי לראות את ההסבר בעברית.")

# טאב 3: אודות וניתוח 10 שנים
with tab3:
    sel = st.selectbox("בחר מניה לניתוח:", MY_STOCKS + SCAN_LIST)
    st.markdown(f'<div class="about-box"><b>🏢 אודות {sel}:</b><br>{ABOUT_DB.get(sel, "חברה מובילה המופיעה ברשימות המעקב של המערכת.")}</div>', unsafe_allow_html=True)
    
    yrs = st.slider("בחר שנים לגרף היסטורי:", 1, 10, 5)
    hist_10 = yf.Ticker(sel).history(period=f"{yrs}y")
    if not hist_10.empty:
        fig = go.Figure(go.Scatter(x=hist_10.index, y=hist_10['Close'], line=dict(color='#1a73e8', width=2)))
        fig.update_layout(height=350, title=f"ביצועי המניה ל-{yrs} שנים", template="plotly_white", margin=dict(l=0,r=0,t=30,b=0))
        st.plotly_chart(fig, use_container_width=True)

# טאב 4: התראות חכמות (7 ימים וזינוקים)
with tab4:
    st.subheader("🔔 מרכז התראות בזמן אמת")
    found_alert = False
    for _, row in df.iterrows():
        # התראת דוחות - 7 ימים מראש
        if row['earnings']:
            e_dt = datetime.fromtimestamp(row['earnings'])
            days = (e_dt - datetime.now()).days
            if 0 <= days <= 7:
                st.markdown(f'<div class="alert-card alert-orange">📅 <b>{row["סימול"]}</b>: מפרסמת דוח בעוד {days} ימים ({e_dt.strftime("%d/%m")})</div>', unsafe_allow_html=True)
                found_alert = True
        
        # התראת זינוק (מעל 3.5%)
        if row['שינוי %'] >= 3.5:
            st.markdown(f'<div class="alert-card alert-green">🚀 <b>{row["סימול"]}</b> בזינוק חריג של {row["שינוי %"]:.1f}% היום!</div>', unsafe_allow_html=True)
            found_alert = True
    
    if not found_alert: st.info("אין התראות חריגות כרגע.")

# טאב 5: רדאר מיזוגים
with tab5:
    st.subheader("🤝 רדאר M&A ושמועות שוק")
    mergers = [
        {"חברה": "Wiz / Google", "סטטוס": "שמועות רכישה", "פרטים": "דיווחים על חידוש המגעים לרכישה הגדולה בהיסטוריה של גוגל."},
        {"חברה": "Intel", "סטטוס": "ספקולציה", "פרטים": "אנליסטים צופים פיצול חטיבות להצלת ערך המניה."},
        {"חברה": "Capital One", "סטטוס": "מיזוג רשמי", "פרטים": "רכישת Discover ממתינה לאישורים רגולטוריים סופיים."}
    ]
    st.table(pd.DataFrame(mergers))
