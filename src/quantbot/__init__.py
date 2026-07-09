"""quantbot — Gemini crypto quant trading system with an AI research layer.

Architecture (data flows top to bottom):

    Data (Gemini WS/REST)
        -> Strategy Library (momentum, mean-reversion, ML, ...)
        -> Quant Engine (signals, sizing)
        -> Risk Engine (hard limits — cannot be overridden)
        -> Execution (PAPER by default; live orders gated)
        -> Store (trade/market history)
        -> Research Agent (Gemini Flash — proposes, never auto-deploys)

Design rule inherited from the predecessor arbitrage bot: the trading engine
stays stable and single-venue (Gemini only). The AI proposes improvements;
only backtested, approved changes ship.
"""

__version__ = "0.1.0"
