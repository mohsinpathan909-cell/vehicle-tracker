import argparse
import sys

from config import config
from journal import TradeJournal
from risk.risk_manager import RiskManager
from strategy.sma_crossover import SmaCrossoverStrategy


def build_risk_manager() -> RiskManager:
    return RiskManager(
        capital=config.capital,
        risk_per_trade_pct=config.risk_per_trade_pct,
        stop_loss_pct=config.stop_loss_pct,
        target_pct=config.target_pct,
        max_daily_loss_pct=config.max_daily_loss_pct,
        max_open_positions=config.max_open_positions,
    )


def build_strategy() -> SmaCrossoverStrategy:
    return SmaCrossoverStrategy(config.short_sma, config.long_sma)


def cmd_backtest(args):
    from backtester import load_csv, run_backtest

    df = load_csv(args.csv)
    result = run_backtest(df, args.symbol, build_strategy(), build_risk_manager(), config.capital)

    print(f"Starting cash: {result['starting_cash']:.2f}")
    print(f"Final equity:  {result['final_equity']:.2f}")
    print(f"Total return:  {result['total_return_pct']:.2f}%")
    print(f"Max drawdown:  {result['max_drawdown_pct']:.2f}%")
    print(f"Fills:         {result['num_fills']}")


def cmd_paper(args):
    from broker.groww_broker import GrowwMarketData, make_access_token
    from broker.paper_broker import PaperOrderExecutor
    from engine import TradingEngine
    from growwapi import GrowwAPI

    if not config.groww_api_key:
        print("GROWW_API_KEY is not set. Paper trading needs real market data from Groww "
              "even though it won't place real orders. Set up your .env first (see README).")
        sys.exit(1)

    token = make_access_token(config.groww_api_key, config.groww_api_secret, config.groww_totp_secret)
    market_data = GrowwMarketData(GrowwAPI(token))
    executor = PaperOrderExecutor(market_data, args.symbol, config.capital)

    engine = TradingEngine(
        market_data, executor, build_strategy(), build_risk_manager(),
        args.symbol, mode="paper", poll_interval_seconds=config.poll_interval_seconds,
        journal=TradeJournal(),
    )
    engine.run_forever()


def cmd_live(args):
    if not args.i_understand_the_risk or config.confirm_live_trading != "YES":
        print(
            "Live trading is disabled.\n"
            "This will place REAL orders with REAL money on your Groww account.\n"
            "No strategy here is guaranteed to be profitable — you can lose money.\n\n"
            "To proceed you must:\n"
            "  1. Set CONFIRM_LIVE_TRADING=YES in your .env\n"
            "  2. Pass --i-understand-the-risk on the command line\n"
            "Strongly recommended: run `backtest` and `paper` first and review the results."
        )
        sys.exit(1)

    typed = input(f"Type the trading symbol ({args.symbol}) to confirm you want to go live: ")
    if typed.strip() != args.symbol:
        print("Confirmation did not match. Aborting.")
        sys.exit(1)

    from broker.groww_broker import GrowwMarketData, GrowwOrderExecutor, make_access_token
    from engine import TradingEngine
    from growwapi import GrowwAPI

    token = make_access_token(config.groww_api_key, config.groww_api_secret, config.groww_totp_secret)
    client = GrowwAPI(token)
    market_data = GrowwMarketData(client)
    executor = GrowwOrderExecutor(client)

    engine = TradingEngine(
        market_data, executor, build_strategy(), build_risk_manager(),
        args.symbol, mode="live", poll_interval_seconds=config.poll_interval_seconds,
        journal=TradeJournal(),
    )
    engine.run_forever()


def main():
    parser = argparse.ArgumentParser(description="ESA: SMA-crossover trading bot for Groww")
    sub = parser.add_subparsers(dest="command", required=True)

    p_bt = sub.add_parser("backtest", help="Run the strategy over historical CSV data, no network needed")
    p_bt.add_argument("--csv", required=True, help="CSV with timestamp,open,high,low,close,volume columns")
    p_bt.add_argument("--symbol", default=config.symbol)
    p_bt.set_defaults(func=cmd_backtest)

    p_paper = sub.add_parser("paper", help="Trade with real market data but simulated (fake) money")
    p_paper.add_argument("--symbol", default=config.symbol)
    p_paper.set_defaults(func=cmd_paper)

    p_live = sub.add_parser("live", help="Trade with REAL money on your Groww account")
    p_live.add_argument("--symbol", default=config.symbol)
    p_live.add_argument("--i-understand-the-risk", action="store_true")
    p_live.set_defaults(func=cmd_live)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
