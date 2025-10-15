# 🚀 Run Transfer Test RIGHT NOW

## 3 Simple Steps:

### Step 1: Get Your API Keys from Railway
1. Go to https://railway.app
2. Open your arbitrage bot project
3. Click **"Variables"** tab
4. You'll see these 4 variables - keep this tab open:
   - `COINBASE_API_KEY`
   - `COINBASE_SECRET`
   - `GEMINI_API_KEY`
   - `GEMINI_SECRET`

### Step 2: Edit the Run Script
```bash
# Open the script in a text editor
open run_transfer_test_local.sh
```

Or use VS Code:
```bash
code run_transfer_test_local.sh
```

**Replace the 4 placeholders** with your actual keys from Railway (copy-paste).

### Step 3: Run the Test
```bash
cd "/Users/jayreddy/Algotrading bot"
bash run_transfer_test_local.sh
```

## What You'll See

```
🧪 CRYPTO TRANSFER MECHANISM TEST
================================================================================

💰 INITIAL BALANCES
Coinbase: $17.36 USD, 0.0000 XRP
Gemini:   $0.81 USD, 0.0000 XRP

🧪 TEST 1: COINBASE → GEMINI
[1/3] 💵 Buying $1.00 of XRP on coinbase...
      ✅ Bought 1.845 XRP for $1.02 (price: $0.5420)
      
[2/3] 🚀 Transferring 1.845 XRP to gemini...
      📋 Deposit address: rDsbeom...
      ✅ Withdrawal initiated (tx: abc123...)
      ⏳ Waiting for arrival (checking every 10s)...
      ⏳ Not arrived yet... (10s)
      ⏳ Not arrived yet... (20s)
      ✅ ARRIVED! Gemini now has 1.845 XRP
      
[3/3] 💰 Selling 1.845 XRP on gemini...
      ✅ Sold 1.845 XRP for $0.98
      
✅ TEST 1 COMPLETE
   Cost: $1.02 | Received: $0.98 | Loss: $0.04 (4% - transfer fees)

🧪 TEST 2: GEMINI → COINBASE
[similar output...]

================================================================================
🎉 TRANSFER TEST COMPLETE
================================================================================
```

## What This Proves

- ✅ API keys work correctly
- ✅ Both exchanges can place orders
- ✅ Deposit addresses can be fetched
- ✅ Withdrawals can be initiated
- ✅ Transfers actually arrive
- ✅ You can sell after receiving

## Cost

**~$0.10 total** (you'll get most of it back when selling)

## Time

**3-5 minutes** (most time is waiting for XRP to transfer)

---

## Alternative: Manual Export (if the script doesn't work)

```bash
# Copy your keys from Railway and run these commands:
export COINBASE_API_KEY="your_key_here"
export COINBASE_SECRET="your_secret_here"
export GEMINI_API_KEY="your_key_here"
export GEMINI_SECRET="your_secret_here"

# Then run the test:
python3 test_transfer_mechanism.py
```

