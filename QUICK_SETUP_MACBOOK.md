# ⚡ QUICK SETUP GUIDE - MacBook (APIs + Whitelisting)

**Time Required**: 30-45 minutes  
**Difficulty**: Easy  
**Result**: Fully automated bot ready to trade

---

## 🚀 **PART 1: COINBASE API SETUP (10 minutes)**

### **Step 1: Log into Coinbase** (1 min)
1. Open browser on MacBook
2. Go to: **https://www.coinbase.com**
3. Click "Sign In" (top right)
4. Enter email + password
5. Enter 2FA code (from Google Authenticator)

### **Step 2: Create API Key** (5 min)
1. Click your **profile icon** (top right)
2. Click **"Settings"**
3. Click **"API"** (in left sidebar)
4. Click **"New API Key"** or **"Create API Key"**

### **Step 3: Set API Permissions** (CRITICAL!)
Select these permissions:
```
✅ View (read account info)
✅ Trade (buy/sell)
✅ Transfer (CRITICAL - enables withdrawals/deposits)
```

**IMPORTANT**: Make sure "Transfer" is checked! This enables automation.

### **Step 4: IP Whitelist** (Optional but recommended)
- Leave blank for now (allows from anywhere)
- Or enter your Railway server IP later

### **Step 5: Create & Save API Key**
1. Click **"Create"**
2. Enter 2FA code
3. **COPY AND SAVE IMMEDIATELY**:
   ```
   API Key: [long string] - SAVE THIS!
   API Secret: [long string] - SAVE THIS!
   Passphrase: [string] - SAVE THIS!
   ```
4. Save to a secure note/file on your Mac
5. Click "Done"

**⚠️ YOU CAN ONLY SEE THESE ONCE! Save them now!**

---

## 🔐 **PART 2: GEMINI API SETUP (10 minutes)**

### **Step 1: Log into Gemini** (1 min)
1. Go to: **https://www.gemini.com**
2. Click "Sign In" (top right)
3. Enter email + password
4. Enter 2FA code

### **Step 2: Navigate to API Settings** (1 min)
1. Click your **profile/name** (top right)
2. Click **"Account"**
3. Click **"API Settings"** (in left menu)
4. Click **"Create a New API Key"**

### **Step 3: Set API Permissions** (CRITICAL!)
1. Give it a name: "Arbitrage Bot"
2. Select scope:
   ```
   ✅ Trading (buy/sell)
   ✅ Fund Manager (CRITICAL - enables transfers)
   ```

**IMPORTANT**: "Fund Manager" must be checked for automated transfers!

### **Step 4: Create & Save API Key**
1. Click **"Create API Key"**
2. Enter 2FA code
3. **COPY AND SAVE IMMEDIATELY**:
   ```
   API Key: [long string] - SAVE THIS!
   API Secret: [very long string] - SAVE THIS!
   ```
4. Save to secure note/file on your Mac
5. Click "Confirm"

**⚠️ YOU CAN ONLY SEE SECRET ONCE! Save it now!**

---

## 🔐 **PART 3: COINBASE ADDRESS WHITELISTING (10 minutes)**

### **Step 1: Get Gemini Deposit Addresses**

For each crypto, get Gemini address:

1. Go to Gemini → **"Transfer Funds"**
2. Click **"Deposit into Gemini"**
3. For **SHIB**:
   - Select "SHIB"
   - Click "Show Address"
   - **COPY the deposit address**
   - Save it: `GEMINI_SHIB: [address]`

**Repeat for all 11 cryptos**:
- SHIB, AAVE, COMP, UNI, DOT, SOL, AVAX, LINK, DOGE, XRP, ATOM

**TIP**: Open a text file and save all addresses as you go:
```
GEMINI_SHIB: 0x1234...
GEMINI_AAVE: 0x5678...
GEMINI_COMP: 0xabcd...
... (11 total)
```

### **Step 2: Whitelist on Coinbase**

For each crypto:

1. Go to Coinbase → **Settings** → **Security**
2. Scroll to **"Address Book"** or **"Whitelisted Addresses"**
3. Click **"Add Address"**
4. Select crypto: **SHIB**
5. Paste Gemini SHIB address
6. Label: "Gemini SHIB"
7. Click "Save"
8. Confirm with 2FA

**Repeat for all 11 cryptos using Gemini addresses**

**TIP**: This is tedious but ONE-TIME. After this, full automation works!

---

## 🔐 **PART 4: GEMINI ADDRESS WHITELISTING (10 minutes)**

### **Step 1: Get Coinbase Deposit Addresses**

For each crypto, get Coinbase address:

