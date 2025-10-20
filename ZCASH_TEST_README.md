# 🧪 Zcash Arbitrage Test

## Overview
This test verifies the complete arbitrage cycle by:
1. **Finding ZEC price difference** between Coinbase and Gemini
2. **Buying $10 worth of ZEC** on the cheaper exchange
3. **Transferring ZEC** to the more expensive exchange
4. **Selling ZEC** on the more expensive exchange
5. **Calculating and reporting profit**

## What This Test Validates
✅ **Exchange Connectivity** - Both Coinbase and Gemini API access  
✅ **Price Discovery** - Real-time ZEC price fetching  
✅ **Arbitrage Detection** - Finding profitable opportunities  
✅ **Order Execution** - Market buy/sell orders  
✅ **Crypto Transfers** - ZEC withdrawal and deposit  
✅ **Profit Calculation** - End-to-end profitability  

## Test Parameters
- **Test Amount**: $10 USD
- **Crypto**: ZEC (Zcash)
- **Minimum Spread**: 0.5% (to ensure profitability)
- **Transfer Timeout**: 30 seconds (ZEC is fast)
- **Order Timeout**: 5 seconds per order

## Expected Results
If successful, you should see:
```
✅ ARBITRAGE TEST PASSED!
   The complete arbitrage cycle worked successfully:
   1. ✅ Found profitable opportunity
   2. ✅ Bought ZEC on cheaper exchange
   3. ✅ Transferred ZEC between exchanges
   4. ✅ Sold ZEC on expensive exchange
   🎉 System is ready for live trading!
```

## Risk Assessment
- **Low Risk**: Only $10 test amount
- **Fast Execution**: ZEC transfers are typically 2-5 minutes
- **Reversible**: Any stuck positions can be manually sold
- **Monitored**: Full logging of every step

## After Test Completion
Once the test passes:
1. **Restore main bot**: `cp Procfile.bot_backup Procfile`
2. **Deploy to Railway**: The main bot will resume normal operation
3. **Monitor performance**: Watch for real arbitrage opportunities

## Troubleshooting
If the test fails:
- Check API key permissions
- Verify ZEC is whitelisted on both exchanges
- Ensure sufficient USD/USDC balance
- Check network connectivity

## Files Modified
- `Procfile` - Points to test script
- `Procfile.zcash_test_backup` - Backup of original
- `zcash_arbitrage_test.py` - Test implementation

## Next Steps
After successful test:
1. Deploy optimized main bot with all improvements
2. Enable aggressive trading parameters
3. Monitor 24/7 for arbitrage opportunities
