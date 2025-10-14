# 🧪 Arbitrage Test Script

## What This Does

Tests the **complete arbitrage cycle** with $0.50 of XRP:

### Test 1: Coinbase → Gemini
1. ✅ Buy $0.50 XRP on Coinbase
2. ✅ Transfer XRP to Gemini
3. ✅ Sell XRP on Gemini

### Test 2: Gemini → Coinbase
1. ✅ Buy $0.50 XRP on Gemini
2. ✅ Transfer XRP to Coinbase
3. ✅ Sell XRP on Coinbase

---

## Why Run This?

**Before risking real money with the bot**, this validates:
- ✅ API keys work correctly
- ✅ Orders execute properly
- ✅ Transfers complete successfully
- ✅ Address whitelisting is configured
- ✅ Full arbitrage cycle works end-to-end

**Cost**: ~$1.00 total (2 tests × $0.50 each)
**Time**: ~10-15 minutes (includes transfer wait times)

---

## Requirements

**Minimum balances:**
- Coinbase: $0.50 USD (for Test 1)
- Gemini: $0.50 USD (for Test 2)

**API Keys:**
- Same environment variables as the main bot
- Already configured if bot is working

---

## How to Run

### Option 1: Quick Test (Recommended)
```bash
python3 test_arbitrage_cycle.py
```

### Option 2: Run in Background (for Railway/remote)
```bash
nohup python3 test_arbitrage_cycle.py > test_output.log 2>&1 &
tail -f test_output.log
```

---

## What You'll See

### Excellent Logging
```
================================================================================
  CROSS-EXCHANGE ARBITRAGE TEST SUITE
================================================================================

[STEP 1] [0.0s] Initializing exchanges
--------------------------------------------------------------------------------
[12:34:56] ℹ️  API credentials found
[12:34:57] ✅ Coinbase initialized: 1062 markets
[12:34:58] ✅ Gemini initialized: 354 markets

[STEP 2] [2.1s] Check initial balances
--------------------------------------------------------------------------------
[12:34:58] ℹ️  Current balances:
   Coinbase USD: $17.36 free, $17.36 total
   Coinbase XRP: 0.0000 free, 0.0000 total
   Gemini USD: $0.81 free, $0.81 total
   Gemini XRP: 0.0000 free, 0.0000 total

================================================================================
  TEST 1: COINBASE → GEMINI ARBITRAGE CYCLE
================================================================================

[STEP 3] [3.2s] Buy $0.50 of XRP on Coinbase
--------------------------------------------------------------------------------
[12:35:01] ℹ️  Buying $0.50 of XRP/USD on Coinbase
   Current price: $0.5234
   Amount to buy: 0.9553 XRP
[12:35:02] ℹ️  Placing market buy order...
[12:35:03] ✅ Order placed: abc123
      Status: closed
      Filled: 0.9553
      Cost: $0.50
[12:35:05] ✅ Buy complete: 0.9553 XRP for $0.50

[STEP 4] [8.5s] Transfer 0.9553 XRP to Gemini
--------------------------------------------------------------------------------
[12:35:08] ℹ️  Transferring 0.9553 XRP from Coinbase to Gemini
[12:35:09] ✅ Deposit address: rN7n7otQDd6FczFgLdlqtyMVrn5x...
      Destination tag: 12345678
   Initial balance on destination: 0.0000 XRP
[12:35:10] ℹ️  Initiating withdrawal from Coinbase...
[12:35:11] ✅ Withdrawal initiated: xyz789
      Status: pending
[12:35:11] ℹ️  Monitoring Gemini for incoming XRP...
[12:35:11] ℹ️  Will check every 5s for up to 300s
[12:35:16] ℹ️  Check #1 (5s): 0.0000 XRP
[12:35:21] ℹ️  Check #2 (10s): 0.0000 XRP
[12:35:26] ℹ️  Check #3 (15s): 0.9553 XRP
[12:35:26] ✅ Transfer complete! Received 0.9553 XRP in 15s

[STEP 5] [23.8s] Sell 0.9553 XRP on Gemini
--------------------------------------------------------------------------------
[12:35:26] ℹ️  Selling 0.9553 XRP on Gemini
   Current price: $0.5236
   Expected revenue: $0.50
[12:35:27] ℹ️  Placing sell order...
[12:35:28] ✅ Order placed: def456
      Status: closed
[12:35:30] ✅ Sell complete: $0.49 received

[STEP 6] [28.9s] Calculate net result
--------------------------------------------------------------------------------
   Initial investment: $0.50
   Final revenue: $0.49
   Net result: $-0.01 (-2.00%)
[12:35:31] ⚠️  Test 1 completed with loss: $0.01

✅ Test 1 PASSED: Coinbase → Gemini cycle complete

================================================================================
  TEST SUMMARY
================================================================================
Total time: 45.2s (0.8 minutes)
Steps completed: 6
Warnings: 1
Errors: 0

⚠️  WARNINGS:
  1. Test 1 completed with loss: $0.01

🎉 ALL TESTS PASSED!
================================================================================
```

---

## Expected Results

### ✅ Success Scenario
```
🎉 ALL TESTS PASSED!
```
- Both cycles complete
- Small loss due to fees (~$0.01-0.02 per test)
- **Bot is ready to run!**

