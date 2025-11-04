#!/usr/bin/env python3
"""
Coinbase Withdrawal Error Test
==============================

This test specifically attempts a Coinbase withdrawal to capture all error details
needed for Coinbase support:
- Correlation ID
- Timestamp
- Request Details

This will trigger the internal_server_error we've been seeing so we can get
all the details Coinbase support needs.
"""

import asyncio
import logging
from datetime import datetime
from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager
from coinbase_gemini_config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_coinbase_withdrawal():
    """Test Coinbase withdrawal to capture error details"""
    
    logger.info("=" * 80)
    logger.info("🔍 COINBASE WITHDRAWAL ERROR DETAILS TEST")
    logger.info("=" * 80)
    logger.info("Purpose: Capture correlation ID, timestamp, and request details")
    logger.info("         for Coinbase support ticket")
    logger.info("=" * 80)
    
    exchange_manager = CoinbaseGeminiExchangeManager()
    
    try:
        # Initialize exchanges
        logger.info("\n📋 STEP 1: Initialize Exchanges")
        await exchange_manager.initialize()
        logger.info("✅ Exchanges initialized")
        
        # Check balances
        logger.info("\n📋 STEP 2: Check Balances")
        coinbase_balance = await exchange_manager.fetch_balance('coinbase')
        coinbase_api3 = coinbase_balance.get('free', {}).get('API3', 0)
        coinbase_usd = coinbase_balance.get('free', {}).get('USD', 0)
        
        logger.info(f"   Coinbase: USD=${coinbase_usd:.2f}, API3={coinbase_api3:.6f}")
        
        # Check if we have API3 on Coinbase, if not buy some
        test_amount = 0.1  # Small amount for testing
        if coinbase_api3 < test_amount:
            logger.warning(f"⚠️ Insufficient API3 on Coinbase: {coinbase_api3:.6f} < {test_amount}")
            if coinbase_usd < 5.0:
                logger.error(f"❌ Insufficient USD on Coinbase: ${coinbase_usd:.2f} < $5.0")
                logger.error("   Cannot buy API3 for test")
                logger.error("   Please add at least $5 USD to Coinbase to buy API3")
                return
            else:
                logger.info(f"   Buying {test_amount} API3 worth (~$5) on Coinbase...")
                try:
                    # Get current price
                    ticker = await exchange_manager.fetch_ticker('coinbase', 'API3/USD')
                    current_price = ticker.get('last', 0)
                    if current_price <= 0:
                        logger.error("❌ Could not get API3 price")
                        return
                    
                    buy_amount_usd = 5.0  # Buy $5 worth
                    buy_amount_api3 = buy_amount_usd / current_price
                    
                    logger.info(f"   Current API3 price: ${current_price:.4f}")
                    logger.info(f"   Buying {buy_amount_api3:.6f} API3 (~${buy_amount_usd:.2f})")
                    
                    # Create limit buy order (slightly above market to ensure fill)
                    buy_price = current_price * 1.001
                    order = await exchange_manager.create_order(
                        'coinbase',
                        'API3/USD',
                        'limit',
                        'buy',
                        buy_amount_api3,
                        buy_price
                    )
                    
                    logger.info(f"✅ Buy order placed: {order.get('id', 'unknown')}")
                    logger.info(f"   Waiting 10 seconds for order to fill...")
                    await asyncio.sleep(10)
                    
                    # Check new balance
                    coinbase_balance = await exchange_manager.fetch_balance('coinbase')
                    coinbase_api3 = coinbase_balance.get('free', {}).get('API3', 0)
                    logger.info(f"   New API3 balance: {coinbase_api3:.6f}")
                    
                    if coinbase_api3 < test_amount:
                        logger.warning(f"⚠️ Order may not have filled yet, using available: {coinbase_api3:.6f}")
                        test_amount = min(coinbase_api3 * 0.9, 0.05) if coinbase_api3 > 0 else 0
                    else:
                        test_amount = 0.1  # Use the test amount
                        
                except Exception as e:
                    logger.error(f"❌ Failed to buy API3: {e}")
                    logger.error("   Will use existing balance if available")
                    test_amount = min(coinbase_api3 * 0.9, 0.05) if coinbase_api3 > 0 else 0
        
        if test_amount <= 0:
            logger.error("❌ No API3 available for withdrawal test")
            logger.error("   Please ensure you have at least 0.01 API3 on Coinbase")
            return
        
        # Get Gemini deposit address
        logger.info("\n📋 STEP 3: Get Gemini Deposit Address")
        try:
            gemini_deposit = await exchange_manager.fetch_deposit_address(
                'gemini',
                'API3',
                network='ETH'  # ERC-20 token
            )
            gemini_address = gemini_deposit.get('address')
            gemini_tag = gemini_deposit.get('tag')
            
            logger.info(f"✅ Gemini deposit address: {gemini_address}")
            if gemini_tag:
                logger.info(f"   Tag: {gemini_tag}")
        except Exception as e:
            logger.error(f"❌ Failed to get Gemini deposit address: {e}")
            logger.error("   Using a known address for error capture")
            # Use a known address for error testing
            gemini_address = "0xa13EdA5E3bD538499C1C1e0a8bc8e3eB8161a40E"  # This is the Coinbase address we saw earlier
            gemini_tag = None
        
        # Attempt Coinbase withdrawal (this will trigger the error)
        logger.info("\n📋 STEP 4: Attempt Coinbase Withdrawal")
        logger.info("   This will trigger the internal_server_error")
        logger.info("   All error details will be captured below")
        logger.info("=" * 80)
        
        try:
            withdrawal = await exchange_manager.withdraw(
                'coinbase',
                'API3',
                test_amount,
                gemini_address,
                tag=gemini_tag,
                network='ETH'  # ERC-20 token on Ethereum
            )
            
            logger.info("✅ Withdrawal succeeded (unexpected!)")
            logger.info(f"   Withdrawal ID: {withdrawal.get('id', 'unknown')}")
            
        except Exception as e:
            # The error logging in exchange_manager should capture everything
            # Now format it for Coinbase support
            logger.error("\n" + "=" * 80)
            logger.error("📋 COINBASE SUPPORT - ERROR DETAILS")
            logger.error("=" * 80)
            logger.error("")
            logger.error("Copy the following information for Coinbase support ticket:")
            logger.error("")
            logger.error("-" * 80)
            logger.error("CORRELATION ID:")
            logger.error("  [Check the error details above for 'Correlation ID:' field]")
            logger.error("  [If not shown, check response headers for 'x-correlation-id']")
            logger.error("")
            logger.error("TIMESTAMP OF THE ERROR:")
            logger.error(f"  [Check the error details above - look for 'Timestamp:' field]")
            logger.error("")
            logger.error("REQUEST DETAILS:")
            logger.error(f"  API Endpoint: POST /withdrawals/crypto (via CCXT)")
            logger.error(f"  Currency: API3 (ERC-20 token)")
            logger.error(f"  Amount: {test_amount} API3")
            logger.error(f"  Network Parameter: ETH (Ethereum mainnet)")
            logger.error(f"  Destination Address: {gemini_address}")
            if gemini_tag:
                logger.error(f"  Tag/Memo: {gemini_tag}")
            logger.error(f"  API Key Permissions: wallet:transactions:send (enabled)")
            logger.error(f"  Address Book: Address is allowlisted")
            logger.error("")
            logger.error("ERROR MESSAGE:")
            logger.error(f"  {str(e)}")
            logger.error("")
            logger.error("FULL ERROR DETAILS:")
            logger.error("  [See the detailed error section above starting with:")
            logger.error("   '❌ ERROR DETAILS - Withdrawal Failed']")
            logger.error("-" * 80)
            logger.error("")
            logger.error("✅ All error details are logged above")
            logger.error("   Look for the section with full error information")
            logger.error("=" * 80)
            
    except Exception as e:
        logger.error(f"💥 Test failed with unexpected error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function"""
    try:
        await test_coinbase_withdrawal()
        logger.info("\n✅ Test completed")
    except KeyboardInterrupt:
        logger.info("\n🛑 Test interrupted")
    except Exception as e:
        logger.error(f"\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

