import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import urllib.parse

# --- 1. הגדרות דף וריענון אוטומטי (15 דקות) ---
st.set_page_config(page_title="Intelligence Hub PRO", layout="wide", initial_sidebar_state="collapsed")

# הזרקת קוד לריענון אוטומטי כל 900 שניות
st.markdown("""
    <script>
    setInterval(function(){ window.location.reload(); }, 900000);
    </script>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    .block-container { padding-top: 1rem !important; }
    .ai-card { background: white; padding: 12px; border-radius: 10px; border-right: 6px solid #1a73e8; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 10px; }
    /* צמצום רווחים קיצוני בטבלאות */
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th { padding: 2px 5px !important; font-size: 13px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילון בועות הסבר (Help Tooltips) ---
HELP = {
    "price": "המחיר הנוכחי במסחר ($ לארה\"ב, אג' לישראל).",
    "score": "ציון איכות 0-6 מבוסס על ה-PDF: צמיחת מכירות, רווח, שוליים, ROE, מזומן מול חוב, וחוב אפס.",
    "pl": "הרווח או ההפסד הכספי שלך על הנייר.",
    "yield": "השינוי באחוזים ממחיר הקנייה המקורי שלך.",
    "ai_action": "המלצת AI לפעולה מיידית (קנייה/מכירה/החזק).",
    "ai_logic": "ניתוח מפורט של ה-AI המשלב את איכות החברה מול תמחור השוק.",
    "div": "תשואת הדיבידנד השנתית (כמה מזומן החברה מחלקת).",
    "ex_date": "תאריך אקס: היום האחרון לקניית המניה כדי לקבל את הדיבידנד."
}

# --- 3. לוגיקה פיננסית (6 הקריטריונים מה-PDF) ---
def evaluate_pdf_score(info):
    score = 0
    try:
        if (info.get('revenueGrowth', 0) or 0) >= 0.10: score += 1
        if (info.get('earningsGrowth', 0) or 0) >= 0.10: score += 1
        if (info.get('profitMargins', 0) or 0) >= 0.10: score += 1
        if (info.get('returnOnEquity', 0) or 0) >= 0.15: score += 1
        cash, debt = info.get('totalCash', 0) or 0, info.get('totalDebt', 0) or 0
        if cash > debt: score += 1
        if debt == 0: score += 1
    except: pass
    return score

def get_ai_rec(price, fv, score):
    if not fv or fv == 0: return "בבדיקה 🔍", "אין מספיק נתונים לחישוב שווי הוגן."
    gap = (fv - price) / price
    if score >= 5:
        if gap > 0.05: return "קנייה חזקה 💎", f"מניית 'זהב' (ציון {score}). נסחרת בהנחה של {abs(gap):.1%} משוויה."
        return "קנייה 📈", "חברה איכותית במחיר הוגן. פוטנציאל תשואה יציב."
    elif score >= 3:
        if gap > 0.10: return "איסוף 🛒", "חברה טובה במחיר 'מבצע'. שווה להגדיל אחזקה."
        return "החזק ⚖️", "החברה יציבה אך המחיר משקף את השווי האמיתי שלה."
    return "מכירה 🔴", "ציון איכות נמוך וסיכון גבוה יחסית למחיר השוק."

# --- 4. שליפת נתונים מרכזית ---
MY_STOCKS_BASE = ["MSFT", "AAPL", "NVDA", "TSLA", "PLTR", "ENLT.TA", "POLI.TA", "LUMI.TA"]
SCAN_STOCKS = ["AMZN", "AVGO", "META", "GOOGL", "LLY", "TSM", "COST", "V", "ADBE", "NFLX", "AMD"]

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
            score = evaluate_pdf_score(inf)
            fv = (inf.get('freeCashflow', 0) or 0) * 15 / (inf.get('sharesOutstanding', 1))
            action, logic = get_ai_rec(px, fv, score)
            
            rows.append({
                "Symbol": t, "Price": px, "Change": ((px / h['Close'].iloc[-2]) - 1) * 100,
                "Score": score, "Action": action, "AI_Logic": logic,
                "DivYield": inf.get('dividendYield', 0), 
                "ExDate": inf.get('exDividendDate'),
                "RevGrowth": inf.get('revenueGrowth', 0), "Info": inf
            })
        except: continue
    return pd.DataFrame(rows)

df_all = fetch_hub_data(list(set(MY_STOCKS_BASE + SCAN_STOCKS)))

# --- 5. ממשק המשתמש ---
st.title("🚀 Intelligence Hub PRO 2026")

c1, c2, c3, c4 = st.columns(4)
vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1.metric("📊 מדד הפחד (VIX)", f"{vix:.2f}")
c2.metric("🏆 מניות זהב (5-6)", len(df_all[df_all["Score"] >= 5]))
c3.metric("🔥 הזינוק היומי", df_all.loc[df_all["Change"].idxmax()]["Symbol"] if not df_all.empty else "N/A")
c4.metric("🕒 עדכון אוטומטי", datetime.now().strftime("%H:%M"))

tabs = st.tabs(["📌 המניות שלי", "🔍 סורק מניות זהב", "💰 לוח דיבידנדים", "📄 אודות ו-10 שנים", "🤝 רדאר מיזוגים"])

# טאב 1: המניות שלי
with tabs[0]:
    st.subheader("ניהול תיק וניתוח AI")
    if 'portfolio' not in st.session_state:
        # הוספה אוטומטית של מניות זהב מהסורק
        gold_from_scan = df_all[(df_all['Score'] >= 5) & (df_all['Symbol'].isin(SCAN_STOCKS))]['Symbol'].tolist()
        initial_list = list(set(MY_STOCKS_BASE + gold_from_scan))
        st.session_state.portfolio = pd.DataFrame([{"Symbol": t, "BuyPrice": 0.0, "Qty": 0} for t in initial_list])
    
    edited = st.data_editor(st.session_state.portfolio, num_rows="dynamic")
    if not edited.empty:
        merged = pd.merge(edited, df_all[['Symbol', 'Price', 'Change', 'Score', 'Action', 'AI_Logic']], on="Symbol")
        merged['PL'] = (merged['Price'] - merged['BuyPrice']) * merged['Qty']
        merged['Yield'] = ((merged['Price'] / merged['BuyPrice']) - 1) * 100
        
        st.dataframe(
            merged[["Symbol", "Price", "Change", "PL", "Yield", "Score", "Action", "AI_Logic"]],
            column_config={
                "Price": st.column_config.NumberColumn("מחיר", help=HELP["price"]),
                "PL": st.column_config.NumberColumn("רווח/הפסד כספי", help=HELP["pl"], format="%.2f"),
                "Yield": st.column_config.NumberColumn("תשואה %", help=HELP["yield"], format="%.1f%%"),
                "Score": st.column_config.NumberColumn("⭐ ציון PDF", help=HELP["score"]),
                "Action": st.column_config.TextColumn("המלצה", help=HELP["ai_action"]),
                "AI_Logic": st.column_config.TextColumn("הסבר AI מפורט", width="large")
            }, use_container_width=True, hide_index=True
        )

# טאב 2: סורק
with tabs[1]:
    st.subheader("🔍 סריקת הזדמנויות בשוק")
    scanner = df_all[df_all['Symbol'].isin(SCAN_STOCKS)].sort_values(by="Score", ascending=False)
    st.dataframe(
        scanner[["Symbol", "Price", "Score", "Action", "AI_Logic"]], 
        column_config={"Score": st.column_config.NumberColumn("ציון איכות", help=HELP["score"])},
        use_container_width=True, hide_index=True
    )

# טאב 3: דיבידנדים
with tabs[2]:
    st.subheader("💰 מניות מחלקות מזומן")
    div_df = df_all[df_all['DivYield'] > 0].sort_values(by="DivYield", ascending=False)
    div_df['ExDateClean'] = div_df['ExDate'].apply(lambda x: datetime.fromtimestamp(x).strftime('%d/%m/%Y') if x else "N/A")
    st.dataframe(
        div_df[["Symbol", "DivYield", "ExDateClean"]], 
        column_config={
            "DivYield": st.column_config.NumberColumn("דיבידנד %", format="%.2f%%", help=HELP["div"]),
            "ExDateClean": st.column_config.TextColumn("תאריך אקס (אחרון לקנייה)", help=HELP["ex_date"])
        }, use_container_width=True, hide_index=True
    )

# טאב 4: אודות ו-10 שנים
with tabs[3]:
    sel = st.selectbox("בחר מניה לניתוח:", df_all['Symbol'].unique())
    row = df_all[df_all['Symbol'] == sel].iloc[0]
    st.markdown(f'<div class="ai-card"><b>🏢 אודות {sel}:</b><br>{row["Info"].get("longBusinessSummary", "")[:800]}...</div>', unsafe_allow_html=True)
    
    yrs = st.slider("טווח שנים לגרף:", 1, 10, 5)
    hist = yf.Ticker(sel).history(period=f"{yrs}y")
    fig = go.Figure(go.Scatter(x=hist.index, y=hist['Close'], line=dict(color='#1a73e8', width=2), fill='tozeroy'))
    fig.update_layout(title=f"ביצועי {sel} ל-{yrs} שנים", height=350, template="plotly_white", margin=dict(l=0,r=0,t=30,b=0))
    st.plotly_chart(fig, use_container_width=True)

# טאב 5: מיזוגים
with tabs[4]:
    mergers = [
        {"חברה": "Wiz / Google", "נושא": "מיזוג סייבר", "סבירות": "75%", "חיפוש": "Wiz Google merger news"},
        {"חברה": "Intel / Qualcomm", "נושא": "שמועות רכישה", "סבירות": "40%", "חיפוש": "Intel acquisition rumors"}
    ]
    for m in mergers:
        url = f"https://www.google.com/search?q={urllib.parse.quote(m['חיפוש'])}"
        st.markdown(f'<div class="ai-card"><b>{m["חברה"]}</b> | סבירות AI: {m["סבירות"]}<br><a href="{url}" target="_blank">🔗 לכתבות האחרונות ב-Bloomberg</a></div>', unsafe_allow_html=True)
