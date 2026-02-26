
import streamlit as st
from live_data import קבל_נרות
from ai_engine import מנועAI
from paper_trading import בצע_קניה, בצע_מכירה

st.set_page_config(page_title="מערכת מסחר AI", layout="wide")

st.title("🚀 מערכת מסחר חכמה - Paper Trading")

symbol = st.text_input("הכנס סימול מניה", "AAPL")

if st.button("הרץ ניתוח"):

    df = קבל_נרות(symbol)

    ai = מנועAI()
    df = ai.הכן_פיצרים(df)
    features = ai.אימון(df)

    df["תחזית"] = ai.חיזוי(df, features)

    last_row = df.iloc[-1]

    st.subheader("נתונים אחרונים")
    st.write(last_row)

    if last_row["תחזית"] == 1:
        st.success("📈 איתות קניה!")
        if st.button("בצע קניה"):
            בצע_קניה(symbol, 1)
            st.success("בוצעה קניה ב-Paper Trading")
    else:
        st.warning("אין איתות קניה כרגע")

st.line_chart(df["close"] if 'df' in locals() else [])
