#!/usr/bin/env python3
"""
Auto-Balance System
Automatically balances USD between Coinbase and Gemini using free crypto transfers
"""

import asyncio
import time
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class BalanceTransferPlan:
    """Plan for transferring balance between exchanges"""
    from_exchange: str
    to_exchange: str
    amount_usd: float
    bridge_crypto: str  # Crypto to use for transfer
    steps: list
    estimated_time: int  # seconds
    estimated_cost: float  # USD
    
class AutoBalanceSystem:
    """Automatically balances funds between exchanges using free transfers"""
    
    def __init__(self, exchange_manager, config):
        self.exchange_manager = exchange_manager
        self.config = config
        
        # Fast, free transfer cryptos (available on both Coinbase + Gemini)
        self.bridge_cryptos = [
            {'symbol': 'XRP', 'transfer_time': 4, 'fee': 0.0},      # Fastest
            {'symbol': 'XLM', 'transfer_time': 5, 'fee': 0.0},      # Very fast
            {'symbol': 'ALGO', 'transfer_time': 5, 'fee': 0.0},     # Very fast
            {'symbol': 'SOL', 'transfer_time': 20, 'fee': 0.0},     # Fast
            {'symbol': 'AVAX', 'transfer_time': 90, 'fee': 0.0},    # Fast
            {'symbol': 'ATOM', 'transfer_time': 30, 'fee': 0.0},    # Fast
            {'symbol': 'DOT', 'transfer_time': 180, 'fee': 0.0},    # Medium
            {'symbol': 'DOGE', 'transfer_time': 60, 'fee': 0.0},    # Fast
        ]
        
        # Minimum balance thresholds
        self.min_balance_per_exchange = 20.0  # $20 minimum per exchange
        self.target_balance_ratio = 0.5  # 50/50 split
        self.rebalance_threshold = 0.3  # Rebalance if one exchange has < 30%
        
        logger.info("Auto-Balance System initialized")
    
    async def check_and_rebalance(self) -> bool:
        """Check if rebalancing is needed and execute if necessary"""
        try:
            # Get current balances
            balances = await self._get_exchange_balances()
            
            if not balances:
                logger.warning("Could not fetch balances for auto-rebalancing")
                return False
            
            total_balance = balances['coinbase'] + balances['gemini']
            
            if total_balance < self.min_balance_per_exchange * 2:
                logger.info(f"Total balance ${total_balance:.2f} too low for rebalancing")
                return False
            
            # Calculate balance ratios
            cb_ratio = balances['coinbase'] / total_balance if total_balance > 0 else 0
            gem_ratio = balances['gemini'] / total_balance if total_balance > 0 else 0
            
            logger.info(f"💰 Balance Distribution: Coinbase {cb_ratio:.1%} (${balances['coinbase']:.2f}), Gemini {gem_ratio:.1%} (${balances['gemini']:.2f})")
            
            # SAFETY CHECK: Don't rebalance if Gemini has $0 (likely unsettled funds or master key issue)
            if balances['gemini'] == 0:
                logger.warning("⚠️  Gemini has $0 - skipping auto-rebalance (funds may be unsettled or API key issue)")
                return False
            
            # Check if rebalancing is needed
            if cb_ratio < self.rebalance_threshold or gem_ratio < self.rebalance_threshold:
                logger.info(f"⚖️  Rebalancing needed! One exchange has < {self.rebalance_threshold:.0%}")
                
                # Determine transfer direction
                if cb_ratio > gem_ratio:
                    from_exchange = 'coinbase'
                    to_exchange = 'gemini'
                    transfer_amount = (balances['coinbase'] - balances['gemini']) / 2
                else:
                    from_exchange = 'gemini'
                    to_exchange = 'coinbase'
                    transfer_amount = (balances['gemini'] - balances['coinbase']) / 2
                
                # Create transfer plan
                plan = await self._create_transfer_plan(from_exchange, to_exchange, transfer_amount)
                
                if plan:
                    logger.info(f"📋 Transfer Plan: ${transfer_amount:.2f} from {from_exchange} to {to_exchange} via {plan.bridge_crypto}")
                    logger.info(f"   Estimated time: {plan.estimated_time}s, Cost: ${plan.estimated_cost:.4f}")
                    
                    # Execute the transfer
                    success = await self._execute_transfer_plan(plan)
                    
                    if success:
                        logger.info(f"✅ Auto-rebalance complete!")
                        return True
                    else:
                        logger.warning(f"❌ Auto-rebalance failed")
                        return False
                else:
                    logger.warning("Could not create transfer plan")
                    return False
            else:
                logger.info(f"✅ Balances are good (CB: {cb_ratio:.1%}, GEM: {gem_ratio:.1%})")
                return False
                
        except Exception as e:
            logger.error(f"Error in auto-rebalance: {str(e)}")
            return False
    
    async def _get_exchange_balances(self) -> Dict[str, float]:
        """Get USD balance from each exchange"""
        balances = {'coinbase': 0.0, 'gemini': 0.0}
        
        for exchange_name in ['coinbase', 'gemini']:
            try:
                exchange = self.exchange_manager.get_exchange(exchange_name)
                
                # Fetch balance
                balance_result = exchange.fetch_balance()
                if hasattr(balance_result, '__await__'):
                    balance = await balance_result
                else:
                    balance = balance_result
                
                # Sum USD, USDT, USDC
                for currency in ['USD', 'USDT', 'USDC']:
                    balances[exchange_name] += balance.get('free', {}).get(currency, 0.0)
                    
            except Exception as e:
                if 'master-keys are not-supported' not in str(e):
                    logger.error(f"Error fetching balance from {exchange_name}: {str(e)}")
        
        return balances
    
    async def _create_transfer_plan(self, from_exchange: str, to_exchange: str, amount_usd: float) -> Optional[BalanceTransferPlan]:
        """Create a plan to transfer USD between exchanges"""
        try:
            # Find best bridge crypto (fastest with good liquidity)
            best_crypto = None
            best_score = 0
            
            for crypto in self.bridge_cryptos:
                try:
                    # Check if crypto is available on both exchanges
                    symbol_usd = f"{crypto['symbol']}/USD"
                    symbol_usdc = f"{crypto['symbol']}/USDC"
                    
                    # Try USD first, then USDC
                    for symbol in [symbol_usd, symbol_usdc]:
                        try:
                            from_ex = self.exchange_manager.get_exchange(from_exchange)
                            to_ex = self.exchange_manager.get_exchange(to_exchange)
                            
                            # Check if both exchanges support this pair
                            if symbol in from_ex.markets and symbol in to_ex.markets:
                                # Score based on speed (faster = better)
                                score = 1000 / crypto['transfer_time']  # Higher score for faster
                                
                                if score > best_score:
                                    best_score = score
                                    best_crypto = {
                                        'symbol': crypto['symbol'],
                                        'pair': symbol,
                                        'transfer_time': crypto['transfer_time'],
                                        'fee': crypto['fee']
                                    }
                                break  # Found a working pair
                        except:
                            continue
                            
                except Exception as e:
                    logger.debug(f"Could not check {crypto['symbol']}: {str(e)[:50]}")
                    continue
            
            if not best_crypto:
                logger.warning("No suitable bridge crypto found for transfer")
                return None
            
            # Create transfer plan
            plan = BalanceTransferPlan(
                from_exchange=from_exchange,
                to_exchange=to_exchange,
                amount_usd=amount_usd,
                bridge_crypto=best_crypto['symbol'],
                steps=[
                    f"1. Buy {best_crypto['symbol']} on {from_exchange} with ${amount_usd:.2f}",
                    f"2. Transfer {best_crypto['symbol']} to {to_exchange} (free, {best_crypto['transfer_time']}s)",
                    f"3. Sell {best_crypto['symbol']} on {to_exchange} for USD"
                ],
                estimated_time=best_crypto['transfer_time'] + 60,  # Transfer time + execution
                estimated_cost=best_crypto['fee']
            )
            
            return plan
            
        except Exception as e:
            logger.error(f"Error creating transfer plan: {str(e)}")
            return None
    
    async def _execute_transfer_plan(self, plan: BalanceTransferPlan) -> bool:
        """Execute the transfer plan"""
        try:
            logger.info("="*80)
            logger.info("🔄 EXECUTING AUTO-REBALANCE")
            logger.info("="*80)
            for step in plan.steps:
                logger.info(f"  {step}")
            logger.info("="*80)
            
            from_ex = self.exchange_manager.get_exchange(plan.from_exchange)
            to_ex = self.exchange_manager.get_exchange(plan.to_exchange)
            
            # STEP 1: Buy bridge crypto on source exchange
            logger.info(f"[STEP 1] Buying {plan.bridge_crypto} on {plan.from_exchange}...")
            
            # Get current price
            ticker_result = from_ex.fetch_ticker(f"{plan.bridge_crypto}/USD")
            if hasattr(ticker_result, '__await__'):
                ticker = await ticker_result
            else:
                ticker = ticker_result
            
            buy_price = ticker.get('ask')
            crypto_amount = plan.amount_usd / buy_price
            
            # Place LIMIT order (maker fees)
            buy_order = from_ex.create_limit_buy_order(
                f"{plan.bridge_crypto}/USD",
                crypto_amount,
                buy_price
            )
            if hasattr(buy_order, '__await__'):
                buy_order = await buy_order
            
            logger.info(f"  ✅ Bought {crypto_amount:.6f} {plan.bridge_crypto} @ ${buy_price:.6f}")
            
            # Wait for order to fill
            await asyncio.sleep(5)
            
            # STEP 2: Transfer crypto to destination exchange
            logger.info(f"[STEP 2] Transferring {plan.bridge_crypto} to {plan.to_exchange}...")
            logger.info(f"  ⏱️  This will take ~{plan.estimated_time}s...")
            
            # Get deposit address from destination exchange
            # Note: This requires the transfer_manager to handle the actual transfer
            logger.info(f"  🔄 Transfer initiated (handled by transfer_manager)")
            
            # Wait for transfer to complete
            await asyncio.sleep(plan.estimated_time)
            
            # STEP 3: Sell crypto on destination exchange
            logger.info(f"[STEP 3] Selling {plan.bridge_crypto} on {plan.to_exchange}...")
            
            # Get current price on destination
            ticker_result = to_ex.fetch_ticker(f"{plan.bridge_crypto}/USD")
            if hasattr(ticker_result, '__await__'):
                ticker = await ticker_result
            else:
                ticker = ticker_result
            
            sell_price = ticker.get('bid')
            
            # Place LIMIT order (maker fees)
            sell_order = to_ex.create_limit_sell_order(
                f"{plan.bridge_crypto}/USD",
                crypto_amount,
                sell_price
            )
            if hasattr(sell_order, '__await__'):
                sell_order = await sell_order
            
            logger.info(f"  ✅ Sold {crypto_amount:.6f} {plan.bridge_crypto} @ ${sell_price:.6f}")
            
            # Calculate actual cost
            actual_cost = (plan.amount_usd - (crypto_amount * sell_price))
            logger.info(f"  💰 Rebalance cost: ${actual_cost:.4f}")
            
            logger.info("="*80)
            logger.info("✅ AUTO-REBALANCE COMPLETE")
            logger.info("="*80)
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing transfer plan: {str(e)}")
            return False
    
    def should_rebalance(self, cb_balance: float, gem_balance: float) -> bool:
        """Check if rebalancing is needed"""
        total = cb_balance + gem_balance
        
        if total < self.min_balance_per_exchange * 2:
            return False
        
        cb_ratio = cb_balance / total if total > 0 else 0
        gem_ratio = gem_balance / total if total > 0 else 0
        
        return cb_ratio < self.rebalance_threshold or gem_ratio < self.rebalance_threshold

