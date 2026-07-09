"""Strategy interface.

A strategy consumes a price panel (dates x symbols) and returns a target-weight
panel over the same index. Each row's weights sum to <= 1.0; the remainder is
implicitly cash. This uniform contract lets the allocator combine sleeves and the
backtester simulate any strategy identically.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

import pandas as pd


def last_trading_day_per_month(index: pd.DatetimeIndex) -> List[pd.Timestamp]:
    """Actual last *trading* day in each calendar month present in the index.

    Returns pandas Timestamps (not numpy datetime64) so set-membership against a
    Timestamp iterated from the same index matches correctly.
    """
    s = pd.Series(index, index=index)
    lasts = s.groupby([index.year, index.month]).max()
    return [pd.Timestamp(x) for x in lasts]


class Strategy(ABC):
    name: str = "base"
    sleeve: str = "unassigned"

    @abstractmethod
    def target_weights(
        self,
        prices: pd.DataFrame,
        regime: Optional[pd.DataFrame] = None,
        volume: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """Target weights per date (index=dates, columns=symbols). Row sum <= 1.
        `volume` (optional) enables volume-confirmation of the signal."""
        raise NotImplementedError
