# ESA — Groww Auto Trading Bot

An algo-trading bot that connects to your Groww account via the official
`growwapi` SDK and trades a configurable SMA-crossover strategy automatically.

## Read this before doing anything else

- **No software can guarantee profit.** This bot follows fixed rules; it does
  not predict the market. Markets can and do move against any strategy,
  including this one. On a synthetic random-walk test run in this repo it
  *lost* 4% — that's normal and expected, not a bug.
- **You can lose real money in live mode.** Only move to `live` after you've
  reviewed backtest results and watched paper trading for a while and are
  comfortable with the strategy's behavior.
- **Compliance:** SEBI has specific rules for algorithmic trading by retail
  investors placing orders through broker APIs (algo registration/tagging
  requirements). Check Groww's current API/algo-trading terms and SEBI's
  retail algo framework before running this against a real account.
- This code was written without live access to `groww.in` (blocked from the
  build sandbox), based on the public `growwapi` PyPI page and cached search
  results. **Verify method/constant names in `broker/groww_broker.py` against
  the official docs** (https://groww.in/trade-api/docs/python-sdk) before
  running `live` mode.

## What's actually implemented

- **Strategy**: simple SMA crossover (configurable short/long windows) —
  `strategy/sma_crossover.py`. A well-known starting strategy, not a proven
  edge. Swap in your own by implementing the same `generate_signal(df)`
  interface.
- **Risk manager** (`risk/risk_manager.py`): position sizing from % capital
  risked per trade, per-trade stop-loss/target levels, a daily loss cutoff
  that halts new positions, and a max open positions cap.
- **Three run modes**, sharing the same strategy/risk code:
  - `backtest` — replays a historical CSV, no network or API keys needed.
  - `paper` — uses **real** Groww market data but simulated money
    (`broker/paper_broker.py`); never places a real order.
  - `live` — places real orders via `broker/groww_broker.py`. Gated behind
    an explicit env flag, a CLI flag, and a typed confirmation prompt.
- **Trade journal**: every fill (paper or live) is appended to
  `logs/trades.csv`.

## Setup

```bash
cd esa-grow-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Getting Groww API credentials

1. Open the Groww app/web → your profile → look for "Trading APIs" /
   "API Keys" (introduced for GrowwAPI algo trading access).
2. Generate an API key, and either an API secret or a TOTP token+secret.
3. Put them in `.env` as `GROWW_API_KEY` / `GROWW_API_SECRET` (or
   `GROWW_TOTP_SECRET`).

Exact menu names may have changed — if you can't find it, search "Groww
trade API" for the current onboarding flow.

## Usage

### 1. Backtest first (no API keys needed)

```bash
python main.py backtest --csv data/sample_synthetic.csv --symbol TEST
```

Point `--csv` at real historical data (timestamp, open, high, low, close,
volume columns) for the symbol you actually want to trade before trusting
any result.

### 2. Paper trade (real prices, fake money)

```bash
python main.py paper --symbol RELIANCE
```

Requires `GROWW_API_KEY` (and secret/TOTP) in `.env` — paper mode reads real
quotes but only ever calls the simulated executor, so no real order is ever
sent.

### 3. Go live (real money — only after the above)

```bash
python main.py live --symbol RELIANCE --i-understand-the-risk
```

Also requires `CONFIRM_LIVE_TRADING=YES` in `.env`, and you'll be asked to
type the symbol name to confirm. There is no other way to trigger a real
order from this codebase.

## Configuration

All strategy/risk parameters are in `.env` — see `.env.example` for the
full list (capital, risk per trade %, stop-loss %, target %, max daily
loss %, SMA windows, poll interval).

## Tests

```bash
python -m pytest tests/ -q
```

Covers the strategy signal logic, risk sizing/limits, and the paper broker's
fill/cash accounting — all offline, no API calls.
