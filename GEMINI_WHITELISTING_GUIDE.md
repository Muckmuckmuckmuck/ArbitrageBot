# 🔐 Gemini Withdrawal Address Whitelisting Guide

## ⚠️ Current Issue
Gemini is blocking withdrawals because address whitelisting is not enabled on your account.

**Error Message:**
```
Cryptocurrency withdrawal address whitelists are not enabled for account primary.
Please contact support@gemini.com for information on setting up a withdrawal address whitelist.
```

## 📋 Step-by-Step Instructions

### Step 1: Log in to Gemini
1. Go to https://exchange.gemini.com/
2. Log in to your account

### Step 2: Navigate to Security Settings
1. Click on your profile/account menu (usually top right)
2. Go to **Settings** → **Security**
3. Look for **"Approved Addresses"** or **"Withdrawal Whitelist"** section

### Step 3: Enable Address Whitelisting
1. Find the toggle or setting to **"Enable withdrawal address whitelisting"**
2. Turn it ON
3. You may need to confirm via email or 2FA

### Step 4: Add Coinbase API3 Address
1. Click **"Add Address"** or **"New Withdrawal Address"**
2. Fill in the details:
   - **Asset/Currency:** API3
   - **Network:** Ethereum (ETH) - API3 is an ERC-20 token
   - **Address:** `0xa13EdA5E3bD538499C1C1e0a8bc8e3eB8161a40E`
   - **Nickname (optional):** Coinbase API3
3. **Verify the address carefully** - double check every character
4. Submit the address
5. Wait for approval (may require email confirmation - check your email)

### Step 5: Verify Address is Active
1. Check that the address shows as **"Active"** or **"Approved"**
2. Status may show "Pending" initially - wait for approval

## ⚠️ Important Notes

### Address Verification
- **Double-check the address:** `0xa13EdA5E3bD538499C1C1e0a8bc8e3eB8161a40E`
- This is the deposit address returned by Coinbase API for API3
- It's an Ethereum address (ERC-20 token)

### Network Selection
- Make sure you select **Ethereum (ETH)** network, not a different network
- API3 is an ERC-20 token on Ethereum

### Processing Time
- Address approval may take a few minutes to a few hours
- Check your email for any confirmation requests

## 📝 Current Coinbase Deposit Addresses

Based on your Coinbase account, here are the addresses to whitelist on Gemini:

### For API3 Transfers:
- **Address:** `0xa13EdA5E3bD538499C1C1e0a8bc8e3eB8161a40E`
- **Network:** Ethereum (ETH)
- **Token:** API3

### For Other ERC-20 Tokens (if needed):
You may also want to whitelist other addresses:
- **IMX:** `0x37E2...ab49` (check full address in Coinbase)
- **AMP:** `0x41e4...87d4`
- **INJ:** `0xfeEC...D8C1`
- **QNT:** `0xbCb1...c85c`
- **COMP:** `0xd2C8...45F2`
- **BAT:** `0xf44B...16Af`

## 🔄 After Whitelisting is Enabled

Once the address is whitelisted on Gemini:
1. The test will be able to proceed with Gemini → Coinbase transfers
2. You can then test Coinbase → Gemini transfers
3. Full bidirectional transfer testing will be possible

## 🆘 If You Can't Find the Setting

If you can't find the address whitelisting option in your Gemini account:
1. **Contact Gemini Support:** support@gemini.com
2. **Request:** "Please enable withdrawal address whitelisting for my account"
3. **Mention:** You need it for API-based trading/arbitrage

## ✅ Verification Checklist

Before running the test again, verify:
- [ ] Address whitelisting is enabled on Gemini
- [ ] Coinbase API3 address is added: `0xa13EdA5E3bD538499C1C1e0a8bc8e3eB8161a40E`
- [ ] Address status shows as "Active" or "Approved"
- [ ] Network is set to Ethereum (ETH)
- [ ] Email confirmation (if required) has been completed

