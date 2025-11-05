# 🔍 Intra-Exchange Arbitrage Scanner

## Overview

Scans **1,000+ cryptos** on Coinbase and Gemini to find the most profitable USD/USDC arbitrage opportunities after accounting for:
- ✅ Trading fees (maker + taker)
- ✅ Slippage (order book depth)
- ✅ Volatility (24h data)
- ✅ Order book depth (liquidity)
- ✅ Volume (activity level)

## How It Works

### 1. **Discovery Phase**
- Scans all available markets on Coinbase and Gemini
- Identifies cryptos with both USD and USDC trading pairs
- Filters to active markets only

### 2. **Analysis Phase**
For each crypto with both pairs:
- Fetches real-time prices for USD and USDC pairs
- Calculates raw spread percentage
- Gets order book data for slippage estimation
- Retrieves 24h volume and volatility data
- Calculates order book depth

### 3. **Profitability Calculation**
```
Net Profit = Raw Spread - Maker Fee - Taker Fee - Total Slippage
```

### 4. **Ranking Algorithm**
Uses the **ArbScore** formula:
```
ArbScore = (Volatility × QuotePairCount × DepthFactor × VolumeFactor × NetProfit) / (AvgSpread × FeeRate)
```

Higher score = better opportunity

## Usage

### Run the Scanner:
```bash
python intra_exchange_arbitrage_scanner.py
```

### Output:
1. **Real-time progress** - Shows opportunities as they're found
2. **Top 50 ranked opportunities** - Best to worst
3. **JSON file** - `arbitrage_opportunities.json` with full data

## Output Format

### Console Output:
```
#1   | COINBASE | API3     | Profit:  0.523% | Spread:  1.023% | Fees:  0.600% | Slippage:  0.200% | Score:   45.23
     API3/USD = $2.500000 | API3/USDC = $2.526000
     Volume: $5,000 | Depth USD: $10,000 | Depth USDC: $12,000 | Volatility: 3.50%
```

### JSON Output:
```json
{
  "scan_timestamp": "2025-11-05T01:15:00",
  "scan_stats": {
    "total_pairs_scanned": 1500,
    "opportunities_found": 47,
    "coinbase_opportunities": 28,
    "gemini_opportunities": 19,
    "scan_duration_seconds": 45.2
  },
  "opportunities": [
    {
      "exchange": "coinbase",
      "crypto": "API3",
      "usd_pair": "API3/USD",
      "usdc_pair": "API3/USDC",
      "usd_price": 2.500000,
      "usdc_price": 2.526000,
      "raw_spread_percent": 1.023,
      "maker_fee": 0.400,
      "taker_fee": 0.600,
      "estimated_slippage": 0.200,
      "net_profit_percent": 0.523,
      "volume_usd": 5000,
      "order_book_depth_usd": 10000,
      "order_book_depth_usdc": 12000,
      "volatility_24h": 3.50,
      "arb_score": 45.23,
      "rank": 1
    }
  ]
}
```

## Key Metrics Explained

### **Net Profit Percent**
- **What**: Profit after all costs (fees + slippage)
- **Minimum**: 0.05% (0.0005) to be considered
- **Good**: 0.2-0.5% (0.002-0.005)
- **Excellent**: >0.5% (0.005+)

### **Raw Spread Percent**
- **What**: Price difference between USD and USDC pairs
- **Example**: API3/USD = $2.50, API3/USDC = $2.52 → 0.8% spread

### **Maker/Taker Fees**
- **Coinbase**: 0.40% maker, 0.60% taker
- **Gemini**: 0.10% maker, 0.35% taker
- **Best case**: Pay maker on one side (0.40% or 0.10%)

### **Estimated Slippage**
- **What**: Price impact of your trade size
- **Based on**: Order book depth
- **Typical**: 0.1-0.3% for $100 trades
- **Higher**: For larger trades or shallow books

### **Arb Score**
- **What**: Overall profitability ranking
- **Factors**: Spread, fees, volatility, depth, volume
- **Higher = Better**: Top opportunities have scores >20

## Best Opportunities Criteria

### **Ideal Characteristics:**
1. ✅ **Net Profit > 0.2%** - Profitable after all costs
2. ✅ **Raw Spread > 0.5%** - Enough room for fees
3. ✅ **Volume > $10k/day** - Liquid enough to trade
4. ✅ **Depth > $50k** - Deep order books = low slippage
5. ✅ **Volatility 2-6%** - Enough movement, not too volatile
6. ✅ **Depth Asymmetry** - Different USD vs USDC depth = better opportunities

### **Avoid:**
- ❌ Net profit < 0.05% - Too small to be profitable
- ❌ Volume < $1k/day - Too illiquid
- ❌ Depth < $10k - High slippage risk
- ❌ Volatility > 10% - Too risky

## Strategy Recommendations

### **Top 10 Opportunities (Conservative)**
- Focus on cryptos ranked #1-10
- These have highest scores and best risk/reward
- Expected: 0.2-0.5% profit per trade

### **Top 20-30 Opportunities (Moderate)**
- Add more pairs for diversification
- Slightly lower scores but still profitable
- Expected: 0.1-0.3% profit per trade

### **Top 50 Opportunities (Aggressive)**
- Maximum diversification
- Some opportunities may be riskier
- Expected: 0.05-0.2% profit per trade

## Integration with Trading Bot

After scanning, use the results to:

1. **Update `CURRENCY_PAIRS`** in `coinbase_gemini_config.py`
2. **Set position sizes** based on order book depth
3. **Adjust spread thresholds** based on actual opportunities
4. **Prioritize high-score pairs** for trading

## Frequency

### **Recommended Scan Schedule:**
- **Daily**: Full scan to find new opportunities
- **Hourly**: Quick scan of top 50 pairs to update prices
- **Real-time**: Monitor top 10 pairs continuously

### **When to Re-scan:**
- After major market events
- When new coins are listed
- If profitability drops
- Weekly for full scan

## Performance

### **Expected Scan Time:**
- **1,000 cryptos**: ~30-60 seconds
- **500 cryptos**: ~15-30 seconds
- **100 cryptos**: ~5-10 seconds

### **API Rate Limits:**
- Scanner includes rate limiting
- Respects exchange limits
- Can be adjusted for faster scans

## Troubleshooting

### **No Opportunities Found:**
- Market conditions may be unfavorable
- Spreads may be too tight
- Fees may be too high
- Try again during volatile periods

### **Low Scores:**
- Normal - most opportunities are small
- Focus on top 10-20
- Even 0.1% profit is valuable with high frequency

### **API Errors:**
- Check API keys are valid
- Verify exchange connectivity
- Check rate limits

## Next Steps

1. **Run the scanner** to find opportunities
2. **Review top 50** pairs
3. **Update trading bot** with best pairs
4. **Monitor performance** and re-scan weekly

---

**Remember**: The scanner finds opportunities, but profitability depends on:
- Execution speed
- Order placement strategy
- Market conditions
- Risk management

