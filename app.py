import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. הגדרות דף ועיצוב דחוס (RTL) ---
st.set_page_config(page_title="Investment Hub PRO 2026", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    
    /* צמצום רווחים אגרסיבי */
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
    [data-testid="stMetric"] { background: white; padding: 10px; border-radius: 10px; border-right: 5px solid #1a73e8; }
    
    /* קופסאות מידע */
    .about-box { background-color: #f1f8ff; padding: 15px; border-radius: 10px; border-right: 6px solid #1a73e8; margin-bottom: 15px; line-height: 1.6; }
    .alert-card { padding: 12px; border-radius: 8px; margin-bottom: 8px; border-right: 5px solid; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .alert-green { background-color: #e8f5e9; border-color: #2e7d32; color: #1b5e20; }
    .alert-orange { background-color: #fff3e0; border-color: #ef6c00; color: #e65100; }
    
    /* תיקון טבלאות */
    [data-testid="stTable"] td, [data-testid="stTable"] th { padding: 4px 8px !important; font-size: 14px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. נתונים ואודות למתחילים ---
MY_STOCKS = ["MSFT", "AAPL", "NVDA", "TSLA", "PLTR", "MSTR", "GOOGL", "META", "ENLT.TA", "POLI.TA", "LUMI.TA"]
SCAN_CANDIDATES = ["AMZN", "AVGO", "COST", "MA", "V", "LLY", "TSM", "ADBE", "NFLX", "ORCL", "ASML", "SBUX", "AMD"]

ABOUT_GUIDE = {
    "MSFT": "מיקרוסופט היא ענקית התוכנה והענן. היא מרוויחה מכל מחשב בעולם (Windows) ומהבינה המלאכותית (ChatGPT). נחשבת למניה בטוחה ויציבה.",
    "NVDA": "אנבידיה מייצרת את ה'מוח' של הבינה המלאכותית. בלעדיה העולם הטכנולוגי לא יכול להתקדם. היא הצומחת ביותר כרגע.",
    "AAPL": "אפל היא מלכת המותג. היא בונה מוצרים שאנשים לא יכולים לעזוב (iPhone), מה שמייצר לה רווחים אדירים וקופת מזומנים ענקית.",
    "TSLA": "טסלה היא חברת טכנולוגיה במסווה של רכב. היא מהמרת על נהיגה אוטונומית ורובוטים, מה שהופך אותה להשקעה עם סיכון וסיכוי גבוה.",
    "ENLT.TA": "אנלייט היא חברה ישראלית שבונה חוות רוח ושדות סולאריים. היא נהנית מהמעבר העולמי לחשמל נקי וירוק."
}

HEBREW_FIN_MAP = {
    'Total Revenue': 'הכנסות כוללות',
    'Net Income': 'רווח נקי',
    'EBITDA': 'רווח תפעולי (EBITDA)',
    'Total Debt': 'חוב כולל',
    'Free Cash Flow': 'תזרים מזומנים חופשי'
}

# --- 3. פונקציות ליבה ---

@st.cache_data(ttl=3600)
def fetch_hub_data(tickers):
    rows = []
    for t in tickers:
        try:
            obj = yf.Ticker(t)
            hist = obj.history(period="5d")
            if hist.empty: continue
            info = obj.info
            curr, prev = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
            
            # קריטריונים לאיכות (מניית זהב)
            rev_g = info.get("revenueGrowth", 0) or 0
            earn_g = info.get("earningsGrowth", 0) or 0
            margin = info.get("profitMargins", 0) or 0
            roe = info.get("returnOnEquity", 0) or 0
            debt = info.get("debtToEquity", 150)
            
            score = sum([rev_g >= 0.1, earn_g >= 0.1, margin >= 0.12, roe >= 0.15, (debt < 100 and debt > 0)])
            
            rows.append({
                "סימול": t, "מחיר": round(curr, 2), "שינוי %": round(((curr/prev)-1)*100, 2),
                "צמיחה": f"{rev_g:.1%}", "שוליים": f"{margin:.1%}", "ROE": f"{roe:.1%}",
                "ציון (5)": score, "earnings_date": info.get('nextEarningsDate'),
                "זהב": "🏆" if score >= 4 else ""
            })
        except: continue
    return pd.DataFrame(rows)

def get_news_secure(ticker="", query=""):
    news = []
    q = query if query else f'"{ticker}" stock merger acquisition news'
    try:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=he&gl=IL&ceid=IL:he"
        import urllib.request, xml.etree.ElementTree as ET
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp:
            root = ET.fromstring(resp.read())
            for item in root.findall(".//item")[:5]:
                news.append({"title": item.find("title").text, "link": item.find("link").text})
    except: pass
    return news

# --- 4. בניית הממשק ---

st.title("Investment Hub PRO 2026 🚀")

all_tickers = list(set(MY_STOCKS + SCAN_CANDIDATES))
df_data = fetch_hub_data(all_tickers)

# דשבורד עליון - הקוביות חזרו!
vix_px = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1, c2, c3, c4 = st.columns(4)
c1.metric("📊 מדד הפחד (VIX)", f"{vix_px:.2f}", delta_color="inverse")
c2.metric("🏆 מניות זהב", len(df_data[df_data["זהב"] == "🏆"]))
c3.metric("🔥 הזינוק היומי", df_data.loc[df_data["שינוי %"].idxmax()]["סימול"], f"{df_data['שינוי %'].max()}%")
c4.metric("📅 עדכון אחרון", datetime.now().strftime("%H:%M"))

tab_my, tab_scan, tab_rep, tab_alerts, tab_merger = st.tabs(["📌 המניות שלי", "🔍 סורק זהב", "📄 דוח חברה ואודות", "🔔 התראות חכמות", "🤝 רדאר מיזוגים"])

# --- טאב 1: המניות שלי ---
with tab_my:
    my_df = df_data[df_data['סימול'].isin(MY_STOCKS)]
    st.table(my_df.drop(columns=["earnings_date", "זהב"]))

# --- טאב 2: סורק זהב (מתוקן - לא ריק!) ---
with tab_scan:
    scan_df = df_data[df_data['סימול'].isin(SCAN_CANDIDATES)].sort_values(by="ציון (5)", ascending=False)
    st.table(scan_df.drop(columns=["earnings_date"]))

# --- טאב 3: דוח חברה, אודות וניתוח 10 שנים ---
with tab_rep:
    sel = st.selectbox("בחר מניה לניתוח עמוק:", all_tickers)
    st.markdown(f'<div class="about-box"><b>🏢 אודות {sel} (למשקיע המתחיל):</b><br>{ABOUT_GUIDE.get(sel, "חברה מובילה בסקטור שלה, נסחרת במדדי המפתח ומהווה חלק מרשימת המעקב.")}</div>', unsafe_allow_html=True)
    
    st.divider()
    years_sel = st.slider("בחר טווח שנים לניתוח היסטורי:", 1, 10, 5)
    
    col_g, col_f = st.columns([2, 1])
    obj_sel = yf.Ticker(sel)
    
    with col_g:
        hist_10 = obj_sel.history(period=f"{years_sel}y")
        fig = go.Figure(go.Scatter(x=hist_10.index, y=hist_10['Close'], line=dict(color='#1a73e8')))
        fig.update_layout(height=350, title=f"ביצועי מניית {sel} - {years_sel} שנים", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
        
    with col_f:
        st.write("📈 **נתונים פיננסיים (עברית)**")
        fin = obj_sel.financials
        if not fin.empty:
            df_fin = fin.loc[fin.index.isin(HEBREW_FIN_MAP.keys())].rename(index=HEBREW_FIN_MAP)
            st.dataframe(df_fin.applymap(lambda x: f"${x/1e9:.1f}B" if x > 1e6 else x), use_container_width=True)

# --- טאב 4: התראות חכמות (דוחות וזינוקים) ---
with tab_alerts:
    st.subheader("🔔 מרכז התראות בזמן אמת")
    
    # התראת דוחות - שבוע מראש
    found_e = False
    for _, row in df_data.iterrows():
        if row['earnings_date']:
            e_dt = datetime.fromtimestamp(row['earnings_date'])
            days_to = (e_dt - datetime.now()).days
            if 0 <= days_to <= 7:
                st.markdown(f'<div class="alert-card alert-orange">📅 <b>{row["סימול"]}</b>: מפרסמת דוחות בעוד {days_to} ימים ({e_dt.strftime("%d/%m")})</div>', unsafe_allow_html=True)
                found_e = True
    if not found_e: st.write("אין דוחות צפויים בשבוע הקרוב.")
    
    st.divider()
    
    # התראת זינוקים/נפילות
    for _, row in df_data.iterrows():
        if row['שינוי %'] >= 3.0:
            st.markdown(f'<div class="alert-card alert-green">🚀 <b>{row["סימול"]}</b> מזנקת ב-{row["שינוי %"]}% היום!</div>', unsafe_allow_html=True)

# --- טאב 5: רדאר מיזוגים ושמועות ---
with tab_merger:
    st.subheader("🤝 רדאר מיזוגים (M&A) ושמועות")
    m_news = get_news_secure(query="merger acquisition stock rumors speculation")
    for n in m_news:
        st.markdown(f"🔹 **[{n['title']}]({n['link']})**")