### ⚠️ Partial Success
```
Test 1 PASSED
Test 2 FAILED: Transfer timeout
```
- One direction works
- Other direction needs address whitelisting
- **Check email for approval links**

### ❌ Failure Scenarios

**"Buy failed: Insufficient funds"**
- Add more USD to the exchange

**"Transfer failed: Address not whitelisted"**
- Check email for Coinbase/Gemini approval
- Click "Approve" in the email
- Re-run test

**"Transfer timeout after 300s"**
- Transfer may still arrive (check manually)
- Network congestion (rare for XRP)
- Re-run test after 5-10 minutes

**"Sell failed: Insufficient balance"**
- Transfer didn't arrive yet
- Check balances manually
- Contact exchange support if stuck

---

## Troubleshooting

### Test Hangs on Transfer
**Normal!** XRP transfers usually take 4-30 seconds, but can take up to 5 minutes.

The script will:
- Check every 5 seconds
- Wait up to 5 minutes
- Show progress: `Check #1 (5s): 0.0000 XRP`

### First-Time Transfer Approval
**Expected!** Coinbase/Gemini will email you to approve the first transfer to a new address.

**What to do:**
1. Check your email
2. Click "Approve this withdrawal"
3. Re-run the test

**After approval:** All future transfers are automatic!

### Crypto Gets Stuck
**Don't panic!** The test logs exactly where your crypto is.

**If stuck on Coinbase:**
```bash
# Manual sell
python3 -c "
import ccxt, os
cb = ccxt.coinbase({'apiKey': os.getenv('COINBASE_API_KEY'), 'secret': os.getenv('COINBASE_API_SECRET')})
cb.load_markets()
balance = cb.fetch_balance()['free']['XRP']
print(f'Selling {balance} XRP')
order = cb.create_market_sell_order('XRP/USD', balance)
print(f'Sold for ${order[\"cost\"]:.2f}')
"
```

**If stuck on Gemini:**
```bash
# Manual sell
python3 -c "
import ccxt, os
gem = ccxt.gemini({'apiKey': os.getenv('GEMINI_API_KEY'), 'secret': os.getenv('GEMINI_API_SECRET')})
gem.load_markets()
balance = gem.fetch_balance()['free']['XRP']
price = gem.fetch_ticker('XRP/USD')['last']
print(f'Selling {balance} XRP at ${price}')
order = gem.create_limit_sell_order('XRP/USD', balance, price)
print(f'Order placed: {order[\"id\"]}')
"
```

---

## What Happens After Tests Pass?

### ✅ You're Ready!
```bash
# Run the full bot
python3 coinbase_gemini_bot.py
```

**The bot will:**
1. Use the same whitelisted addresses (no more approvals!)
2. Execute trades automatically
3. Transfer crypto seamlessly
4. Make profit 24/7

---

## Cost Breakdown

**Test 1 (CB→GEM):**
- Buy: $0.50 + ~$0.005 fee
- Transfer: $0.00 (free)
- Sell: ~$0.005 fee
- **Net loss: ~$0.01**

**Test 2 (GEM→CB):**
- Buy: $0.50 + ~$0.005 fee
- Transfer: $0.00 (free)
- Sell: ~$0.005 fee
- **Net loss: ~$0.01**

**Total cost: ~$0.02** (basically free!)

---

## FAQ

**Q: Why XRP?**
A: Fastest transfers (4-30 seconds), lowest fees, most reliable.

**Q: Can I use more than $0.50?**
A: Yes! Edit `TEST_AMOUNT_USD = 0.50` in the script. But $0.50 is enough to validate everything.

**Q: What if I only have funds on one exchange?**
A: The script will skip the test for the exchange without funds. Run at least one test.

**Q: How long does this take?**
A: ~5-10 minutes per test (mostly waiting for transfers).

**Q: Will this affect my main bot?**
A: No! The test uses the same API keys but doesn't interfere with the bot.

**Q: Can I run this while the bot is running?**
A: Yes, but not recommended. Stop the bot first to avoid confusion.

---

## Success Indicators

### ✅ Ready to Run Bot
- Both tests pass
- Transfers complete in < 60s
- Net loss < $0.05 per test
- No errors in logs

### ⚠️ Needs Attention
- One test passes, one fails
- Transfers take > 2 minutes
- Net loss > $0.10 per test
- Warnings in logs

### ❌ Not Ready
- Both tests fail
- Transfers timeout
- Orders don't execute
- Multiple errors in logs

---

## Next Steps

### After Tests Pass
1. ✅ **Manual rebalance** (see `MANUAL_REBALANCE_GUIDE.md`)
2. ✅ **Run the bot** (`python3 coinbase_gemini_bot.py`)
3. ✅ **Monitor logs** for first few trades
4. ✅ **Profit!** 💰

### If Tests Fail
1. ❌ Read error messages carefully
2. ❌ Check troubleshooting section above
3. ❌ Verify API keys and balances
4. ❌ Contact support if stuck

---

## Support

**Issues?** Check:
1. This README (troubleshooting section)
2. `FINAL_DEPLOYMENT_CHECKLIST.md`
3. `MANUAL_REBALANCE_GUIDE.md`

**Still stuck?** The test logs show exactly what went wrong!