1. Go to Coinbase → **"Assets"**
2. Find **SHIB** in list
3. Click **"Receive"**
4. **COPY the deposit address**
5. Save it: `COINBASE_SHIB: [address]`

**Repeat for all 11 cryptos**:
- SHIB, AAVE, COMP, UNI, DOT, SOL, AVAX, LINK, DOGE, XRP, ATOM

**TIP**: Add to your text file:
```
COINBASE_SHIB: 0x9876...
COINBASE_AAVE: 0x5432...
COINBASE_COMP: 0xfedc...
... (11 total)
```

### **Step 2: Whitelist on Gemini**

For each crypto:

1. Go to Gemini → **Account** → **Security**
2. Scroll to **"Approved Addresses"** or **"Whitelisted Addresses"**
3. Click **"Add New Address"**
4. Select crypto: **SHIB**
5. Paste Coinbase SHIB address
6. Label: "Coinbase SHIB"
7. Click "Add"
8. Confirm with 2FA

**Repeat for all 11 cryptos using Coinbase addresses**

---

## 💾 **PART 5: SAVE API KEYS TO .env FILE (5 minutes)**

### **Step 1: Open Terminal on Mac**
1. Press `Cmd + Space`
2. Type "Terminal"
3. Press Enter

### **Step 2: Navigate to Bot Directory**
```bash
cd ~/Algotrading\ bot
```

### **Step 3: Create .env File**
```bash
nano .env
```

### **Step 4: Paste API Keys**
Copy this template and fill in your actual keys:

```bash
# Coinbase Advanced API Keys
COINBASE_API_KEY=your_coinbase_api_key_here
COINBASE_SECRET_KEY=your_coinbase_secret_here
COINBASE_PASSPHRASE=your_coinbase_passphrase_here
COINBASE_SANDBOX=false

# Gemini API Keys
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_SECRET_KEY=your_gemini_secret_here
GEMINI_SANDBOX=false
```

**Replace** `your_coinbase_api_key_here` etc. with your actual keys!

### **Step 5: Save & Exit**
1. Press `Ctrl + O` (save)
2. Press `Enter` (confirm)
3. Press `Ctrl + X` (exit)

### **Step 6: Verify .env File**
```bash
cat .env
```

**Make sure all 6 keys are filled in!**

---

## 🧪 **PART 6: TEST LOCALLY (5 minutes)**

### **Step 1: Install Dependencies**
```bash
pip3 install ccxt python-dotenv aiohttp asyncio
```

### **Step 2: Test API Connection**
```bash
python3 -c "
from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager
import asyncio

async def test():
    manager = CoinbaseGeminiExchangeManager()
    cb = manager.get_exchange('coinbase')
    gem = manager.get_exchange('gemini')
    
    print('Testing Coinbase...')
    cb_balance = await cb.fetch_balance()
    print(f'✅ Coinbase connected! Balance: {cb_balance}')
    
    print('Testing Gemini...')
    gem_balance = await gem.fetch_balance()
    print(f'✅ Gemini connected! Balance: {gem_balance}')

asyncio.run(test())
"
```

**Expected**: Should show your balances from both exchanges

---

## 💰 **PART 7: FUND ACCOUNTS (5 minutes)**

### **Option 1: Bank Transfer** (Takes 1-3 days)
**Coinbase**:
1. Click "Add funds"
2. Link bank account
3. Transfer $50

**Gemini**:
1. Click "Transfer Funds"
2. Link bank account
3. Transfer $50

**Total: $100** ($50 on each exchange)

### **Option 2: Crypto Transfer** (Instant, if you have crypto)
Transfer USDT, SOL, or any supported crypto to:
- Coinbase: $50 worth
- Gemini: $50 worth

Then convert to USD on each exchange.

---

## 🚀 **PART 8: DEPLOY TO RAILWAY (5 minutes)**

### **Step 1: Add API Keys to Railway**
1. Go to: **https://railway.app**
2. Find your deployed bot project
3. Click **"Variables"** tab
4. Click **"+ New Variable"**
5. Add each key one by one:

```
COINBASE_API_KEY = [your key]
COINBASE_SECRET_KEY = [your secret]
COINBASE_PASSPHRASE = [your passphrase]
COINBASE_SANDBOX = false

GEMINI_API_KEY = [your key]
GEMINI_SECRET_KEY = [your secret]
GEMINI_SANDBOX = false
```

### **Step 2: Restart Bot**
1. Click **"Deployments"** tab
2. Click **"Restart"** (or bot auto-restarts after adding variables)

### **Step 3: Check Logs**
1. Click **"Logs"** tab
2. Watch for:
   ```
   ✅ Coinbase connected!
   ✅ Gemini connected!
   ✅ Balances loaded
   ✅ Starting arbitrage bot...
   ```

