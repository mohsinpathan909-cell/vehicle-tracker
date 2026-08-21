import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


@dataclass(frozen=True)
class Config:
    groww_api_key: str = os.getenv("GROWW_API_KEY", "")
    groww_api_secret: str = os.getenv("GROWW_API_SECRET", "")
    groww_totp_secret: str = os.getenv("GROWW_TOTP_SECRET", "")

    symbol: str = os.getenv("TRADING_SYMBOL", "RELIANCE")
    exchange: str = os.getenv("EXCHANGE", "NSE")

    capital: float = _float("CAPITAL", 50000)
    risk_per_trade_pct: float = _float("RISK_PER_TRADE_PCT", 1.0)
    stop_loss_pct: float = _float("STOP_LOSS_PCT", 1.5)
    target_pct: float = _float("TARGET_PCT", 3.0)
    max_daily_loss_pct: float = _float("MAX_DAILY_LOSS_PCT", 3.0)
    max_open_positions: int = _int("MAX_OPEN_POSITIONS", 1)

    short_sma: int = _int("SHORT_SMA", 20)
    long_sma: int = _int("LONG_SMA", 50)

    poll_interval_seconds: int = _int("POLL_INTERVAL_SECONDS", 60)

    confirm_live_trading: str = os.getenv("CONFIRM_LIVE_TRADING", "NO")


config = Config()
