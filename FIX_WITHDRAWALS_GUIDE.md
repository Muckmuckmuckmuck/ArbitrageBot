# 🔧 Fix Withdrawal Configuration - Step-by-Step Guide

## Overview

Both Coinbase and Gemini require you to **whitelist crypto addresses** before you can withdraw to them via API. This is a security feature.

**Time needed:** 5-10 minutes per exchange

---

## 🟦 COINBASE - Enable Withdrawals

### Step 1: Log into Coinbase

Go to: https://www.coinbase.com

### Step 2: Navigate to Settings

1. Click your **profile icon** (top right)
2. Click **"Settings"**
3. Click **"Security"** (left sidebar)

### Step 3: Find Address Book

Look for one of these sections:
- **"Address Book"**
- **"Approved Addresses"**
- **"Withdrawal Addresses"**
- **"Crypto Addresses"**

### Step 4: Check API Withdrawal Settings

Scroll down to find:
- **"API Access"** or **"API Settings"**
- Look for **"Allow API withdrawals"** or similar
- **Enable it** if it's disabled

### Step 5: Whitelist Gemini's XRP Address

**Option A: If Address Book Exists**

1. Click **"Add Address"** or **"New Address"**
2. Select **"XRP"** as the cryptocurrency
3. Enter Gemini's XRP deposit address: `raBQUYdAhnnojJQ6Xi3e...` (you'll get this from Gemini)
4. Enter the **destination tag** if required
5. Give it a nickname: `"Gemini XRP"`
6. Click **"Save"** or **"Add"**
7. **Confirm via email/2FA**

**Option B: If No Address Book (Auto-Whitelist)**

Some Coinbase accounts auto-whitelist on first withdrawal:
1. The first withdrawal will require **email confirmation**
2. Check your email after the bot tries to withdraw
3. Click the confirmation link
4. Future withdrawals to that address will be automatic

**Option C: If Withdrawals Are Restricted**

If you see "Withdrawals disabled" or similar:
1. Check for **account verification** requirements
2. Look for **holding periods** (new deposits may have 7-14 day holds)
3. Contact Coinbase support if needed

### Step 6: Verify API Key Permissions

Go back to: https://www.coinbase.com/settings/api

