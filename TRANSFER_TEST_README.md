# Transfer Mechanism Test

## What This Does

This script validates that crypto transfers work correctly between Coinbase and Gemini by:

1. **Test 1 (Coinbase → Gemini):**
   - Buy $1 of XRP on Coinbase
   - Transfer XRP to Gemini
   - Sell XRP on Gemini

2. **Test 2 (Gemini → Coinbase):**
   - Buy $1 of XRP on Gemini  
   - Transfer XRP to Coinbase
   - Sell XRP on Coinbase

## Why Run This

The main bot has been finding profitable opportunities but failing to execute due to balance issues. Before fixing the balance logic, we need to verify that the core transfer mechanism works.

## Current Balances

- **Coinbase:** $17.36 USD (available)
- **Gemini:** $0.81 USD (available) + $8.19 (on hold)

## Requirements

- At least $2 total USD across both exchanges (for 2 x $1 tests)
- XRP is chosen because it's:
  - Fast (30-120 second transfers)
  - Cheap (low fees)
  - Reliable (stable network)
  - Available on both exchanges

## How to Run

```bash
cd "/Users/jayreddy/Algotrading bot"
python3 test_transfer_mechanism.py
```

## Expected Output

```
🧪 TEST 1: COINBASE → GEMINI TRANSFER
💰 BUYING $1.00 of XRP/USD on COINBASE
   ✅ Order placed
🚀 TRANSFERRING XRP from COINBASE → GEMINI
   ✅ Transfer confirmed!
💸 SELLING XRP on GEMINI
   ✅ Order placed
✅ TEST 1 PASSED

🧪 TEST 2: GEMINI → COINBASE TRANSFER
💰 BUYING $1.00 of XRP/USD on GEMINI
   ✅ Order placed
🚀 TRANSFERRING XRP from GEMINI → COINBASE
   ✅ Transfer confirmed!
💸 SELLING XRP on COINBASE
   ✅ Order placed
✅ TEST 2 PASSED

🎉 ALL TESTS PASSED - TRANSFER MECHANISM WORKING!
```

## What Happens Next

- **If tests pass:** We know transfers work, and we can focus on fixing the balance validation logic in the main bot
- **If tests fail:** We'll see exactly where the transfer pipeline breaks (buy/transfer/sell) and fix it

## Notes

- This test uses **$2 total** ($1 per direction)
- The script includes comprehensive logging so you can see exactly what's happening
- Transfer monitoring includes 5-minute timeout with 10-second status checks
- The main bot is NOT affected by this test (separate script)
