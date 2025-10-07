
# Add to exchanges.py

import asyncio
import threading
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class ThreadSafeBalance:
    """Thread-safe balance management"""
    balance: Dict[str, float]
    lock: asyncio.Lock
    last_updated: float

class ThreadSafeExchangeManager:
    """Thread-safe exchange manager"""
    
    def __init__(self):
        self.exchanges = {}
        self.balance_locks = {}  # Per-exchange balance locks
        self.order_locks = {}    # Per-exchange order locks
        self.rate_limit_locks = {}  # Per-exchange rate limit locks
        self.thread_safe_balances = {}  # Thread-safe balance storage
    
    async def get_thread_safe_balance(self, exchange_name: str) -> Dict[str, float]:
        """Get thread-safe balance"""
        if exchange_name not in self.balance_locks:
            self.balance_locks[exchange_name] = asyncio.Lock()
        
        async with self.balance_locks[exchange_name]:
            try:
                # Get fresh balance from exchange
                exchange = self.exchanges[exchange_name]
                balance = await exchange.get_balance()
                
                # Update thread-safe balance
                if exchange_name not in self.thread_safe_balances:
                    self.thread_safe_balances[exchange_name] = ThreadSafeBalance(
                        balance=balance.copy(),
                        lock=asyncio.Lock(),
                        last_updated=time.time()
                    )
                else:
                    self.thread_safe_balances[exchange_name].balance = balance.copy()
                    self.thread_safe_balances[exchange_name].last_updated = time.time()
                
                return balance.copy()
                
            except Exception as e:
                logger.error(f"Error getting thread-safe balance: {str(e)}")
                return {}
    
    async def update_thread_safe_balance(self, exchange_name: str, currency: str, 
                                        amount: float, operation: str):
        """Update thread-safe balance"""
        if exchange_name not in self.balance_locks:
            self.balance_locks[exchange_name] = asyncio.Lock()
        
        async with self.balance_locks[exchange_name]:
            try:
                if exchange_name not in self.thread_safe_balances:
                    self.thread_safe_balances[exchange_name] = ThreadSafeBalance(
                        balance={},
                        lock=asyncio.Lock(),
                        last_updated=time.time()
                    )
                
                current_balance = self.thread_safe_balances[exchange_name].balance.get(currency, 0.0)
                
                if operation == 'add':
                    new_balance = current_balance + amount
                elif operation == 'subtract':
                    new_balance = current_balance - amount
                else:
                    new_balance = amount
                
                self.thread_safe_balances[exchange_name].balance[currency] = new_balance
                self.thread_safe_balances[exchange_name].last_updated = time.time()
                
                logger.info(f"Updated {exchange_name} {currency} balance: {current_balance} -> {new_balance}")
                
            except Exception as e:
                logger.error(f"Error updating thread-safe balance: {str(e)}")
    
    async def execute_thread_safe_trade(self, exchange_name: str, symbol: str, 
                                      side: str, amount: float, price: float) -> Dict[str, Any]:
        """Execute thread-safe trade"""
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
                    raise Exception(f"Insufficient {currency} balance. Required: {required_amount}, Available: {available}")
                
                # Execute trade
                exchange = self.exchanges[exchange_name]
                result = await exchange.create_order(symbol, 'market', side, amount, price)
                
                # Update balance after successful trade
                if side == 'buy':
                    await self.update_thread_safe_balance(exchange_name, 'USDT', -required_amount, 'subtract')
                    await self.update_thread_safe_balance(exchange_name, currency, amount, 'add')
                else:
                    await self.update_thread_safe_balance(exchange_name, currency, -amount, 'subtract')
                    await self.update_thread_safe_balance(exchange_name, 'USDT', amount * price, 'add')
                
                return result
                
            except Exception as e:
                logger.error(f"Error executing thread-safe trade: {str(e)}")
                raise
