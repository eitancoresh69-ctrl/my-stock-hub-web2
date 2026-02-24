import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# --- 1. הגדרות דף וריענון אוטומטי (15 דקות) ---
st.set_page_config(page_title="Intelligence Hub PRO", layout="wide", initial_sidebar_state="collapsed")

# הזרקת קוד לריענון אוטומטי כל 900 שניות (15 דקות)
st.markdown("""
    <script>
    setInterval(function(){
        window.location.reload();
    }, 900000);
    </script>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; direction: rtl; text-align: right; }
    .block-container { padding-top: 1rem !important; }
    .ai-card { background: white; padding: 12px; border-radius: 10px; border-right: 6px solid #1a73e8; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 10px; }
    .bull-box { background-color: #e8f5e9; border-color: #2e7d32; color: #1b5e20; padding: 10px; border-radius: 8px; border-right: 5px solid; }
    .bear-box { background-color: #ffeef0; border-color: #d73a49; color: #b71c1c; padding: 10px; border-radius: 8px; border-right: 5px solid; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילון בועות הסבר (Help Tooltips) ---
HELP = {
    "price": "המחיר הנוכחי במסחר ($ לארה\"ב, אג' לישראל).",
    "score": "ציון איכות 0-6 מבוסס על ה-PDF: צמיחת מכירות, צמיחת רווח, שוליים, ROE, מזומן מול חוב, וחוב אפס.",
    "pl": "הרווח או ההפסד הכספי שלך על הנייר.",
    "yield": "השינוי באחוזים ממחיר הקנייה המקורי שלך.",
    "ai_action": "המלצה אוטומטית: קנייה חזקה, החזק או מכירה.",
    "ai_logic": "ניתוח מפורט של ה-AI המשלב את איכות החברה מול מחיר השוק.",
    "div": "תשואת הדיבידנד השנתית (כמה מזומן החברה מחלקת)."
}

# --- 3. לוגיקה פיננסית (6 הקריטריונים מה-PDF) ---
def evaluate_pdf_score(info):
    score = 0
    try:
        if (info.get('revenueGrowth', 0) or 0) >= 0.10: score += 1      # 1. צמיחת מכירות
        if (info.get('earningsGrowth', 0) or 0) >= 0.10: score += 1     # 2. צמיחת רווחים
        if (info.get('profitMargins', 0) or 0) >= 0.10: score += 1      # 3. שולי רווח
        if (info.get('returnOnEquity', 0) or 0) >= 0.15: score += 1     # 4. ROE
        cash = info.get('totalCash', 0) or 0
        debt = info.get('totalDebt', 0) or 0
        if cash > debt: score += 1                                       # 5. מזומן > חוב
        if debt == 0: score += 1                                         # 6. חוב אפס
    except: pass
    return score

def get_ai_recommendation(price, fv, score):
    if not fv or fv == 0: return "בבדיקה 🔍", "אין מספיק נתונים לחישוב שווי הוגן."
    gap = (fv - price) / price
    if score >= 5:
        if gap > 0.05: return "קנייה חזקה 💎", f"מניית 'זהב' (ציון {score}) שנסחרת בהנחה של {abs(gap):.0%} מהשווי שלה."
        return "קנייה 📈", "חברה מעולה במחיר הוגן. פוטנציאל צמיחה גבוה."
    elif score >= 3:
        if gap > 0.10: return "איסוף 🛒", "חברה איכותית שנמצאת כרגע ב'מבצע' יחסית לרווחים שלה."
        return "החזק ⚖️", "החברה יציבה אך המחיר משקף את השווי האמיתי שלה כרגע."
    return "מכירה/המתנה 🔴", "ציון איכות נמוך יחסית לסיכון בשוק."

# --- 4. שליפת נתונים מרכזית ---
MY_STOCKS = ["MSFT", "AAPL", "NVDA", "TSLA", "PLTR", "ENLT.TA", "POLI.TA", "LUMI.TA"]
SCAN_STOCKS = ["AMZN", "AVGO", "META", "GOOGL", "LLY", "TSM", "COST", "V", "ADBE", "NFLX"]

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
            fcf = inf.get('freeCashflow', 0) or 0
            shares = inf.get('sharesOutstanding', 1)
            fv = (fcf * 15) / shares if fcf > 0 else 0
            action, logic = get_ai_recommendation(px, fv, score)
            
            rows.append({
                "Symbol": t, "Price": px, "Change": ((px / h['Close'].iloc[-2]) - 1) * 100,
                "Score": score, "Action": action, "AI_Logic": logic,
                "Dividend": inf.get('dividendYield', 0),
                "ExDate": inf.get('exDividendDate'),
                "RevGrowth": inf.get('revenueGrowth', 0), "Info": inf
            })
        except: continue
    return pd.DataFrame(rows)

df_all = fetch_hub_data(list(set(MY_STOCKS + SCAN_STOCKS)))

# --- 5. ממשק המשתמש ---
st.title("🚀 Investment Intelligence Hub 2026")

c1, c2, c3, c4 = st.columns(4)
vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1.metric("📊 מדד הפחד (VIX)", f"{vix:.2f}")
c2.metric("🏆 מניות זהב (5-6)", len(df_all[df_all["Score"] >= 5]))
c3.metric("🕒 עדכון אוטומטי", datetime.now().strftime("%H:%M"))
c4.metric("🔥 הזינוק היומי", df_all.loc[df_all["Change"].idxmax()]["Symbol"] if not df_all.empty else "N/A")

tabs = st.tabs(["📌 המניות שלי", "🔍 סורק מניות זהב", "💰 דיבידנדים", "📄 אודות וניתוח (10 שנים)", "🤝 רדאר מיזוגים"])

# טאב 1: המניות שלי
with tabs[0]:
    st.subheader("ניהול תיק וניתוח AI לפעולה")
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = pd.DataFrame([{"Symbol": t, "BuyPrice": 0.0, "Qty": 0} for t in MY_STOCKS])

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
                "AI_Logic": st.column_config.TextColumn("הסבר AI מפורט", help=HELP["ai_logic"])
            },
            use_container_width=True, hide_index=True
        )

# טאב 2: סורק
with tabs[1]:
    st.subheader("🔍 סריקת הזדמנויות בשוק")
    scanner = df_all[df_all['Symbol'].isin(SCAN_STOCKS)].sort_values(by="Score", ascending=False)
    st.dataframe(scanner[["Symbol", "Price", "Score", "Action", "AI_Logic"]], use_container_width=True, hide_index=True)

# טאב 3: דיבידנדים
with tabs[2]:
    st.subheader("💰 מניות מחלקות מזומן")
    div_df = df_all[df_all['Dividend'] > 0].sort_values(by="Dividend", ascending=False)
    div_df['ExDateClean'] = div_df['ExDate'].apply(lambda x: datetime.fromtimestamp(x).strftime('%d/%m/%Y') if x else "N/A")
    st.dataframe(
        div_df[["Symbol", "Dividend", "ExDateClean"]],
        column_config={
            "Dividend": st.column_config.NumberColumn("דיבידנד %", format="%.2%"),
            "ExDateClean": st.column_config.TextColumn("תאריך אקס (אחרון לקנייה)")
        },
        use_container_width=True, hide_index=True
    )

# טאב 4: אודות ו-10 שנים
with tabs[3]:
    sel = st.selectbox("בחר מניה לניתוח:", df_all['Symbol'].unique())
    row = df_all[df_all['Symbol'] == sel].iloc[0]
    st.markdown(f'<div class="ai-card"><b>🏢 אודות {sel}:</b><br>{row["Info"].get("longBusinessSummary", "")[:800]}...</div>', unsafe_allow_html=True)
    
    col_bull, col_bear = st.columns(2)
    with col_bull: st.markdown(f'<div class="bull-box"><b>🐂 שור:</b> צמיחת מכירות של {row["RevGrowth"]:.1%}.</div>', unsafe_allow_html=True)
    with col_bear: st.markdown(f'<div class="bear-box"><b>🐻 דוב:</b> תמחור השוק עשוי להיות מתוח בטווח הקצר.</div>', unsafe_allow_html=True)
    
    yrs = st.slider("טווח שנים לגרף:", 1, 10, 5)
    hist = yf.Ticker(sel).history(period=f"{yrs}y")
    fig = go.Figure(go.Scatter(x=hist.index, y=hist['Close'], line=dict(color='#1a73e8', width=2), fill='tozeroy'))
    fig.update_layout(title=f"ביצועי מניית {sel} ל-{yrs} שנים", height=350, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

# טאב 5: מיזוגים
with tabs[4]:
    st.subheader("🤝 רדאר M&A ושמועות שוק")
    mergers = [
        {"חברה": "Wiz / Google", "נושא": "מיזוג סייבר", "סבירות": "75%", "לינק": "https://www.google.com/search?q=Wiz+Google+merger"},
        {"חברה": "Intel / Qualcomm", "נושא": "שמועות רכישה", "סבירות": "40%", "לינק": "https://www.google.com/search?q=Intel+acquisition"}
    ]
    for m in mergers:
        st.markdown(f'<div class="ai-card"><b>{m["חברה"]}</b> | סבירות AI: {m["סבירות"]}<br><a href="{m["לינק"]}" target="_blank">🔗 קרא עוד ב-Bloomberg/Reuters</a></div>', unsafe_allow_html=True)
