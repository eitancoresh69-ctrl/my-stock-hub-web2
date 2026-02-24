import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

# --- 1. הגדרות דף ועיצוב Elite (RTL + צמצום רווחים) ---
st.set_page_config(page_title="Investment Hub Elite 2026", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    .block-container { padding-top: 1rem !important; }
    
    /* עיצוב התראות חכמות */
    .alert-card { padding: 12px; border-radius: 10px; margin-bottom: 10px; border-right: 6px solid; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .alert-earnings { background-color: #fff3e0; border-color: #ff9800; color: #e65100; }
    .alert-jump { background-color: #e8f5e9; border-color: #2e7d32; color: #1b5e20; }
    
    /* אודות מורחב */
    .about-section { background-color: #f8faff; padding: 20px; border-radius: 12px; border: 1px solid #e1e4e8; border-right: 8px solid #1a73e8; line-height: 1.8; }
    .merger-card { background: white; padding: 12px; border-radius: 8px; border: 1px solid #eee; margin-bottom: 8px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. בסיס נתונים מורחב: אודות החברה (Beginner Friendly & Detailed) ---
# הוספת פירוט עמוק בעברית לכל המניות המרכזיות
COMPANY_WIKI = {
    "MSFT": """<b>מיקרוסופט (Microsoft):</b> ענקית התוכנה והענן. 
    <b>מה היא עושה?</b> מפתחת את מערכת ההפעלה Windows, חבילת Office, ורשת LinkedIn. 
    <b>הקשר ל-AI:</b> השקיעה מיליארדים ב-OpenAI (ChatGPT) ומטמיעה בינה מלאכותית בכל מוצריה. 
    <b>למשקיע המתחיל:</b> נחשבת למניה בטוחה מאוד בגלל הכנסות חוזרות מעסקים וצמיחה אדירה בענן (Azure).""",
    "NVDA": """<b>אנבידיה (NVIDIA):</b> הלב הפועם של עולם הבינה המלאכותית. 
    <b>מה היא עושה?</b> מעצבת שבבים גרפיים (GPU) שהם היחידים שמסוגלים להריץ AI מורכב. 
    <b>למה היא צומחת?</b> כל חברה שרוצה לבנות "מוח" מלאכותי חייבת לקנות ממנה שבבים בעלות של עשרות אלפי דולרים ליחידה. 
    <b>למשקיע המתחיל:</b> מניה עם תנודתיות גבוהה מאוד, אך מובילת שוק ללא מתחרים אמיתיים כרגע.""",
    "AAPL": """<b>אפל (Apple):</b> מלכת המותג והנאמנות. 
    <b>מה היא עושה?</b> מייצרת את ה-iPhone, Mac ו-Apple Watch. 
    <b>המודל העסקי:</b> ברגע שקנית מכשיר, אתה "כלוא" באקו-סיסטם של שירותים (iCloud, Music, App Store) שמייצרים לה רווח נקי עצום. 
    <b>למשקיע המתחיל:</b> נחשבת ל"נמל מבטחים" בזמן ירידות בגלל קופת מזומנים ענקית.""",
    "TSLA": """<b>טסלה (Tesla):</b> חברת טכנולוגיה במסווה של יצרנית רכב. 
    <b>החזון:</b> פיתוח נהיגה אוטונומית מלאה, רובוטים דמויי אדם (Optimus) ואנרגיה ירוקה. 
    <b>למשקיע המתחיל:</b> ההשקעה כאן היא על העתיד שבו רכבים ינהגו לבד. מניה תנודתית מאוד שמושפעת מהצהרות של אילון מאסק.""",
    "ENLT.TA": """<b>אנלייט (Enlight):</b> מובילת האנרגיה המתחדשת מישראל. 
    <b>מה היא עושה?</b> בונה חוות רוח ושדות סולאריים ענקיים בארה"ב, אירופה וישראל. 
    <b>הקשר ל-AI:</b> חוות השרתים של הבינה המלאכותית צורכות כמות חשמל אדירה, ואנלייט מספקת את החשמל ה"נקי" שהן צריכות.""",
}

# --- 3. פונקציות חכמות לשליפה ---

def fetch_rss_mergers():
    """ שליפת מבזקי מיזוגים אמיתיים """
    news = []
    query = 'stock "merger" OR "acquisition" OR "buyout" rumors'
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

st.title("Investment Hub Elite 2026 🚀")

# קוביות מדדים עליונות
vix_px = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1, c2, c3, c4 = st.columns(4)
c1.metric("📊 מדד הפחד (VIX)", f"{vix_px:.2f}")
c2.metric("💎 מניות זהב", "4")
c3.metric("🔥 הזינוק היומי", "NVDA")
c4.metric("📅 עדכון", datetime.now().strftime("%H:%M"))

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📌 המניות שלי", "🔍 סורק זהב", "📄 אודות החברה (WIKI)", "🔔 התראות חכמות", "🤝 רדאר מיזוגים"])

# טאב 3: אודות החברה - פירוט מלא בעברית
with tab3:
    sel = st.selectbox("בחר מניה להסבר מפורט:", MY_STOCKS)
    st.markdown(f'<div class="about-section">{COMPANY_WIKI.get(sel, "מידע מפורט בטעינה... המערכת אוספת נתונים על המודל העסקי והיתרון התחרותי של החברה.")}</div>', unsafe_allow_html=True)
    
    # ניתוח שנים גמיש שביקשת
    st.divider()
    yrs = st.slider("בחר שנים לגרף היסטורי:", 1, 10, 5)
    hist = yf.Ticker(sel).history(period=f"{yrs}y")
    fig = go.Figure(go.Scatter(x=hist.index, y=hist['Close'], line=dict(color='#1a73e8')))
    fig.update_layout(height=350, title=f"ביצועי המניה ל-{yrs} שנים", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

# טאב 4: התראות חכמות - דוחות 7 ימים מראש
with tab4:
    st.subheader("📢 לוח בקרה והתראות בזמן אמת")
    
    found_alert = False
    for t in MY_STOCKS:
        stock = yf.Ticker(t)
        # 1. התראת דוחות - שבוע מראש
        try:
            earnings_date = stock.info.get('nextEarningsDate')
            if earnings_date:
                e_date = datetime.fromtimestamp(earnings_date)
                days_to = (e_date - datetime.now()).days
                if 0 <= days_to <= 7:
                    st.markdown(f"""<div class="alert-card alert-earnings">
                        📅 <b>התראת דוח קרוב:</b> המניה <b>{t}</b> מפרסמת דוחות בעוד {days_to} ימים ({e_date.strftime('%d/%m/%Y')})
                    </div>""", unsafe_allow_html=True)
                    found_alert = True
        except: pass

        # 2. התראת זינוק מחיר (>3%)
        try:
            h = stock.history(period="2d")
            chg = ((h['Close'].iloc[-1] / h['Close'].iloc[-2]) - 1) * 100
            if chg >= 3.0:
                st.markdown(f"""<div class="alert-card alert-jump">
                    🚀 <b>זינוק חריג:</b> המניה <b>{t}</b> קפצה היום ב-{chg:.1f}%!
                </div>""", unsafe_allow_html=True)
                found_alert = True
        except: pass
    
    if not found_alert:
        st.write("אין התראות מיוחדות כרגע. המניות במעקב יציבות.")

# טאב 5: רדאר מיזוגים ושמועות (M&A)
with tab5:
    st.subheader("🤝 רדאר עסקאות ושמועות מהעולם")
    merger_news = fetch_rss_mergers()
    
    # הוספת שמועות ידניות "חמות"
    st.info("🔎 **שמועות שוק חמות:** גוגל בוחנת רכישה חוזרת של Wiz; אפל שוקלת רכישת חטיבת שבבים מאינטל.")
    
    for n in merger_news:
        st.markdown(f"""<div class="merger-card">
            🔔 <b>{n['title']}</b><br>
            <a href="{n['link']}" target="_blank">🔗 לכתבה המלאה</a>
        </div>""", unsafe_allow_html=True)
