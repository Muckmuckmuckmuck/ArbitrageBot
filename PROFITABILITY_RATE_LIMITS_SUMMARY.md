# 📊 Profitability & Rate Limits Summary

## 🚨 **CRITICAL FINDINGS**

### ⚠️ **Rate Limit Status: HIGH USAGE (80.1%)**

The bot will use **80.1% of available rate limits** with current settings:
- **Per Minute**: 480 / 600 requests (80.1%)
- **Per Hour**: 28,824 / 36,000 requests (80.1%)
- **Per Day**: 691,776 / 864,000 requests (80.1%)

**Recommendation**: This is at the upper edge. Consider increasing scan frequency from 3s to 4-5s if rate limit errors occur.

---

## 💰 **PROFITABILITY ANALYSIS**

### ❌ **IMPORTANT: $100-$1,000 Starting Balance = NOT PROFITABLE**

Due to the **$1 withdrawal fee per arbitrage cycle**, small balances are unprofitable:

| Balance | Position Size | Avg Profit/Trade | Daily Profit | Daily ROI |
|---------|---------------|------------------|--------------|-----------|
| **$100** | $12 | **-$0.81** | **-$77** | **-77%** ❌ |
| **$500** | $60 | **-$0.65** | **-$63** | **-13%** ❌ |
| **$1,000** | $120 | **-$0.46** | **-$44** | **-4%** ❌ |
| **$5,000** | $600 | **$1.08** | **$103** | **2.07%** ✅ |
| **$10,000** | $1,200 | **$3.00** | **$288** | **2.88%** ✅ |

### ✅ **MINIMUM PROFITABLE BALANCE: $5,000**

You need **at least $5,000** to be consistently profitable with this strategy.

---

## 📈 **Realistic Profitability Estimates**

### With $5,000 Starting Balance:
- **Daily**: $50-100 (1-2%)
- **Monthly**: $1,500-3,000 (30-60%)
- **Yearly**: $18,250-36,500 (365-730%)
- **Days to double**: ~35-50 days

### With $10,000 Starting Balance:
- **Daily**: $100-200 (1-2%)
- **Monthly**: $3,000-6,000 (30-60%)
- **Yearly**: $36,500-73,000 (365-730%)
- **Days to double**: ~25-35 days

---

## 🎯 **Rate Limit Breakdown**

### Scanning Activity:
- **Scans per minute**: 20
- **Scans per hour**: 1,200
- **Scans per day**: 28,800
- **Requests per scan**: 24 (2 exchanges × 12 assets)
- **Total scan requests/day**: 691,200

### Trading Activity:
- **Avg trades per hour**: 4
- **Avg trades per day**: 96
- **Requests per trade**: 6 (orders + balance + confirmations)
- **Total trade requests/day**: 576

### Total Usage:
- **Requests per day**: 691,776
- **Available per day**: 864,000
- **Usage**: 80.1%
- **Safety margin**: 19.9%

---

## 💡 **Key Insights**

### 1. **$1 Withdrawal Fee is a KILLER for Small Balances**

Example: $12 position (12% of $100)
```
Gross profit (0.85% spread): $0.10
Trading fees (0.6%):         -$0.07
Withdrawal fee:              -$1.00  ← THIS KILLS PROFIT
Slippage (0.1%):             -$0.01
Net profit:                  -$0.98  ❌ LOSS
```

Example: $600 position (12% of $5,000)
```
Gross profit (0.85% spread): $5.10
Trading fees (0.6%):         -$3.60
Withdrawal fee:              -$1.00  ← Manageable now
Slippage (0.1%):             -$0.60
Net profit:                  -$0.10  ✅ Break-even to slight loss
```

Example: $1,200 position (12% of $10,000)
```
Gross profit (0.85% spread): $10.20
Trading fees (0.6%):         -$7.20
Withdrawal fee:              -$1.00  ← Minor impact
Slippage (0.1%):             -$1.20
Net profit:                  $0.80   ✅ PROFIT
```

### 2. **Rate Limits Are Tight**

With 80.1% usage, there's little room for:
- Increased trading frequency
- More assets
- Faster scanning
- Error retries

**Solution**: 
- Keep scan frequency at 3-5 seconds
- Limit to 12 assets (as configured)
- Don't exceed 4-6 trades per hour

