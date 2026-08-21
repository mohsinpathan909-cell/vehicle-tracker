"""Simulated order execution: no real money ever moves. Fills instantly at the
current LTP from whatever MarketData source it's given (live Groww quotes
during paper trading, or replayed historical bars during a backtest)."""
from broker.base import MarketData, OrderExecutor


class PaperOrderExecutor(OrderExecutor):
    def __init__(self, market_data: MarketData, symbol: str, starting_cash: float, slippage_pct: float = 0.05):
        self._market_data = market_data
        self._symbol = symbol
        self.cash = starting_cash
        self.slippage_pct = slippage_pct
        self.positions: dict[str, dict] = {}
        self.fills: list[dict] = []

    def place_order(self, symbol: str, transaction_type: str, quantity: int,
                     order_type: str = "MARKET", price: float | None = None) -> dict:
        ltp = price if order_type == "LIMIT" and price else self._market_data.get_ltp(symbol)
        slip = ltp * self.slippage_pct / 100
        fill_price = ltp + slip if transaction_type == "BUY" else ltp - slip

        if transaction_type == "BUY":
            cost = fill_price * quantity
            if cost > self.cash:
                return {"status": "REJECTED", "reason": "insufficient paper cash"}
            self.cash -= cost
            pos = self.positions.setdefault(symbol, {"quantity": 0, "avg_price": 0.0})
            new_qty = pos["quantity"] + quantity
            pos["avg_price"] = (pos["avg_price"] * pos["quantity"] + fill_price * quantity) / new_qty
            pos["quantity"] = new_qty
        else:
            pos = self.positions.get(symbol)
            if not pos or pos["quantity"] < quantity:
                return {"status": "REJECTED", "reason": "insufficient paper position"}
            pos["quantity"] -= quantity
            self.cash += fill_price * quantity
            if pos["quantity"] == 0:
                del self.positions[symbol]

        fill = {
            "symbol": symbol,
            "transaction_type": transaction_type,
            "quantity": quantity,
            "price": fill_price,
            "status": "FILLED",
        }
        self.fills.append(fill)
        return fill

    def get_positions(self) -> dict:
        return self.positions

    def get_cash(self) -> float:
        return self.cash
