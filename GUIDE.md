# quantbot — Complete Step-by-Step Guide

Everything from zero to a paper-trading bot running on a cloud VM, and how to keep
improving it. Do the parts in order the first time. Commands are copy-paste ready.

**What you have:** a multi-strategy quant system — three risk-tiered sleeves
(high / mid / safe growth), a regime-aware allocator, and a hard-cap risk engine.
It backtests on free data and trades on an **IBKR paper account**, long-only, no
shorting.

**Honest performance (2010–2026 backtest):**

| | CAGR | Sharpe | Max drawdown |
|---|---|---|---|
| Combined (default) | 11.6% | 0.76 | −19% |
| High-growth sleeve | 19.5% | 0.83 | −24% |
| Buy & hold SPY | 14.1% | 0.86 | −34% |

The system runs at **half SPY's drawdown** and cuts every crisis (2020, 2022) to a
third-to-half. It is *not* a magic 20% machine — see Part 7 for the honest way to push
returns.

**Repo:** `github.com/Muckmuckmuckmuck/ArbitrageBot`, branch **`quantbot`**.

**Data flow:** free daily bars → regime classifier → 3 sleeves → allocator
(regime-tilted, volatility-targeted) → risk engine → broker (IBKR paper) → logs.

---

## Part 1 — Local setup (your Mac)

```bash
# If not already here, clone the code branch:
git clone --branch quantbot https://github.com/Muckmuckmuckmuck/ArbitrageBot.git ~/algo
cd ~/algo

python3 -m venv .venv
./.venv/bin/pip install --prefer-binary -r requirements.txt   # --prefer-binary avoids a Rust build
cp .env.example .env        # defaults are SAFE: PAPER mode, dry-run, no live orders
```

> Python 3.9 is fine locally for everything **except** live IBKR (`ib_async` needs
> 3.10+). That only matters on the VM, which has 3.10. Local backtests/dry-runs work.

---

## Part 2 — Run it locally (learn the system)

Run these in order. Output also lands in `data/` (git-ignored): `backtests/`, `live/`, `logs/`.

```bash
./.venv/bin/python scripts/fetch_check.py       # 1. proves the data pipeline (pulls real prices)
./.venv/bin/python scripts/run_backtest.py      # 2. full system: per-sleeve + combined vs SPY + today's target book
./.venv/bin/python scripts/stress_test.py       # 3. per-year returns + crisis windows (2020, 2022) — does it survive bad regimes?
./.venv/bin/python scripts/ablation.py          # 4. which signal choices actually help (Sharpe + robustness)
./.venv/bin/python scripts/allocation_sweep.py  # 5. the return-vs-protection dial across sleeve mixes
./.venv/bin/python scripts/sim_trade.py         # 6. end-to-end rebalance against a simulated $100k account
./.venv/bin/python scripts/daily_run.py         # 7. the exact headless run the VM does (dry-run: logs orders, places none)
```

**How to read the main outputs:**
- `run_backtest.py` — the scorecard. `combined` is what the bot trades by default.
- `stress_test.py` — the honesty check. Look at 2022: combined ≈ −8% vs SPY −18%.
- `allocation_sweep.py` — shows CAGR/drawdown at 50/30/20 (default) up to 90/6/4.
- `daily_run.py` — prints "today's target book" and writes `data/live/target_YYYYMMDD.json`.

---

## Part 3 — Choose your config (the one real decision)

Return vs. protection is a dial you set. Defaults trade the **balanced** blend
(~11.6% / −19%). To lean more aggressive (toward ~14–17%, but bigger drawdowns):

**A. Change the sleeve mix** — edit `src/quantbot/universe.py`:
```python
SLEEVE_TARGET_WEIGHTS = {
    "high_growth": 0.50,   # ↑ raise this for more return / more risk
    "mid_growth":  0.30,
    "safe_growth": 0.20,
}
```

**B. Change how hard it's throttled** — edit `src/quantbot/system.py`:
```python
VOL_TARGET = {"high_growth": 0.24, "mid_growth": 0.16, "safe_growth": 0.12}
PORTFOLIO_VOL_TARGET = 0.16   # ↑ raise to run hotter (more exposure, more drawdown)
```

After any change, **re-validate** before trusting it:
```bash
./.venv/bin/python scripts/run_backtest.py && ./.venv/bin/python scripts/stress_test.py
```
> Reminder from the research: don't chase a backtest number. If a change only looks
> good full-sample but not in the 2020/2022 windows, it's overfit — revert it.

---

## Part 4 — Deploy to Oracle Cloud (always-free ARM VM)

Full details in [`deploy/README.md`](deploy/README.md). Short version:

1. **Account:** create a free Oracle Cloud account — https://www.oracle.com/cloud/free/ (card to verify; not charged).
2. **Authenticate the CLI** (installed already: `oci --version`):
   ```bash
   oci setup config     # enter tenancy OCID, user OCID, region; paste the generated
                        # key into Console → Profile → API keys. Verify: oci iam region list
   ```
