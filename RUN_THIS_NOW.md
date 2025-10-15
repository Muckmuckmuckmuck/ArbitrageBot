# 🚀 RUN THE TRANSFER TEST NOW

## What This Does
This script will:
1. Buy $1 of XRP on Coinbase
2. Transfer it to Gemini (should take 30-90 seconds)
3. Sell it on Gemini

**This tests your full transfer pipeline in isolation.**

## Current Balances
- Coinbase: $17.36 USD ✅
- Gemini: $9.00 USD ✅

**You have plenty of funds to test.**

## How to Run

### Option 1: Via Railway (Easiest - Recommended)

```bash
# In Railway dashboard, go to your bot deployment
# Click "Deployments" tab
# Click the three dots (•••) next to your latest deployment
# Select "Restart" or "Redeploy"

# Then run this command in Railway's shell:
railway run python3 simple_transfer_test.py
```

### Option 2: Locally (If Railway is slow)

```bash
# Step 1: Set environment variables
export COINBASE_API_KEY="your_key_here"
export COINBASE_SECRET="your_secret_here"
export GEMINI_API_KEY="your_key_here"
export GEMINI_SECRET="your_secret_here"

# Step 2: Run test
cd "/Users/jayreddy/Algotrading bot"
python3 simple_transfer_test.py
```

## What You'll See

```
🧪 SIMPLE TRANSFER TEST: COINBASE → GEMINI
===============================================================================

[1/7] 🔧 Initializing exchanges...
      ✅ Connected to Coinbase and Gemini

[2/7] 💰 Checking balances...
      Coinbase: $17.36 USD, 0.0000 XRP
      Gemini:   $9.00 USD, 0.0000 XRP

[3/7] 📊 Getting XRP price...
      XRP price: $0.5234
      Will buy: 1.91 XRP for $1.00

[4/7] 💸 Buying XRP on Coinbase...
      ✅ Order placed: abc123
      ✅ Bought 1.91 XRP

[5/7] 📍 Getting Gemini XRP deposit address...
      Address: rDsbeomae4FXwgQTJp9Rs64Qg9vDiTCdBv
      Tag: 123456789

[6/7] 🚀 Transferring 1.91 XRP to Gemini...
      ✅ Withdrawal initiated: xyz789
      ⏳ Waiting for transfer to complete (XRP is fast, ~30-90 seconds)...
      ⏳ Still waiting... (15s elapsed, Gemini XRP: 0.0000)
      ⏳ Still waiting... (30s elapsed, Gemini XRP: 0.0000)
      ⏳ Still waiting... (45s elapsed, Gemini XRP: 0.0000)
      ✅ Transfer confirmed! Gemini now has 1.91 XRP
      Time taken: 60s

[7/7] 💵 Selling XRP on Gemini...
      ✅ Sell order placed: def456
      Amount: 1.91 XRP at $0.5182
      ✅ Gemini USD balance: $9.99

===============================================================================
✅ TEST COMPLETE!
===============================================================================
Successfully bought $1.00 XRP on Coinbase,
transferred to Gemini, and sold for USD.

This confirms your transfer mechanism is working! 🎉
===============================================================================
```

## If It Fails

### Error: "Coinbase has insufficient USD"
- **Cause:** Funds might be on hold
- **Fix:** Wait 1-2 hours for recent deposits/trades to settle

### Error: "Buy failed: requires a price argument"
- **Cause:** CCXT version issue
- **Fix:** Already handled in script - shouldn't happen

### Error: "Transfer timed out after 300s"
- **Cause:** XRP network congestion (rare)
- **Fix:** Check Gemini manually - XRP will still arrive, just slower

### Error: "Gemini sign() requires account-key"
- **Cause:** You're using a Master API key
- **Fix:** Create a new "Primary" API key on Gemini (Settings → API)

## Why This Test Matters

**Your main bot isn't getting transfers because:**
1. Bot finds profitable opportunities ✅
2. Bot tries to validate balances ❌ (fails due to balance distribution)
3. Bot never reaches the buy/transfer/sell code ⏸️

**This test bypasses balance validation** to prove the core transfer mechanism works.

Once this passes, you'll know:
- ✅ API keys work
- ✅ Withdrawals work
- ✅ Transfers complete
- ✅ Addresses are whitelisted
- ✅ Tags are configured correctly

Then we can fix the main bot's balance validation logic.

## Next Steps After Test Passes

1. **Keep main bot running** (it's fine, just waiting for better balance distribution)
2. **Fix balance validation** to allow single-exchange trades
3. **Or wait** for Gemini's "on hold" funds to settle

## Push to Railway

I'll push this test script to your repository now so Railway has it.

Ready? Let's run it! 🚀