---

## 📋 **COMPLETE CHECKLIST**

### **Coinbase** ✅
- [ ] Log in at coinbase.com
- [ ] Settings → API → Create API Key
- [ ] Enable: View, Trade, **Transfer**
- [ ] Save: API Key, Secret, Passphrase
- [ ] Get 11 deposit addresses (Assets → Receive)
- [ ] Whitelist 11 Gemini addresses (Settings → Security → Address Book)
- [ ] Fund with $50

### **Gemini** ✅
- [ ] Log in at gemini.com
- [ ] Account → API Settings → Create API Key
- [ ] Enable: Trading, **Fund Manager**
- [ ] Save: API Key, Secret
- [ ] Get 11 deposit addresses (Transfer → Deposit)
- [ ] Whitelist 11 Coinbase addresses (Account → Security → Approved Addresses)
- [ ] Fund with $50

### **Local Setup** ✅
- [ ] Create .env file with 6 API keys
- [ ] Test API connection locally
- [ ] Verify balances show correctly

### **Railway Deployment** ✅
- [ ] Add 6 variables to Railway
- [ ] Restart bot
- [ ] Check logs for success
- [ ] Monitor first trades

---

## ⚡ **QUICK REFERENCE - THE 11 CRYPTOS TO WHITELIST**

For each exchange, whitelist these 11:

1. **SHIB** (Shiba Inu)
2. **AAVE** (Aave)
3. **COMP** (Compound)
4. **UNI** (Uniswap)
5. **DOT** (Polkadot)
6. **SOL** (Solana)
7. **AVAX** (Avalanche)
8. **LINK** (Chainlink)
9. **DOGE** (Dogecoin)
10. **XRP** (Ripple)
11. **ATOM** (Cosmos)

**Total addresses to whitelist**: 22 (11 on each exchange)

---

## 🎯 **PRO TIPS FOR SPEED**

### **1. Use Two Browser Windows**:
- Window 1: Coinbase (left side of screen)
- Window 2: Gemini (right side of screen)
- Copy addresses between them quickly

### **2. Text File for Addresses**:
```bash
# Open TextEdit or Notes
# Save all addresses as you go:

GEMINI ADDRESSES (to whitelist on Coinbase):
SHIB: 0x1234...
AAVE: 0x5678...
... etc

COINBASE ADDRESSES (to whitelist on Gemini):
SHIB: 0x9876...
AAVE: 0x5432...
... etc
```

### **3. Do Whitelisting in Batches**:
- Get all 11 Gemini addresses first
- Then whitelist all 11 on Coinbase
- Then get all 11 Coinbase addresses
- Then whitelist all 11 on Gemini

### **4. Use Copy-Paste Shortcuts**:
- `Cmd + C` to copy
- `Cmd + V` to paste
- `Cmd + Tab` to switch windows

---

## 🔥 **FASTEST PATH (30 MIN TOTAL)**

### **Minutes 0-5**: Coinbase API
- Login → Settings → API → Create Key
- Enable: View, Trade, Transfer
- Save all 3 credentials

### **Minutes 5-10**: Gemini API
- Login → Account → API Settings → Create Key
- Enable: Trading, Fund Manager
- Save both credentials

### **Minutes 10-20**: Get ALL Addresses
- Get 11 Gemini addresses (save to text file)
- Get 11 Coinbase addresses (save to text file)

### **Minutes 20-25**: Whitelist on Coinbase
- Settings → Security → Address Book
- Add all 11 Gemini addresses

### **Minutes 25-30**: Whitelist on Gemini
- Account → Security → Approved Addresses
- Add all 11 Coinbase addresses

### **Minutes 30-35**: Setup .env File
- Terminal → cd to bot directory
- Create .env with 6 API keys

### **Minutes 35-40**: Deploy to Railway
- Add 6 variables
- Restart bot
- Check logs

### **Minutes 40-45**: Fund & Go!
- Transfer $100 ($50 to each exchange)
- Watch bot start trading!

---

## 📝 **COPY-PASTE TEMPLATES**

### **Template 1: Address Collection**
Copy this to TextEdit:

```
=== GEMINI DEPOSIT ADDRESSES (to whitelist on Coinbase) ===
SHIB: 
AAVE: 
COMP: 
UNI: 
DOT: 
SOL: 
AVAX: 
LINK: 
DOGE: 
XRP: 
ATOM: 

=== COINBASE DEPOSIT ADDRESSES (to whitelist on Gemini) ===
SHIB: 
AAVE: 
COMP: 
UNI: 
DOT: 
SOL: 
AVAX: 
LINK: 
DOGE: 
XRP: 
ATOM: 
```

