
# Add to exchanges.py or create balance_validator.py

import asyncio
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class BalanceValidation:
    """Balance validation result"""
    is_valid: bool
    required_amount: float
    available_amount: float
    shortfall: float
    message: str

class BalanceValidator:
    """Comprehensive balance validation system"""
    
    def __init__(self):
        self.balance_locks = {}  # Per-exchange balance locks
        self.balance_cache = {}  # Cached balance data
        self.cache_ttl = 5  # 5 seconds cache TTL
        self.last_update = {}
    
    async def validate_balance(self, exchange_name: str, currency: str, 
                            required_amount: float, buffer_percent: float = 0.1) -> BalanceValidation:
        """Validate balance with comprehensive checks"""
        try:
            # Get current balance
            current_balance = await self._get_current_balance(exchange_name, currency)
            
            # Calculate required amount with buffer
            required_with_buffer = required_amount * (1 + buffer_percent)
            
            # Check if balance is sufficient
            if current_balance >= required_with_buffer:
                return BalanceValidation(
                    is_valid=True,
                    required_amount=required_with_buffer,
                    available_amount=current_balance,
                    shortfall=0.0,
                    message="Balance sufficient"
                )
            else:
                shortfall = required_with_buffer - current_balance
                return BalanceValidation(
                    is_valid=False,
                    required_amount=required_with_buffer,
                    available_amount=current_balance,
                    shortfall=shortfall,
                    message=f"Insufficient balance. Shortfall: {shortfall:.2f} {currency}"
                )
                
        except Exception as e:
            return BalanceValidation(
                is_valid=False,
                required_amount=required_amount,
                available_amount=0.0,
                shortfall=required_amount,
                message=f"Balance validation error: {str(e)}"
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
                exchange = self.get_exchange(exchange_name)
                balance = await exchange.get_balance()
                current_balance = balance.get(currency, 0.0)
                
                # Update cache
                self.balance_cache[cache_key] = current_balance
                self.last_update[cache_key] = current_time
                
                return current_balance
                
            except Exception as e:
                logger.error(f"Error getting balance from {exchange_name}: {str(e)}")
                return 0.0
    
    async def validate_trade_balance(self, buy_exchange: str, sell_exchange: str,
                                   symbol: str, amount: float, price: float) -> Dict[str, BalanceValidation]:
        """Validate balances for both sides of a trade"""
        results = {}
        
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
        
        return results
