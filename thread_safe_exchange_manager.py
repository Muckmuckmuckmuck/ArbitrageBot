#!/usr/bin/env python3
"""
Thread-Safe Exchange Manager - Critical Fix 4
Thread-safe operations for exchange management and balance updates
"""

import asyncio
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ThreadSafeBalance:
    """Thread-safe balance management"""
    balance: Dict[str, float]
    lock: asyncio.Lock
    last_updated: float
    exchange_name: str

@dataclass
class ThreadSafeOrder:
    """Thread-safe order management"""
    order_id: str
    symbol: str
    side: str
    amount: float
    price: float
    status: str
    timestamp: float
    exchange: str

class ThreadSafeExchangeManager:
    """Thread-safe exchange manager with comprehensive locking mechanisms"""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.balance_locks = {}  # Per-exchange balance locks
        self.order_locks = {}   # Per-exchange order locks
        self.rate_limit_locks = {}  # Per-exchange rate limit locks
        self.thread_safe_balances = {}  # Thread-safe balance storage
        self.active_orders = {}  # Track active orders
        self.operation_locks = {}  # General operation locks
        self.thread_safety_stats = {
            'balance_updates': 0,
            'order_operations': 0,
            'lock_contention': 0,
            'concurrent_operations': 0
        }
        
    async def get_thread_safe_balance(self, exchange_name: str) -> Dict[str, float]:
        """Get thread-safe balance with proper locking"""
        if exchange_name not in self.balance_locks:
            self.balance_locks[exchange_name] = asyncio.Lock()
        
        async with self.balance_locks[exchange_name]:
            try:
                # Get fresh balance from exchange
                exchange = self.exchange_manager.get_exchange(exchange_name)
                balance = await exchange.get_balance()
                
                # Update thread-safe balance
                if exchange_name not in self.thread_safe_balances:
                    self.thread_safe_balances[exchange_name] = ThreadSafeBalance(
                        balance=balance.copy(),
                        lock=asyncio.Lock(),
                        last_updated=time.time(),
                        exchange_name=exchange_name
                    )
                else:
                    self.thread_safe_balances[exchange_name].balance = balance.copy()
                    self.thread_safe_balances[exchange_name].last_updated = time.time()
                
                self.thread_safety_stats['balance_updates'] += 1
                logger.debug(f"Updated thread-safe balance for {exchange_name}")
                return balance.copy()
                
            except Exception as e:
                logger.error(f"Error getting thread-safe balance from {exchange_name}: {str(e)}")
                return {}
    
    async def update_thread_safe_balance(self, exchange_name: str, currency: str, 
                                      amount: float, operation: str):
        """Update thread-safe balance with proper locking"""
        if exchange_name not in self.balance_locks:
            self.balance_locks[exchange_name] = asyncio.Lock()
        
        async with self.balance_locks[exchange_name]:
            try:
                if exchange_name not in self.thread_safe_balances:
                    self.thread_safe_balances[exchange_name] = ThreadSafeBalance(
                        balance={},
                        lock=asyncio.Lock(),
                        last_updated=time.time(),
                        exchange_name=exchange_name
                    )
                
                current_balance = self.thread_safe_balances[exchange_name].balance.get(currency, 0.0)
                
                if operation == 'add':
                    new_balance = current_balance + amount
                elif operation == 'subtract':
                    new_balance = current_balance - amount
                elif operation == 'set':
                    new_balance = amount
                else:
                    raise ValueError(f"Invalid operation: {operation}")
                
                # Validate balance doesn't go negative
                if new_balance < 0:
                    logger.warning(f"Balance would go negative for {exchange_name} {currency}: {new_balance}")
                    new_balance = 0.0
                
                self.thread_safe_balances[exchange_name].balance[currency] = new_balance
                self.thread_safe_balances[exchange_name].last_updated = time.time()
                
                logger.info(f"Updated {exchange_name} {currency} balance: {current_balance:.2f} -> {new_balance:.2f}")
                self.thread_safety_stats['balance_updates'] += 1
                
            except Exception as e:
                logger.error(f"Error updating thread-safe balance: {str(e)}")
    
    async def execute_thread_safe_trade(self, exchange_name: str, symbol: str, 
                                      side: str, amount: float, price: float) -> Dict[str, Any]:
        """Execute thread-safe trade with comprehensive validation"""
        if exchange_name not in self.order_locks:
            self.order_locks[exchange_name] = asyncio.Lock()
        
        async with self.order_locks[exchange_name]:
            try:
                # Validate balance before trade
                currency = 'USDT' if side == 'buy' else symbol.split('/')[0]
                required_amount = amount * price if side == 'buy' else amount
                
                balance = await self.get_thread_safe_balance(exchange_name)
                available = balance.get(currency, 0.0)
                
                if available < required_amount * 1.1:  # 10% buffer
                    raise Exception(f"Insufficient {currency} balance. Required: {required_amount:.2f}, Available: {available:.2f}")
                
                # Execute trade
                exchange = self.exchange_manager.get_exchange(exchange_name)
                result = await exchange.create_order(symbol, 'market', side, amount, price)
                
                # Update balance after successful trade
                if side == 'buy':
                    await self.update_thread_safe_balance(exchange_name, 'USDT', -required_amount, 'subtract')
                    await self.update_thread_safe_balance(exchange_name, currency, amount, 'add')
                else:
                    await self.update_thread_safe_balance(exchange_name, currency, -amount, 'subtract')
                    await self.update_thread_safe_balance(exchange_name, 'USDT', amount * price, 'add')
                
                # Track order
                order = ThreadSafeOrder(
                    order_id=result.get('id', 'unknown'),
                    symbol=symbol,
                    side=side,
                    amount=amount,
                    price=price,
                    status=result.get('status', 'unknown'),
                    timestamp=time.time(),
                    exchange=exchange_name
                )
                
                self.active_orders[order.order_id] = order
                self.thread_safety_stats['order_operations'] += 1
                
                logger.info(f"✅ Thread-safe trade executed: {symbol} {side} {amount} @ {price}")
                return result
                
            except Exception as e:
                logger.error(f"Error executing thread-safe trade: {str(e)}")
                raise
    
    async def get_thread_safe_balance_for_currency(self, exchange_name: str, currency: str) -> float:
        """Get thread-safe balance for a specific currency"""
        try:
            balance = await self.get_thread_safe_balance(exchange_name)
            return balance.get(currency, 0.0)
        except Exception as e:
            logger.error(f"Error getting balance for {currency} on {exchange_name}: {str(e)}")
            return 0.0
    
    async def validate_thread_safe_balance(self, exchange_name: str, currency: str, 
                                         required_amount: float) -> Tuple[bool, float]:
        """Validate thread-safe balance for a required amount"""
        try:
            current_balance = await self.get_thread_safe_balance_for_currency(exchange_name, currency)
            is_sufficient = current_balance >= required_amount
            return is_sufficient, current_balance
        except Exception as e:
            logger.error(f"Error validating balance: {str(e)}")
            return False, 0.0
    
    async def execute_thread_safe_arbitrage(self, buy_exchange: str, sell_exchange: str,
                                          symbol: str, amount: float, buy_price: float, 
                                          sell_price: float) -> Dict[str, Any]:
        """Execute thread-safe arbitrage trade"""
        try:
            # Validate balances on both exchanges
            buy_currency = 'USDT'
            sell_currency = symbol.split('/')[0]
            
            # Check buy exchange balance
            buy_sufficient, buy_balance = await self.validate_thread_safe_balance(
                buy_exchange, buy_currency, amount * buy_price
            )
            
            if not buy_sufficient:
                raise Exception(f"Insufficient {buy_currency} balance on {buy_exchange}: {buy_balance:.2f} < {amount * buy_price:.2f}")
            
            # Check sell exchange balance
            sell_sufficient, sell_balance = await self.validate_thread_safe_balance(
                sell_exchange, sell_currency, amount
            )
            
            if not sell_sufficient:
                raise Exception(f"Insufficient {sell_currency} balance on {sell_exchange}: {sell_balance:.2f} < {amount:.2f}")
            
            # Execute buy order
            buy_result = await self.execute_thread_safe_trade(
                buy_exchange, symbol, 'buy', amount, buy_price
            )
            
            # Execute sell order
            sell_result = await self.execute_thread_safe_trade(
                sell_exchange, symbol, 'sell', amount, sell_price
            )
            
            # Calculate profit
            profit = (sell_price - buy_price) * amount
            
            result = {
                'buy_order': buy_result,
                'sell_order': sell_result,
                'profit': profit,
                'symbol': symbol,
                'amount': amount,
                'buy_price': buy_price,
                'sell_price': sell_price,
                'timestamp': time.time()
            }
            
            logger.info(f"✅ Thread-safe arbitrage executed: {symbol} - Profit: ${profit:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error executing thread-safe arbitrage: {str(e)}")
            raise
    
    def get_thread_safety_stats(self) -> Dict[str, any]:
        """Get thread safety statistics"""
        return {
            'balance_updates': self.thread_safety_stats['balance_updates'],
            'order_operations': self.thread_safety_stats['order_operations'],
            'active_orders': len(self.active_orders),
            'thread_safe_balances': len(self.thread_safe_balances),
            'balance_locks': len(self.balance_locks),
            'order_locks': len(self.order_locks),
            'rate_limit_locks': len(self.rate_limit_locks),
            'recent_orders': list(self.active_orders.values())[-10:] if self.active_orders else []
        }
    
    def get_active_orders(self) -> Dict[str, ThreadSafeOrder]:
        """Get all active orders"""
        return self.active_orders.copy()
    
    def clear_active_orders(self):
        """Clear all active orders"""
        self.active_orders.clear()
        logger.info("Active orders cleared")
    
    def get_balance_summary(self) -> Dict[str, Dict[str, float]]:
        """Get balance summary for all exchanges"""
        summary = {}
        for exchange_name, balance_data in self.thread_safe_balances.items():
            summary[exchange_name] = balance_data.balance.copy()
        return summary
    
    async def sync_all_balances(self):
        """Sync all balances across all exchanges"""
        try:
            exchanges = ['binance', 'okx']
            for exchange_name in exchanges:
                await self.get_thread_safe_balance(exchange_name)
            
            logger.info("All balances synced successfully")
        except Exception as e:
            logger.error(f"Error syncing balances: {str(e)}")
    
    def reset_thread_safety_stats(self):
        """Reset thread safety statistics"""
        self.thread_safety_stats = {
            'balance_updates': 0,
            'order_operations': 0,
            'lock_contention': 0,
            'concurrent_operations': 0
        }
        logger.info("Thread safety statistics reset")
