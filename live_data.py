
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from config import API_KEY, SECRET_KEY

client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

def קבל_נרות(symbol, דקות=300):
    end = datetime.utcnow()
    start = end - timedelta(minutes=דקות)

    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Minute,
        start=start,
        end=end
    )

    bars = client.get_stock_bars(request).df
    bars.reset_index(inplace=True)
    return bars
