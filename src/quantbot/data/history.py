"""Historical price panels for backtesting & research.

Bulk daily bars from free sources (yfinance primary, Stooq fallback), cached to
parquet so "backtest a lot" doesn't re-hit the network. Returns an adjusted-close
panel: index = dates, columns = symbols. Adjusted close is all the daily
strategies + backtester need; richer OHLCV can be added later.

Deliberately NOT sourced from IBKR — its historical API has strict pacing limits
and would throttle heavy backtesting.
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import List, Sequence

import pandas as pd

from quantbot.config import CACHE_DIR

# A daily bot must never trade on stale prices: the cache is only good for a few
# hours, after which we refetch. (The cache key can't encode "today" because `end`
# is an open-ended sentinel, so freshness is enforced by file age.)
CACHE_MAX_AGE_HOURS = 12.0


def _cache_path(symbols: Sequence[str], start: str, end: str) -> Path:
    key = "|".join(sorted(symbols)) + f"|{start}|{end}"
    h = hashlib.sha1(key.encode()).hexdigest()[:16]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"prices_{h}.parquet"


def _is_fresh(cache: Path, max_age_hours: float = CACHE_MAX_AGE_HOURS) -> bool:
    if not cache.exists():
        return False
    return (time.time() - cache.stat().st_mtime) < max_age_hours * 3600


def _from_yfinance(symbols: List[str], start: str, end: str) -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(
        symbols, start=start, end=end, auto_adjust=True, progress=False, threads=True
    )
    if raw is None or len(raw) == 0:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"].copy()
    else:  # single symbol
        close = raw[["Close"]].copy()
        close.columns = [symbols[0]]
    return close.dropna(how="all")


def _from_stooq(symbols: List[str], start: str, end: str) -> pd.DataFrame:
    frames = {}
    for s in symbols:
        url = f"https://stooq.com/q/d/l/?s={s.lower()}.us&i=d"
        try:
            df = pd.read_csv(url)
        except Exception:
            continue
        if "Date" not in df.columns or "Close" not in df.columns:
            continue
        df["Date"] = pd.to_datetime(df["Date"])
        frames[s] = df.set_index("Date")["Close"]
    if not frames:
        return pd.DataFrame()
    close = pd.DataFrame(frames)
    return close.loc[start:end]


def get_volume(
    symbols: Sequence[str],
    start: str = "2010-01-01",
    end: str = "2100-01-01",
    use_cache: bool = True,
) -> pd.DataFrame:
    """Daily volume panel (dates x symbols) from yfinance. Used for volume-confirmation
    signals (the transferable idea from OHLCV foundation models like Kronos)."""
    symbols = list(dict.fromkeys(symbols))
    cache = _cache_path(symbols, start, end)
    cache = cache.with_name("vol_" + cache.name)
    if use_cache and _is_fresh(cache):
        return pd.read_parquet(cache)
    import yfinance as yf

    raw = yf.download(symbols, start=start, end=end, auto_adjust=True, progress=False, threads=True)
    if raw is None or len(raw) == 0:
        raise RuntimeError(f"No volume data for {symbols}")
    if isinstance(raw.columns, pd.MultiIndex):
        vol = raw["Volume"].copy()
    else:
        vol = raw[["Volume"]].copy()
        vol.columns = [symbols[0]]
    vol = vol.sort_index().dropna(how="all")
    vol = vol[[c for c in symbols if c in vol.columns]]
    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        vol.to_parquet(cache)
    return vol


def get_prices(
    symbols: Sequence[str],
    start: str = "2010-01-01",
    end: str = "2100-01-01",
    provider: str = "yfinance",
    use_cache: bool = True,
) -> pd.DataFrame:
    """Adjusted-close panel (dates x symbols). Falls back yfinance -> Stooq."""
    symbols = list(dict.fromkeys(symbols))  # de-dup, keep order
    cache = _cache_path(symbols, start, end)
    if use_cache and _is_fresh(cache):
        return pd.read_parquet(cache)

    close = pd.DataFrame()
    if provider == "yfinance":
        try:
            close = _from_yfinance(symbols, start, end)
        except Exception:
            close = pd.DataFrame()
        if close.empty:
            close = _from_stooq(symbols, start, end)
    else:
        close = _from_stooq(symbols, start, end)
        if close.empty:
            close = _from_yfinance(symbols, start, end)

    if close.empty:
        raise RuntimeError(f"No price data returned for {symbols} from any provider.")

    close = close.sort_index()
    # Keep only requested symbols that actually returned data.
    close = close[[c for c in symbols if c in close.columns]]
    if use_cache:
        close.to_parquet(cache)
    return close
