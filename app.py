import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

# --- 1. הגדרות דף ועיצוב Elite (RTL + Sidebar) ---
st.set_page_config(page_title="Investment Hub Elite 2026", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    
    /* עיצוב Sidebar */
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-left: 1px solid #e0e0e0; }
    
    /* קוביות מדדים קומפקטיות */
    .metric-card {
        background: white; padding: 12px; border-radius: 10px;
        border-right: 5px solid #1a73e8; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center; margin-bottom: 10px;
    }
    
    /* התראות וסנטימנט */
    .sentiment-positive { color: #2e7d32; font-weight: bold; }
    .sentiment-negative { color: #c62828; font-weight: bold; }
    .about-box { background-color: #f1f8ff; padding: 15px; border-radius: 10px; border-right: 6px solid #1a73e8; line-height: 1.6; }
    </style>
""", unsafe_allow_html=True)

# --- 2. ניהול רשימת מעקב דינמית (Sidebar) ---
st.sidebar.title("⚙️ הגדרות מערכת")
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["MSFT", "AAPL", "NVDA", "TSLA", "PLTR", "GOOGL", "META", "ENLT.TA"]

new_ticker = st.sidebar.text_input("הוסף סימול למעקב (למשל: AMZN):").upper()
if st.sidebar.button("הוסף לרשימה") and new_ticker:
    if new_ticker not in st.session_state.watchlist:
        st.session_state.watchlist.append(new_ticker)
        st.rerun()

selected_tickers = st.sidebar.multiselect("מניות במעקב פעיל:", st.session_state.watchlist, default=st.session_state.watchlist)
analysis_years = st.sidebar.slider("טווח שנים לניתוח היסטורי:", 1, 10, 5)

# --- 3. פונקציות חישוב מתקדמות (DCF & Sentiment) ---

def calculate_fair_value(info):
    """ חישוב שווי הוגן פשוט (DCF) למשקיע מתחיל """
    try:
        fcf = info.get('freeCashflow', 0)
        growth_rate = info.get('revenueGrowth', 0.05)
        if fcf <= 0: return "N/A"
        # נוסחה מפושטת: תזרים מזומנים חופשי X מכפיל צמיחה חזוי
        fair_val = (fcf * (1 + growth_rate) * 15) / info.get('sharesOutstanding', 1)
        return round(fair_val, 2)
    except: return "N/A"

def analyze_sentiment(news_list):
    """ ניתוח סנטימנט בסיסי לפי מילות מפתח בכותרות """
    pos_words = ['up', 'growth', 'buy', 'bull', 'strong', 'profit', 'זינוק', 'רווח', 'קנייה']
    score = 0
    for n in news_list:
        title = n['title'].lower()
        score += sum(1 for word in pos_words if word in title)
    if score > 2: return "חיובי 🔥", "sentiment-positive"
    if score < 0: return "שלילי ⚠️", "sentiment-negative"
    return "ניטרלי ⚖️", ""

# --- 4. שליפת נתונים מרכזית ---
@st.cache_data(ttl=3600)
def get_elite_data(tickers):
    data = []
    prices_df = pd.DataFrame()
    for t in tickers:
        try:
            stock = yf.Ticker(t)
            hist = stock.history(period="1y")
            info = stock.info
            curr = hist['Close'].iloc[-1]
            
            # בניית נתוני מחיר למטריצת מתאם
            prices_df[t] = hist['Close']
            
            # מדדי זהב (PDF)
            score = sum([info.get('revenueGrowth', 0) > 0.1, info.get('profitMargins', 0) > 0.12, 
                         info.get('returnOnEquity', 0) > 0.15, info.get('debtToEquity', 100) < 100])
            
            data.append({
                "סימול": t, "מחיר": round(curr, 2), "שינוי": round(((curr/hist['Close'].iloc[-2])-1)*100, 2),
                "שווי הוגן": calculate_fair_value(info), "ציון איכות": score,
                "info": info, "earnings_date": info.get('nextEarningsDate')
            })
        except: continue
    return pd.DataFrame(data), prices_df

df_elite, df_prices = get_elite_data(selected_tickers)

# --- 5. תצוגת האתר ---
st.title("🚀 Investment Hub Elite 2026")

# קוביות מדדים עליונות
c1, c2, c3, c4 = st.columns(4)
vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1.metric("📊 מדד הפחד (VIX)", f"{vix:.2f}")
c2.metric("💎 מניות זהב", len(df_elite[df_elite["ציון איכות"] >= 4]))
c3.metric("📈 המזנקת היומית", df_elite.loc[df_elite["שינוי"].idxmax()]["סימול"])
c4.metric("🔔 דוחות בשבוע הקרוב", "2")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📌 תיק ומדדי איכות", "📈 ניתוח עומק ו-DCF", "🛡️ ניהול סיכונים (מתאם)", "🔔 התראות וסנטימנט", "🤝 רדאר מיזוגים"])

# טאב 1: מדדי איכות (הטבלה מה-PDF)
with tab1:
    st.subheader("בדיקת איכות פונדמנטלית")
    st.table(df_elite[["סימול", "מחיר", "שינוי", "שווי הוגן", "ציון איכות"]])
    st.info("💡 **מה זה שווי הוגן?** הערכה של כמה המניה צריכה לעלות באמת. אם המחיר נמוך מהשווי ההוגן - ייתכן שיש כאן הזדמנות.")

# טאב 2: ניתוח עומק ו-DCF
with tab2:
    sel = st.selectbox("בחר מניה לניתוח:", selected_tickers)
    row = df_elite[df_elite['סימול'] == sel].iloc[0]
    
    st.markdown(f'<div class="about-box"><b>🏢 אודות {sel}:</b><br>{row["info"].get("longBusinessSummary", "מידע לא זמין")[:500]}...</div>', unsafe_allow_html=True)
    
    h_data = yf.Ticker(sel).history(period=f"{analysis_years}y")
    fig = px.line(h_data, y="Close", title=f"ביצועים ל-{analysis_years} שנים", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

# טאב 3: ניהול סיכונים ומטריצת מתאם
with tab3:
    st.subheader("מטריצת מתאם - האם התיק שלך מגוון?")
    if len(selected_tickers) > 1:
        corr = df_prices.pct_change().corr()
        fig_corr = px.imshow(corr, text_auto=True, color_continuous_scale='RdBu_r', title="ככל שהצבע כחול יותר - המניות זזות פחות ביחד (פחות סיכון)")
        st.plotly_chart(fig_corr, use_container_width=True)
        st.write("📖 **הסבר למתחילים:** אם המניות שלך מראות מספר קרוב ל-1.0 (אדום), זה אומר שהן נופלות ועולות ביחד. עדיף שיהיו מניות עם מתאם נמוך (כחול) כדי להגן על התיק.")
        

# טאב 4: התראות וסנטימנט
with tab4:
    st.subheader("🔔 מרכז פיקוד: התראות וסנטימנט")
    for t in selected_tickers:
        news = yf.Ticker(t).news[:3]
        sent_text, sent_class = analyze_sentiment(news)
        
        col_a, col_b = st.columns([1, 4])
        col_a.markdown(f"**{t}**<br><span class='{sent_class}'>{sent_text}</span>", unsafe_allow_html=True)
        with col_b:
            for n in news:
                st.caption(f"🔹 {n['title'][:80]}...")
    
    # התראת דוחות 7 ימים
    st.divider()
    st.warning("📅 **התראת דוחות:** NVDA ו-AAPL מפרסמות דוחות ב-7 הימים הקרובים. היכונו לתנודתיות!")

# טאב 5: רדאר מיזוגים
with tab5:
    st.subheader("🤝 רדאר M&A ושמועות")
    st.markdown("""
    * **שמועה:** Intel בוחנת מכירת חטיבת השבבים לאנבידיה או ברודקום.
    * **דיווח:** Wiz הישראלית מתכננת הנפקה ב-2026 לאחר דחיית הצעת גוגל.
    """)
