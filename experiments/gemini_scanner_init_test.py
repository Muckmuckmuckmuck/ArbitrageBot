import os
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, List, Tuple

import ccxt  # type: ignore


def d(x: Any) -> Decimal:
	return Decimal(str(x))


def pct_bps(a: Decimal, b: Decimal) -> Decimal:
	if a <= 0 or b <= 0:
		return Decimal("0")
	return (a - b) / ((a + b) / Decimal("2")) * Decimal("10000")


def build_gemini_public() -> ccxt.Exchange:
	client = ccxt.gemini(
		{
			"enableRateLimit": True,
			"options": {
				"nonce": "milliseconds",
				"defaultType": "spot",
				"defaultMarket": "spot",
			},
		}
	)
	# Sandbox not required for public reads; leave default
	return client


def top_of_book_metrics(book: Dict[str, Any]) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
	bid = d(book["bids"][0][0]) if book.get("bids") else Decimal("0")
	ask = d(book["asks"][0][0]) if book.get("asks") else Decimal("0")
	bid_qty = d(book["bids"][0][1]) if book.get("bids") else Decimal("0")
	ask_qty = d(book["asks"][0][1]) if book.get("asks") else Decimal("0")
	return bid, ask, bid_qty, ask_qty


def compute_depth_usd(book: Dict[str, Any], price_hint: Decimal) -> Tuple[Decimal, Decimal, Decimal]:
	def side_value(levels: List[List[Any]]) -> Decimal:
		total = Decimal("0")
		for px, qty in levels[:5]:
			total += d(px) * d(qty)
		return total

	depth_bid = side_value(book.get("bids", []))
	depth_ask = side_value(book.get("asks", []))
	return depth_bid + depth_ask, depth_bid, depth_ask


def main() -> None:
	print("[TEST] Gemini scanner init - starting (public-only)")
	client = build_gemini_public()
	markets = client.load_markets()

	# Configurable floors via env (defaults chosen for visibility)
	target_edge_bps = Decimal(os.environ.get("SCANNER_MIN_NET_EDGE_BPS", "80"))
	maker_fee_bps = Decimal(os.environ.get("GEMINI_MAKER_FEE_BPS", "35"))
	taker_fee_bps = Decimal(os.environ.get("GEMINI_TAKER_FEE_BPS", "100"))
	slippage_floor_bps = Decimal(os.environ.get("SCANNER_SLIPPAGE_FLOOR_BPS", "10"))

	candidates = []
	for sym, meta in markets.items():
		# Gemini spot symbols are typically BASE/QUOTE; skip non-USD/USDC quotes by default
		if meta.get("spot") is not True:
			continue
		quote = str(meta.get("quote", "")).upper()
		if quote not in ("USD", "USDC"):
			continue

		try:
			book = client.fetch_order_book(sym, limit=5)
			bid, ask, bid_qty, ask_qty = top_of_book_metrics(book)
			if bid <= 0 or ask <= 0 or ask <= bid:
				continue
			spread_bps = pct_bps(ask, bid).quantize(Decimal("0.01"))
			mid = (ask + bid) / Decimal("2")
			depth_usd, top_bid_usd, top_ask_usd = compute_depth_usd(book, mid)

			# Simple model: net_edge = spread - (maker+maker) - slippage_floor
			# We assume maker on both legs for visibility; scanner only
			total_fee_bps = maker_fee_bps * Decimal("2")
			gross_edge_bps = spread_bps
			effective_edge_bps = gross_edge_bps - slippage_floor_bps
			net_edge_bps = effective_edge_bps - total_fee_bps
			effective_edge_bps = effective_edge_bps.quantize(Decimal("0.01"))
			net_edge_bps = net_edge_bps.quantize(Decimal("0.01"))

			marker = "GREEN_CHECK" if net_edge_bps >= target_edge_bps else "RED_X"
			reason = "edge_ok" if marker == "GREEN_CHECK" else f"edge<{target_edge_bps}"
			print(
				f"[SCAN:{marker}] GEMINI {sym} spread={spread_bps}bps gross={gross_edge_bps}bps slip={slippage_floor_bps}bps net={net_edge_bps}bps "
				f"maker_fee={maker_fee_bps}bps taker_fee={taker_fee_bps}bps depth_usd={depth_usd} top_bid={top_bid_usd} top_ask={top_ask_usd} "
				f"reason={reason}"
			)
			candidates.append((sym, net_edge_bps, depth_usd))
		except Exception as e:
			print(f"[SCAN:ERROR] {sym} error={e}")

	print("[TEST] Gemini scanner init - complete")


if __name__ == "__main__":
	main()

