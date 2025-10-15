# 🧪 QUICK START: Transfer Test

## Run This Test to Verify Transfers Work

**Cost**: $0.02-0.05 in fees  
**Time**: 10-15 minutes  
**Purpose**: Validate that XRP transfers work in both directions before trusting the bot with larger amounts

---

## Steps

### 1. Set Environment Variables (One-time)

```bash
export COINBASE_API_KEY='your-coinbase-key-here'
export COINBASE_SECRET_KEY='your-coinbase-secret-here'
export GEMINI_API_KEY='your-gemini-key-here'
export GEMINI_SECRET_KEY='your-gemini-secret-here'
```

**Get your keys from Railway:**
- Go to Railway dashboard → Your project → Variables tab
- Copy each value

---

### 2. Run the Test

```bash
cd "/Users/jayreddy/Algotrading bot"
python3 test_transfer.py
```

---

### 3. Watch the Output

You'll see each step in real-time:
- ✅ Buying XRP
- ✅ Transferring (with live monitoring)
- ✅ Selling XRP
- ✅ Results summary

**This takes 10-15 minutes** because XRP transfers take ~60-120 seconds each.

---

## What Success Looks Like

```
🎉 ALL TESTS PASSED!
   Transfers work in both directions!
   Bot is ready for live trading!

Total cost: $0.02
```

---

## If It Fails

The script will show:
- **Exactly what failed** (buy, transfer, or sell)
- **Which exchange** it failed on
- **The error message** to help debug
- **What to check** next

Common issues:
1. **Insufficient balance** → Add $0.50 to that exchange
2. **Address not whitelisted** → Coinbase/Gemini auto-whitelist on first use
3. **Transfer timeout** → XRP may still arrive (check manually)

---

## After Test Passes

**Your bot is ready!** The main bot will now:
1. Find profitable opportunities
2. Place aggressive limit orders (0.01% from market)
3. Complete transfers successfully
4. Generate consistent profits

Check Railway logs to see it working!

