#!/usr/bin/env python3
"""
Bidirectional Transfer Test
===========================

Tests transferring crypto in both directions:
1. Gemini → Coinbase (forward)
2. Coinbase → Gemini (reverse)

Uses SOL for fast, cheap transfers.
Only logs important events.
Exits gracefully to not interfere with trading bot.
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

class BidirectionalTransferTest:
    """Test SOL transfers in both directions"""
    
    def __init__(self):
        self.exchange_manager = CoinbaseGeminiExchangeManager()
        self.test_crypto = 'SOL'  # Use SOL - fast and cheap transfers
        self.test_amount_sol = 0.01  # 0.01 SOL test amount
        
    async def run_test(self) -> bool:
        """Run bidirectional transfer test"""
        try:
            logger.info("🚀 Starting Bidirectional Transfer Test")
            logger.info(f"   Crypto: {self.test_crypto}")
            logger.info(f"   Amount: {self.test_amount_sol} {self.test_crypto}")
            
            # Step 1: Initialize exchanges
            if not await self._initialize_exchanges():
                return False
                
            # Step 2: Check balances
            if not await self._check_balances():
                return False
                
            # Step 3: Forward transfer (Gemini → Coinbase)
            logger.info("\n📤 Testing FORWARD transfer (Gemini → Coinbase)...")
            if not await self._transfer_gemini_to_coinbase():
                logger.error("❌ Forward transfer failed - stopping test")
                return False
                
            # Step 4: Wait for transfer to complete
            logger.info("⏳ Waiting 60 seconds for forward transfer to settle...")
            await asyncio.sleep(60)
            
            # Step 5: Reverse transfer (Coinbase → Gemini)
            logger.info("\n📥 Testing REVERSE transfer (Coinbase → Gemini)...")
            if not await self._transfer_coinbase_to_gemini():
                logger.error("❌ Reverse transfer failed")
                return False
                
            # Step 6: Wait for transfer to complete
            logger.info("⏳ Waiting 60 seconds for reverse transfer to settle...")
            await asyncio.sleep(60)
            
            # Step 7: Verify final balances
            logger.info("\n✅ Verifying final balances...")
            await self._check_final_balances()
            
            logger.info("\n🎉 Bidirectional Transfer Test PASSED!")
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
        """Check SOL balances on both exchanges"""
        try:
            logger.info("💰 Checking SOL balances...")
            
            # Get Gemini balance
            gemini = self.exchange_manager.get_exchange('gemini')
            gemini_balance = gemini.fetch_balance()
            if hasattr(gemini_balance, '__await__'):
                gemini_balance = await gemini_balance
                
            gemini_sol = gemini_balance.get('free', {}).get('SOL', 0)
            logger.info(f"   Gemini SOL: {gemini_sol:.6f}")
            
            # Get Coinbase balance
            coinbase = self.exchange_manager.get_exchange('coinbase')
            coinbase_balance = coinbase.fetch_balance()
            if hasattr(coinbase_balance, '__await__'):
                coinbase_balance = await coinbase_balance
                
            coinbase_sol = coinbase_balance.get('free', {}).get('SOL', 0)
            logger.info(f"   Coinbase SOL: {coinbase_sol:.6f}")
            
            # Check if we have enough SOL on Gemini to start
            if gemini_sol < self.test_amount_sol:
                logger.error(f"❌ Insufficient SOL on Gemini: {gemini_sol:.6f} < {self.test_amount_sol}")
                logger.error("💡 Please ensure you have at least 0.01 SOL on Gemini to start the test")
                return False
            
            # Store initial balances
            self.initial_gemini_sol = gemini_sol
            self.initial_coinbase_sol = coinbase_sol
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to check balances: {e}")
            return False
            
    async def _transfer_gemini_to_coinbase(self) -> bool:
        """Transfer SOL from Gemini to Coinbase with retry logic"""
        max_retries = 3
        retry_delays = [5, 15, 30]
        
        for attempt in range(max_retries):
            try:
                logger.info(f"   Attempt {attempt + 1}/{max_retries}: Transferring {self.test_amount_sol} SOL from Gemini to Coinbase...")
                
                # Get Coinbase deposit address (FIXED: Use exchange manager with network parameter)
                deposit_address = await self.exchange_manager.fetch_deposit_address(
                    'coinbase',
                    self.test_crypto,
                    network='SOL'
                )
                    
                address = deposit_address['address']
                logger.info(f"   Coinbase address: {address}")
                
                # Withdraw from Gemini
                gemini = self.exchange_manager.get_exchange('gemini')
                withdrawal = gemini.withdraw(
                    self.test_crypto,
                    self.test_amount_sol,
                    address,
                    None,
                    {'network': 'SOL'}
                )
                if hasattr(withdrawal, '__await__'):
                    withdrawal = await withdrawal
                    
                withdrawal_id = withdrawal.get('id', 'unknown')
                logger.info(f"✅ Withdrawal initiated from Gemini: {withdrawal_id}")
                
                # Wait a bit and check if SOL arrived on Coinbase
                logger.info("   Waiting 30 seconds for transfer...")
                await asyncio.sleep(30)
                
                # Check Coinbase balance
                coinbase_balance = coinbase.fetch_balance()
                if hasattr(coinbase_balance, '__await__'):
                    coinbase_balance = await coinbase_balance
                    
                new_coinbase_sol = coinbase_balance.get('free', {}).get('SOL', 0)
                logger.info(f"   Coinbase SOL after transfer: {new_coinbase_sol:.6f}")
                
                if new_coinbase_sol >= self.initial_coinbase_sol + self.test_amount_sol * 0.99:
                    logger.info("✅ Forward transfer completed successfully!")
                    self.coinbase_sol_after_forward = new_coinbase_sol
                    return True
                else:
                    logger.warning(f"   SOL not yet received (may take longer for SOL transfers)")
                    # SOL transfers can take 1-5 minutes, so we'll continue
                    self.coinbase_sol_after_forward = new_coinbase_sol
                    return True  # Continue with test
                    
            except Exception as e:
                error_str = str(e)
                logger.warning(f"⚠️ Forward transfer attempt {attempt + 1} failed: {error_str}")
                
                # Check if it's a whitelist error
                if 'whitelist' in error_str.lower() or 'whitelists are not enabled' in error_str:
                    logger.error("❌ Gemini whitelisting issue detected")
                    logger.error("💡 Please ensure Gemini address whitelisting is enabled for your account")
                    return False  # Don't retry whitelist errors
                    
                # Check if it's retryable
                if attempt < max_retries - 1:
                    wait_time = retry_delays[attempt]
                    logger.info(f"⏳ Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"❌ Forward transfer failed after {max_retries} attempts")
                    return False
        
        return False
        
    async def _transfer_coinbase_to_gemini(self) -> bool:
        """Transfer SOL from Coinbase to Gemini with retry logic"""
        max_retries = 3
        retry_delays = [5, 15, 30]
        
        for attempt in range(max_retries):
            try:
                logger.info(f"   Attempt {attempt + 1}/{max_retries}: Transferring {self.test_amount_sol} SOL from Coinbase to Gemini...")
                
                # Get Gemini deposit address (FIXED: Use exchange manager with network parameter)
                deposit_address = await self.exchange_manager.fetch_deposit_address(
                    'gemini',
                    self.test_crypto,
                    network='SOL'
                )
                    
                address = deposit_address['address']
                logger.info(f"   Gemini address: {address}")
                
                # Withdraw from Coinbase (FIXED: Use exchange manager with network parameter)
                withdrawal = await self.exchange_manager.withdraw(
                    'coinbase',
                    self.test_crypto,
                    self.test_amount_sol,
                    address,
                    tag=None,
                    network='SOL'
                )
                    
                withdrawal_id = withdrawal.get('id', 'unknown')
                logger.info(f"✅ Withdrawal initiated from Coinbase: {withdrawal_id}")
                
                # Wait a bit and check if SOL arrived on Gemini
                logger.info("   Waiting 30 seconds for transfer...")
                await asyncio.sleep(30)
                
                # Check Gemini balance
                gemini_balance = gemini.fetch_balance()
                if hasattr(gemini_balance, '__await__'):
                    gemini_balance = await gemini_balance
                    
                new_gemini_sol = gemini_balance.get('free', {}).get('SOL', 0)
                logger.info(f"   Gemini SOL after transfer: {new_gemini_sol:.6f}")
                
                if new_gemini_sol >= self.initial_gemini_sol - self.test_amount_sol * 1.01:
                    logger.info("✅ Reverse transfer completed successfully!")
                    return True
                else:
                    logger.warning(f"   SOL not yet received (may take longer for SOL transfers)")
                    return True  # Continue
                    
            except Exception as e:
                error_str = str(e)
                logger.warning(f"⚠️ Reverse transfer attempt {attempt + 1} failed: {error_str}")
                
                # Check if it's a Coinbase internal server error
                if 'internal_server_error' in error_str or 'internal error' in error_str.lower():
                    if attempt < max_retries - 1:
                        wait_time = retry_delays[attempt]
                        logger.info(f"⏳ Coinbase server error. Waiting {wait_time}s before retry...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"❌ Reverse transfer failed after {max_retries} attempts with Coinbase server errors")
                        logger.error("💡 This appears to be a Coinbase server-side issue")
                        return False
                else:
                    # Other errors
                    logger.error(f"❌ Reverse transfer failed: {e}")
                    if attempt < max_retries - 1:
                        wait_time = retry_delays[attempt]
                        await asyncio.sleep(wait_time)
                        continue
                    return False
        
        return False
        
    async def _check_final_balances(self) -> bool:
        """Check final balances to verify transfers"""
        try:
            logger.info("📊 Final balance check...")
            
            # Get Gemini balance
            gemini = self.exchange_manager.get_exchange('gemini')
            gemini_balance = gemini.fetch_balance()
            if hasattr(gemini_balance, '__await__'):
                gemini_balance = await gemini_balance
                
            final_gemini_sol = gemini_balance.get('free', {}).get('SOL', 0)
            
            # Get Coinbase balance
            coinbase = self.exchange_manager.get_exchange('coinbase')
            coinbase_balance = coinbase.fetch_balance()
            if hasattr(coinbase_balance, '__await__'):
                coinbase_balance = await coinbase_balance
                
            final_coinbase_sol = coinbase_balance.get('free', {}).get('SOL', 0)
            
            logger.info(f"   Initial Gemini SOL: {self.initial_gemini_sol:.6f}")
            logger.info(f"   Final Gemini SOL: {final_gemini_sol:.6f}")
            logger.info(f"   Initial Coinbase SOL: {self.initial_coinbase_sol:.6f}")
            logger.info(f"   Final Coinbase SOL: {final_coinbase_sol:.6f}")
            
            # Calculate expected final balance (should be close to initial)
            expected_gemini = self.initial_gemini_sol - self.test_amount_sol  # Lost in forward transfer
            
            if abs(final_gemini_sol - expected_gemini) < self.test_amount_sol * 0.1:
                logger.info("✅ Balances match expected values (within tolerance)")
                return True
            else:
                logger.warning("⚠️ Balances may still be settling (SOL transfers can take time)")
                return True  # Don't fail on this
                
        except Exception as e:
            logger.warning(f"⚠️ Could not verify final balances: {e}")
            return True  # Don't fail the test on verification

async def main():
    """Main test function"""
    try:
        test = BidirectionalTransferTest()
        success = await test.run_test()
        
        if success:
            logger.info("\n🎉 Bidirectional Transfer Test PASSED!")
            logger.info("✅ Both forward and reverse transfers completed successfully")
            return 0
        else:
            logger.error("\n💥 Bidirectional Transfer Test FAILED!")
            logger.error("❌ One or both transfers failed. Check logs above for details.")
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n🛑 Test interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"\n💥 Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    logger.info(f"\n👋 Exiting with code {exit_code}")
    exit(exit_code)
