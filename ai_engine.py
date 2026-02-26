
import ta
import numpy as np
from xgboost import XGBClassifier

class מנועAI:

    def __init__(self):
        self.model = XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05
        )

    def הכן_פיצרים(self, df):

        df["RSI"] = ta.momentum.RSIIndicator(df["close"]).rsi()
        df["EMA20"] = ta.trend.EMAIndicator(df["close"], 20).ema_indicator()
        df["EMA50"] = ta.trend.EMAIndicator(df["close"], 50).ema_indicator()

        macd = ta.trend.MACD(df["close"])
        df["MACD"] = macd.macd()
        df["MACD_SIGNAL"] = macd.macd_signal()

        df["ATR"] = ta.volatility.AverageTrueRange(
            df["high"], df["low"], df["close"]
        ).average_true_range()

        df.dropna(inplace=True)
        return df

    def אימון(self, df):

        df["יעד"] = np.where(df["close"].shift(-1) > df["close"], 1, 0)
        df.dropna(inplace=True)

        features = ["RSI","EMA20","EMA50","MACD","MACD_SIGNAL","ATR"]

        X = df[features]
        y = df["יעד"]

        self.model.fit(X, y)
        return features

    def חיזוי(self, df, features):
        return self.model.predict(df[features])
