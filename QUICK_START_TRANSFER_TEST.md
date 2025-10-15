# 🚀 RUN TRANSFER TEST - 3 STEPS

## Your bot is finding opportunities but can't trade due to balance distribution.
## This test proves transfers work so we can fix the balance validation.

---

## ⚡ FASTEST WAY (30 seconds)

### Step 1: Open Terminal
```bash
cd "/Users/jayreddy/Algotrading bot"
```

### Step 2: Run Test
```bash
./run_transfer_test.sh
```

### Step 3: Watch Output
You'll see:
```
🧪 SIMPLE TRANSFER TEST: COINBASE → GEMINI
[1/7] 🔧 Initializing exchanges...
[2/7] 💰 Checking balances...
[3/7] 📊 Getting XRP price...
[4/7] 💸 Buying XRP on Coinbase...
[5/7] 📍 Getting Gemini XRP deposit address...
[6/7] 🚀 Transferring XRP to Gemini...
      ⏳ Waiting... (this takes 30-90 seconds)
      ✅ Transfer confirmed!
[7/7] 💵 Selling XRP on Gemini...
      ✅ Done!

✅ TEST COMPLETE!
```

**That's it!** ✅

---

## If Railway CLI Not Installed

Install it first:
```bash
npm i -g @railway/cli
railway login
railway link
```

Then run `./run_transfer_test.sh`

---

## Alternative: Direct Command

```bash
railway run python3 simple_transfer_test.py
```

---

## What This Proves

- ✅ Coinbase buy works
- ✅ Gemini deposit address works
- ✅ Transfer completes (no whitelist issues)
- ✅ Gemini sell works
- ✅ Your full arbitrage pipeline works

---

## Current Status

**Main Bot:** ✅ Still running (unchanged)
**Finding opportunities:** ✅ Yes (IMX 3.488%, API3 7.602%)
**Executing trades:** ❌ No (blocked by balance validation)

**This test bypasses that block to prove the transfer mechanism works.**

---

## After Test Passes

We have 2 options:

### Option A: Wait (Easy)
- Gemini's $8.19 "on hold" will settle in 1-5 days
- Bot will auto-trade once it settles
- No code changes needed

### Option B: Fix Now (30 min)
- Modify balance validation to allow single-exchange trades
- Bot trades immediately with your $17.36 on Coinbase
- Requires code changes & testing

---

## Current Balances

```
Coinbase: $17.36 USD ✅
Gemini:   $9.00 USD ✅
```

**Plenty to test with!**

---

## Cost

- Test amount: $1.00
- Fees: ~$0.01
- **Net cost: ~$0.01** (you get ~$0.99 back)

---

## Need Help?

If test fails, paste the error output and I'll debug it.

**Common issues:**
- API key problems → Check Railway env vars
- Whitelist issues → Coinbase/Gemini auto-whitelist on first use
- Master key error → Create "Primary" API key on Gemini

---

## Ready? Run This:

```bash
cd "/Users/jayreddy/Algotrading bot"
./run_transfer_test.sh
```

**Go!** 🚀

