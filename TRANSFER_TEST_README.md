# 🧪 Transfer Test Script

## What This Does

Tests if crypto transfers work between Coinbase and Gemini with **$0.50 of XRP**.

### Test 1: Coinbase → Gemini
1. Buy $0.50 XRP on Coinbase
2. Transfer to Gemini
3. Sell on Gemini
4. Measure net loss (should be just fees, ~$0.01)

### Test 2: Gemini → Coinbase
1. Buy $0.50 XRP on Gemini
2. Transfer to Coinbase
3. Sell on Coinbase
4. Measure net loss (should be just fees, ~$0.01)

---

## Why Run This?

Your bot keeps finding profitable opportunities but we need to verify:
- ✅ Transfers actually work
- ✅ Deposit addresses are correct
- ✅ XRP arrives on destination exchange
- ✅ Full cycle completes successfully

**Cost**: ~$0.02-0.05 total (fees + slippage)  
**Time**: ~10-15 minutes (includes 2 transfer wait times)

---

## Requirements

**Minimum balances:**
- Coinbase: $0.50 USD (for Test 1)
- Gemini: $0.50 USD (for Test 2, can skip if not enough)

**API Keys:**
- Same environment variables as the main bot

---

## How to Run

### Option 1: Local (Requires .env file)

```bash
# Create .env file with your keys
cat > .env << 'EOF'
COINBASE_API_KEY=your-key-here
COINBASE_SECRET_KEY=your-secret-here
GEMINI_API_KEY=your-key-here
GEMINI_SECRET_KEY=your-secret-here
EOF

# Run the test
python3 test_transfer.py
```

### Option 2: Export Variables (One-time)

```bash
# Export keys in terminal
export COINBASE_API_KEY='your-key-here'
export COINBASE_SECRET_KEY='your-secret-here'
export GEMINI_API_KEY='your-key-here'
export GEMINI_SECRET_KEY='your-secret-here'

# Run the test
python3 test_transfer.py
```

---

## Expected Output

### Successful Test

```
================================================================================
  INITIALIZING EXCHANGES
================================================================================

[00:00:00] INFO  | ✅ Coinbase initialized
[00:00:00] INFO  | ✅ Gemini initialized

================================================================================
  TEST 1: COINBASE → GEMINI TRANSFER
================================================================================

[00:00:01] INFO  | Step 1: Check initial balances
[00:00:01] INFO  |    Coinbase: $17.07 USD, 0.0000 XRP
[00:00:01] INFO  |    Gemini:   $3.26 USD, 0.0000 XRP

================================================================================

[00:00:02] INFO  | Step 2: Buy XRP on Coinbase
[00:00:02] INFO  | Buying $0.50 of XRP on Coinbase...
[00:00:02] INFO  |    Price: $0.5234
[00:00:02] INFO  |    Amount: 0.9553 XRP
[00:00:02] INFO  | ✅ Buy order placed: abc-123
[00:00:04] INFO  | ✅ Balance after buy: 0.9553 XRP

================================================================================

[00:00:05] INFO  | Step 3: Transfer XRP from Coinbase to Gemini
[00:00:05] INFO  | Transferring 0.9553 XRP from Coinbase to Gemini...
[00:00:05] INFO  |    Getting XRP deposit address on Gemini...
[00:00:06] INFO  |    Deposit address: rABC123def456...
[00:00:06] INFO  |    Destination tag: 987654321
[00:00:06] INFO  |    Initial Gemini balance: 0.0000 XRP
[00:00:06] INFO  |    Initiating withdrawal from Coinbase...
[00:00:07] INFO  | ✅ Withdrawal initiated: withdraw-789
[00:00:07] INFO  |    Txn ID: 0x123abc...
[00:00:07] INFO  |    Monitoring Gemini balance (timeout: 300s)...
[00:00:42] INFO  |    [35s] Still waiting... (balance: 0.0000)
[00:01:07] INFO  | ✅ TRANSFER COMPLETE!
[00:01:07] INFO  |    Sent: 0.9553 XRP
[00:01:07] INFO  |    Received: 0.9553 XRP
[00:01:07] INFO  |    Time: 60s (12 checks)

================================================================================

[00:01:08] INFO  | Step 4: Sell XRP on Gemini
[00:01:08] INFO  | Selling 0.9553 XRP on Gemini...
[00:01:08] INFO  |    Price: $0.5234
[00:01:08] INFO  |    Expected: $0.50
[00:01:08] INFO  | ✅ Sell order placed: def-456
[00:01:10] INFO  | ✅ USD balance after sell: $3.75

================================================================================
  TEST 1 RESULTS: COINBASE → GEMINI
================================================================================

[00:01:11] INFO  | 💰 USD spent on Coinbase: $0.50
[00:01:11] INFO  | 💰 USD gained on Gemini:  $0.49
[00:01:11] INFO  | 📊 Net change: -$0.01
[00:01:11] SUCCESS | ✅ TEST 1 PASSED: Transfer works!

================================================================================
  TEST 2: GEMINI → COINBASE TRANSFER
================================================================================

(Similar output for reverse direction)

================================================================================
  FINAL SUMMARY
================================================================================

[00:05:30] INFO  | Test 1 (Coinbase → Gemini):
[00:05:30] INFO  |    Net change: -$0.01
[00:05:30] INFO  |    Status: ✅ PASS
[00:05:30] INFO  | Test 2 (Gemini → Coinbase):
[00:05:30] INFO  |    Net change: -$0.01
[00:05:30] INFO  |    Status: ✅ PASS

================================================================================

[00:05:30] SUCCESS | 🎉 ALL TESTS PASSED!
[00:05:30] INFO  |    Transfers work in both directions!
[00:05:30] INFO  |    Bot is ready for live trading!

================================================================================

[00:05:30] INFO  | Total cost: $0.02
[00:05:30] INFO  | (This is the cost of testing - fees + slippage)
```

