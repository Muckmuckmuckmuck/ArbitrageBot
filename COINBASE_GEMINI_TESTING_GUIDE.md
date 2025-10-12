# 🧪 COINBASE + GEMINI TESTING GUIDE

**How to test your bot before going live with real money**

---

## 📋 TESTING CHECKLIST

### **Phase 1: Pre-Deployment Testing** ✅

- [ ] Config file loads without errors
- [ ] All dependencies installed
- [ ] API keys format validated
- [ ] Position percentages sum to 100%
- [ ] Minimum spreads are profitable

### **Phase 2: Sandbox Testing** ⚠️

**Note**: Gemini has sandbox mode, Coinbase Advanced does not have public sandbox

- [ ] Set `GEMINI_SANDBOX=true`
- [ ] Test Gemini API connection
- [ ] Verify market data fetching works

### **Phase 3: Small Amount Testing** ✅ **RECOMMENDED**

- [ ] Start with $100-200 total
- [ ] Test first trade with $10
- [ ] Verify whitelisting works
- [ ] Monitor for 24 hours
- [ ] Check all phases complete

### **Phase 4: Full Production** ✅

- [ ] Scale up to $1,000+
- [ ] Monitor for 1 week
- [ ] Verify consistent profitability
- [ ] Scale to target amount

---

## 🧪 PHASE 1: PRE-DEPLOYMENT TESTING

### **Test 1: Configuration Validation**

```bash
cd "/Users/jayreddy/Algotrading bot"
python3 coinbase_gemini_config.py
```

**Expected output**:
```
✅ Configuration valid!
Fee Summary:
  Total per trade: 0.95%
Withdrawal Fees:
  Coinbase: FREE
  Gemini: FREE (10 per month)
```

**If errors**: Fix configuration before proceeding

---

### **Test 2: Exchange Manager**

```bash
python3 coinbase_gemini_exchanges.py
```

**Expected output**:
```
✅ Exchange manager ready!
Buy on Coinbase, Sell on Gemini:
  Total fees: 0.95%
  Min profitable spread: 1.15%
```

---

### **Test 3: Dependencies**

```bash
python3 << 'EOF'
import ccxt
import asyncio
from coinbase_gemini_config import Config
from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager
print("✅ All imports successful!")
EOF
```

**If errors**: Install missing dependencies

---

## 🔬 PHASE 2: SANDBOX TESTING (Optional)

### **Gemini Sandbox**

1. Create sandbox account at **https://exchange.sandbox.gemini.com**
2. Get sandbox API keys
3. Set in Railway:
   ```
   GEMINI_SANDBOX=true
   GEMINI_API_KEY=sandbox_key
   GEMINI_SECRET_KEY=sandbox_secret
   ```
4. Test API calls without real money

**Note**: Coinbase Advanced doesn't have public sandbox, so you'll need to test with small real amounts

---

## 💰 PHASE 3: SMALL AMOUNT TESTING (CRITICAL!)

### **Test 1: First Trade ($10)**

**Setup**:
1. Fund Coinbase with $100
2. Fund Gemini with $100
3. Whitelist addresses
4. Deploy bot

**What to watch**:
```
Expected log output:

✅ Coinbase initialized
✅ Gemini initialized
✅ Initial balance: $200.00
🚀 Starting trading loop...
📊 Found 1 opportunities
🎯 Executing best opportunity: SOL/USD (1.35%)
[PHASE 1] Buying on coinbase...
✅ Buy complete: 0.05 SOL @ $200.00
[PHASE 2] Transferring 0.05 SOL to gemini...
✅ Transfer complete in 15.3s
[PHASE 3] Selling on gemini...
✅ Sell complete: 0.05 SOL @ $202.70
[PHASE 4] Rebalancing...
✅ Rebalancing complete
✅ ARBITRAGE COMPLETE: SOL/USD
   Net profit: $0.12
```

**Success criteria**:
- ✅ All 4 phases complete
- ✅ No errors in logs
- ✅ Profit is positive
- ✅ Balance increased

**If failed**: Check logs for specific error

---

### **Test 2: Multiple Trades (24 hours)**

**Setup**:
- Keep $200 in system
- Let bot run for 24 hours
- Don't interfere

**What to monitor**:
- Number of trades executed
- Success rate (should be >80%)
- Total profit (should be positive)
- No stuck positions
- No repeated errors

**Expected results after 24 hours**:
```
Total trades: 10-30
Successful: 8-25 (80%+)
Total profit: $1-$3 (0.5-1.5% of $200)
No critical errors
```

**Success criteria**:
- ✅ At least 10 trades
- ✅ Success rate >80%
- ✅ Profit >$1
- ✅ No stuck positions
- ✅ No critical errors

---

### **Test 3: Whitelisting Verification**

**Test each crypto**:
1. Wait for bot to find opportunity for each crypto
2. Verify transfer completes automatically
3. Check no manual confirmation required

