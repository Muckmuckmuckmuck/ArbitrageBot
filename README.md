# quantbot — IBKR multi-strategy quant system

A single-broker (**Interactive Brokers**) paper-trading system that runs **three
research-grounded strategy sleeves** (high / mid / safe growth), blends them with a
**regime-aware, volatility-targeted allocator**, and enforces a **hard-cap risk
engine**. Everything is heavily instrumented so the tracked data drives iteration
(you + Claude Code — no paid LLM API).

> **Status:** Backtesting engine + all three sleeves + allocator + risk engine built
> and validated on 16 years of real data. Order execution (IBKR paper) is the next
> layer and is **not yet wired** — nothing trades real or paper money today.

## Architecture

```
Backtest data (yfinance/Stooq, bulk, free)          Live: IBKR paper (ib_async → IB Gateway)  [todo]
        │
        ▼
   Regime Engine (trend × vol)
        │
        ▼
   Strategy Sleeves ──► Allocator (regime-tilted + vol-targeted) ──► Risk Engine ──► Execution
   high  = risk-managed momentum                                      (hard caps,      (paper→live
   mid   = dual-momentum rotation                                     drawdown kill)    gated)
   safe  = defensive risk parity
        │
        ▼
   Intensive tracking  ──►  data/backtests/*.json + equity_*.csv  ──►  iterate
```

## The three sleeves (and the papers behind them)

**High-growth — risk-managed time-series / dual momentum**
12-1 momentum (Jegadeesh-Titman; Antonacci), keep only positive *absolute* momentum
names (dual-momentum crash filter), weight by inverse-vol (risk parity), and
vol-target the sleeve — Moskowitz-Ooi-Pedersen (2012) + Barroso-Santa-Clara (2015),
which cut this sleeve's max drawdown from −32% to −18%.

**Mid-growth — dual-momentum rotation (Antonacci GEM)**
Relative-strength pick of a broad equity basket; when absolute momentum turns
negative it rotates to **bonds** (which outperform in equity sell-offs). Holds
top-2 inverse-vol weighted to avoid vanilla GEM's single-asset fragility.

**Safe-growth — defensive risk parity + trend filter**
Inverse-vol (low-vol / betting-against-beta tilt, Frazzini-Pedersen 2014) across a
defensive basket, with a Faber (2007) 10-month SMA filter so it doesn't hold assets
in a downtrend (e.g. long bonds in 2022) — those rotate to T-bills.

**Allocator — regime tilt + portfolio vol targeting**
Sleeve capital is tilted by regime (more momentum in calm bulls, more defense in
bear/volatile), then the whole book is scaled to a constant vol target
(Moreira-Muir 2017) — a top-level, long-only crash brake.

## Results (2010-2026, real data, `scripts/run_backtest.py`)

| Strategy | CAGR | Vol | Sharpe | MaxDD |
| --- | --- | --- | --- | --- |
| High-growth (momentum) | 14.1% | 14.4% | 0.71 | −18.3% |
| Mid-growth (dual-mom) | 6.7% | 10.5% | 0.29 | −17.8% |
| Safe-growth (def. RP) | 4.1% | 5.1% | 0.03 | −10.6% |
| **Combined + risk engine** | **9.5%** | **8.9%** | **0.61** | **−14.6%** |
| Buy & Hold SPY | 14.1% | 17.1% | 0.86 | −33.7% |

The system runs at ~half SPY's volatility and drawdown. On full-sample Sharpe it
still trails buy-and-hold SPY — 2010-2026 was an exceptional bull market — so the
open work is (a) stress-test on bad regimes (2020, 2022) where the protection pays
off, and (b) stronger mid/safe return engines. This is the substrate for that
iteration, not a finished alpha.

## Lessons carried from the predecessor arbitrage bot

Single-broker (deletes the cross-exchange transfer bug class that dominated the old
bot), async-friendly, backtest-before-live, size to the binding constraint, clean
and tested — no 143-file status-doc sprawl.

## Quickstart

```bash
python3 -m venv .venv
./.venv/bin/pip install --prefer-binary -r requirements.txt   # --prefer-binary avoids a Rust build of cryptography
./.venv/bin/python scripts/fetch_check.py      # prove the data pipeline
./.venv/bin/python scripts/run_backtest.py     # run the full system, save artifacts
```

## Roadmap

- [x] Scaffold, config, universe (3 sleeves), free bulk data layer (+ parquet cache)
- [x] Regime engine (trend × vol)
- [x] Three research-grounded sleeves + regime-tilted vol-targeted allocator
- [x] Hard-cap risk engine + drawdown kill-switch
- [x] Backtester with per-regime attribution + tracking artifacts
- [ ] Stress tests on sub-periods (2020 crash, 2022 bear) + walk-forward validation
- [ ] Stronger mid/safe sleeves; parameter robustness sweeps
- [ ] IBKR paper execution adapter (ib_async) + one-command connection test
- [ ] Live daily loop: regime → allocate → risk-check → (paper) execute → log
