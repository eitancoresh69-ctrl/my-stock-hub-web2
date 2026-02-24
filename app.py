import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import urllib.parse

# --- 1. הגדרות דף ועיצוב (RTL מלא, ללא סרגל צד, צמצום רווחים) ---
st.set_page_config(page_title="Investment Hub Ultimate 2026", layout="wide", initial_sidebar_state="collapsed")

# מנגנון ריענון אוטומטי (15 דקות)
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 900:
    st.session_state.last_refresh = time.time()
    st.rerun()

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    .block-container { padding-top: 1rem !important; }
    
    /* עיצוב כרטיסי מודיעין AI */
    .ai-card { background: white; padding: 12px; border-radius: 10px; border-right: 6px solid #1a73e8; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 10px; }
    .bull-box { background-color: #e8f5e9; border-color: #2e7d32; color: #1b5e20; padding: 10px; border-radius: 8px; border-right: 5px solid; }
    .bear-box { background-color: #ffeef0; border-color: #d73a49; color: #b71c1c; padding: 10px; border-radius: 8px; border-right: 5px solid; }
    
    /* צמצום רווחים בטבלאות */
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th { padding: 3px 8px !important; font-size: 13px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילון בועות הסבר (Tooltips) בעברית ---
GLOSSARY = {
    "price": "המחיר הנוכחי: $ לארה\"ב או אג' לישראל.",
    "score": "ציון 0-6 לפי ה-PDF: צמיחה (מכירות/רווח), שוליים, ROE, ומזומן מול חוב.",
    "pl": "רווח או הפסד כספי נומינלי מההשקעה שלך.",
    "yield": "השינוי באחוזים ממחיר הקנייה המקורי.",
    "ai_rec": "המלצת AI מפורטת המשלבת את איכות החברה מול תמחור השוק.",
    "div": "דיבידנד שנתי באחוזים.",
    "ex_date": "תאריך אקס: היום האחרון לקניית המניה כדי לקבל את הדיבידנד הקרוב."
}

# --- 3. פונקציות ליבה (PDF Logic & AI Recommendation) ---

def evaluate_by_pdf(info):
    """ חישוב ציון לפי 6 הקריטריונים מהמדריך """
    score = 0
    try:
        rev_g = info.get('revenueGrowth', 0) or 0
        earn_g = info.get('earningsGrowth', 0) or 0
        margin = info.get('profitMargins', 0) or 0
        roe = info.get('returnOnEquity', 0) or 0
        cash = info.get('totalCash', 0) or 0
        debt = info.get('totalDebt', 0) or 1
        
        if rev_g >= 0.10: score += 1      # 1. צמיחת מכירות
        if earn_g >= 0.10: score += 1     # 2. צמיחת רווחים
        if margin >= 0.10: score += 1     # 3. שולי רווח
        if roe >= 0.15: score += 1        # 4. תשואה על ההון
        if cash > debt: score += 1        # 5. מזומן מול חוב
        if debt == 0: score += 1          # 6. חוב אפס
    except: pass
    return score

def get_ai_action_logic(px, fv, score, ticker):
    """ לוגיקת המלצה מפורטת מבוססת AI """
    if not fv or fv == 0: return "בבדיקה 🔍", "אין מספיק נתונים לחישוב שווי הוגן."
    
    gap = (fv - px) / px
    if score >= 5:
        if gap > 0.05: return "קנייה חזקה 💎", f"מניית 'זהב' (ציון {score}). נסחרת ב-{(gap*100):.0f}% מתחת לשווי ההוגן."
        return "קנייה 📈", f"חברה איכותית מאוד. מחיר השוק הוגן ביחס לצמיחה."
    elif score >= 3:
        if gap > 0.10: return "איסוף 🛒", f"חברה טובה במחיר 'מבצע'. פוטנציאל תשואה גבוה."
        return "החזק ⚖️", "החברה יציבה אך המחיר משקף את השווי האמיתי."
    else:
        if gap < -0.10: return "מכירה 🔴", "ציון איכות נמוך ותמחור יקר מדי. סיכון גבוה."
        return "המתנה 🕒", "מניה תנודתית עם נתוני איכות בינוניים."

# --- 4. שליפת נתונים מרכזית ---
MY_STOCKS_LIST = ["MSFT", "AAPL", "NVDA", "TSLA", "PLTR", "ENLT.TA", "POLI.TA", "LUMI.TA"]
SCAN_LIST = ["AMZN", "AVGO", "META", "GOOGL", "LLY", "TSM", "COST", "V", "ADBE", "NFLX", "AMD", "MSTR"]

@st.cache_data(ttl=600)
def fetch_hub_data(tickers):
    rows = []
    for t in tickers:
        try:
            s = yf.Ticker(t)
            inf = s.info
            h = s.history(period="2d")
            if h.empty: continue
            px = h['Close'].iloc[-1]
            
            # חישובים
            score = evaluate_by_pdf(inf)
            fcf = inf.get('freeCashflow', 0) or 0
            shares = inf.get('sharesOutstanding', 1)
            fv = (fcf * 15) / shares if fcf > 0 else 0
            
            action, reason = get_ai_action_logic(px, fv, score, t)
            
            rows.append({
                "Symbol": t, "Price": px, "Change": ((px / h['Close'].iloc[-2]) - 1) * 100,
                "Score": score, "FairValue": fv, "Action": action, "AI_Reason": reason,
                "DivYield": inf.get('dividendYield', 0), 
                "ExDate": inf.get('exDividendDate'),
                "RevenueGrowth": inf.get('revenueGrowth', 0), "Info": inf
            })
        except: continue
    return pd.DataFrame(rows)

df_all = fetch_hub_data(list(set(MY_STOCKS_LIST + SCAN_LIST)))

# --- 5. ממשק המשתמש ---
st.title("🚀 Investment Hub Ultimate AI 2026")

# מדדים עליונים
c1, c2, c3, c4 = st.columns(4)
vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1.metric("📊 מדד הפחד (VIX)", f"{vix:.2f}")
c2.metric("🏆 מניות זהב (5-6)", len(df_all[df_all["Score"] >= 5]))
c3.metric("🔥 הזינוק היומי", df_all.loc[df_all["Change"].idxmax()]["Symbol"] if not df_all.empty else "N/A")
c4.metric("🕒 עדכון אוטומטי", datetime.now().strftime("%H:%M"))

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📌 המניות שלי (P/L)", "🔍 סורק מניות זהב", "💰 דיבידנדים", "📄 דוח וניתוח (10 שנים)", "🤝 רדאר מיזוגים"])

# טאב 1: המניות שלי עם רווח והפסד והמלצה מפורטת
with tab1:
    st.subheader("ניהול תיק וניתוח AI לפעולה")
    if 'portfolio' not in st.session_state:
        # הוספה אוטומטית של מניות זהב מהסורק
        gold_stocks = df_all[df_all['Score'] >= 5]['Symbol'].tolist()
        initial_list = list(set(MY_STOCKS_LIST + gold_stocks))
        st.session_state.portfolio = pd.DataFrame([{"Symbol": t, "BuyPrice": 0.0, "Qty": 0} for t in initial_list])

    edited_df = st.data_editor(st.session_state.portfolio, num_rows="dynamic")
    st.session_state.portfolio = edited_df

    if not edited_df.empty:
        merged = pd.merge(edited_df, df_all[['Symbol', 'Price', 'Change', 'Score', 'Action', 'AI_Reason']], on="Symbol")
        merged['P_L'] = (merged['Price'] - merged['BuyPrice']) * merged['Qty']
        merged['Yield_Pct'] = ((merged['Price'] / merged['BuyPrice']) - 1) * 100
        
        st.dataframe(
            merged[["Symbol", "Price", "Change", "P_L", "Yield_Pct", "Score", "Action", "AI_Reason"]],
            column_config={
                "Price": st.column_config.NumberColumn("מחיר", help=GLOSSARY["price"]),
                "P_L": st.column_config.NumberColumn("רווח/הפסד כספי", help=GLOSSARY["pl"], format="%.2f"),
                "Yield_Pct": st.column_config.NumberColumn("תשואה %", help=GLOSSARY["yield"], format="%.1f%%"),
                "Score": st.column_config.NumberColumn("⭐ ציון (PDF)", help=GLOSSARY["score"]),
                "Action": st.column_config.TextColumn("המלצה", help=GLOSSARY["ai_rec"]),
                "AI_Reason": st.column_config.TextColumn("הסבר AI מפורט")
            },
            use_container_width=True, hide_index=True
        )

# טאב 2: סורק מניות זהב (PDF BASED)
with tab2:
    st.subheader("🔍 סורק הזדמנויות: מניות שעומדות בקריטריונים מה-PDF")
    scanner_results = df_all[df_all['Score'] >= 4].sort_values(by="Score", ascending=False)
    st.dataframe(
        scanner_results[["Symbol", "Price", "Score", "RevenueGrowth", "Action", "AI_Reason"]],
        column_config={
            "Score": st.column_config.NumberColumn("ציון איכות", help=GLOSSARY["score"]),
            "RevenueGrowth": st.column_config.NumberColumn("צמיחה", format="%.1%"),
            "Action": st.column_config.TextColumn("המלצה")
        },
        use_container_width=True, hide_index=True
    )

# טאב 3: דיבידנדים
with tab3:
    st.subheader("💰 לוח תזרים מזומנים (דיבידנדים)")
    div_df = df_all[df_all['DivYield'] > 0].sort_values(by="DivYield", ascending=False)
    div_df['ExDateClean'] = div_df['ExDate'].apply(lambda x: datetime.fromtimestamp(x).strftime('%d/%m/%Y') if x else "N/A")
    
    st.dataframe(
        div_df[["Symbol", "Price", "DivYield", "ExDateClean"]],
        column_config={
            "DivYield": st.column_config.NumberColumn("תשואת דיבידנד", format="%.2%", help=GLOSSARY["div"]),
            "ExDateClean": st.column_config.TextColumn("תאריך אקס", help=GLOSSARY["ex_date"])
        },
        use_container_width=True, hide_index=True
    )

# טאב 4: דוח ואודות (10 שנים)
with tab4:
    sel = st.selectbox("בחר מניה לניתוח 10 שנים:", df_all['Symbol'].unique())
    row = df_all[df_all['Symbol'] == sel].iloc[0]
    
    st.markdown(f'<div class="ai-card"><b>🏢 אודות {sel}:</b><br>{row["Info"].get("longBusinessSummary", "מידע בטעינה...")[:800]}</div>', unsafe_allow_html=True)
    
    c_bull, c_bear = st.columns(2)
    with c_bull:
        st.markdown(f'<div class="bull-box"><b>🐂 תרחיש השור (Bull):</b> צמיחה של {row["RevenueGrowth"]:.1%} ומובילות שוק.</div>', unsafe_allow_html=True)
    with c_bear:
        st.markdown(f'<div class="bear-box"><b>🐻 תרחיש הדוב (Bear):</b> סיכון תנודתיות ותמחור גבוה מהממוצע.</div>', unsafe_allow_html=True)

    yrs = st.slider("טווח שנים לגרף:", 1, 10, 5)
    hist = yf.Ticker(sel).history(period=f"{yrs}y")
    fig = go.Figure(go.Scatter(x=hist.index, y=hist['Close'], line=dict(color='#1a73e8', width=2), fill='tozeroy'))
    fig.update_layout(title=f"ביצועי מניית {sel} ל-{yrs} שנים", height=350, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

# טאב 5: רדאר מיזוגים
with tab5:
    st.subheader("🤝 רדאר M&A ושמועות שוק")
    mergers = [
        {"חברה": "Wiz / Google", "נושא": "מיזוג סייבר ענק", "סבירות": "75%", "לינק": "https://www.google.com/search?q=Wiz+Google+merger"},
        {"חברה": "Intel / Qualcomm", "נושא": "ספקולציות רכישה", "סבירות": "40%", "לינק": "https://www.google.com/search?q=Intel+acquisition+rumors"}
    ]
    for m in mergers:
        st.markdown(f"""
        <div class="ai-card">
            <b>{m['חברה']}</b> | {m['נושא']} | סבירות AI: {m['סבירות']}<br>
            <a href="{m['לינק']}" target="_blank" style="color:#1a73e8;">🔗 לכתבות האחרונות ב-Bloomberg/Reuters</a>
        </div>
        """, unsafe_allow_html=True)