---

## Possible Issues

### Issue 1: "Insufficient balance"
```
❌ ERROR: Insufficient USD on Coinbase (need $0.50, have $0.30)
```
**Fix**: Add more USD to that exchange

### Issue 2: "Address not whitelisted"
```
❌ ERROR: Withdrawal failed: Address not whitelisted
```
**Fix**: 
- **Coinbase/Gemini auto-whitelist** on first use
- Wait a few minutes and try again
- Check exchange security settings

### Issue 3: "Transfer timeout"
```
❌ TIMEOUT: Transfer not confirmed after 300s
```
**Possible causes:**
- Network congestion (XRP usually takes 60-120s)
- Exchange processing delay
- Check blockchain explorer to verify transaction

**What to do:**
- Check your Gemini account manually - XRP may arrive later
- If it arrives, the test still validates the transfer works

### Issue 4: "Invalid destination tag"
```
❌ ERROR: Invalid destination tag
```
**Fix**: 
- Some exchanges require a destination tag for XRP
- The script automatically includes it
- If this fails, check Gemini's deposit instructions

---

## What Success Looks Like

**Both tests pass = Transfers work = Bot ready!**

```
✅ Test 1: PASS (Coinbase → Gemini)
✅ Test 2: PASS (Gemini → Coinbase)
🎉 ALL TESTS PASSED!
   Transfers work in both directions!
   Bot is ready for live trading!

Total cost: $0.02-0.05
```

**If both tests pass:**
- ✅ API keys work
- ✅ Transfers complete successfully
- ✅ Deposit addresses correct
- ✅ Full arbitrage cycle works
- ✅ **Bot is ready for live trading!**

---

## Next Steps After Test Passes

1. **Let the main bot run** (`coinbase_gemini_bot.py`)
2. **Monitor Railway logs** for first trade
3. **Watch for**:
   ```
   🎯 EXECUTING BEST TRADE: QNT/USD
   ✅ Limit buy filled (or Market buy filled)
   ✅ Transfer complete
   ✅ Limit sell filled
   💰 NET PROFIT: $2.44
   ```

---

## Troubleshooting

If the test fails, you'll see detailed error messages:
- **What step failed** (buy, transfer, or sell)
- **Which exchange** it failed on
- **The exact error** from CCXT
- **What to check** to fix it

The test is **non-destructive** - worst case you lose $0.05 in fees, but you'll know exactly what needs to be fixed before risking real money with the bot.

