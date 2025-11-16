import os
import time
from decimal import Decimal
from typing import Any, Dict

import ccxt  # type: ignore


def _env(*names: str, default: str = "") -> str:
	"""
	Try multiple environment variable names and return the first non-empty.
	"""
	for name in names:
		val = os.environ.get(name, "")
		if val:
			return val
	return default


def build_gemini_client(*, sandbox: bool = True) -> ccxt.Exchange:
	api_key = _env("GEMINI_API_KEY", "GEMINI_KEY", "GEMINI_API", default="")
	api_secret = _env("GEMINI_API_SECRET", "GEMINI_SECRET", default="")
	if not api_key or not api_secret:
		raise RuntimeError("Missing GEMINI_API_KEY/GEMINI_API_SECRET in environment")

	# Per ccxt docs, set spot defaults and a safe nonce
	client = ccxt.gemini(
		{
			"apiKey": api_key,
			"secret": api_secret,
			"enableRateLimit": True,
			"options": {
				"nonce": "milliseconds",
				"defaultType": "spot",
				"defaultMarket": "spot",
			},
		}
	)
	client.set_sandbox_mode(sandbox)
	return client


def _sleep_ms(ms: int) -> None:
	time.sleep(ms / 1000.0)


def sanity_dump(m: Dict[str, Any]) -> str:
	return ", ".join(f"{k}={m.get(k)}" for k in ("symbol", "id", "type", "spot", "active", "limits"))


def run() -> None:
	print("[TEST] Gemini init - starting (sandbox mode)")
	client = build_gemini_client(sandbox=True)

	# Fetch markets and confirm common symbols exist
	markets = client.load_markets()
	assert isinstance(markets, dict) and len(markets) > 0, "No markets returned"
	for sym in ("BTC/USD", "ETH/USD", "SOL/USD"):
		if sym in markets:
			print(f"[TEST] market ok: {sanity_dump(markets[sym])}")
		else:
			print(f"[WARN] market not found in load_markets(): {sym}")

	# Pull an order book to validate REST access and symbol formatting
	for sym in ("BTC/USD", "ETH/USD"):
		ob = client.fetch_order_book(sym, limit=5)
		bid = ob["bids"][0][0] if ob["bids"] else None
		ask = ob["asks"][0][0] if ob["asks"] else None
		print(f"[TEST] orderbook {sym} top bid={bid} ask={ask}")
		assert bid and ask and ask > bid, f"Bad book for {sym}: bid={bid} ask={ask}"

	# Place and cancel a tiny post-only limit order (sandbox)
	# Use a very small size to avoid min-notional in sandbox; adjust if it errors
	symbol = "BTC/USD"
	ob = client.fetch_order_book(symbol, limit=5)
	best_bid = Decimal(str(ob["bids"][0][0])) if ob["bids"] else Decimal("0")
	price = (best_bid * Decimal("0.999")).quantize(Decimal("0.01"))
	amount = Decimal("0.00002")  # ~1 USD at 50k, adjust if sandbox rejects

	params: Dict[str, Any] = {
		"type": "exchange limit",  # Gemini requires explicit type
		"postOnly": True,          # maker-or-cancel behavior
	}

	try:
		order = client.create_order(symbol, "limit", "buy", float(amount), float(price), params)
		order_id = str(order.get("id") or order.get("order_id") or order.get("clientOrderId"))
		market_id = markets[symbol]["id"] if symbol in markets else symbol.replace("/", "")
		print(f"[TEST] placed post-only order id={order_id} symbol_id={market_id} price={price} amount={amount}")
		_sleep_ms(300)
		if order_id:
			client.cancel_order(order_id, symbol)
			print(f"[TEST] cancel ok id={order_id}")
		else:
			print("[WARN] no order id returned; skipping cancel")
	except ccxt.InsufficientFunds as e:  # type: ignore
		print(f"[SKIP] insufficient funds in sandbox for limit test: {e}")
	except ccxt.InvalidNonce as e:  # type: ignore
		raise AssertionError(f"Nonce error encountered - check serialization/clock: {e}") from e
	except ccxt.ExchangeError as e:  # type: ignore
		# Common in sandbox if min size/notional is hit; report clearly
		print(f"[WARN] exchange error placing/cancelling test order: {e}")

	print("[TEST] Gemini init - complete")


if __name__ == "__main__":
	run()


