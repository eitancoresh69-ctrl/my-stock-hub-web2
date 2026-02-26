
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from config import API_KEY, SECRET_KEY

trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)

def בצע_קניה(symbol, qty):

    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY
    )

    trading_client.submit_order(order)

def בצע_מכירה(symbol, qty):

    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY
    )

    trading_client.submit_order(order)
