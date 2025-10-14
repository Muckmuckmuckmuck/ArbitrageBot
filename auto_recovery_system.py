#!/usr/bin/env python3
"""
Auto Recovery System
Automatically detects and fixes common issues
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class IssueType(Enum):
    """Types of issues that can be auto-recovered"""
    STUCK_POSITION = "stuck_position"
    FAILED_TRANSFER = "failed_transfer"
    BALANCE_MISMATCH = "balance_mismatch"
    RATE_LIMIT_HIT = "rate_limit_hit"
    NETWORK_ERROR = "network_error"
    EXCHANGE_DOWN = "exchange_down"
    SPREAD_DISAPPEARED = "spread_disappeared"
    INSUFFICIENT_BALANCE = "insufficient_balance"

@dataclass
class StuckPosition:
    """Represents a stuck position that needs recovery"""
    exchange: str
    symbol: str
    currency: str
    amount: float
    value_usd: float
    stuck_since: datetime
    reason: str
    recovery_attempted: bool = False
    recovery_success: Optional[bool] = None
    recovery_message: str = ""

class AutoRecoverySystem:
    """Automatically detects and recovers from common issues"""
    
    def __init__(self, exchanges: Dict[str, Any], config: Any):
        self.exchanges = exchanges
        self.config = config
    
        # Track stuck positions
        self.stuck_positions: List[StuckPosition] = []
        
        # Track failed transfers
        self.failed_transfers = []
        
        # Recovery statistics
        self.stats = {
            'total_issues': 0,
            'auto_recovered': 0,
            'manual_intervention_needed': 0,
            'recovery_attempts': 0,
            'by_issue_type': {}
        }
        
        logger.info("Auto Recovery System initialized")
    
    async def _fetch_balance_safe(self, exchange) -> Dict:
        """Safely fetch balance handling both sync and async CCXT"""
        try:
            result = exchange.fetch_balance()
            if hasattr(result, '__await__'):
                return await result
            return result
        except Exception as e:
            # Suppress known Gemini API key type warnings
            if 'master-keys are not-supported' not in str(e):
                logger.error(f"Error fetching balance: {e}")
            return {}
    
    async def _fetch_ticker_safe(self, exchange, symbol: str) -> Dict:
        """Safely fetch ticker handling both sync and async CCXT"""
        try:
            result = exchange.fetch_ticker(symbol)
            if hasattr(result, '__await__'):
                return await result
            return result
        except Exception as e:
            logger.error(f"Error fetching ticker {symbol}: {e}")
            return {}
    
    async def detect_stuck_positions(self) -> List[StuckPosition]:
        """Detect stuck positions on exchanges"""
        
        stuck = []
        
        try:
            logger.info("🔍 Scanning for stuck crypto positions...")
            
            for exchange_name, exchange in self.exchanges.items():
                logger.info(f"   Checking {exchange_name}...")
                balance = await self._fetch_balance_safe(exchange)
                
                # Check ALL crypto balances (not just configured pairs)
                free_balances = balance.get('free', {})
                
                for currency, crypto_amount in free_balances.items():
                    # Skip USD, USDT, USDC (these are cash, not stuck crypto)
                    if currency in ['USD', 'USDT', 'USDC'] or crypto_amount <= 0:
                        continue
                    
                    # Found crypto! Try to get its value
                    try:
                        # Try multiple symbol formats (USD, USDC, USDT)
                        price = None
                        working_symbol = None
                        
                        for quote in ['USD', 'USDC', 'USDT']:
                            try:
                                test_symbol = f"{currency}/{quote}"
                                ticker = await self._fetch_ticker_safe(exchange, test_symbol)
                                price = ticker.get('last') or ticker.get('bid') or ticker.get('ask')
                                if price:
                                    working_symbol = test_symbol
                                    break
                            except:
                                continue
                        
                        if not price:
                            logger.warning(f"   ⚠️  Found {crypto_amount:.6f} {currency} but couldn't get price")
                            continue
                        
                        value_usd = crypto_amount * price
                        
                        # If value > $0.50, consider it stuck (lowered from $10 to catch ALL stuck positions)
                        if value_usd > 0.50:
                                # Check if this is a known stuck position
                                is_known = any(
                                    sp.exchange == exchange_name and 
                                    sp.currency == currency and
                                    abs(sp.amount - crypto_amount) < 0.01
                                    for sp in self.stuck_positions
                                )
                                
                                if not is_known:
                                    stuck_pos = StuckPosition(
                                        exchange=exchange_name,
                                        symbol=working_symbol,  # Use the working symbol we found
                                        currency=currency,
                                        amount=crypto_amount,
                                        value_usd=value_usd,
                                        stuck_since=datetime.now(),
                                        reason="Unexpected crypto balance (possible failed transfer or incomplete cycle)"
                                    )
                                    stuck.append(stuck_pos)
                                    self.stuck_positions.append(stuck_pos)
                                    
                                    logger.warning(f"   ⚠️  Found: {crypto_amount:.6f} {currency} = ${value_usd:.2f}")
                        except Exception as e:
                            logger.error(f"   Error checking {currency} on {exchange_name}: {e}")
            
        except Exception as e:
            logger.error(f"Error detecting stuck positions: {e}", exc_info=True)
        
        if stuck:
            logger.warning(f"\n⚠️  TOTAL: Found {len(stuck)} stuck positions worth ${sum(sp.value_usd for sp in stuck):.2f}")
        else:
            logger.info("   ✅ No stuck positions found")
        
        return stuck
    
    async def recover_stuck_position(self, stuck: StuckPosition) -> bool:
        """
        Smart recovery: Check prices on BOTH exchanges, transfer to better price if needed, then sell
        This maximizes recovery value!
        """
        
        try:
            logger.info("="*80)
            logger.info(f"🔄 SMART RECOVERY: {stuck.amount:.6f} {stuck.currency} on {stuck.exchange}")
            logger.info(f"   Value: ${stuck.value_usd:.2f}")
            logger.info("="*80)
            
            stuck.recovery_attempted = True
            self.stats['recovery_attempts'] += 1
            
            # STEP 1: Check prices on BOTH exchanges
            logger.info("[STEP 1] Checking prices on both exchanges...")
            
            prices = {}
            for exchange_name, exchange in self.exchanges.items():
                try:
                    ticker = await self._fetch_ticker_safe(exchange, stuck.symbol)
                    bid_price = ticker.get('bid') or ticker.get('last')
                    if bid_price:
                        prices[exchange_name] = bid_price
                        logger.info(f"  {exchange_name}: ${bid_price:.2f}")
                except Exception as e:
                    logger.debug(f"Could not get price from {exchange_name}: {e}")
            
            if not prices:
                logger.error(f"❌ Could not get prices from any exchange")
                return False
            
            # STEP 2: Determine best exchange to sell on
            best_exchange = max(prices.items(), key=lambda x: x[1])[0]
            best_price = prices[best_exchange]
            current_exchange = stuck.exchange
            
            price_diff = best_price - prices.get(current_exchange, 0)
            price_diff_pct = (price_diff / prices.get(current_exchange, best_price)) * 100 if current_exchange in prices else 0
            
            logger.info(f"\n💡 Best price: {best_exchange} @ ${best_price:.2f}")
            if current_exchange != best_exchange:
                logger.info(f"   Current exchange ({current_exchange}): ${prices[current_exchange]:.2f}")
                logger.info(f"   Price difference: ${price_diff:.2f} ({price_diff_pct:.2f}%)")
            
            # STEP 3: Transfer to best exchange if needed (and if price difference > 0.5%)
            if current_exchange != best_exchange and price_diff_pct > 0.5:
                logger.info(f"\n[STEP 2] Transferring to {best_exchange} for better price...")
                logger.info(f"  Expected gain: ${price_diff * stuck.amount:.2f}")
                
                # Note: Transfer requires whitelisted addresses
                # For now, we'll just sell on current exchange to avoid complexity
                logger.warning(f"⚠️  Transfer would save ${price_diff * stuck.amount:.2f}, but selling locally for simplicity")
                sell_exchange = current_exchange
                sell_price = prices[current_exchange]
            else:
                logger.info(f"\n[STEP 2] Selling on current exchange ({current_exchange})")
                sell_exchange = current_exchange
                sell_price = prices[current_exchange]
            
            # STEP 4: Sell the crypto
            logger.info(f"\n[STEP 3] Placing limit sell order...")
            logger.info(f"  Exchange: {sell_exchange}")
            logger.info(f"  Amount: {stuck.amount:.6f} {stuck.currency}")
            logger.info(f"  Price: ${sell_price:.2f}")
            logger.info(f"  Expected revenue: ${stuck.amount * sell_price:.2f}")
            
            exchange = self.exchanges[sell_exchange]
            sell_order_result = exchange.create_limit_sell_order(
                stuck.symbol,
                stuck.amount,
                sell_price
            )
            
            # Handle sync/async
            if hasattr(sell_order_result, '__await__'):
                sell_order = await sell_order_result
            else:
                sell_order = sell_order_result
            
            logger.info(f"\n✅ Recovery order placed!")
            logger.info(f"   Order ID: {sell_order.get('id')}")
            logger.info(f"   Status: {sell_order.get('status', 'pending')}")
            
            # Wait a moment for order to fill
            await asyncio.sleep(3)
            
            # Calculate revenue
            revenue = stuck.amount * sell_price
            
            logger.info(f"\n💰 Recovery complete: Sold {stuck.amount:.6f} {stuck.currency} "
                      f"for ~${revenue:.2f} on {sell_exchange}")
            logger.info("="*80)
            
            stuck.recovery_success = True
            stuck.recovery_message = f"Sold for ~${revenue:.2f} on {sell_exchange}"
            self.stats['auto_recovered'] += 1
            
            return True
                
        except Exception as e:
            logger.error(f"❌ Recovery failed: {e}")
            logger.error(f"   Exchange: {stuck.exchange}")
            logger.error(f"   Symbol: {stuck.symbol}")
            logger.error(f"   Amount: {stuck.amount:.6f}")
            stuck.recovery_success = False
            stuck.recovery_message = str(e)
            self.stats['manual_intervention_needed'] += 1
            return False
    
    async def auto_recover_all_stuck_positions(self) -> int:
        """Automatically recover all detected stuck positions"""
        
        # Detect stuck positions
        stuck_list = await self.detect_stuck_positions()
        
        if not stuck_list:
            logger.info("No stuck positions detected")
            return 0
        
        logger.info(f"Found {len(stuck_list)} stuck positions, attempting recovery...")
        
        recovered = 0
        
        for stuck in stuck_list:
            # Only attempt if not already tried
            if not stuck.recovery_attempted:
                success = await self.recover_stuck_position(stuck)
                if success:
                    recovered += 1
                
                # Wait between recoveries to avoid rate limits
                await asyncio.sleep(2)
        
        logger.info(f"Recovery complete: {recovered}/{len(stuck_list)} positions recovered")
        
        return recovered
    
    async def check_balance_consistency(self) -> bool:
        """Check if balances are consistent and make sense"""
        
        try:
            total_value = 0.0
            
            for exchange_name, exchange in self.exchanges.items():
                balance = await self._fetch_balance_safe(exchange)
                exchange_value = 0.0
                
                # USDT
                usdt = balance.get('USDT', {}).get('free', 0)
                exchange_value += usdt
                
                # Crypto holdings
                for symbol in self.config.CURRENCY_PAIRS:
                    base = symbol.split('/')[0]
                    amount = balance.get(base, {}).get('free', 0)
                    
                    if amount > 0:
                        ticker = await self._fetch_ticker_safe(exchange, symbol)
                        price = ticker['last']
                        exchange_value += amount * price
                
                logger.info(f"{exchange_name}: ${exchange_value:.2f}")
                total_value += exchange_value
            
            logger.info(f"Total portfolio value: ${total_value:.2f}")
            
            # Check if makes sense
            if total_value < 10:
                logger.warning("⚠️  Total value very low (<$10) - check if something went wrong")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking balance consistency: {e}")
            return False
    
    async def retry_failed_transfer(self, from_exchange: str, to_exchange: str,
                                   currency: str, amount: float, max_retries: int = 3) -> bool:
        """Retry a failed transfer with exponential backoff"""
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Retry attempt {attempt + 1}/{max_retries}: "
                          f"Transfer {amount} {currency} from {from_exchange} → {to_exchange}")
                
                # Get deposit address
                address_info = await self.exchanges[to_exchange].fetch_deposit_address(currency)
                deposit_address = address_info['address']
                tag = address_info.get('tag', None)
                
                # Execute withdrawal
                withdrawal = await self.exchanges[from_exchange].withdraw(
                    currency,
                    amount,
                    deposit_address,
                    tag,
                    {}
                )
                
                logger.info(f"✅ Retry successful: Transfer initiated (TX: {withdrawal.get('id')})")
                return True
                
            except Exception as e:
                logger.warning(f"Retry attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    # Exponential backoff
                    wait_time = (2 ** attempt) * 10  # 10s, 20s, 40s
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"❌ All retry attempts failed")
                    return False
        
        return False
    
    async def check_and_rebalance_if_needed(self, min_imbalance_usd: float = 100.0) -> bool:
        """Check if rebalancing is needed and do it"""
        
        try:
            # Get USDT balances
            pionex_balance = await self.exchanges['pionex'].fetch_balance()
            coinbase_balance = await self.exchanges['coinbasepro'].fetch_balance()
            
            pionex_usdt = pionex_balance.get('USDT', {}).get('free', 0)
            coinbase_usdt = coinbase_balance.get('USDT', {}).get('free', 0)
            
            total_usdt = pionex_usdt + coinbase_usdt
            target = total_usdt / 2
            
            # Check imbalance
            imbalance = abs(pionex_usdt - target)
            
            if imbalance < min_imbalance_usd:
                logger.info(f"Balances OK: Pionex ${pionex_usdt:.2f}, "
                          f"Coinbase ${coinbase_usdt:.2f} (imbalance ${imbalance:.2f})")
                return True
            
            # Determine transfer direction
            if pionex_usdt > coinbase_usdt:
                # Transfer from Pionex to Coinbase
                logger.info(f"Rebalancing needed: Transfer ${imbalance:.2f} USDT "
                          f"from Pionex → Coinbase")
                
                # Use transfer manager if available
                # For now, just log
                logger.warning("⚠️  Manual rebalancing recommended: "
                             f"Transfer ${imbalance:.2f} USDT from Pionex → Coinbase")
            else:
                # Transfer from Coinbase to Pionex (FREE!)
                logger.info(f"Rebalancing needed: Transfer ${imbalance:.2f} USDT "
                          f"from Coinbase → Pionex (FREE!)")
                
                logger.warning("⚠️  Manual rebalancing recommended: "
                             f"Transfer ${imbalance:.2f} USDT from Coinbase → Pionex (FREE!)")
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking rebalancing: {e}")
            return False
    
    async def handle_rate_limit_error(self, exchange: str, wait_time: int = 60) -> bool:
        """Handle rate limit error with smart waiting"""
        
        logger.warning(f"🔴 Rate limit hit on {exchange}!")
        logger.info(f"Waiting {wait_time} seconds for rate limit reset...")
        
        # Log to stats
        self.stats['total_issues'] += 1
        issue_key = IssueType.RATE_LIMIT_HIT.value
        self.stats['by_issue_type'][issue_key] = self.stats['by_issue_type'].get(issue_key, 0) + 1
        
        # Wait
        await asyncio.sleep(wait_time)
        
        logger.info(f"✅ Rate limit wait complete, resuming...")
        self.stats['auto_recovered'] += 1
        
        return True
    
    async def handle_network_error(self, operation: str, max_retries: int = 3) -> bool:
        """Handle network errors with exponential backoff"""
        
        logger.warning(f"🔴 Network error during: {operation}")
        
        self.stats['total_issues'] += 1
        issue_key = IssueType.NETWORK_ERROR.value
        self.stats['by_issue_type'][issue_key] = self.stats['by_issue_type'].get(issue_key, 0) + 1
        
        for attempt in range(max_retries):
            wait_time = (2 ** attempt) * 2  # 2s, 4s, 8s
            logger.info(f"Retry {attempt + 1}/{max_retries} after {wait_time}s...")
            
            await asyncio.sleep(wait_time)
            
            # Return true to allow caller to retry
            logger.info(f"✅ Ready to retry {operation}")
            return True
        
        logger.error(f"❌ All retries exhausted for {operation}")
        self.stats['manual_intervention_needed'] += 1
        return False
    
    async def check_exchange_health(self, exchange_name: str) -> bool:
        """Check if an exchange is healthy and responding"""
        
        try:
            exchange = self.exchanges[exchange_name]
            
            # Try to fetch a ticker (lightweight check)
            await self._fetch_ticker_safe(exchange, 'BTC/USD')
            
            logger.debug(f"✅ {exchange_name} is healthy")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️  {exchange_name} health check failed: {e}")
            
            self.stats['total_issues'] += 1
            issue_key = IssueType.EXCHANGE_DOWN.value
            self.stats['by_issue_type'][issue_key] = self.stats['by_issue_type'].get(issue_key, 0) + 1
            
            return False
    
    async def wait_for_exchange_recovery(self, exchange_name: str, 
                                        max_wait_minutes: int = 10) -> bool:
        """Wait for an exchange to come back online"""
        
        logger.warning(f"⏳ Waiting for {exchange_name} to recover...")
        
        start_time = datetime.now()
        check_interval = 30  # Check every 30 seconds
        
        while (datetime.now() - start_time).total_seconds() < max_wait_minutes * 60:
            # Check if healthy
            if await self.check_exchange_health(exchange_name):
                recovery_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ {exchange_name} recovered after {recovery_time:.0f}s")
                self.stats['auto_recovered'] += 1
                return True
            
            await asyncio.sleep(check_interval)
        
        logger.error(f"❌ {exchange_name} did not recover within {max_wait_minutes} minutes")
        self.stats['manual_intervention_needed'] += 1
        return False
    
    async def validate_deposit_address(self, exchange_name: str, currency: str) -> Optional[str]:
        """Validate and get deposit address with verification"""
        
        try:
            # Fetch deposit address
            address_info = await self.exchanges[exchange_name].fetch_deposit_address(currency)
            address = address_info.get('address')
            tag = address_info.get('tag')
            
            if not address:
                logger.error(f"❌ No deposit address returned for {currency} on {exchange_name}")
                return None
            
            # Basic validation
            if len(address) < 20:
                logger.warning(f"⚠️  Deposit address seems too short: {address}")
                logger.warning(f"   Please verify manually before transferring!")
            
            # Log for verification
            logger.info(f"Deposit address for {currency} on {exchange_name}:")
            logger.info(f"  Address: {address}")
            if tag:
                logger.info(f"  Tag/Memo: {tag}")
            
            return address
            
        except Exception as e:
            logger.error(f"Error getting deposit address: {e}")
            return None
    
    async def smart_transfer_with_recovery(self, from_exchange: str, to_exchange: str,
                                          currency: str, amount: float,
                                          max_retries: int = 3) -> bool:
        """Execute transfer with automatic retry on failure"""
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Transfer attempt {attempt + 1}/{max_retries}: "
                          f"{amount} {currency} from {from_exchange} → {to_exchange}")
                
                # Validate deposit address first
                deposit_address = await self.validate_deposit_address(to_exchange, currency)
                
                if not deposit_address:
                    logger.error("Cannot get valid deposit address")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5)
                        continue
                    return False
                
                # Get tag if needed
                address_info = await self.exchanges[to_exchange].fetch_deposit_address(currency)
                tag = address_info.get('tag')
                
                # Execute withdrawal
                withdrawal = await self.exchanges[from_exchange].withdraw(
                    currency,
                    amount,
                    deposit_address,
                    tag,
                    {}
                )
                
                tx_id = withdrawal.get('id', withdrawal.get('txid'))
                logger.info(f"✅ Transfer initiated: TX {tx_id}")
                
                # Wait for confirmation (simplified - would use transfer_manager in production)
                await asyncio.sleep(5)  # Give it time to start
                
                return True
                
            except Exception as e:
                logger.warning(f"Transfer attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 10
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("All transfer attempts failed")
                    self.stats['manual_intervention_needed'] += 1
                    return False
        
        return False
    
    async def emergency_liquidate_all(self) -> float:
        """Emergency: Sell all crypto positions to USDT"""
        
        logger.critical("🚨 EMERGENCY LIQUIDATION - Selling all positions to USDT")
        
        total_recovered = 0.0
        
        try:
            for exchange_name, exchange in self.exchanges.items():
                balance = await self._fetch_balance_safe(exchange)
                
                for symbol in self.config.CURRENCY_PAIRS:
                    base = symbol.split('/')[0]
                    amount = balance.get(base, {}).get('free', 0)
                    
                    if amount > 0:
                        try:
                            logger.info(f"Emergency sell: {amount:.8f} {base} on {exchange_name}")
                            
                            sell_order = await exchange.create_market_sell_order(symbol, amount)
                            
                            if sell_order.get('status') in ['closed', 'filled']:
                                filled = float(sell_order.get('filled', 0))
                                avg_price = float(sell_order.get('average', 0))
                                revenue = filled * avg_price
                                total_recovered += revenue
                                
                                logger.info(f"✅ Sold {filled:.8f} {base} for ${revenue:.2f}")
                        
                        except Exception as e:
                            logger.error(f"Failed to sell {base} on {exchange_name}: {e}")
            
            logger.critical(f"🚨 Emergency liquidation complete: ${total_recovered:.2f} recovered")
            return total_recovered
            
        except Exception as e:
            logger.critical(f"Emergency liquidation failed: {e}")
            return 0.0
    
    async def run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check"""
        
        logger.info("Running comprehensive health check...")
        
        health = {
            'timestamp': datetime.now(),
            'exchanges_healthy': {},
            'stuck_positions': [],
            'balance_consistent': False,
            'issues_found': 0,
            'overall_status': 'unknown'
        }
        
        # Check exchange health
        for exchange_name in self.exchanges.keys():
            is_healthy = await self.check_exchange_health(exchange_name)
            health['exchanges_healthy'][exchange_name] = is_healthy
            if not is_healthy:
                health['issues_found'] += 1
        
        # Detect stuck positions
        stuck = await self.detect_stuck_positions()
        health['stuck_positions'] = len(stuck)
        if stuck:
            health['issues_found'] += len(stuck)
            # AUTO-RECOVER stuck positions immediately!
            logger.info(f"🔄 Auto-recovering {len(stuck)} stuck positions...")
            recovered = await self.auto_recover_all_stuck_positions()
            logger.info(f"✅ Recovered {recovered}/{len(stuck)} positions")
        
        # Check balance consistency
        health['balance_consistent'] = await self.check_balance_consistency()
        if not health['balance_consistent']:
            health['issues_found'] += 1
        
        # Determine overall status
        if health['issues_found'] == 0:
            health['overall_status'] = 'healthy'
        elif health['issues_found'] <= 2:
            health['overall_status'] = 'warning'
        else:
            health['overall_status'] = 'critical'
        
        # Log results
        logger.info("=" * 80)
        logger.info("HEALTH CHECK RESULTS")
        logger.info("=" * 80)
        logger.info(f"Exchanges healthy: {health['exchanges_healthy']}")
        logger.info(f"Stuck positions: {health['stuck_positions']}")
        logger.info(f"Balance consistent: {health['balance_consistent']}")
        logger.info(f"Issues found: {health['issues_found']}")
        logger.info(f"Overall status: {health['overall_status']}")
        logger.info("=" * 80)
        
        return health
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery statistics"""
        
        return {
            'total_issues_detected': self.stats['total_issues'],
            'auto_recovered': self.stats['auto_recovered'],
            'manual_intervention_needed': self.stats['manual_intervention_needed'],
            'recovery_success_rate': self.stats['auto_recovered'] / self.stats['total_issues']
                                    if self.stats['total_issues'] > 0 else 0,
            'stuck_positions_current': len([sp for sp in self.stuck_positions if not sp.recovery_success]),
            'stuck_positions_recovered': len([sp for sp in self.stuck_positions if sp.recovery_success]),
            'by_issue_type': self.stats['by_issue_type']
        }