3. **Create the VM** — easiest is the **web Console** "Create instance" wizard (it
   auto-creates networking): shape **`VM.Standard.A1.Flex`**, **4 OCPU / 24 GB**,
   image **Ubuntu 22.04 (aarch64)**, add your SSH public key.
   *(If you see "out of host capacity," retry later or pick another region — it's
   Oracle's known ARM scarcity.)*
4. **Set it up** — SSH in and run one command:
   ```bash
   ssh ubuntu@<public-ip>
   curl -fsSL https://raw.githubusercontent.com/Muckmuckmuckmuck/ArbitrageBot/quantbot/deploy/setup_vm.sh | bash
   ```
   This installs deps, builds the venv, enables the daily timer (weekdays 22:00 UTC), and does a smoke run.
5. **Verify:**
   ```bash
   systemctl list-timers quantbot.timer      # next scheduled run
   journalctl -u quantbot.service -n 50      # last run's log
   cat ~/quantbot/data/live/target_*.json    # today's target book
   ```

At this point the bot runs daily and **logs** its target book. It does not place
orders yet — that's Part 5.

---

## Part 5 — Connect IBKR paper trading

Full details in [`deploy/ibgateway.md`](deploy/ibgateway.md). Short version:

1. Get an **IBKR paper trading** login (paper account id looks like `DU1234567`).
2. On the VM, install **IB Gateway + IBC** (auto-login) and run it headless under
   Xvfb via the provided `deploy/ibc.service`. Put your IBKR username/password in
   `~/ibc/config.ini` (`chmod 600` it), `TradingMode=paper`, API port `4002`.
3. **Point the bot at it** — edit `~/quantbot/.env`:
   ```
   QUANTBOT_MODE=PAPER
   IBKR_PORT=4002
   QUANTBOT_EXECUTE=false     # keep false for the first run to confirm connectivity
   ```
4. **Confirm, then enable orders:**
   ```bash
   cd ~/quantbot && ./.venv/bin/python scripts/daily_run.py    # should log "broker=ibkr"
   # once it connects cleanly, flip execution on:
   sed -i 's/QUANTBOT_EXECUTE=false/QUANTBOT_EXECUTE=true/' .env
   ```
   The daily timer now places **paper** orders to rebalance the account to the target book.

---

## Part 6 — Operate it

```bash
# on the VM:
tail -f ~/quantbot/data/logs/quantbot.log     # live app log
ls  ~/quantbot/data/live/                      # daily target-book + orders JSON
systemctl status quantbot.timer                # is the schedule active
journalctl -u ibc -n 50                        # IB Gateway / IBC status

# update to the latest code:
cd ~/quantbot && git pull && ./.venv/bin/pip install --prefer-binary -r requirements.txt
```

**Safety gates (all on by default):**
- `QUANTBOT_MODE=PAPER` — never touches real money.
- `QUANTBOT_EXECUTE=false` — dry-run: computes + logs orders, places none.
- No IB Gateway reachable → falls back to a simulated account (still logs a target book).
- Hard risk caps + a **drawdown kill-switch** (goes to cash if drawdown breaches the limit).

---

## Part 7 — Keep improving it (the research loop)

This is the honest version of "devise higher-return strategies." It works **today**,
manually, using the tools you already have:

1. **Generate evidence:** `run_backtest.py`, `stress_test.py`, `ablation.py` write
   artifacts to `data/backtests/`.
2. **Propose:** paste those results to **Claude Code** (this assistant) and ask for a
   specific, testable change (a new signal, a parameter, a sleeve tweak).
3. **Validate — the non-negotiable step:** test the change with `ablation.py` /
   `stress_test.py`. Keep it **only if it improves Sharpe AND holds up in the
   out-of-sample 2020/2022 windows.** Discard anything that only looks good
   full-sample. (This is López de Prado's rule: try enough strategies and one will
   look great by luck — the out-of-sample + robustness check is what separates edge
   from noise.)
4. **Deploy:** commit the winner, `git pull` on the VM.

A short-term **mean-reversion** signal knob (`reversion_weight`, from the stat-arb
literature) is already wired into the strategies as one dimension to explore.

> Optional next build: a fully-automated loop (headless Claude Code proposes → a
> deflated-Sharpe gate auto-accepts/rejects). Ask for it when you want it — the manual
> loop above is the same discipline without the plumbing.

---

## Part 8 — Gotchas (read once)

- **Install:** always `pip install --prefer-binary` (Intel Mac + Py3.9 otherwise tries
  to compile `cryptography` from Rust and fails).
- **`ib_async` needs Python 3.10+** — the Ubuntu 22.04 VM has it; a 3.9 Mac does not
  (live trading only runs on the VM).
- **ARM capacity** on Oracle's free tier is often exhausted — retry or change region.
- **Timer is UTC** (22:00, after the US close year-round); it doesn't shift for DST.
- **Keep `.env` and IBKR `config.ini` private** — they're git-ignored; never commit them.

---

## Part 9 — Git / repo

- `quantbot` branch = the current system. `main` = the old arbitrage-bot history (archived, untouched).
- **Make quantbot the default branch** (optional, one-time): GitHub → Settings →
  General → Default branch → switch to `quantbot`.
- **Push a change:**
  ```bash
  git add -A && git commit -m "your message" && git push origin HEAD:quantbot
  ```

---

## Command cheat sheet

| Goal | Command |
|---|---|
| Prove data works | `./.venv/bin/python scripts/fetch_check.py` |
| Full backtest | `./.venv/bin/python scripts/run_backtest.py` |
| Crisis/stress test | `./.venv/bin/python scripts/stress_test.py` |
| Signal ablation | `./.venv/bin/python scripts/ablation.py` |
| Return/protection dial | `./.venv/bin/python scripts/allocation_sweep.py` |
| Simulated rebalance | `./.venv/bin/python scripts/sim_trade.py` |
| The daily run (VM does this) | `./.venv/bin/python scripts/daily_run.py` |
| Run tests | `./.venv/bin/python -m pytest tests/ -q` |
