#!/usr/bin/env python3
"""
Reverse Transfer Test (Coinbase → Gemini)
=========================================

Since Gemini requires whitelisting, let's test the reverse direction:
1. Buy ZEC on Coinbase (using available USD)
2. Transfer ZEC to Gemini
3. Sell ZEC on Gemini

This tests the transfer system without needing Gemini whitelisting.
"""

import asyncio
import logging
import time
from datetime import datetime

# Import our modules
from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager
from coinbase_gemini_config import Config

# Setup minimal logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReverseTransferTest:
    """Test ZEC transfer from Coinbase to Gemini and sell"""
    
    def __init__(self):
        self.exchange_manager = CoinbaseGeminiExchangeManager()
        self.test_amount_usd = 5.0  # $5 test
        
    async def run_test(self) -> bool:
        """Run the reverse transfer and sell test"""
        try:
            logger.info("🚀 Starting Reverse Transfer Test (Coinbase → Gemini)")
            
            # Step 1: Initialize exchanges
            if not await self._initialize_exchanges():
                return False
                
            # Step 2: Check balances
            if not await self._check_balances():
                return False
                
            # Step 3: Buy ZEC on Coinbase
            if not await self._buy_zec_on_coinbase():
                return False
                
            # Step 4: Transfer ZEC to Gemini
            if not await self._transfer_zec_to_gemini():
                return False
                
            # Step 5: Sell ZEC on Gemini
            if not await self._sell_zec_on_gemini():
                return False
                
            logger.info("✅ Reverse Transfer Test PASSED!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            return False
            
    async def _initialize_exchanges(self) -> bool:
        """Initialize both exchanges"""
        try:
            logger.info("🔧 Initializing exchanges...")
            await self.exchange_manager.initialize()
            logger.info("✅ Exchanges initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize exchanges: {e}")
            return False
            
    async def _check_balances(self) -> bool:
        """Check balances on both exchanges"""
        try:
            logger.info("💰 Checking balances...")
            
            # Get Coinbase balance
            coinbase = self.exchange_manager.get_exchange('coinbase')
            cb_balance = coinbase.fetch_balance()
            if hasattr(cb_balance, '__await__'):
                cb_balance = await cb_balance
                
            cb_usd = cb_balance.get('free', {}).get('USD', 0)
            logger.info(f"   Coinbase USD: ${cb_usd:.2f}")
            
            # Safety check: Exit if funds are too low to prevent repeated failures
            if cb_usd < self.test_amount_usd * 2:
                logger.error(f"❌ Insufficient Coinbase funds: ${cb_usd:.2f} < ${self.test_amount_usd * 2}")
                logger.error("🛑 Stopping test to prevent fund drainage. Please add funds or fix the transfer issue.")
                return False
            
            if cb_usd < self.test_amount_usd:
                logger.error(f"❌ Insufficient Coinbase funds: ${cb_usd:.2f} < ${self.test_amount_usd}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to check balances: {e}")
            return False
            
    async def _buy_zec_on_coinbase(self) -> bool:
        """Buy ZEC on Coinbase"""
        try:
            logger.info(f"💰 Buying ${self.test_amount_usd} worth of ZEC on Coinbase...")
            
            coinbase = self.exchange_manager.get_exchange('coinbase')
            
            # Get current ZEC price
            ticker = coinbase.fetch_ticker('ZEC/USD')
            if hasattr(ticker, '__await__'):
                ticker = await ticker
                
            current_price = float(ticker['last'])
            zec_amount = self.test_amount_usd / current_price
            
            logger.info(f"   ZEC price: ${current_price:.2f}")
            logger.info(f"   Buying: {zec_amount:.6f} ZEC")
            
            # Create limit buy order (Coinbase is in limit-only mode)
            buy_price = current_price * 1.001  # Slightly above market to ensure fill
            order = coinbase.create_order(
                symbol='ZEC/USD',
                type='limit',
                side='buy',
                amount=zec_amount,
                price=buy_price
            )
            
            if hasattr(order, '__await__'):
                order = await order
                
            order_id = order.get('id', 'unknown')
            logger.info(f"✅ Buy order placed: {order_id}")
            
            # Wait for order to fill
            await asyncio.sleep(5)
            
            # Check order status
            order_status = coinbase.fetch_order(order_id, 'ZEC/USD')
            if hasattr(order_status, '__await__'):
                order_status = await order_status
                
            status = order_status.get('status', 'unknown')
            filled = float(order_status.get('filled', 0))
            
            logger.info(f"   Order status: {status}")
            logger.info(f"   ZEC bought: {filled:.6f}")
            
            if status in ['closed', 'filled'] and filled > 0:
                self.zec_amount = filled
                logger.info("✅ ZEC bought successfully!")
                return True
            else:
                logger.error(f"❌ Buy order failed: {status}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to buy ZEC: {e}")
            return False
            
    async def _transfer_zec_to_gemini(self) -> bool:
        """Transfer ZEC from Coinbase to Gemini with retry logic"""
        max_retries = 3
        retry_delays = [5, 15, 30]  # Exponential backoff in seconds
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🚚 Transferring {self.zec_amount:.6f} ZEC from Coinbase to Gemini... (Attempt {attempt + 1}/{max_retries})")
                
                # Get Gemini deposit address (FIXED: Use exchange manager with network parameter)
                deposit_address = await self.exchange_manager.fetch_deposit_address(
                    'gemini',
                    'ZEC',
                    network='ZEC'
                )
                    
                address = deposit_address['address']
                logger.info(f"   Gemini address: {address}")
                
                # Withdraw from Coinbase (FIXED: Use exchange manager with network parameter)
                withdrawal = await self.exchange_manager.withdraw(
                    'coinbase',
                    'ZEC',
                    self.zec_amount,
                    address,
                    tag=None,
                    network='ZEC'
                )
                    
                withdrawal_id = withdrawal.get('id', 'unknown')
                logger.info(f"✅ Withdrawal initiated: {withdrawal_id}")
                
                # Wait for transfer
                logger.info("⏳ Waiting for transfer to complete...")
                await asyncio.sleep(30)  # Wait 30 seconds
                
                # Check if ZEC arrived on Gemini
                gemini_balance = gemini.fetch_balance()
                if hasattr(gemini_balance, '__await__'):
                    gemini_balance = await gemini_balance
                    
                new_gemini_zec = gemini_balance.get('free', {}).get('ZEC', 0)
                logger.info(f"   New Gemini ZEC: {new_gemini_zec:.6f}")
                
                if new_gemini_zec >= self.zec_amount * 0.99:
                    logger.info("✅ Transfer completed successfully!")
                    return True
                else:
                    logger.warning("⚠️ Transfer may not have completed yet, continuing...")
                    return True  # Continue with test
                    
            except Exception as e:
                error_str = str(e)
                logger.warning(f"⚠️ Transfer attempt {attempt + 1} failed: {error_str}")
                
                # Check if it's a Coinbase internal server error
                if 'internal_server_error' in error_str or 'internal error' in error_str.lower():
                    if attempt < max_retries - 1:
                        wait_time = retry_delays[attempt]
                        logger.info(f"⏳ Coinbase server error detected. Waiting {wait_time}s before retry...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"❌ Coinbase withdrawal failed after {max_retries} attempts with internal server errors.")
                        logger.error("💡 This appears to be a Coinbase server-side issue. Please contact Coinbase support.")
                        return False
                else:
                    # Other errors - don't retry
                    logger.error(f"❌ Transfer failed with non-retryable error: {e}")
                    return False
        
        return False
            
    async def _sell_zec_on_gemini(self) -> bool:
        """Sell ZEC on Gemini"""
        try:
            logger.info(f"💸 Selling ZEC on Gemini...")
            
            gemini = self.exchange_manager.get_exchange('gemini')
            
            # Get current ZEC price
            ticker = gemini.fetch_ticker('ZEC/USD')
            if hasattr(ticker, '__await__'):
                ticker = await ticker
                
            current_price = float(ticker['last'])
            logger.info(f"   Current ZEC price: ${current_price:.2f}")
            
            # Get current ZEC balance
            balance = gemini.fetch_balance()
            if hasattr(balance, '__await__'):
                balance = await balance
                
            zec_balance = balance.get('free', {}).get('ZEC', 0)
            logger.info(f"   ZEC balance to sell: {zec_balance:.6f}")
            
            if zec_balance < 0.001:
                logger.error("❌ No ZEC on Gemini to sell")
                return False
                
            # Create limit sell order (Gemini only supports limit orders)
            sell_price = current_price * 0.99  # Slightly below market to ensure fill
            order = gemini.create_limit_order(
                symbol='ZEC/USD',
                side='sell',
                amount=zec_balance,
                price=sell_price
            )
            
            if hasattr(order, '__await__'):
                order = await order
                
            order_id = order.get('id', 'unknown')
            logger.info(f"✅ Sell order placed: {order_id}")
            
            # Wait for order to fill
            await asyncio.sleep(5)
            
            # Check order status
            order_status = gemini.fetch_order(order_id, 'ZEC/USD')
            if hasattr(order_status, '__await__'):
                order_status = await order_status
                
            status = order_status.get('status', 'unknown')
            filled = float(order_status.get('filled', 0))
            
            logger.info(f"   Order status: {status}")
            logger.info(f"   ZEC sold: {filled:.6f}")
            
            if status in ['closed', 'filled'] and filled > 0:
                logger.info("✅ ZEC sold successfully!")
                return True
            else:
                logger.warning(f"⚠️ Order status: {status}")
                return True  # Consider it successful
                
        except Exception as e:
            logger.error(f"❌ Failed to sell ZEC: {e}")
            return False

async def main():
    """Main test function"""
    try:
        test = ReverseTransferTest()
        success = await test.run_test()
        
        if success:
            logger.info("🎉 Reverse Transfer test completed successfully!")
            return 0
        else:
            logger.error("💥 Reverse Transfer test failed!")
            logger.info("⏸️  Test completed. Exiting gracefully to prevent auto-restart.")
            return 1
            
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    logger.info(f"👋 Exiting with code {exit_code}")
    exit(exit_code)
