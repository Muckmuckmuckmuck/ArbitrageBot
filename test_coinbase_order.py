#!/usr/bin/env python3
"""
Quick test to diagnose Coinbase order creation issue
Tests buying $2 worth of BTC with USDC
"""

import asyncio
import ccxt
import logging
import os
from dotenv import load_dotenv
from coinbase_gemini_config import Config

# Load environment variables first
# Try .env first, then .env.railway
env_loaded = load_dotenv() or load_dotenv('.env.railway')
if not env_loaded:
    # Check if env vars are already set (e.g., in Railway)
    if not os.getenv('COINBASE_API_KEY'):
        print("⚠️  Warning: No .env file found and COINBASE_API_KEY not in environment")
        print("   This script needs Coinbase API credentials to run")

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_coinbase_order():
    """Test creating a small order on Coinbase"""
    logger.info("=" * 80)
    logger.info("TEST: Coinbase Order Creation")
    logger.info("=" * 80)
    logger.info("")
    
    try:
        # Verify credentials are loaded
        logger.info("STEP 0: Verifying credentials...")
        api_key = Config.COINBASE_API_KEY or os.getenv('COINBASE_API_KEY')
        secret_key = Config.COINBASE_SECRET_KEY or os.getenv('COINBASE_SECRET_KEY')
        passphrase = Config.COINBASE_PASSPHRASE or os.getenv('COINBASE_PASSPHRASE')
        
        if not api_key or not secret_key:
            logger.error("❌ Missing Coinbase API credentials!")
            logger.error(f"   API Key: {'SET' if api_key else 'MISSING'}")
            logger.error(f"   Secret Key: {'SET' if secret_key else 'MISSING'}")
            logger.error(f"   Passphrase: {'SET' if passphrase else 'MISSING (optional)'}")
            logger.error("")
            logger.error("   Please ensure .env file exists with:")
            logger.error("   - COINBASE_API_KEY")
            logger.error("   - COINBASE_SECRET_KEY")
            logger.error("   - COINBASE_PASSPHRASE (optional for newer API keys)")
            return
        
        logger.info(f"✅ Credentials loaded:")
        logger.info(f"   API Key: {api_key[:10]}...{api_key[-5:] if len(api_key) > 15 else 'SET'}")
        logger.info(f"   Secret Key: {'SET' if secret_key else 'MISSING'}")
        logger.info(f"   Passphrase: {'SET' if passphrase else 'NOT SET (optional)'}")
        logger.info("")
        
        # Initialize Coinbase
        logger.info("STEP 1: Initializing Coinbase exchange...")
        coinbase_config = {
            'apiKey': api_key,
            'secret': secret_key,
            'password': passphrase,
            **Config.EXCHANGE_CONFIGS['coinbase'],
        }
        
        # Ensure Advanced Trade mode
        if 'options' not in coinbase_config:
            coinbase_config['options'] = {}
        coinbase_config['options'].setdefault('advanced', True)
        
        coinbase = ccxt.coinbase(coinbase_config)
        logger.info(f"✅ Exchange initialized: {coinbase.id}")
        logger.info(f"   Advanced Trade mode: {coinbase.options.get('advanced', False)}")
        
        # Load markets
        logger.info("")
        logger.info("STEP 2: Loading markets...")
        coinbase.load_markets()
        logger.info(f"✅ Markets loaded: {len(coinbase.markets)} markets")
        
        # Check balance
        logger.info("")
        logger.info("STEP 3: Checking USDC balance...")
        balance = coinbase.fetch_balance()
        usdc_balance = balance.get('USDC', {}).get('free', 0)
        logger.info(f"✅ Balance fetched")
        logger.info(f"   USDC available: {usdc_balance:.2f}")
        logger.info(f"   Total balance keys: {list(balance.keys())[:10]}")
        
        if usdc_balance < 2:
            logger.error(f"❌ Insufficient USDC: {usdc_balance:.2f} < $2.00")
            return
        
        # Get BTC price
        logger.info("")
        logger.info("STEP 4: Getting BTC/USDC price...")
        symbol = 'BTC/USDC'
        ticker = coinbase.fetch_ticker(symbol)
        btc_price = ticker['last']
        logger.info(f"✅ Price fetched: ${btc_price:,.2f}")
        logger.info(f"   Bid: ${ticker.get('bid', 0):,.2f}")
        logger.info(f"   Ask: ${ticker.get('ask', 0):,.2f}")
        
        # Calculate amount
        usd_amount = 2.0
        btc_amount = usd_amount / btc_price
        logger.info("")
        logger.info(f"STEP 5: Calculating order details...")
        logger.info(f"   USD amount: ${usd_amount:.2f}")
        logger.info(f"   BTC amount: {btc_amount:.8f} BTC")
        logger.info(f"   Price: ${btc_price:,.2f}")
        
        # Place LIMIT order (buy BTC with USDC)
        logger.info("")
        logger.info("STEP 6: Placing LIMIT BUY order...")
        logger.info(f"   Symbol: {symbol}")
        logger.info(f"   Type: limit")
        logger.info(f"   Side: buy")
        logger.info(f"   Amount: {btc_amount:.8f} BTC")
        logger.info(f"   Price: ${btc_price * 1.01:,.2f} (1% above market to ensure fill)")
        
        buy_price = btc_price * 1.01  # 1% above to ensure fill
        
        logger.info("")
        logger.info("📞 Calling coinbase.create_order()...")
        logger.info(f"   Parameters being passed:")
        logger.info(f"     - symbol: {symbol}")
        logger.info(f"     - type: 'limit'")
        logger.info(f"     - side: 'buy'")
        logger.info(f"     - amount: {btc_amount:.8f}")
        logger.info(f"     - price: {buy_price:.2f}")
        
        try:
            order = coinbase.create_order(
                symbol=symbol,
                type='limit',
                side='buy',
                amount=btc_amount,
                price=buy_price
            )
            
            logger.info("")
            logger.info("✅ ORDER CREATED SUCCESSFULLY!")
            logger.info(f"   Order ID: {order.get('id', 'N/A')}")
            logger.info(f"   Status: {order.get('status', 'N/A')}")
            logger.info(f"   Amount: {order.get('amount', 'N/A')}")
            logger.info(f"   Price: {order.get('price', 'N/A')}")
            logger.info(f"   Full response: {order}")
            
        except Exception as order_error:
            logger.error("")
            logger.error("❌ ORDER CREATION FAILED!")
            logger.error(f"   Error type: {type(order_error).__name__}")
            logger.error(f"   Error message: {str(order_error)}")
            
            # Detailed error analysis
            error_str = str(order_error)
            if 'account is not available' in error_str.lower():
                logger.error("")
                logger.error("🔍 DIAGNOSIS: 'account is not available' error")
                logger.error("   This means Coinbase API received the request but")
                logger.error("   cannot find/access the trading account.")
                logger.error("")
                logger.error("   Possible causes:")
                logger.error("   1. Account type: Business account (Advanced Trade not supported)")
                logger.error("   2. Trading disabled: Account trading not enabled")
                logger.error("   3. Account restrictions: Holds or limitations")
                logger.error("   4. KYC incomplete: Account verification needed")
            
            import traceback
            logger.error("")
            logger.error("📋 Full traceback:")
            logger.error(traceback.format_exc())
            
    except Exception as e:
        logger.error("")
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_coinbase_order())