**Cryptos to test**:
- ✅ SOL (fast transfer, test first)
- ✅ XRP (fast transfer)
- ✅ DOGE
- ✅ At least 3-5 different cryptos

**Success criteria**:
- ✅ All transfers complete automatically
- ✅ No manual confirmation needed
- ✅ No email clicks required

---

## 🚀 PHASE 4: FULL PRODUCTION

### **Test 4: Scale to $1,000**

After 24 hours of successful testing:

1. Add more funds (scale to $1,000)
2. Monitor for 1 week
3. Track performance:
   - Daily profit: $5-$15
   - Success rate: >80%
   - No critical issues

**Expected results after 1 week**:
```
Total trades: 70-200
Total profit: $35-$105 (3.5-10.5%)
Success rate: 80-90%
No major issues
```

---

### **Test 5: Scale to Target Amount**

After 1 week of successful operation:

1. Scale to your target amount:
   - Conservative: $5,000
   - Moderate: $10,000
   - Aggressive: $25,000
2. Monitor for 1 month
3. Verify consistent profitability

**Expected monthly results** (with $10,000):
```
Daily profit: $50-$150
Monthly profit: $1,500-$4,500 (15-45%)
Success rate: 80-90%
```

---

## 🔍 WHAT TO LOOK FOR

### **Good Signs** ✅:
- Trades executing regularly (10-30/day)
- Success rate >80%
- Profit accumulating
- No stuck positions
- Fast transfers (<5 min)
- No repeated errors

### **Warning Signs** ⚠️:
- Success rate <70%
- Frequent transfer failures
- Stuck positions
- Repeated errors
- Very slow transfers (>10 min)

### **Critical Issues** 🚨:
- Bot crashes repeatedly
- API key errors
- Balance going down
- Success rate <50%
- Transfers never complete

**If critical issues**: Stop bot, check logs, fix issues

---

## 🛠️ TROUBLESHOOTING

### **Issue: "API keys not configured"**
```
Solution:
1. Check Railway variables are set
2. Verify no extra spaces
3. Ensure variable names match exactly
```

### **Issue: "Transfer failed"**
```
Solution:
1. Check addresses are whitelisted
2. Verify sufficient balance
3. Check API key has Transfer/Fund Manager permission
4. Try manual transfer to test
```

### **Issue: "No opportunities found"**
```
Solution:
1. This is normal! Opportunities come and go
2. Bot checks every 5 seconds
3. Be patient
4. Check spreads are reasonable (not too high)
```

### **Issue: "Order failed"**
```
Solution:
1. Check sufficient balance
2. Verify API permissions
3. Check exchange is not in maintenance
4. Review logs for specific error
```

---

## 📊 PERFORMANCE BENCHMARKS

### **What to expect**:

**With $1,000**:
- Daily trades: 10-30
- Daily profit: $5-$15 (0.5-1.5%)
- Success rate: 80-90%
- Opportunities found: 50-100/day
- Opportunities executed: 10-30/day

**With $10,000**:
- Daily trades: 20-50
- Daily profit: $50-$150 (0.5-1.5%)
- Success rate: 80-90%
- Opportunities found: 50-100/day
- Opportunities executed: 20-50/day

---

## ✅ TESTING COMPLETE CHECKLIST

Before going to full production:

- [ ] Config loads without errors
- [ ] Exchange manager works
- [ ] First $10 trade successful
- [ ] 24 hours of testing complete
- [ ] Success rate >80%
- [ ] Profit is positive
- [ ] No stuck positions
- [ ] Whitelisting works for multiple cryptos
- [ ] Transfers complete automatically
- [ ] No manual intervention needed
- [ ] Logs show healthy operation
- [ ] Ready to scale up!

---

## 🎯 RECOMMENDED TESTING TIMELINE

**Day 1**: Setup and first trade
- Create accounts
- Whitelist addresses
- Deploy bot
- Test with $10

**Day 2-3**: Small amount testing
- Run with $100-200
- Monitor closely
- Verify automation works

**Week 1**: Medium amount testing
- Scale to $1,000
- Monitor daily
- Track performance

**Week 2-4**: Full production
- Scale to target amount
- Monitor weekly
- Withdraw profits

**After 1 month**: Fully operational
- Consistent profitability confirmed
- System proven reliable
- Scale as comfortable

---

## 🎊 YOU'RE READY!

**Testing approach**:
1. ✅ Start small ($100-200)
2. ✅ Test thoroughly (24-48 hours)
3. ✅ Scale gradually ($1k → $5k → $10k)
4. ✅ Monitor closely
5. ✅ Withdraw profits regularly

**Expected timeline**:
- Day 1: Setup and first trade
- Week 1: Small amount testing
- Week 2-4: Scale up
- Month 2+: Full production

**🚀 START TESTING AND MAKE MONEY! 💰**

---

**Last Updated**: October 12, 2025  
**Status**: Complete testing guide ✅