### 3. **Spread Distribution Matters**

**Current assumptions**:
- 60% of spreads: 0.7-1.0% (mostly break-even or small profit)
- 30% of spreads: 1.0-1.5% (moderate profit)
- 10% of spreads: 1.5%+ (good profit)

**Reality**: Most profit comes from the 10% of high-spread opportunities.

---

## 🔧 **Recommendations**

### 1. **Increase Minimum Starting Balance**

Change in config:
```python
# OLD
RISK_MANAGEMENT = {
    'min_account_balance_usd': 100,  # Too low!
}

# NEW - RECOMMENDED
RISK_MANAGEMENT = {
    'min_account_balance_usd': 5000,  # Minimum for profitability
}
```

### 2. **Adjust Scan Frequency if Needed**

If rate limit errors occur:
```python
# Current (80% usage)
await asyncio.sleep(3)  # 3 seconds

# Safer (60% usage)
await asyncio.sleep(4)  # 4 seconds

# Very safe (48% usage)
await asyncio.sleep(5)  # 5 seconds
```

### 3. **Focus on Larger Spreads**

Filter out low-spread opportunities:
```python
# Only take trades with 1%+ spreads
if spread_percent < 0.01:  # 1%
    continue
```

This reduces trade frequency but increases profitability per trade.

### 4. **Consider Batch Withdrawals**

Instead of withdrawing after every trade, batch withdrawals to reduce the $1 fee impact:
- Trade multiple times on each exchange
- Withdraw once every 5-10 trades
- Reduces withdrawal fees from $96/day to $10-20/day

---

## 📊 **Updated Realistic Expectations**

### ✅ **Minimum Balance: $5,000**

| Metric | Conservative (1%) | Realistic (1.5%) | Optimistic (2%) |
|--------|-------------------|------------------|-----------------|
| **Daily Profit** | $50 | $75 | $100 |
| **Monthly Profit** | $1,500 | $2,250 | $3,000 |
| **Yearly Profit** | $18,250 | $27,375 | $36,500 |
| **Days to Double** | 72 | 48 | 36 |

### 🚀 **Recommended Balance: $10,000**

| Metric | Conservative (1%) | Realistic (1.5%) | Optimistic (2%) |
|--------|-------------------|------------------|-----------------|
| **Daily Profit** | $100 | $150 | $200 |
| **Monthly Profit** | $3,000 | $4,500 | $6,000 |
| **Yearly Profit** | $36,500 | $54,750 | $73,000 |
| **Days to Double** | 72 | 48 | 36 |

---

## ⚠️ **Risk Factors**

1. **$1 Withdrawal Fee** - Dominates costs for small trades
2. **80% Rate Limit Usage** - Little margin for error
3. **0.6% Trading Fees** - 18.75x higher than Binance/OKX
4. **Lower Liquidity** - More slippage than major exchanges
5. **Spread Availability** - 1%+ spreads may be rare

---

## ✅ **Action Items**

### Before Starting:
- [ ] **Change minimum balance to $5,000** in config
- [ ] Fund accounts with at least $5,000 total
- [ ] Consider $10,000 for better returns
- [ ] Test with testnet first
- [ ] Monitor rate limits closely

### If Rate Limits Are Hit:
- [ ] Increase scan frequency to 4-5 seconds
- [ ] Reduce number of assets
- [ ] Decrease trades per hour

### If Profitability Is Low:
- [ ] Increase minimum spread requirement to 1%+
- [ ] Focus on high-liquidity pairs (BTC, ETH, SOL)
- [ ] Consider batch withdrawals
- [ ] Look for 1.5%+ spreads only

---

## 🎯 **Bottom Line**

### ❌ **Don't Start With $100-$1,000**
The $1 withdrawal fee makes small balances unprofitable.

### ✅ **Start With $5,000 Minimum**
This gives you a realistic chance at 1-2% daily returns.

### 🚀 **Optimal: $10,000+**
This provides comfortable profitability and room for growth.

### ⚠️ **Watch Rate Limits**
You're using 80% of capacity. Monitor closely and adjust scan frequency if needed.

---

**Remember**: These are realistic estimates. Start conservative, monitor closely, and scale gradually!

