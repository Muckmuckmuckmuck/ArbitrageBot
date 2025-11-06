# 📊 Minimum Spread Calculation for Profitability

## Fee Structure

### Coinbase:
- Maker fee: 0.40% per trade
- Total fees per round trip (buy + sell): **0.80%**

### Gemini:
- Maker fee: 0.10% per trade  
- Total fees per round trip (buy + sell): **0.20%**

---

## How Grid Spacing Works

### Current Logic:
1. Check market spread (bid-ask spread)
2. Set grid spacing = 50% of market spread (min 0.15%, max 0.5%)
3. Place buy order at: `current_price * (1 - grid_spacing/100)`
4. Place sell order at: `current_price * (1 + grid_spacing/100)`
5. **Spread captured** = distance between buy and sell prices

### Example:
- Market spread: 1.00%
- Grid spacing: 50% of 1.00% = 0.50%
- Buy at: $100 * 0.995 = $99.50
- Sell at: $100 * 1.005 = $100.50
- **Spread captured**: 1.00% ($100.50 / $99.50 - 1)

Wait, that's not right. Let me recalculate:

- Current price (mid): $100
- Buy at: $100 * (1 - 0.005) = $99.50 (0.50% below)
- Sell at: $100 * (1 + 0.005) = $100.50 (0.50% above)
- **Spread captured**: ($100.50 - $99.50) / $99.50 = 1.00%

So if grid spacing is 0.50%, we capture 1.00% spread.

But wait, the code says grid spacing is 50% of market spread. So:
- If market spread is 1.00%, grid spacing = 0.50%
- We capture: 1.00% (0.50% below + 0.50% above)
- Fees: 0.80% (Coinbase)
- **Profit**: 1.00% - 0.80% = **0.20%** ✅

---

## Minimum Market Spread Required

### Coinbase (0.80% fees):
To break even:
- Need to capture ≥ 0.80% spread
- If we capture 50% of market spread, need market spread ≥ 1.60%
- But grid spacing has min 0.15%, so we always capture at least 0.30%

To be profitable (0.20% profit):
- Need to capture ≥ 1.00% spread
- If market spread is 1.00%, grid spacing = 0.50%, we capture 1.00%
- **Minimum market spread: 1.00%** ✅

### Gemini (0.20% fees):
To break even:
- Need to capture ≥ 0.20% spread
- If market spread is 0.40%, grid spacing = 0.20%, we capture 0.40%
- But grid spacing min is 0.15%, so we capture at least 0.30%

To be profitable (0.10% profit):
- Need to capture ≥ 0.30% spread
- If market spread is 0.30%, grid spacing = 0.15% (min), we capture 0.30%
- **Minimum market spread: 0.30%** ✅

---

## ✅ CORRECT MINIMUM SPREADS

### Coinbase:
- **Minimum market spread: 1.00%**
  - Grid spacing: 0.50% (50% of 1.00%)
  - Spread captured: 1.00%
  - Fees: 0.80%
  - **Profit: 0.20%** ✅

### Gemini:
- **Minimum market spread: 0.30%**
  - Grid spacing: 0.15% (min, since 50% of 0.30% = 0.15%)
  - Spread captured: 0.30%
  - Fees: 0.20%
  - **Profit: 0.10%** ✅

---

## ⚠️ IMPORTANT NOTE

The grid spacing logic uses `min(max(spread * 0.5, 0.15), 0.5)`:
- If market spread is 0.30%, grid spacing = 0.15% (min)
- We capture 0.30% spread
- This works for Gemini (0.20% fees) but NOT for Coinbase (0.80% fees)

So for Coinbase, we MUST require market spread ≥ 1.00% to be profitable.

