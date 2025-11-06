# 📊 Market Making Spread Calculation

## How Market Making Works

### Example Trade:
1. **Place buy limit order** at $99.85 (0.15% below market of $100)
2. **Place sell limit order** at $100.15 (0.15% above market of $100)
3. **When both fill:**
   - Bought at $99.85
   - Sold at $100.15
   - **Spread captured**: $0.30 per $100 = **0.30%**

### Fees Paid:
- **Buy order** (maker fee): 0.40% on Coinbase, 0.10% on Gemini
- **Sell order** (maker fee): 0.40% on Coinbase, 0.10% on Gemini
- **Total fees**: 
  - Coinbase: 0.40% + 0.40% = **0.80%**
  - Gemini: 0.10% + 0.10% = **0.20%**

### Profit Calculation:
- **Coinbase**: 0.30% spread - 0.80% fees = **-0.50% (LOSS!)**
- **Gemini**: 0.30% spread - 0.20% fees = **+0.10% (PROFIT!)**

---

## ✅ CORRECT MINIMUM SPREADS

### Coinbase:
- **Minimum spread needed**: 0.80% (to cover fees)
- **With 0.20% buffer**: **1.00%** ✅ (Current setting is correct!)

### Gemini:
- **Minimum spread needed**: 0.20% (to cover fees)
- **With 0.20% buffer**: **0.40%** ✅ (Current setting is correct!)

---

## 🤔 BUT WAIT - You're Right About Something!

If the **market spread** (bid-ask spread) is 0.30%, we can't capture more than that!

### The Real Question:
**What is the actual bid-ask spread on these pairs?**

If typical spreads are:
- **BTC/USD**: 0.05-0.10% (very tight)
- **ETH/USD**: 0.05-0.10% (very tight)
- **SOL/USD**: 0.10-0.20% (tight)
- **Less liquid pairs**: 0.20-0.50% (wider)

Then:
- **Coinbase with 1.00% minimum**: Will only trade on pairs with >1.00% spread (rare!)
- **Gemini with 0.40% minimum**: Will only trade on pairs with >0.40% spread (more common)

---

## 💡 SOLUTION: Adjust Strategy

### Option 1: Lower Minimum Spread (More Trades, Lower Profit Margin)
```python
# Coinbase: 0.50% minimum (0.80% fees - 0.30% buffer = risky!)
# Gemini: 0.30% minimum (0.20% fees + 0.10% buffer = safe)
```

### Option 2: Use Market Spread, Not Our Grid Spacing
```python
# Instead of requiring 1.00% spread, require:
# - Market spread > 0.80% (Coinbase) or > 0.20% (Gemini)
# - Then place orders to capture portion of that spread
```

### Option 3: Multi-Level Orders (Capture More Spread)
```python
# Place multiple buy/sell levels:
# - Level 1: 0.10% from market (quick fills, lower profit)
# - Level 2: 0.20% from market (medium fills, medium profit)
# - Level 3: 0.30% from market (slow fills, higher profit)
# Total spread captured: 0.60% (enough for Coinbase!)
```

---

## 🎯 RECOMMENDATION

**You're partially right!** 0.30% spread CAN be profitable on Gemini (0.30% - 0.20% fees = 0.10% profit).

But for Coinbase, we need at least 0.80% to break even.

**Best approach:**
1. **Gemini**: Lower to 0.30% minimum (0.20% fees + 0.10% buffer)
2. **Coinbase**: Keep at 1.00% OR implement multi-level orders to capture more spread

Let me update the code with more reasonable minimums!

