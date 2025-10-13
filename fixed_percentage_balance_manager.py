#!/usr/bin/env python3
"""
Fixed Percentage Balance Manager - Critical Fix 2
Balance-aware position sizing with comprehensive validation
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from balance_validator import BalanceValidator, BalanceValidation
try:
    from coinbase_gemini_config import Config
except ImportError:
    from fixed_config import FixedConfig as Config

logger = logging.getLogger(__name__)

@dataclass
class PositionSizeResult:
    """Position size calculation result"""
    position_size: float
    is_valid: bool
    reason: str
    max_allowed: float
    min_required: float
    available_balance: float
    required_balance: float

class FixedPercentageBalanceManager:
    """Fixed percentage balance manager with balance validation"""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.balance_validator = BalanceValidator(exchange_manager)
        self.config = Config
        self.current_positions = {}
        self.active_concurrent_trades = 0
        self.position_history = []
        self.balance_locks = {}  # Per-exchange balance locks
        
    async def get_total_account_value(self) -> float:
        """Get total account value across all exchanges"""
        total_value = 0.0
        
        try:
            for exchange_name in ['coinbase', 'gemini']:
                try:
                    exchange = self.exchange_manager.get_exchange(exchange_name)
                    balance = await exchange.get_balance()
                    
                    # Convert all balances to USD
                    for currency, amount in balance.items():
                        if amount > 0:
                            if currency == 'USDT':
                                total_value += amount
                            else:
                                try:
                                    ticker = await exchange.get_ticker(f"{currency}/USDT")
                                    total_value += amount * ticker['last']
                                except Exception:
                                    logger.warning(f"Could not get USDT value for {currency} on {exchange_name}")
                                    pass
                                    
                except Exception as e:
                    logger.error(f"Error fetching balance from {exchange_name}: {str(e)}")
                    
            logger.info(f"Total account value: ${total_value:,.2f}")
            return total_value
            
        except Exception as e:
            logger.error(f"Error calculating total account value: {str(e)}")
            return 0.0
    
    async def get_adaptive_position_size(self, symbol: str, spread_percent: float, 
                                      volatility: float) -> float:
        """Calculate adaptive position size with balance validation"""
        try:
            # Get total account value
            total_account_value = await self.get_total_account_value()
            
            if total_account_value < self.config.RISK_MANAGEMENT['min_account_balance_usd']:
                logger.warning(f"Account value ${total_account_value:,.2f} below minimum ${self.config.RISK_MANAGEMENT['min_account_balance_usd']:,.2f}")
                return 0.0
            
            # Calculate base position size
            asset_allocation_percent = self.config.POSITION_PERCENTAGES.get(symbol, 0.05)
            base_position_size = total_account_value * asset_allocation_percent
            
            # Apply risk limits
            max_position_size = total_account_value * self.config.RISK_MANAGEMENT['max_position_percent']
            min_position_size = total_account_value * self.config.RISK_MANAGEMENT['min_position_percent']
            
            position_size = min(base_position_size, max_position_size)
            position_size = max(position_size, min_position_size)
            
            # Validate against available balances
            validated_result = await self._validate_position_size(symbol, position_size, spread_percent)
            
            if validated_result.is_valid:
                logger.info(f"✅ Position size validated for {symbol}: ${validated_result.position_size:,.2f}")
                return validated_result.position_size
            else:
                logger.warning(f"❌ Position size validation failed for {symbol}: {validated_result.reason}")
                return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating position size for {symbol}: {str(e)}")
            return 0.0
    
    async def _validate_position_size(self, symbol: str, position_size: float, 
                                    spread_percent: float) -> PositionSizeResult:
        """Validate position size against available balances"""
        try:
            # Get exchanges
            exchanges = ['coinbase', 'gemini']
            validated_sizes = []
            validation_details = []
            
            for exchange_name in exchanges:
                try:
                    # Get current price
                    exchange = self.exchange_manager.get_exchange(exchange_name)
                    ticker = await exchange.get_ticker(symbol)
                    current_price = ticker['last']
                    
                    # Calculate required USDT for this position
                    required_usdt = position_size * current_price
                    
                    # Validate USDT balance for buy side
                    buy_validation = await self.balance_validator.validate_balance(
                        exchange_name, 'USDT', required_usdt, buffer_percent=0.1
                    )
                    
                    if buy_validation.is_valid:
                        # Calculate max position based on available balance
                        max_position = buy_validation.available_amount / (current_price * 1.1)
                        validated_sizes.append(max_position)
                        validation_details.append({
                            'exchange': exchange_name,
                            'max_position': max_position,
                            'available_usdt': buy_validation.available_amount,
                            'required_usdt': required_usdt
                        })
                        logger.info(f"✅ {exchange_name} can handle position: ${max_position:,.2f}")
                    else:
                        logger.warning(f"❌ {exchange_name} insufficient USDT: {buy_validation.message}")
                        validated_sizes.append(0.0)
                        validation_details.append({
                            'exchange': exchange_name,
                            'max_position': 0.0,
                            'available_usdt': buy_validation.available_amount,
                            'required_usdt': required_usdt,
                            'error': buy_validation.message
                        })
                        
                except Exception as e:
                    logger.error(f"Error validating position size on {exchange_name}: {str(e)}")
                    validated_sizes.append(0.0)
                    validation_details.append({
                        'exchange': exchange_name,
                        'max_position': 0.0,
                        'error': str(e)
                    })
            
            # Find the maximum validated position size
            max_validated = max(validated_sizes) if validated_sizes else 0.0
            
            # Ensure minimum position size
            min_position = self.config.RISK_MANAGEMENT['min_position_percent'] * await self.get_total_account_value()
            
            if max_validated < min_position:
                return PositionSizeResult(
                    position_size=0.0,
                    is_valid=False,
                    reason=f"Maximum validated position ${max_validated:,.2f} below minimum ${min_position:,.2f}",
                    max_allowed=max_validated,
                    min_required=min_position,
                    available_balance=0.0,
                    required_balance=min_position
                )
            
            # Scale position based on spread quality
            scaled_position = self._scale_position_by_spread(max_validated, spread_percent)
            
            return PositionSizeResult(
                position_size=scaled_position,
                is_valid=True,
                reason="Position size validated successfully",
                max_allowed=max_validated,
                min_required=min_position,
                available_balance=max_validated,
                required_balance=scaled_position
            )
            
        except Exception as e:
            logger.error(f"Error validating position size: {str(e)}")
            return PositionSizeResult(
                position_size=0.0,
                is_valid=False,
                reason=f"Validation error: {str(e)}",
                max_allowed=0.0,
                min_required=0.0,
                available_balance=0.0,
                required_balance=0.0
            )
    
    def _scale_position_by_spread(self, base_position: float, spread_percent: float) -> float:
        """Scale position size based on spread quality"""
        try:
            # Higher spread = higher confidence = larger position
            if spread_percent > 0.02:  # > 2% spread
                scale_factor = 1.0
            elif spread_percent > 0.015:  # > 1.5% spread
                scale_factor = 0.9
            elif spread_percent > 0.01:  # > 1% spread
                scale_factor = 0.8
            else:  # < 1% spread
                scale_factor = 0.7
            
            scaled_position = base_position * scale_factor
            logger.debug(f"Scaled position by {scale_factor:.1f}x based on {spread_percent:.1%} spread")
            return scaled_position
            
        except Exception as e:
            logger.error(f"Error scaling position: {str(e)}")
            return base_position
    
    async def update_position_tracking(self, symbol: str, amount: float, is_opening: bool):
        """Update position tracking"""
        try:
            if is_opening:
                self.current_positions[symbol] = self.current_positions.get(symbol, 0.0) + amount
                self.active_concurrent_trades += 1
                logger.info(f"Opened position for {symbol}: ${amount:,.2f}")
            else:
                if symbol in self.current_positions:
                    self.current_positions[symbol] -= amount
                    if self.current_positions[symbol] <= 0:
                        del self.current_positions[symbol]
                    self.active_concurrent_trades = max(0, self.active_concurrent_trades - 1)
                    logger.info(f"Closed position for {symbol}: ${amount:,.2f}")
            
            # Store in history
            self.position_history.append({
                'symbol': symbol,
                'amount': amount,
                'is_opening': is_opening,
                'timestamp': time.time(),
                'active_positions': len(self.current_positions),
                'concurrent_trades': self.active_concurrent_trades
            })
            
        except Exception as e:
            logger.error(f"Error updating position tracking: {str(e)}")
    
    def get_position_stats(self) -> Dict[str, any]:
        """Get position statistics"""
        return {
            'active_positions': len(self.current_positions),
            'concurrent_trades': self.active_concurrent_trades,
            'current_positions': self.current_positions.copy(),
            'position_history_count': len(self.position_history),
            'recent_positions': self.position_history[-10:] if self.position_history else []
        }
    
    def can_open_new_position(self) -> bool:
        """Check if we can open a new position"""
        return self.active_concurrent_trades < self.config.RISK_MANAGEMENT['max_concurrent_trades']
    
    def get_total_exposure(self) -> float:
        """Get total current exposure"""
        return sum(self.current_positions.values())
    
    async def check_exposure_limits(self, new_position_size: float) -> bool:
        """Check if new position would exceed exposure limits"""
        try:
            total_account_value = await self.get_total_account_value()
            current_exposure = self.get_total_exposure()
            new_total_exposure = current_exposure + new_position_size
            
            max_exposure = total_account_value * self.config.RISK_MANAGEMENT['max_total_exposure']
            
            if new_total_exposure > max_exposure:
                logger.warning(f"New position would exceed exposure limit: {new_total_exposure:,.2f} > {max_exposure:,.2f}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking exposure limits: {str(e)}")
            return False
