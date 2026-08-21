import csv
import os
from datetime import datetime, timezone


class TradeJournal:
    def __init__(self, path: str = "logs/trades.csv"):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            with open(path, "w", newline="") as f:
                csv.writer(f).writerow(
                    ["timestamp", "mode", "symbol", "side", "quantity", "price", "status"]
                )

    def log(self, mode: str, symbol: str, side: str, quantity: int, price: float, status: str):
        with open(self.path, "a", newline="") as f:
            csv.writer(f).writerow(
                [datetime.now(timezone.utc).isoformat(), mode, symbol, side, quantity, price, status]
            )
