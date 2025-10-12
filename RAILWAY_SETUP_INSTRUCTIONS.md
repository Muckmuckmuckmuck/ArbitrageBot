# 🚀 RAILWAY SETUP INSTRUCTIONS

## Your Bot is Deployed! Just Need to Add API Keys

**Status**: ✅ Bot is running on Railway  
**Issue**: Missing environment variables (API keys)  
**Fix Time**: 2 minutes

---

## ✅ GOOD NEWS

The error you're seeing is **EXPECTED and GOOD**!

```
ValueError: API keys not configured. Please set up .env file.
```

This means:
- ✅ Your code deployed successfully
- ✅ Bot is trying to start
- ✅ Just needs API keys to be added
- ✅ Everything else is working!

---

## 🔑 HOW TO FIX (2 MINUTES)

### **Step 1: Go to Railway Dashboard**
1. Open your Railway project
2. Click on your service (ArbitrageBot)
3. Go to "Variables" tab

### **Step 2: Add Environment Variables**

Click "New Variable" and add each of these:

#### **Pionex.US API Keys**:
```
Variable Name: PIONEX_API_KEY
Value: [paste your Pionex API key]

Variable Name: PIONEX_SECRET_KEY
Value: [paste your Pionex secret key]

Variable Name: PIONEX_TESTNET
Value: true    (for testing) or false (for production)
```

#### **Coinbase Pro API Keys**:
```
Variable Name: COINBASE_API_KEY
Value: [paste your Coinbase API key]

Variable Name: COINBASE_SECRET_KEY
Value: [paste your Coinbase secret key]

Variable Name: COINBASE_PASSPHRASE
Value: [paste your Coinbase passphrase]

Variable Name: COINBASE_SANDBOX
Value: true    (for testing) or false (for production)
```

#### **Logging** (optional):
```
Variable Name: LOG_LEVEL
Value: INFO

Variable Name: LOG_FILE
Value: aggressive_arbitrage.log
```

### **Step 3: Save and Redeploy**

1. Click "Save" or "Deploy"
2. Railway will automatically redeploy
3. Wait 1-2 minutes for restart

### **Step 4: Check Logs**

Go to "Deployments" → "Logs"

**You should see**:
```
✓ API keys validated
✓ Exchanges initialized
✓ Pionex connected (XXX markets)
✓ Coinbase Pro connected (XXX markets)
✓ Initial balance: $X.XX
✓ All components initialized
BOT INITIALIZATION COMPLETE - READY FOR CROSS-EXCHANGE ARBITRAGE
```

**If you see this** → ✅ **SUCCESS! Bot is running!**

---

## ⚠️ IMPORTANT: TESTNET FIRST!

### **For Testing** (Start Here):
```
PIONEX_TESTNET=true
COINBASE_SANDBOX=true
```

This uses sandbox/testnet mode (fake money for testing)

### **For Production** (After Testing):
```
PIONEX_TESTNET=false
COINBASE_SANDBOX=false
```

This uses real money - **only switch after 24-48 hours of successful sandbox testing!**

---

## 🗄️ DATABASE (Optional)

I see Railway suggested a database:
```
DATABASE_URL
postgresql://postgres:UpeCrcSVNTgCHRdaZqIDBLZTuQIOxgBo@postgres.railway.internal:5432/railway
```

**Do you need it?**
- **Not required** for basic operation
- **Recommended** for persistent logs and statistics
- **Cost**: $5/month

**Add it later if you want persistent data!**

For now, bot works fine without it (just loses logs on restart).

---

## 🎯 WHAT TO DO RIGHT NOW

### **Immediate Actions**:

1. **Add API keys to Railway Variables** (2 minutes)
   - Go to Railway → Variables
   - Add all 7 environment variables above
   - Start with TESTNET=true, SANDBOX=true

2. **Check Logs** (1 minute)
   - Railway → Deployments → Logs
   - Look for "READY FOR CROSS-EXCHANGE ARBITRAGE"
   - Verify no errors

3. **Monitor for 1 Hour** (first test)
   - Watch logs for any activity
   - See if bot finds opportunities
   - Verify it tries to execute trades

4. **Let Run for 24-48 Hours in Sandbox**
   - Don't touch it
   - Check logs periodically
   - Verify no crashes

5. **After Sandbox Success, Switch to Production**
   - Change TESTNET=false, SANDBOX=false
   - Add real funds ($200-500)
   - Monitor closely for first week

---

## 📋 CHECKLIST

Before adding API keys, make sure you have:

- [ ] Created Pionex.US account
- [ ] Created Coinbase Pro account
- [ ] Completed KYC on both exchanges
- [ ] Generated API keys on both
- [ ] API keys have correct permissions (Read + Trade)
- [ ] Set API keys to never expire
- [ ] Written down the keys securely

---

## 🚨 TROUBLESHOOTING

### **If bot still shows error after adding keys**:

1. **Check variable names exactly match**:
   - `PIONEX_API_KEY` (not `pionex_api_key`)
   - `COINBASE_API_KEY` (not `coinbase_api_key`)
   - Case matters!

2. **Check no extra spaces**:
   - No spaces before/after the value
   - Copy-paste carefully

3. **Check keys are valid**:
   - Test on exchange dashboard
   - Make sure not expired
   - Verify permissions are correct

4. **Force redeploy**:
   - Railway → Settings → Redeploy
   - Wait 1-2 minutes

5. **Check .env file isn't committed** (security):
   - Your actual API keys should ONLY be in Railway Variables
   - Never commit .env to GitHub!

---

## ✅ AFTER KEYS ARE ADDED

**You should see in logs**:
```
✓ API keys validated
✓ Exchanges initialized
  ✓ Pionex connected (XXX markets)
  ✓ Coinbase Pro connected (XXX markets)
✓ All components initialized
✓ Initial balance: $X.XX
BOT INITIALIZATION COMPLETE - READY FOR CROSS-EXCHANGE ARBITRAGE
STARTING ARBITRAGE BOT WITH AUTOMATED TRANSFERS
Trading loop started
Monitoring loop started
Balance refresh loop started
Auto-recovery loop started
```

**Then**: Bot will start scanning for arbitrage opportunities!

---

## 🎊 YOU'RE ALMOST THERE!

**Current Status**: ✅ Deployed to Railway  
**Next Step**: Add API keys (2 minutes)  
**Then**: Bot starts automatically!  

**Just add those 7 environment variables and you're ready to make money!** 🚀💰

---

## 📞 QUICK REFERENCE

### **Required Environment Variables**:
1. `PIONEX_API_KEY` = your Pionex API key
2. `PIONEX_SECRET_KEY` = your Pionex secret
3. `PIONEX_TESTNET` = true (for testing)
4. `COINBASE_API_KEY` = your Coinbase API key
5. `COINBASE_SECRET_KEY` = your Coinbase secret
6. `COINBASE_PASSPHRASE` = your Coinbase passphrase
7. `COINBASE_SANDBOX` = true (for testing)

**Where to add**: Railway Dashboard → Your Project → Variables → New Variable

**After adding**: Bot auto-restarts and starts trading!

---

**Last Updated**: October 8, 2025  
**Status**: Ready for API Keys ✅

