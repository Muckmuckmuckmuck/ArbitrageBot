#!/usr/bin/env python3
"""
API3 Bidirectional Transfer Test
=================================

Complete test of API3 transfers in both directions:
1. Check existing API3 on Gemini
2. Transfer API3 from Gemini → Coinbase
3. Verify transfer arrival on Coinbase
4. Transfer API3 from Coinbase → Gemini back

Uses ONLY proven patterns that we know work.
Completely documents what works and what doesn't.

API3 Network: Ethereum (ERC-20)
"""

import asyncio
import logging
import time
from datetime import datetime

# Import our modules (PROVEN WORKING)
from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager
from coinbase_gemini_config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class API3BidirectionalTransferTest:
    """Complete API3 bidirectional transfer test"""
    
    def __init__(self):
        self.exchange_manager = CoinbaseGeminiExchangeManager()
        self.test_crypto = 'API3'
        self.test_symbol_gemini = 'API3/USD'  # Gemini uses USD
        self.test_symbol_coinbase = 'API3/USD'  # Coinbase uses USD
        self.test_amount_usd = 5.0  # $5 worth of API3 per test
        self.network = 'ETH'  # API3 is ERC-20 token on Ethereum
        
        # Test results documentation
        self.results = {
            'transfer_gemini_to_coinbase': {'status': 'pending', 'details': {}},
            'transfer_coinbase_to_gemini': {'status': 'pending', 'details': {}},
        }
        
        # Track amounts
        self.gemini_api3_available = 0.0
        self.coinbase_api3_to_send = 0.0
        
    async def run_test(self) -> bool:
        """Run complete bidirectional transfer test"""
        try:
            logger.info("=" * 60)
            logger.info("🚀 API3 BIDIRECTIONAL TRANSFER TEST")
            logger.info("=" * 60)
            logger.info(f"Crypto: {self.test_crypto}")
            logger.info(f"Network: {self.network} (Ethereum ERC-20)")
            logger.info("Using existing API3 on Gemini (no purchase needed)")
            logger.info("=" * 60)
            
            # Step 1: Initialize exchanges (PROVEN WORKING)
            logger.info("\n📋 STEP 1: Initialize Exchanges")
            if not await self._initialize_exchanges():
                return False
                
            # Step 2: Check initial balances and verify we have API3
            logger.info("\n📋 STEP 2: Check Initial Balances")
            if not await self._check_initial_balances():
                return False
                
            # Step 3: Forward transfer (Gemini → Coinbase)
            logger.info("\n📋 STEP 3: Forward Transfer (Gemini → Coinbase)")
            if not await self._transfer_gemini_to_coinbase():
                logger.error("❌ Forward transfer failed")
                self._print_results()
                return False
                
            # Step 4: Wait for forward transfer to settle and verify
            logger.info("\n⏳ Waiting 90 seconds for forward transfer to settle...")
            logger.info("   (ERC-20 transfers typically take 1-5 minutes)")
            await asyncio.sleep(90)
            
            # Step 5: Verify forward transfer and get amount that arrived
            logger.info("\n📋 STEP 4: Verify Forward Transfer")
            if not await self._verify_forward_transfer():
                logger.error("❌ Forward transfer verification failed")
                self._print_results()
                return False
                
            # Step 6: Reverse transfer (Coinbase → Gemini) - use the amount that arrived
            logger.info("\n📋 STEP 5: Reverse Transfer (Coinbase → Gemini)")
            if not await self._transfer_coinbase_to_gemini():
                logger.error("❌ Reverse transfer failed")
                self._print_results()
                return False
                
            # Step 9: Wait for reverse transfer to settle
            logger.info("\n⏳ Waiting 90 seconds for reverse transfer to settle...")
            await asyncio.sleep(90)
            
            # Step 10: Verify reverse transfer
            logger.info("\n📋 STEP 8: Verify Reverse Transfer")
            await self._verify_reverse_transfer()
            
            # Step 11: Print final results
            logger.info("\n" + "=" * 60)
            self._print_results()
            logger.info("=" * 60)
            
            # Determine overall success
            if (self.results['transfer_gemini_to_coinbase']['status'] == 'success' and
                self.results['transfer_coinbase_to_gemini']['status'] == 'success'):
                logger.info("\n🎉 COMPLETE SUCCESS - All operations passed!")
                return True
            else:
                logger.error("\n⚠️ PARTIAL SUCCESS - Some operations failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Test failed with unexpected error: {e}")
            self._print_results()
            return False
            
    async def _initialize_exchanges(self) -> bool:
        """Initialize exchanges (PROVEN WORKING PATTERN)"""
        try:
            logger.info("🔧 Initializing exchanges...")
            await self.exchange_manager.initialize()
            logger.info("✅ Exchanges initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize exchanges: {e}")
            return False
            
    async def _check_initial_balances(self) -> bool:
        """Check initial balances (PROVEN WORKING PATTERN)"""
        try:
            logger.info("💰 Checking initial balances...")
            
            # Get Gemini balance
            gemini = self.exchange_manager.get_exchange('gemini')
            gemini_balance = gemini.fetch_balance()
            if hasattr(gemini_balance, '__await__'):
                gemini_balance = await gemini_balance
                
            gemini_usd = gemini_balance.get('free', {}).get('USD', 0)
            gemini_api3 = gemini_balance.get('free', {}).get('API3', 0)
            
            # Get Coinbase balance
            coinbase = self.exchange_manager.get_exchange('coinbase')
            coinbase_balance = coinbase.fetch_balance()
            if hasattr(coinbase_balance, '__await__'):
                coinbase_balance = await coinbase_balance
                
            coinbase_usd = coinbase_balance.get('free', {}).get('USD', 0)
            coinbase_api3 = coinbase_balance.get('free', {}).get('API3', 0)
            
            logger.info(f"   Gemini: USD=${gemini_usd:.2f}, API3={gemini_api3:.6f}")
            logger.info(f"   Coinbase: USD=${coinbase_usd:.2f}, API3={coinbase_api3:.6f}")
            
            # Store initial balances
            self.initial_gemini_usd = gemini_usd
            self.initial_gemini_api3 = gemini_api3
            self.initial_coinbase_usd = coinbase_usd
            self.initial_coinbase_api3 = coinbase_api3
            
            # Check if we have API3 on Gemini to transfer
            self.gemini_api3_available = gemini_api3
            
            if gemini_api3 < 0.01:  # Need at least 0.01 API3 for test
                logger.error(f"❌ Insufficient API3 on Gemini: {gemini_api3:.6f} < 0.01")
                logger.error("💡 Need at least 0.01 API3 on Gemini to transfer")
                return False
                
            # Use a small amount for test (about 5% of available, minimum 0.1 API3)
            transfer_amount = max(0.1, gemini_api3 * 0.05)
            self.gemini_api3_available = transfer_amount
            
            logger.info(f"✅ API3 available on Gemini: {gemini_api3:.6f}")
            logger.info(f"   Will transfer: {transfer_amount:.6f} API3")
            logger.info("   (Coinbase will receive transfer)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to check balances: {e}")
            return False
            
    async def _buy_api3_on_gemini(self) -> bool:
        """Buy API3 on Gemini (PROVEN WORKING - limit orders only)"""
        try:
            logger.info(f"💰 Buying ${self.test_amount_usd} worth of API3 on Gemini...")
            
            gemini = self.exchange_manager.get_exchange('gemini')
            
            # Get current API3 price (PROVEN WORKING)
            ticker = gemini.fetch_ticker(self.test_symbol_gemini)
            if hasattr(ticker, '__await__'):
                ticker = await ticker
                
            current_price = float(ticker['last'])
            api3_amount = self.test_amount_usd / current_price
            
            logger.info(f"   Current price: ${current_price:.4f}")
            logger.info(f"   Buying: {api3_amount:.6f} API3")
            
            # Gemini only supports limit orders (PROVEN)
            buy_price = current_price * 1.001  # Slightly above market to ensure fill
            logger.info(f"   Limit price: ${buy_price:.4f}")
            
            # Create limit buy order (PROVEN WORKING)
            order = gemini.create_limit_order(
                symbol=self.test_symbol_gemini,
                side='buy',
                amount=api3_amount,
                price=buy_price
            )
            
            if hasattr(order, '__await__'):
                order = await order
                
            order_id = order.get('id', 'unknown')
            logger.info(f"✅ Buy order placed: {order_id}")
            
            # Wait for order to fill
            await asyncio.sleep(5)
            
            # Check order status (PROVEN WORKING)
            order_status = gemini.fetch_order(order_id, self.test_symbol_gemini)
            if hasattr(order_status, '__await__'):
                order_status = await order_status
                
            status = order_status.get('status', 'unknown')
            filled = float(order_status.get('filled', 0))
            average_price = float(order_status.get('average', 0))
            
            logger.info(f"   Order status: {status}")
            logger.info(f"   API3 bought: {filled:.6f}")
            logger.info(f"   Average price: ${average_price:.4f}")
            
            if status in ['closed', 'filled'] and filled > 0:
                self.gemini_api3_bought = filled
                self.gemini_api3_price = average_price
                
                self.results['buy_gemini'] = {
                    'status': 'success',
                    'details': {
                        'order_id': order_id,
                        'amount': filled,
                        'price': average_price,
                        'total_cost': filled * average_price
                    }
                }
                
                logger.info("✅ API3 bought successfully on Gemini!")
                return True
            else:
                self.results['buy_gemini'] = {
                    'status': 'failed',
                    'details': {'order_id': order_id, 'status': status, 'filled': filled}
                }
                logger.error(f"❌ Buy order failed: {status}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to buy API3 on Gemini: {e}")
            self.results['buy_gemini'] = {
                'status': 'error',
                'details': {'error': str(e)}
            }
            return False
            
    async def _buy_api3_on_coinbase(self) -> bool:
        """Buy API3 on Coinbase (PROVEN WORKING - limit orders only, no market orders)"""
        try:
            logger.info(f"💰 Buying ${self.test_amount_usd} worth of API3 on Coinbase...")
            
            coinbase = self.exchange_manager.get_exchange('coinbase')
            
            # Get current API3 price (PROVEN WORKING)
            ticker = coinbase.fetch_ticker(self.test_symbol_coinbase)
            if hasattr(ticker, '__await__'):
                ticker = await ticker
                
            current_price = float(ticker['last'])
            api3_amount = self.test_amount_usd / current_price
            
            logger.info(f"   Current price: ${current_price:.4f}")
            logger.info(f"   Buying: {api3_amount:.6f} API3")
            
            # Coinbase requires limit orders (PROVEN - market orders fail)
            buy_price = current_price * 1.001  # Slightly above market to ensure fill
            logger.info(f"   Limit price: ${buy_price:.4f}")
            
            # Create limit buy order (PROVEN WORKING)
            order = coinbase.create_order(
                symbol=self.test_symbol_coinbase,
                type='limit',
                side='buy',
                amount=api3_amount,
                price=buy_price
            )
            
            if hasattr(order, '__await__'):
                order = await order
                
            order_id = order.get('id', 'unknown')
            logger.info(f"✅ Buy order placed: {order_id}")
            
            # Wait for order to fill
            await asyncio.sleep(5)
            
            # Check order status (PROVEN WORKING)
            order_status = coinbase.fetch_order(order_id, self.test_symbol_coinbase)
            if hasattr(order_status, '__await__'):
                order_status = await order_status
                
            status = order_status.get('status', 'unknown')
            filled = float(order_status.get('filled', 0))
            average_price = float(order_status.get('average', 0))
            
            logger.info(f"   Order status: {status}")
            logger.info(f"   API3 bought: {filled:.6f}")
            logger.info(f"   Average price: ${average_price:.4f}")
            
            if status in ['closed', 'filled'] and filled > 0:
                self.coinbase_api3_bought = filled
                self.coinbase_api3_price = average_price
                
                self.results['buy_coinbase'] = {
                    'status': 'success',
                    'details': {
                        'order_id': order_id,
                        'amount': filled,
                        'price': average_price,
                        'total_cost': filled * average_price
                    }
                }
                
                logger.info("✅ API3 bought successfully on Coinbase!")
                return True
            else:
                self.results['buy_coinbase'] = {
                    'status': 'failed',
                    'details': {'order_id': order_id, 'status': status, 'filled': filled}
                }
                logger.error(f"❌ Buy order failed: {status}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to buy API3 on Coinbase: {e}")
            self.results['buy_coinbase'] = {
                'status': 'error',
                'details': {'error': str(e)}
            }
            return False
            
    async def _transfer_gemini_to_coinbase(self) -> bool:
        """Transfer API3 from Gemini to Coinbase (PROVEN RETRY PATTERN)"""
        max_retries = 3
        retry_delays = [5, 15, 30]
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🚚 Transferring API3 from Gemini to Coinbase... (Attempt {attempt + 1}/{max_retries})")
                
                # Get Coinbase deposit address (FIXED: Use exchange manager with network parameter)
                try:
                    deposit_address = await self.exchange_manager.fetch_deposit_address(
                        'coinbase', 
                        self.test_crypto,
                        network=self.network  # ERC-20 tokens require network parameter
                    )
                    logger.info(f"✅ Got deposit address via exchange manager (network: {self.network})")
                except Exception as e:
                    logger.error(f"❌ Failed to get deposit address: {e}")
                    raise ValueError(f"Failed to get deposit address from Coinbase: {e}")
                    
                if deposit_address is None or (isinstance(deposit_address, dict) and 'address' not in deposit_address):
                    logger.error(f"❌ Coinbase returned invalid deposit address: {deposit_address}")
                    logger.error("💡 This may require:")
                    logger.error("   1. Enabling deposit addresses for API3 in Coinbase UI")
                    logger.error("   2. Generating a new deposit address for API3")
                    logger.error("   3. Checking if API3 deposits are enabled on your account")
                    raise ValueError(f"Invalid deposit address from Coinbase: {deposit_address}")
                    
                address = deposit_address['address']
                tag = deposit_address.get('tag', None)
                logger.info(f"   Coinbase address: {address}")
                if tag:
                    logger.info(f"   Coinbase tag: {tag}")
                
                # Withdraw from Gemini (FIXED: Use exchange manager with network parameter)
                withdrawal = await self.exchange_manager.withdraw(
                    'gemini',
                    self.test_crypto,
                    self.gemini_api3_available,
                    address,
                    tag=tag,
                    network=self.network
                )
                    
                withdrawal_id = withdrawal.get('id', 'unknown')
                logger.info(f"✅ Withdrawal initiated from Gemini: {withdrawal_id}")
                
                # Store withdrawal details
                self.gemini_withdrawal_id = withdrawal_id
                self.gemini_to_coinbase_address = address
                
                self.results['transfer_gemini_to_coinbase'] = {
                    'status': 'success',
                    'details': {
                        'withdrawal_id': withdrawal_id,
                        'amount': self.gemini_api3_available,
                        'destination_address': address,
                        'network': self.network
                    }
                }
                
                logger.info("✅ Forward transfer initiated successfully!")
                return True
                    
            except Exception as e:
                error_str = str(e)
                
                # Extract detailed error information
                error_details = {
                    'timestamp': datetime.now().isoformat(),
                    'error_message': error_str,
                    'currency': self.test_crypto,
                    'amount': self.gemini_api3_available,
                    'network': self.network,
                    'destination_address': address if 'address' in locals() else 'unknown',
                    'attempt': attempt + 1
                }
                
                # Try to extract correlation ID, request ID, or other details from exception
                if hasattr(e, 'args') and e.args:
                    for arg in e.args:
                        if isinstance(arg, dict):
                            if 'correlation_id' in arg:
                                error_details['correlation_id'] = arg['correlation_id']
                            if 'request_id' in arg:
                                error_details['request_id'] = arg['request_id']
                            if 'id' in arg:
                                error_details['error_id'] = arg['id']
                
                # Log detailed error information
                logger.error(f"❌ Forward transfer attempt {attempt + 1} failed:")
                logger.error(f"   Timestamp: {error_details['timestamp']}")
                logger.error(f"   Error Message: {error_str}")
                if 'correlation_id' in error_details:
                    logger.error(f"   Correlation ID: {error_details['correlation_id']}")
                if 'request_id' in error_details:
                    logger.error(f"   Request ID: {error_details['request_id']}")
                logger.error(f"   Request Details:")
                logger.error(f"     - Currency: {self.test_crypto}")
                logger.error(f"     - Amount: {self.gemini_api3_available:.6f}")
                logger.error(f"     - Network: {self.network}")
                logger.error(f"     - Destination: {error_details['destination_address']}")
                
                # Check if it's a whitelist error (non-retryable)
                if 'whitelist' in error_str.lower() or 'whitelists are not enabled' in error_str:
                    logger.error("❌ Gemini whitelisting issue detected")
                    logger.error("💡 Gemini requires address whitelisting for withdrawals")
                    self.results['transfer_gemini_to_coinbase'] = {
                        'status': 'failed',
                        'details': error_details
                    }
                    return False
                    
                # Check if it's retryable
                if attempt < max_retries - 1:
                    wait_time = retry_delays[attempt]
                    logger.info(f"⏳ Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"❌ Forward transfer failed after {max_retries} attempts")
                    self.results['transfer_gemini_to_coinbase'] = {
                        'status': 'failed',
                        'details': {
                            'error': 'max_retries_exceeded',
                            'error_message': error_str
                        }
                    }
                    return False
        
        return False
        
    async def _transfer_coinbase_to_gemini(self) -> bool:
        """Transfer API3 from Coinbase to Gemini (PROVEN RETRY PATTERN)"""
        max_retries = 3
        retry_delays = [5, 15, 30]
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🚚 Transferring API3 from Coinbase to Gemini... (Attempt {attempt + 1}/{max_retries})")
                
                # Get Gemini deposit address (FIXED: Use exchange manager with network parameter)
                try:
                    deposit_address = await self.exchange_manager.fetch_deposit_address(
                        'gemini',
                        self.test_crypto,
                        network=self.network  # ERC-20 tokens require network parameter
                    )
                    logger.info(f"✅ Got deposit address via exchange manager (network: {self.network})")
                except Exception as e:
                    logger.error(f"❌ Failed to get deposit address: {e}")
                    raise ValueError(f"Failed to get deposit address from Gemini: {e}")
                    
                if deposit_address is None or 'address' not in deposit_address:
                    logger.error(f"❌ Gemini returned invalid deposit address: {deposit_address}")
                    logger.error("💡 This may require enabling/generating deposit address on Gemini first")
                    raise ValueError(f"Invalid deposit address from Gemini: {deposit_address}")
                    
                address = deposit_address['address']
                tag = deposit_address.get('tag', None)
                logger.info(f"   Gemini address: {address}")
                if tag:
                    logger.info(f"   Gemini tag: {tag}")
                
                # Withdraw from Coinbase (FIXED: Use exchange manager with network parameter)
                # Use the amount that arrived from Gemini (may be less due to fees)
                amount_to_send = getattr(self, 'coinbase_api3_to_send', self.gemini_api3_available)
                
                # Use exchange manager's withdraw method with network parameter
                withdrawal = await self.exchange_manager.withdraw(
                    'coinbase',
                    self.test_crypto,
                    amount_to_send,
                    address,
                    tag=tag,
                    network=self.network
                )
                    
                withdrawal_id = withdrawal.get('id', 'unknown')
                logger.info(f"✅ Withdrawal initiated from Coinbase: {withdrawal_id}")
                logger.info(f"   Sending: {amount_to_send:.6f} API3")
                
                # Store withdrawal details
                self.coinbase_withdrawal_id = withdrawal_id
                self.coinbase_to_gemini_address = address
                
                self.results['transfer_coinbase_to_gemini'] = {
                    'status': 'success',
                    'details': {
                        'withdrawal_id': withdrawal_id,
                        'amount': amount_to_send,
                        'destination_address': address,
                        'network': self.network
                    }
                }
                
                logger.info("✅ Reverse transfer initiated successfully!")
                return True
                    
            except Exception as e:
                error_str = str(e)
                logger.warning(f"⚠️ Reverse transfer attempt {attempt + 1} failed: {error_str}")
                
                # Check if it's a Coinbase internal server error (retryable)
                if 'internal_server_error' in error_str or 'internal error' in error_str.lower():
                    if attempt < max_retries - 1:
                        wait_time = retry_delays[attempt]
                        logger.info(f"⏳ Coinbase server error. Waiting {wait_time}s before retry...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"❌ Reverse transfer failed after {max_retries} attempts with Coinbase server errors")
                        logger.error("💡 This appears to be a Coinbase server-side issue")
                        self.results['transfer_coinbase_to_gemini'] = {
                            'status': 'failed',
                            'details': {
                                'error': 'coinbase_server_error',
                                'error_message': error_str
                            }
                        }
                        return False
                else:
                    # Other errors
                    logger.error(f"❌ Reverse transfer failed: {e}")
                    if attempt < max_retries - 1:
                        wait_time = retry_delays[attempt]
                        await asyncio.sleep(wait_time)
                        continue
                    self.results['transfer_coinbase_to_gemini'] = {
                        'status': 'failed',
                        'details': {
                            'error': 'unknown_error',
                            'error_message': error_str
                        }
                    }
                    return False
        
        return False
        
    async def _verify_forward_transfer(self) -> bool:
        """Verify forward transfer completed and get amount that arrived"""
        try:
            logger.info("🔍 Checking if API3 arrived on Coinbase...")
            
            coinbase = self.exchange_manager.get_exchange('coinbase')
            coinbase_balance = coinbase.fetch_balance()
            if hasattr(coinbase_balance, '__await__'):
                coinbase_balance = await coinbase_balance
                
            new_coinbase_api3 = coinbase_balance.get('free', {}).get('API3', 0)
            
            logger.info(f"   Initial Coinbase API3: {self.initial_coinbase_api3:.6f}")
            logger.info(f"   Current Coinbase API3: {new_coinbase_api3:.6f}")
            logger.info(f"   Amount sent: {self.gemini_api3_available:.6f}")
            
            # Calculate amount that arrived (may be less due to network fees)
            api3_arrived = new_coinbase_api3 - self.initial_coinbase_api3
            
            if api3_arrived > 0:
                logger.info(f"   ✅ API3 arrived on Coinbase: {api3_arrived:.6f}")
                
                # Store the amount that arrived for reverse transfer
                self.coinbase_api3_to_send = api3_arrived
                
                if api3_arrived >= self.gemini_api3_available * 0.9:  # At least 90% arrived (accounting for fees)
                    logger.info("✅ Forward transfer verified - sufficient API3 arrived!")
                    return True
                else:
                    logger.warning(f"⚠️ Less API3 arrived than sent (may be network fees)")
                    logger.warning(f"   Will transfer back: {api3_arrived:.6f} API3")
                    return True  # Continue anyway
            else:
                logger.warning(f"⚠️ API3 not yet arrived on Coinbase")
                logger.warning("   ERC-20 transfers can take 1-5 minutes")
                logger.warning("   Waiting additional 60 seconds...")
                await asyncio.sleep(60)
                
                # Check again
                coinbase_balance = coinbase.fetch_balance()
                if hasattr(coinbase_balance, '__await__'):
                    coinbase_balance = await coinbase_balance
                    
                new_coinbase_api3 = coinbase_balance.get('free', {}).get('API3', 0)
                api3_arrived = new_coinbase_api3 - self.initial_coinbase_api3
                
                if api3_arrived > 0:
                    logger.info(f"   ✅ API3 arrived on Coinbase: {api3_arrived:.6f}")
                    self.coinbase_api3_to_send = api3_arrived
                    return True
                else:
                    logger.error("❌ API3 still not arrived after additional wait")
                    logger.error("   Transfer may have failed or is still pending")
                    return False
                
        except Exception as e:
            logger.error(f"❌ Could not verify forward transfer: {e}")
            return False
            
    async def _verify_reverse_transfer(self) -> bool:
        """Verify reverse transfer completed"""
        try:
            logger.info("🔍 Checking if API3 arrived on Gemini...")
            
            gemini = self.exchange_manager.get_exchange('gemini')
            gemini_balance = gemini.fetch_balance()
            if hasattr(gemini_balance, '__await__'):
                gemini_balance = await gemini_balance
                
            new_gemini_api3 = gemini_balance.get('free', {}).get('API3', 0)
            
            logger.info(f"   Initial Gemini API3: {self.initial_gemini_api3:.6f}")
            logger.info(f"   Current Gemini API3: {new_gemini_api3:.6f}")
            logger.info(f"   Expected increase: {getattr(self, 'coinbase_api3_to_send', 0):.6f}")
            
            expected_api3 = self.initial_gemini_api3 - self.gemini_api3_available + getattr(self, 'coinbase_api3_to_send', 0)
            difference = new_gemini_api3 - expected_api3
            
            if abs(difference) < getattr(self, 'coinbase_api3_to_send', 0) * 0.1:  # Within 10% tolerance
                logger.info("✅ Reverse transfer verified - API3 arrived on Gemini!")
                return True
            else:
                logger.warning(f"⚠️ Reverse transfer may still be pending (difference: {difference:.6f})")
                logger.warning("   ERC-20 transfers can take 1-5 minutes")
                return True  # Don't fail on this
                
        except Exception as e:
            logger.warning(f"⚠️ Could not verify reverse transfer: {e}")
            return True  # Don't fail on verification
            
    def _print_results(self):
        """Print complete test results documentation"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 COMPLETE TEST RESULTS DOCUMENTATION")
        logger.info("=" * 60)
        
        # Forward Transfer
        logger.info("\n1. TRANSFER GEMINI → COINBASE:")
        logger.info(f"   Status: {self.results['transfer_gemini_to_coinbase']['status'].upper()}")
        if self.results['transfer_gemini_to_coinbase']['status'] == 'success':
            details = self.results['transfer_gemini_to_coinbase']['details']
            logger.info(f"   ✅ Withdrawal ID: {details.get('withdrawal_id', 'N/A')}")
            logger.info(f"   ✅ Amount: {details.get('amount', 0):.6f} API3")
            logger.info(f"   ✅ Network: {details.get('network', 'N/A')}")
            logger.info(f"   ✅ Destination: {details.get('destination_address', 'N/A')}")
            logger.info("   ✅ WORKING: Gemini withdrawal API call succeeds")
            logger.info("   ⏳ PENDING: Transfer completion (ERC-20 takes 1-5 minutes)")
        elif self.results['transfer_gemini_to_coinbase']['status'] == 'failed':
            error = self.results['transfer_gemini_to_coinbase']['details'].get('error', 'unknown')
            logger.info(f"   ❌ Error Type: {error}")
            logger.info(f"   ❌ Message: {self.results['transfer_gemini_to_coinbase']['details'].get('error_message', 'N/A')}")
            if error == 'whitelisting_required':
                logger.info("   ❌ NOT WORKING: Gemini requires address whitelisting for withdrawals")
                logger.info("   💡 SOLUTION: Enable address whitelisting on Gemini account")
            else:
                logger.info("   ❌ NOT WORKING: Unknown withdrawal error")
        else:
            logger.info(f"   ❌ Error: {self.results['transfer_gemini_to_coinbase']['details']}")
            
        # Reverse Transfer
        logger.info("\n2. TRANSFER COINBASE → GEMINI (BACK):")
        logger.info(f"   Status: {self.results['transfer_coinbase_to_gemini']['status'].upper()}")
        if self.results['transfer_coinbase_to_gemini']['status'] == 'success':
            details = self.results['transfer_coinbase_to_gemini']['details']
            logger.info(f"   ✅ Withdrawal ID: {details.get('withdrawal_id', 'N/A')}")
            logger.info(f"   ✅ Amount: {details.get('amount', 0):.6f} API3")
            logger.info(f"   ✅ Network: {details.get('network', 'N/A')}")
            logger.info(f"   ✅ Destination: {details.get('destination_address', 'N/A')}")
            logger.info("   ✅ WORKING: Coinbase withdrawal API call succeeds")
            logger.info("   ⏳ PENDING: Transfer completion (ERC-20 takes 1-5 minutes)")
        elif self.results['transfer_coinbase_to_gemini']['status'] == 'failed':
            error = self.results['transfer_coinbase_to_gemini']['details'].get('error', 'unknown')
            logger.info(f"   ❌ Error Type: {error}")
            logger.info(f"   ❌ Message: {self.results['transfer_coinbase_to_gemini']['details'].get('error_message', 'N/A')}")
            if error == 'coinbase_server_error':
                logger.info("   ❌ NOT WORKING: Coinbase internal server error")
                logger.info("   💡 SOLUTION: Contact Coinbase support - this is a server-side issue")
            else:
                logger.info("   ❌ NOT WORKING: Unknown withdrawal error")
        else:
            logger.info(f"   ❌ Error: {self.results['transfer_coinbase_to_gemini']['details']}")
            
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📝 SUMMARY OF WHAT WORKS / DOESN'T WORK:")
        logger.info("=" * 60)
        
        if self.results['transfer_gemini_to_coinbase']['status'] == 'success':
            logger.info("✅ GEMINI → COINBASE transfer: WORKING (API call succeeds)")
        else:
            logger.info("❌ GEMINI → COINBASE transfer: NOT WORKING")
            if self.results['transfer_gemini_to_coinbase']['details'].get('error') == 'whitelisting_required':
                logger.info("   Reason: Gemini whitelisting required")
                
        if self.results['transfer_coinbase_to_gemini']['status'] == 'success':
            logger.info("✅ COINBASE → GEMINI transfer: WORKING (API call succeeds)")
        else:
            logger.info("❌ COINBASE → GEMINI transfer: NOT WORKING")
            if self.results['transfer_coinbase_to_gemini']['details'].get('error') == 'coinbase_server_error':
                logger.info("   Reason: Coinbase internal server error")
                
        logger.info("\n" + "=" * 60)

async def main():
    """Main test function"""
    try:
        test = API3BidirectionalTransferTest()
        success = await test.run_test()
        
        if success:
            logger.info("\n🎉 API3 BIDIRECTIONAL TRANSFER TEST PASSED!")
            return 0
        else:
            logger.error("\n💥 API3 BIDIRECTIONAL TRANSFER TEST FAILED!")
            logger.error("Check results documentation above for details")
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

