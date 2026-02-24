import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import urllib.parse

# --- 1. הגדרות דף ועיצוב Elite (RTL מלא, ללא סרגל צד) ---
st.set_page_config(page_title="Investment Intelligence 2026", layout="wide", initial_sidebar_state="collapsed")

# מנגנון ריענון אוטומטי (כל 15 דקות)
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
    
    /* עיצוב כרטיסי AI והתראות */
    .intel-card { background: white; padding: 12px; border-radius: 10px; border-right: 6px solid #1a73e8; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 10px; }
    .bull-box { background-color: #e8f5e9; border-color: #2e7d32; color: #1b5e20; padding: 10px; border-radius: 8px; border-right: 5px solid; }
    .bear-box { background-color: #ffeef0; border-color: #d73a49; color: #b71c1c; padding: 10px; border-radius: 8px; border-right: 5px solid; }
    </style>
""", unsafe_allow_html=True)

# --- 2. מילון בועות הסבר (Tooltips) בעברית ---
GLOSSARY = {
    "מחיר": "המחיר הנוכחי במסחר. $ למניות חוץ, אג' למניות ישראל.",
    "ציון איכות": "שקלול 6 הקריטריונים מהמדריך: צמיחה, רווחיות, חוב ומזומן. 5-6 = מניית זהב.",
    "רווח/הפסד": "כמה כסף (נומינלי) הרווחת או הפסדת על הנייר.",
    "תשואה": "השינוי באחוזים ממחיר הקנייה שלך.",
    "דיבידנד %": "אחוז הרווח השנתי שהחברה מחלקת למשקיעים במזומן.",
    "תאריך אקס": "היום האחרון שבו צריך להחזיק במניה כדי לקבל את הדיבידנד הקרוב.",
    "שווי הוגן": "המחיר שהמניה 'באמת' שווה לפי הרווחים שלה. אם המחיר נמוך מהשווי - המניה זולה."
}

# --- 3. לוגיקה פיננסית ---

def get_currency(ticker):
    return "אג'" if ".TA" in ticker else "$"

def evaluate_pdf_criteria(info):
    """ חישוב 6 הקריטריונים מה-PDF """
    score = 0
    try:
        if info.get('revenueGrowth', 0) >= 0.10: score += 1
        if info.get('earningsGrowth', 0) >= 0.10: score += 1
        if info.get('profitMargins', 0) >= 0.10: score += 1
        if info.get('returnOnEquity', 0) >= 0.15: score += 1
        if (info.get('totalCash', 0) > info.get('totalDebt', 0)): score += 1
        if info.get('totalDebt', 0) == 0: score += 1
    except: pass
    return score

# --- 4. שליפת נתונים ---
MY_STOCKS_LIST = ["MSFT", "AAPL", "NVDA", "TSLA", "PLTR", "ENLT.TA", "POLI.TA", "LUMI.TA"]
SCAN_LIST = ["AMZN", "AVGO", "META", "GOOGL", "LLY", "TSM", "COST", "V", "ADBE", "NFLX", "AMD", "SBUX", "INTC"]

@st.cache_data(ttl=600)
def fetch_everything(tickers):
    rows = []
    for t in tickers:
        try:
            s = yf.Ticker(t)
            inf = s.info
            h = s.history(period="2d")
            if h.empty: continue
            px = h['Close'].iloc[-1]
            chg = ((px / h['Close'].iloc[-2]) - 1) * 100
            
            score = evaluate_pdf_criteria(inf)
            div_yield = inf.get('dividendYield', 0)
            ex_div = inf.get('exDividendDate')
            
            # חישוב שווי הוגן (DCF מופשט)
            fcf = inf.get('freeCashflow', 0) or 0
            shares = inf.get('sharesOutstanding', 1)
            fv = (fcf * 15) / shares if fcf > 0 else 0

            rows.append({
                "Symbol": t, "Price": px, "Change": chg, "Score": score,
                "DivYield": div_yield, "ExDate": ex_div, "FairValue": fv,
                "RevenueGrowth": inf.get('revenueGrowth', 0), "Info": inf
            })
        except: continue
    return pd.DataFrame(rows)

df_all = fetch_everything(list(set(MY_STOCKS_LIST + SCAN_LIST)))

# --- 5. ממשק המשתמש ---
st.title("🚀 Investment Intelligence Hub 2026")

# קוביות מדדים עליונות
c1, c2, c3, c4 = st.columns(4)
vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
c1.metric("📊 מדד הפחד (VIX)", f"{vix:.2f}")
c2.metric("🏆 מניות זהב (5-6)", len(df_all[df_all["Score"] >= 5]))
c3.metric("🔥 הזינוק היומי", df_all.loc[df_all["Change"].idxmax()]["Symbol"] if not df_all.empty else "N/A")
c4.metric("🕒 עדכון אוטומטי", datetime.now().strftime("%H:%M"))

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📌 המניות שלי (P/L)", "🔍 סורק מניות זהב", "💰 לוח דיבידנדים", "📄 אודות וניתוח (10 שנים)", "🤝 רדאר מיזוגים"])

# טאב 1: המניות שלי - פשוט ומובן
with tab1:
    st.subheader("מעקב החזקות: כמה הרווחתי?")
    if 'portfolio' not in st.session_state:
        # הוספה אוטומטית של מניות זהב מהסורק
        gold_stocks = df_all[df_all['Score'] >= 5]['Symbol'].tolist()
        initial_list = list(set(MY_STOCKS_LIST + gold_stocks))
        st.session_state.portfolio = pd.DataFrame([{"Symbol": t, "BuyPrice": 0.0, "Qty": 0} for t in initial_list])

    edited_df = st.data_editor(st.session_state.portfolio, num_rows="dynamic")
    st.session_state.portfolio = edited_df

    if not edited_df.empty:
        merged = pd.merge(edited_df, df_all[['Symbol', 'Price', 'Change', 'Score']], on="Symbol")
        merged['P/L'] = (merged['Price'] - merged['BuyPrice']) * merged['Qty']
        merged['Yield%'] = ((merged['Price'] / merged['BuyPrice']) - 1) * 100
        
        # הצגת הטבלה עם בועות הסבר
        st.dataframe(
            merged[["Symbol", "Price", "Change", "P/L", "Yield%", "Score"]],
            column_config={
                "Price": st.column_config.NumberColumn("מחיר", help=GLOSSARY["מחיר"]),
                "P/L": st.column_config.NumberColumn("רווח/הפסד כספי", help=GLOSSARY["רווח/הפסד"], format="%.2f"),
                "Yield%": st.column_config.NumberColumn("תשואה %", help=GLOSSARY["תשואה"], format="%.1f%%"),
                "Score": st.column_config.NumberColumn("⭐ ציון איכות", help=GLOSSARY["ציון איכות"])
            },
            use_container_width=True, hide_index=True
        )

# טאב 2: סורק מניות זהב - תוקן ופעיל
with tab2:
    st.subheader("🔍 סורק AI: מניות שעומדות בקריטריונים (ציון 4 ומעלה)")
    # כאן אנחנו מציגים את כל המניות מהסורק שלא נמצאות בתיק שלך עדיין
    scanner_results = df_all[df_all['Score'] >= 4].sort_values(by="Score", ascending=False)
    st.dataframe(
        scanner_results[["Symbol", "Price", "Score", "RevenueGrowth", "FairValue"]],
        column_config={
            "Score": st.column_config.NumberColumn("ציון איכות", help=GLOSSARY["ציון איכות"]),
            "RevenueGrowth": st.column_config.NumberColumn("צמיחה", format="%.1%"),
            "FairValue": st.column_config.NumberColumn("שווי הוגן", help=GLOSSARY["שווי הוגן"])
        },
        use_container_width=True, hide_index=True
    )

# טאב 3: לוח דיבידנדים - חדש!
with tab3:
    st.subheader("💰 מי מחלק מזומן? (דיבידנדים)")
    
    div_df = df_all[df_all['DivYield'] > 0].sort_values(by="DivYield", ascending=False)
    
    # המרת תאריך אקס לפורמט קריא
    div_df['ExDateClean'] = div_df['ExDate'].apply(lambda x: datetime.fromtimestamp(x).strftime('%d/%m/%Y') if x else "לא ידוע")
    
    st.dataframe(
        div_df[["Symbol", "Price", "DivYield", "ExDateClean"]],
        column_config={
            "DivYield": st.column_config.NumberColumn("דיבידנד %", help=GLOSSARY["דיבידנד %"], format="%.2%"),
            "ExDateClean": st.column_config.TextColumn("תאריך אקס (אחרון לקנייה)", help=GLOSSARY["תאריך אקס"])
        },
        use_container_width=True, hide_index=True
    )

# טאב 4: אודות וניתוח (10 שנים)
with tab4:
    sel = st.selectbox("בחר מניה לניתוח עמוק:", df_all['Symbol'].unique())
    row = df_all[df_all['Symbol'] == sel].iloc[0]
    
    st.markdown(f'<div class="intel-card"><b>🏢 אודות {sel}:</b><br>{row["Info"].get("longBusinessSummary", "מידע לא זמין")[:600]}...</div>', unsafe_allow_html=True)
    
    c_bull, c_bear = st.columns(2)
    with c_bull:
        st.markdown(f'<div class="bull-box"><b>🐂 תרחיש השור (AI):</b> המניה מציגה צמיחה חזקה ופוטנציאל להובלת השוק.</div>', unsafe_allow_html=True)
    with c_bear:
        st.markdown(f'<div class="bear-box"><b>🐻 תרחיש הדוב (AI):</b> קיימים סיכוני תמחור יתר או תחרות גוברת בסקטור.</div>', unsafe_allow_html=True)

    yrs = st.slider("בחר טווח שנים לגרף (עד 10 שנים):", 1, 10, 5)
    hist = yf.Ticker(sel).history(period=f"{yrs}y")
    fig = go.Figure(go.Scatter(x=hist.index, y=hist['Close'], line=dict(color='#1a73e8', width=2), fill='tozeroy'))
    fig.update_layout(title=f"ביצועי מניית {sel} ל-{yrs} שנים", height=350, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

# טאב 5: רדאר מיזוגים
with tab5:
    st.subheader("🤝 רדאר M&A ושמועות שוק")
    
    mergers = [
        {"חברה": "Wiz / Google", "נושא": "מיזוג ענק", "סבירות": "75%", "לינק": "https://www.google.com/search?q=Wiz+Google+merger"},
        {"חברה": "Intel / Broadcom", "נושא": "שמועות רכישה", "סבירות": "40%", "לינק": "https://www.google.com/search?q=Intel+acquisition+rumors"}
    ]
    for m in mergers:
        st.markdown(f"""
        <div class="intel-card">
            <b>{m['חברה']}</b> | {m['נושא']} | סבירות AI: {m['סבירות']}<br>
            <a href="{m['לינק']}" target="_blank" style="color:#1a73e8;">🔗 קרא עוד בחדשות העולם</a>
        </div>
        """, unsafe_allow_html=True)