### **Template 2: .env File**
```bash
# Coinbase Advanced API Keys
COINBASE_API_KEY=
COINBASE_SECRET_KEY=
COINBASE_PASSPHRASE=
COINBASE_SANDBOX=false

# Gemini API Keys
GEMINI_API_KEY=
GEMINI_SECRET_KEY=
GEMINI_SANDBOX=false
```

---

## 🎯 **STEP-BY-STEP: WHITELISTING PROCESS**

### **For EACH of the 11 Cryptos**:

#### **Coinbase → Gemini Direction**:
1. Get Gemini deposit address for crypto X
2. Go to Coinbase → Settings → Security → Address Book
3. Add address, select crypto X, label "Gemini [CRYPTO]"
4. Confirm with 2FA

#### **Gemini → Coinbase Direction**:
1. Get Coinbase deposit address for crypto X
2. Go to Gemini → Account → Security → Approved Addresses
3. Add address, select crypto X, label "Coinbase [CRYPTO]"
4. Confirm with 2FA

**Do this for all 11**: SHIB, AAVE, COMP, UNI, DOT, SOL, AVAX, LINK, DOGE, XRP, ATOM

---

## 🚨 **COMMON MISTAKES TO AVOID**

### **❌ MISTAKE 1**: Forgetting "Transfer" permission on Coinbase
**✅ FIX**: Make sure "Transfer" checkbox is selected

### **❌ MISTAKE 2**: Forgetting "Fund Manager" on Gemini
**✅ FIX**: Make sure "Fund Manager" checkbox is selected

### **❌ MISTAKE 3**: Not saving API credentials immediately
**✅ FIX**: Copy and save ALL credentials before clicking "Done"

### **❌ MISTAKE 4**: Mixing up addresses
**✅ FIX**: Label clearly: "Gemini SHIB" when whitelisting on Coinbase

### **❌ MISTAKE 5**: Wrong network for crypto
**✅ FIX**: Most are automatic, but verify:
- SHIB/AAVE/COMP/LINK/UNI use Ethereum network
- SOL uses Solana network
- XRP uses XRP Ledger
- Others use their native networks

### **❌ MISTAKE 6**: Not enabling 2FA
**✅ FIX**: Must have 2FA enabled for API creation

---

## 💻 **TERMINAL COMMANDS (MacBook)**

### **Navigate to Bot**:
```bash
cd ~/Algotrading\ bot
```

### **Create .env File**:
```bash
nano .env
# Paste template
# Fill in keys
# Ctrl+O to save, Enter to confirm, Ctrl+X to exit
```

### **Test API Connection**:
```bash
python3 coinbase_gemini_config.py
```

**Expected output**: 
```
✅ API keys configured
✅ Coinbase keys: Set
✅ Gemini keys: Set
```

---

## ✅ **VERIFICATION CHECKLIST**

Before deploying, verify:

- [ ] ✅ Coinbase API created with View + Trade + **Transfer**
- [ ] ✅ Gemini API created with Trading + **Fund Manager**
- [ ] ✅ All 6 API credentials saved securely
- [ ] ✅ 11 Gemini addresses whitelisted on Coinbase
- [ ] ✅ 11 Coinbase addresses whitelisted on Gemini
- [ ] ✅ .env file created with all 6 keys
- [ ] ✅ API connection tested locally
- [ ] ✅ $50 deposited on Coinbase
- [ ] ✅ $50 deposited on Gemini
- [ ] ✅ 6 variables added to Railway
- [ ] ✅ Bot restarted on Railway
- [ ] ✅ Logs show successful connection

---

## 🎊 **YOU'RE DONE!**

Once all checkboxes are complete:

✅ APIs configured  
✅ Addresses whitelisted (full automation enabled!)  
✅ .env file created  
✅ Accounts funded  
✅ Bot deployed  

**🚀 YOUR BOT WILL START TRADING AUTOMATICALLY! 💰**

---

## 📞 **NEED HELP?**

### **Coinbase Support**:
- Help Center: https://help.coinbase.com
- API Docs: https://docs.cloud.coinbase.com

### **Gemini Support**:
- Help Center: https://support.gemini.com
- API Docs: https://docs.gemini.com

---

## ⏱️ **TIME ESTIMATE**

- **Coinbase API**: 5 min
- **Gemini API**: 5 min
- **Get addresses**: 10 min
- **Whitelist Coinbase**: 5 min
- **Whitelist Gemini**: 5 min
- **Setup .env**: 5 min
- **Deploy**: 5 min

**Total: 30-40 minutes for complete setup!**

---

**Last Updated**: October 12, 2025  
**Platform**: MacBook  
**Status**: READY TO EXECUTE ✅