1. Find your API key (the one you're using for the bot)
2. Click **"Edit"** or **"View Permissions"**
3. Make sure these are **enabled**:
   - ✅ **"wallet:accounts:read"**
   - ✅ **"wallet:buys:create"**
   - ✅ **"wallet:sells:create"**
   - ✅ **"wallet:transactions:send"** ← **CRITICAL for withdrawals**
   - ✅ **"wallet:withdrawals:create"** ← **CRITICAL for withdrawals**
4. If any are missing, **enable them** and save

---

## 🟩 GEMINI - Enable Withdrawals

### Step 1: Log into Gemini

Go to: https://exchange.gemini.com

### Step 2: Navigate to API Settings

1. Click **"Account"** (top right)
2. Click **"Settings"**
3. Click **"API"** (left sidebar)

### Step 3: Check Your API Key Type

**CRITICAL:** Gemini has two types of API keys:

#### Master Key (Trading Only) ❌
- **Cannot withdraw funds**
- Only for trading
- If you have this, you need to create a new key

#### Primary (Account) Key ✅
- **Can withdraw funds**
- Full account access
- This is what you need

**To check:**
1. Look at your API key in the list
2. It will say **"Master"** or **"Primary"**
3. If it says **"Master"**, you need to create a new **"Primary"** key

### Step 4: Create a Primary API Key (If Needed)

1. Click **"Create a New API Key"**
2. Select **"Primary"** (NOT "Master")
3. Give it a name: `"Arbitrage Bot"`
4. **Enable these permissions:**
   - ✅ **"Auditor"** (read account data)
   - ✅ **"Trader"** (place orders)
   - ✅ **"Fund Manager"** ← **CRITICAL for withdrawals**
5. **Set IP whitelist** (optional but recommended):
   - If running on Railway, leave blank or use Railway's IP
   - If running locally, add your home IP
6. Click **"Create"**
7. **Save the API Key and Secret** (you'll need to update your bot)

### Step 5: Enable Withdrawal Permissions

On the API key details page:

1. Find **"Fund Manager"** section
2. Make sure **"Withdraw Crypto"** is **enabled**
3. If there's a **"Withdrawal Whitelist"** option:
   - Either **disable it** (allow withdrawals to any address)
   - Or **add Coinbase's XRP address** to the whitelist

### Step 6: Get Your XRP Deposit Address

You need this to give to Coinbase:

1. Go to **"Transfer Funds"** or **"Deposit"**
2. Select **"XRP"**
3. Click **"Generate Address"** or **"Show Address"**
4. Copy the **address** and **destination tag**
5. **Save these** - you'll add them to Coinbase's address book

**Example:**
```
Address: raBQUYdAhnnojJQ6Xi3e4DzWZveRrjm3yt
Destination Tag: 123456789
```

### Step 7: Whitelist Coinbase's XRP Address (Optional)

If Gemini has a withdrawal whitelist:

1. Go to **"Transfer Funds"** → **"Withdraw"**
2. Select **"XRP"**
3. Look for **"Add Address"** or **"Whitelist"**
4. Add Coinbase's XRP deposit address (you'll get this from Coinbase)
5. Confirm via email/2FA

---

## 🔄 Update Your Bot with New API Keys (If Needed)

If you created a new Gemini Primary API key:

### On Railway:

1. Go to your Railway dashboard
2. Click your bot project
3. Click **"Variables"** tab
4. Update:
   - `GEMINI_API_KEY` = your new key
   - `GEMINI_SECRET` = your new secret
5. Click **"Save"**
6. Railway will automatically redeploy

### Locally (for testing):

```bash
export GEMINI_API_KEY="your_new_key"
export GEMINI_SECRET="your_new_secret"
```

---

## 🧪 Test Withdrawals

Once you've configured both exchanges:

### Option 1: Run the Full Test Again

```bash
# Update Procfile to run the test
# (Already set up - just push to Railway)
railway logs
```

The bi-directional test will:
1. Buy XRP on Coinbase
2. **Withdraw to Gemini** ← Should work now!
3. Sell on Gemini
4. Buy XRP on Gemini
5. **Withdraw to Coinbase** ← Should work now!
6. Sell on Coinbase

### Option 2: Manual Test (Safer)

Try a small manual withdrawal first:

**From Coinbase to Gemini:**
1. Go to Coinbase → Send/Receive
2. Select XRP
3. Enter Gemini's address and tag
4. Send a small amount (0.1 XRP)
5. Check if it arrives on Gemini

**From Gemini to Coinbase:**
1. Go to Gemini → Transfer → Withdraw
2. Select XRP
3. Enter Coinbase's address
4. Send a small amount (0.1 XRP)
5. Check if it arrives on Coinbase

---

## 📋 Checklist - Are You Ready?

### Coinbase ✅
- [ ] API key has "wallet:transactions:send" permission
- [ ] API key has "wallet:withdrawals:create" permission
- [ ] Gemini's XRP address is whitelisted (or auto-whitelist is enabled)
- [ ] No withdrawal holds on account

### Gemini ✅
- [ ] Using "Primary" API key (NOT "Master")
- [ ] API key has "Fund Manager" permission
- [ ] "Withdraw Crypto" is enabled
- [ ] Coinbase's XRP address is whitelisted (or whitelist is disabled)

### Both ✅
- [ ] You have both exchanges' XRP deposit addresses
- [ ] You've saved destination tags (if required)
- [ ] Account is fully verified
- [ ] No pending security holds

---

## 🚨 Common Issues & Solutions

### "Withdrawals are disabled on your account"
- **Cause:** Account verification incomplete or recent deposit hold
- **Fix:** Complete verification, wait for deposit hold to expire (usually 7-14 days)

### "Address not whitelisted"
- **Cause:** Address book/whitelist feature is enabled
- **Fix:** Add the destination address to your whitelist, confirm via email

### "API key doesn't have withdrawal permissions"
- **Cause:** Key created without withdrawal scope
- **Fix:** Edit key permissions or create new key with full permissions

### "Master key cannot withdraw funds" (Gemini)
- **Cause:** Using Master API key instead of Primary
- **Fix:** Create a new Primary API key with Fund Manager permissions

### "Destination tag required"
- **Cause:** XRP requires a destination tag for some exchanges
- **Fix:** Include the destination tag in your withdrawal request

### "Internal server error"
- **Cause:** Usually permission or whitelist issue
- **Fix:** Double-check all permissions and whitelist settings

---

## 🎯 Quick Reference

### Get Gemini XRP Address:
```
Gemini → Transfer Funds → Deposit → XRP → Show Address
```

### Get Coinbase XRP Address:
```
Coinbase → Assets → XRP → Receive → Copy Address
```

### Check Coinbase API Permissions:
```
Coinbase → Settings → API → [Your Key] → Edit Permissions
```

### Check Gemini API Type:
```
Gemini → Settings → API → [Your Key] → Check if "Master" or "Primary"
```

---

## ⏭️ After Configuration

Once you've fixed the configuration:

1. **Sell the stuck XRP** on Coinbase:
   ```bash
   railway run python sell_coinbase_xrp.py
   ```

2. **Run the bi-directional test** again:
   - It's already deployed on Railway
   - Just watch the logs: `railway logs`
   - It will automatically retry

3. **If test passes:**
   - ✅ Restore your main bot
   - ✅ Start real arbitrage trading!

4. **If test still fails:**
   - Send me the error logs
   - We'll debug further

---

## 💡 Pro Tips

1. **Start with small amounts** - Test with $1-2 before going bigger
2. **Save addresses** - Keep a note of both exchanges' XRP addresses
3. **Check email** - First withdrawals often need email confirmation
4. **Be patient** - Whitelist approval can take a few minutes to 48 hours
5. **Use Primary keys** - Always use Gemini "Primary" keys for full access

---

## 📞 Need Help?

If you get stuck:

1. **Screenshot the error** - Show me exactly what you see
2. **Check permissions** - Verify API key scopes on both exchanges
3. **Check email** - Look for confirmation requests
4. **Try manual withdrawal** - Test outside the bot first

---

**Start with Coinbase (Step 1), then Gemini (Step 2), then test!** 🚀

Let me know when you're done and I'll help you run the test again!

