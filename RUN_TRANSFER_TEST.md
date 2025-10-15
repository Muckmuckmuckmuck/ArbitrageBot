# 🚀 Run Transfer Test NOW

## Quick Start

### Option 1: Run Locally (RECOMMENDED)

```bash
cd "/Users/jayreddy/Algotrading bot"

# Set environment variables (copy from Railway)
export COINBASE_API_KEY="your_key_here"
export COINBASE_SECRET="your_secret_here"
export GEMINI_API_KEY="your_key_here"
export GEMINI_SECRET="your_secret_here"

# Run the test
python3 test_transfer_mechanism.py
```

### Option 2: Run on Railway

1. **SSH into Railway:**
   ```bash
   railway run
   ```

2. **Run the test:**
   ```bash
   python3 test_transfer_mechanism.py
   ```

## What You'll See

The test will show you **every step** in real-time:

```
🧪 CRYPTO TRANSFER MECHANISM TEST
================================================================================

💰 INITIAL BALANCES
Coinbase: $17.36 USD, 0.0000 XRP
Gemini:   $0.81 USD, 0.0000 XRP

🧪 TEST 1: COINBASE → GEMINI TRANSFER
================================================================================

💰 BUYING $1.00 of XRP/USD on COINBASE
   Current price: $0.5234
   Will buy: 1.9106 XRP
   ✅ Order placed: abc123
   XRP balance: 1.9106

🚀 TRANSFERRING 1.9106 XRP from COINBASE → GEMINI
   📍 Getting deposit address on gemini...
   Address: rXXXXXXXXXXXXXXXXXXXX
   Tag: 123456789
   gemini balance before: 0.0000 XRP
   💸 Initiating withdrawal from coinbase...
   ✅ Withdrawal initiated: xyz789
   ⏳ Waiting for transfer to complete...
   (XRP transfers typically take 30-120 seconds)
   ⏳ Still waiting... (10s elapsed, balance: 0.0000)
   ⏳ Still waiting... (20s elapsed, balance: 0.0000)
   ⏳ Still waiting... (30s elapsed, balance: 0.0000)
   ⏳ Still waiting... (40s elapsed, balance: 1.9050)
   ✅ Transfer confirmed! gemini balance: 1.9050 XRP
   Time elapsed: 40s

💸 SELLING 1.9050 XRP on GEMINI
   Current price: $0.5236
   Expected USD: $0.99
   ✅ Order placed: def456
   USD balance: $1.78

✅ TEST 1 PASSED: Coinbase → Gemini transfer successful!
```

## Why This Test Matters

Your main bot is currently stuck because:
- ✅ It finds profitable opportunities (spreads > 3%)
- ❌ But fails on balance validation (Gemini has only $0.81)

**This test will prove:**
1. ✅ Transfers work correctly
2. ✅ Buy/sell mechanics work
3. ✅ We can then confidently fix the balance logic

## Current Issue Analysis

From your Railway logs:
```
IMX/USD | GEM→CB | Spread: 3.488% | Profit: $0.278 | ✅ TRADE
```

Bot found a **$0.28 profit opportunity** but didn't execute because:
```
❌ gemini insufficient USD: Shortfall: 0.20 USD
```

The balance manager needs fixing, but **first** we need to verify transfers work.

## Time Estimate

- **Test 1 (CB → GEM):** ~2 minutes
- **Test 2 (GEM → CB):** ~2 minutes  
- **Total:** ~5 minutes

## After the Test

- ✅ **If passes:** We'll fix the balance validation to use the $17.36 on Coinbase
- ❌ **If fails:** We'll fix whatever's broken in the transfer pipeline

Ready? Run it now! 🚀
