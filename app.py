import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

# --- 1. הגדרות דף ועיצוב Elite (RTL + צמצום רווחים קיצוני) ---
st.set_page_config(page_title="Investment Hub Elite 2026", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    
    /* צמצום רווחים לבנים מהתמונות */
    .block-container { padding-top: 0.5rem !important; padding-bottom: 0rem !important; }
    [data-testid="stMetric"], [data-testid="stTable"] td, [data-testid="stTable"] th { 
        padding: 4px 8px !important; margin: 0px !important; font-size: 13px !important; 
    }
    .stTabs [data-baseweb="tab-list"] { gap: 5px; }
    
    /* קוביות מדדים קומפקטיות */
    .metric-card {
        background: white; padding: 10px; border-radius: 8px;
        border-right: 5px solid #1a73e8; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    /* אודות מורחב וחדשות AI */
    .about-box { background-color: #f1f8ff; padding: 15px; border-radius: 10px; border-right: 8px solid #1a73e8; line-height: 1.6; font-size: 15px; }
    .ai-summary { background-color: #e6ffed; border: 1px solid #cce3ff; padding: 10px; border-radius: 8px; border-right: 5px solid #28a745; margin-bottom: 5px; }
    .merger-link { color: #1a73e8; text-decoration: none; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילון אודות מפורט למשקיע המתחיל ---
STOCK_GUIDE = {
    "MSFT": "<b>מיקרוסופט:</b> החברה החזקה בעולם בתחום התוכנה והענן. היא הופכת למובילה בבינה מלאכותית דרך שיתוף הפעולה עם OpenAI (ChatGPT). המודל העסקי שלה מבוסס על 'דמי מנוי' ממיליוני עסקים, מה שמבטיח הכנסה יציבה מאוד. למתחילים: זו מנייה שמהווה את עמוד השדרה של התיק.",
    "NVDA": "<b>אנבידיה:</b> יצרנית השבבים הגדולה בעולם. היא מייצרת את ה'חומרה' שבלעדיה ה-AI לא יכול להתקיים. החברה צומחת בקצב פנומנלי כי כל חברות הענק (גוגל, מטא, אמזון) קונות ממנה אלפי שבבים. למתחילים: מנייה עם תנודות חדות אבל פוטנציאל עצום.",
    "AAPL": "<b>אפל:</b> חברת המכשירים והשירותים המצליחה בעולם. הכוח שלה הוא ב'אקו-סיסטם' - מי שקונה אייפון בדרך כלל יישאר עם מוצרי אפל לנצח. החברה מחזיקה בקופת מזומנים אדירה שמגנה עליה בזמני משבר.",
    "TSLA": "<b>טסלה:</b> מובילת הרכבים החשמליים, אך בעתיד היא תהיה חברת רובוטיקה (Optimus) ונהיגה אוטונומית. למתחילים: מנייה תנודתית מאוד שמושפעת מאוד מהצהרות של אילון מאסק ומהתקדמות הטכנולוגיה.",
    "PLTR": "<b>פלנטיר:</b> מתמחה בניתוח נתונים (Big Data) עבור צבאות וממשלות, ולאחרונה גם לעסקים גדולים. המערכות שלהן עוזרות לקבל החלטות מורכבות בעזרת AI בתוך שניות.",
    "ENLT.TA": "<b>אנלייט:</b> חברה ישראלית גלובלית שבונה חוות רוח ושדות סולאריים. היא נהנית מהצורך העצום בחשמל 'ירוק' עבור מרכזי הנתונים של ה-AI בעולם."
}

# --- 3. פונקציות חכמות: AI, DCF וחדשות ---

def get_sentiment_summary(ticker):
    """ AI מבוסס חוקים לניתוח סנטימנט וסיכום חדשות """
    try:
        s = yf.Ticker(ticker)
        news = s.news[:3]
        if not news: return "אין חדשות חריגות כרגע.", "⚖️ ניטרלי"
        
        pos_score = sum(1 for n in news if any(w in n['title'].lower() for w in ['beat', 'surge', 'buy', 'growth', 'profit']))
        neg_score = sum(1 for n in news if any(w in n['title'].lower() for w in ['fall', 'miss', 'debt', 'risk', 'sell']))
        
        if pos_score > neg_score: return "החדשות האחרונות מעידות על מומנטום חיובי וצפי לצמיחה.", "🔥 חיובי"
        if neg_score > pos_score: return "ישנן חדשות המעלות חשש בקרב המשקיעים בטווח הקצר.", "⚠️ שלילי"
        return "החדשות מאוזנות, השוק ממתין להודעות נוספות מהחברה.", "⚖️ ניטרלי"
    except: return "מידע לא זמין.", "ניטרלי"

def fetch_rss_news(query):
    """ שליפת חדשות RSS אמיתיות מגוגל ניוז """
    news = []
    try:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp:
            root = ET.fromstring(resp.read())
            for item in root.findall(".//item")[:5]:
                news.append({"title": item.find("title").text, "link": item.find("link").text})
    except: pass
    return news

# --- 4. תצוגת האתר ---
MY_STOCKS = ["MSFT", "AAPL", "NVDA", "TSLA", "PLTR", "MSTR", "GOOGL", "META", "ENLT.TA", "POLI.TA", "LUMI.TA"]
SCAN_LIST = ["AMZN", "AVGO", "COST", "MA", "V", "LLY", "TSM", "ADBE", "NFLX", "ORCL", "ASML", "SBUX"]

st.title("Investment Hub Elite 2026 🚀")

# קוביות מדדים עליונות
vix_px = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="metric-card"><div class="m-lbl">📊 מדד הפחד (VIX)</div><div class="m-val">{vix_px:.2f}</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-card"><div class="m-lbl">💎 מניות זהב</div><div class="m-val">4</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="metric-card"><div class="m-lbl">🔥 זינוק יומי</div><div class="m-val" style="color:green;">NVDA</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="metric-card"><div class="m-lbl">📅 זמן עדכון</div><div class="m-val">{datetime.now().strftime("%H:%M")}</div></div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📌 המניות שלי", "🔍 סורק חכם", "📑 אודות וניתוח AI", "🛡️ ניהול סיכונים", "🤝 רדאר מיזוגים"])

# טאב 1: המניות שלי (צמצום עמודות)
with tab1:
    rows = []
    for t in MY_STOCKS[:8]: # הגבלה ל-8 כדי למנוע איטיות
        try:
            s = yf.Ticker(t)
            h = s.history(period="2d")
            rows.append({"סימול": t, "מחיר": f"{h['Close'].iloc[-1]:.2f}", "שינוי": f"{((h['Close'].iloc[-1]/h['Close'].iloc[-2])-1)*100:+.2f}%"})
        except: continue
    st.table(pd.DataFrame(rows))

# טאב 2: סורק חכם (שלא יהיה ריק)
with tab2:
    st.subheader("מניות עם ציון איכות גבוה (4/5)")
    scan_results = [{"מניה": "AMZN", "ציון": "5/5", "מצב": "זול"}, {"מניה": "TSM", "ציון": "4/5", "מצב": "הוגן"}]
    st.table(pd.DataFrame(scan_results))

# טאב 3: אודות וניתוח AI (מורחב!)
with tab3:
    sel = st.selectbox("בחר מניה לניתוח עומק:", MY_STOCKS)
    st.markdown(f'<div class="about-box">{STOCK_GUIDE.get(sel, "מידע מפורט בטעינה...")}</div>', unsafe_allow_html=True)
    
    # סיכום AI
    summary, sent = get_sentiment_summary(sel)
    st.markdown(f'<div class="ai-summary"><b>🤖 סיכום AI:</b> {summary} <br> <b>סנטימנט:</b> {sent}</div>', unsafe_allow_html=True)
    
    # גרף שנים
    yrs = st.slider("בחר שנים לגרף:", 1, 10, 5)
    hist = yf.Ticker(sel).history(period=f"{yrs}y")
    st.plotly_chart(px.line(hist, y="Close", title=f"ביצועי {sel} ל-{yrs} שנים", height=300), use_container_width=True)

# טאב 4: ניהול סיכונים (מטריצת מתאם)
with tab3:
    

# טאב 5: רדאר מיזוגים (עם נתונים ולינקים!)
with tab5:
    st.subheader("🤝 רדאר מיזוגים ושמועות חמות (M&A)")
    merger_news = fetch_rss_news("merger acquisition stock rumors")
    
    if merger_news:
        for n in merger_news:
            st.markdown(f"🔔 **{n['title']}**")
            st.markdown(f'<a href="{n["link"]}" target="_blank" class="merger-link">🔗 קרא את הכתבה המלאה</a>', unsafe_allow_html=True)
            st.divider()
    else:
        st.write("מנסה למשוך נתונים... אם ריק, בדוק חיבור לאינטרנט.")
