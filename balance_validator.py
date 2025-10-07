#!/usr/bin/env python3
"""
Balance Validator - Critical Fix 1
Comprehensive balance validation system for the arbitrage bot
"""

import asyncio
import time
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class BalanceValidation:
    """Balance validation result"""
    is_valid: bool
    required_amount: float
    available_amount: float
    shortfall: float
    message: str
    exchange: str
    currency: str
    timestamp: float

class BalanceValidator:
    """Comprehensive balance validation system"""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.balance_locks = {}  # Per-exchange balance locks
        self.balance_cache = {}  # Cached balance data
        self.cache_ttl = 5  # 5 seconds cache TTL
        self.last_update = {}
        self.validation_history = []  # Track validation history
        
    async def validate_balance(self, exchange_name: str, currency: str, 
                            required_amount: float, buffer_percent: float = 0.1) -> BalanceValidation:
        """Validate balance with comprehensive checks"""
        try:
            # Get current balance
            current_balance = await self._get_current_balance(exchange_name, currency)
            
            # Calculate required amount with buffer
            required_with_buffer = required_amount * (1 + buffer_percent)
            
            # Check if balance is sufficient
            is_valid = current_balance >= required_with_buffer
            shortfall = max(0, required_with_buffer - current_balance)
            
            validation = BalanceValidation(
                is_valid=is_valid,
                required_amount=required_with_buffer,
                available_amount=current_balance,
                shortfall=shortfall,
                message="Balance sufficient" if is_valid else f"Insufficient balance. Shortfall: {shortfall:.2f} {currency}",
                exchange=exchange_name,
                currency=currency,
                timestamp=time.time()
            )
            
            # Log validation result
            if is_valid:
                logger.info(f"✅ Balance validation passed for {exchange_name} {currency}: {current_balance:.2f} >= {required_with_buffer:.2f}")
            else:
                logger.warning(f"❌ Balance validation failed for {exchange_name} {currency}: {current_balance:.2f} < {required_with_buffer:.2f}")
            
            # Store in history
            self.validation_history.append(validation)
            
            return validation
                
        except Exception as e:
            logger.error(f"Balance validation error for {exchange_name} {currency}: {str(e)}")
            return BalanceValidation(
                is_valid=False,
                required_amount=required_amount,
                available_amount=0.0,
                shortfall=required_amount,
                message=f"Balance validation error: {str(e)}",
                exchange=exchange_name,
                currency=currency,
                timestamp=time.time()
            )
    
    async def _get_current_balance(self, exchange_name: str, currency: str) -> float:
        """Get current balance with caching and locking"""
        # Check cache first
        cache_key = f"{exchange_name}_{currency}"
        current_time = time.time()
        
        if (cache_key in self.balance_cache and 
            current_time - self.last_update.get(cache_key, 0) < self.cache_ttl):
            return self.balance_cache[cache_key]
        
        # Acquire lock for this exchange
        if exchange_name not in self.balance_locks:
            self.balance_locks[exchange_name] = asyncio.Lock()
        
        async with self.balance_locks[exchange_name]:
            try:
                # Get fresh balance from exchange
                exchange = self.exchange_manager.get_exchange(exchange_name)
                balance = await exchange.get_balance()
                current_balance = balance.get(currency, 0.0)
                
                # Update cache
                self.balance_cache[cache_key] = current_balance
                self.last_update[cache_key] = current_time
                
                logger.debug(f"Updated balance cache for {exchange_name} {currency}: {current_balance:.2f}")
                return current_balance
                
            except Exception as e:
                logger.error(f"Error getting balance from {exchange_name}: {str(e)}")
                return 0.0
    
    async def validate_trade_balance(self, buy_exchange: str, sell_exchange: str,
                                   symbol: str, amount: float, price: float) -> Dict[str, BalanceValidation]:
        """Validate balances for both sides of a trade"""
        results = {}
        
        try:
            # Validate buy side (USDT balance)
            buy_validation = await self.validate_balance(
                buy_exchange, 'USDT', amount * price, buffer_percent=0.1
            )
            results['buy_side'] = buy_validation
            
            # Validate sell side (crypto balance)
            crypto_symbol = symbol.split('/')[0]
            sell_validation = await self.validate_balance(
                sell_exchange, crypto_symbol, amount, buffer_percent=0.05
            )
            results['sell_side'] = sell_validation
            
            # Overall validation
            overall_valid = buy_validation.is_valid and sell_validation.is_valid
            results['overall_valid'] = overall_valid
            
            if overall_valid:
                logger.info(f"✅ Trade balance validation passed for {symbol}")
            else:
                logger.warning(f"❌ Trade balance validation failed for {symbol}")
                if not buy_validation.is_valid:
                    logger.warning(f"   Buy side issue: {buy_validation.message}")
                if not sell_validation.is_valid:
                    logger.warning(f"   Sell side issue: {sell_validation.message}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error validating trade balance for {symbol}: {str(e)}")
            return {
                'buy_side': BalanceValidation(False, 0, 0, 0, f"Error: {str(e)}", buy_exchange, 'USDT', time.time()),
                'sell_side': BalanceValidation(False, 0, 0, 0, f"Error: {str(e)}", sell_exchange, symbol.split('/')[0], time.time()),
                'overall_valid': False
            }
    
    async def update_balance_after_trade(self, exchange_name: str, currency: str, 
                                       amount: float, operation: str):
        """Update balance cache after a trade"""
        try:
            cache_key = f"{exchange_name}_{currency}"
            current_balance = self.balance_cache.get(cache_key, 0.0)
            
            if operation == 'add':
                new_balance = current_balance + amount
            elif operation == 'subtract':
                new_balance = current_balance - amount
            else:
                new_balance = amount
            
            self.balance_cache[cache_key] = new_balance
            self.last_update[cache_key] = time.time()
            
            logger.info(f"Updated balance cache for {exchange_name} {currency}: {current_balance:.2f} -> {new_balance:.2f}")
            
        except Exception as e:
            logger.error(f"Error updating balance cache: {str(e)}")
    
    def get_validation_stats(self) -> Dict[str, any]:
        """Get validation statistics"""
        if not self.validation_history:
            return {"total_validations": 0, "success_rate": 0.0}
        
        total_validations = len(self.validation_history)
        successful_validations = len([v for v in self.validation_history if v.is_valid])
        success_rate = (successful_validations / total_validations) * 100
        
        return {
            "total_validations": total_validations,
            "successful_validations": successful_validations,
            "success_rate": success_rate,
            "recent_validations": self.validation_history[-10:]  # Last 10 validations
        }
    
    def clear_cache(self):
        """Clear balance cache"""
        self.balance_cache.clear()
        self.last_update.clear()
        logger.info("Balance cache cleared")
    
    def get_cache_info(self) -> Dict[str, any]:
        """Get cache information"""
        return {
            "cached_balances": len(self.balance_cache),
            "cache_ttl": self.cache_ttl,
            "last_updates": self.last_update
        }
