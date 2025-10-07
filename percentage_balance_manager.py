#!/usr/bin/env python3
"""
Percentage-Based Balance Manager
Manages dynamic position sizing based on percentage of total account value
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from config import Config

logger = logging.getLogger(__name__)

@dataclass
class PositionAllocation:
    """Position allocation data"""
    symbol: str
    tier: str
    percentage: float
    recommended_position_usd: float
    max_position_usd: float
    min_position_usd: float
    risk_score: float
    opportunity_score: float

@dataclass
class AccountBalance:
    """Account balance information"""
    exchange: str
    total_usd: float
    crypto_holdings: Dict[str, float]  # symbol -> USD value
    cash_holdings: Dict[str, float]    # currency -> USD value
    available_for_trading: float
    reserve_amount: float

class PercentageBalanceManager:
    """Manages dynamic position sizing based on percentage of total account value"""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.config = Config()
        self.position_percentages = self.config.POSITION_PERCENTAGES
        self.risk_management = self.config.RISK_MANAGEMENT
        
        # Track account balances
        self.account_balances: Dict[str, AccountBalance] = {}
        self.total_account_value = 0.0
        self.last_balance_update = 0.0
        
        logger.info("Percentage-based balance manager initialized")
    
    async def update_account_balances(self) -> Dict[str, AccountBalance]:
        """Update account balances from all exchanges"""
        try:
            balances = {}
            total_value = 0.0
            
            # Get balances from each exchange
            for exchange_name in ['binance', 'okx']:
                try:
                    exchange_balance = await self._get_exchange_balance(exchange_name)
                    balances[exchange_name] = exchange_balance
                    total_value += exchange_balance.total_usd
                except Exception as e:
                    logger.error(f"Error getting balance from {exchange_name}: {str(e)}")
                    continue
            
            self.account_balances = balances
            self.total_account_value = total_value
            self.last_balance_update = asyncio.get_event_loop().time()
            
            logger.info(f"Updated account balances - Total value: ${total_value:,.2f}")
            return balances
            
        except Exception as e:
            logger.error(f"Error updating account balances: {str(e)}")
            return {}
    
    async def _get_exchange_balance(self, exchange_name: str) -> AccountBalance:
        """Get balance from a specific exchange"""
        try:
            exchange = getattr(self.exchange_manager, exchange_name, None)
            if not exchange:
                raise ValueError(f"Exchange {exchange_name} not found")
            
            # Get account balance
            balance_info = await exchange.get_balance()
            
            # Calculate total USD value
            total_usd = 0.0
            crypto_holdings = {}
            cash_holdings = {}
            
            for currency, amount in balance_info.items():
                if currency in ['USDT', 'USDC', 'DAI', 'BUSD']:
                    cash_holdings[currency] = amount
                    total_usd += amount
                else:
                    # Get current price for crypto
                    try:
                        price = await exchange.get_ticker(f"{currency}/USDT")
                        usd_value = amount * price
                        crypto_holdings[currency] = usd_value
                        total_usd += usd_value
                    except:
                        # If can't get price, assume 0 value
                        crypto_holdings[currency] = 0.0
            
            # Calculate available for trading
            reserve_amount = total_usd * self.risk_management['reserve_percent']
            available_for_trading = total_usd - reserve_amount
            
            return AccountBalance(
                exchange=exchange_name,
                total_usd=total_usd,
                crypto_holdings=crypto_holdings,
                cash_holdings=cash_holdings,
                available_for_trading=available_for_trading,
                reserve_amount=reserve_amount
            )
            
        except Exception as e:
            logger.error(f"Error getting balance from {exchange_name}: {str(e)}")
            return AccountBalance(
                exchange=exchange_name,
                total_usd=0.0,
                crypto_holdings={},
                cash_holdings={},
                available_for_trading=0.0,
                reserve_amount=0.0
            )
    
    async def calculate_position_allocations(self) -> Dict[str, PositionAllocation]:
        """Calculate position allocations based on percentage of total account value"""
        try:
            # Update balances if needed
            if not self.account_balances or (asyncio.get_event_loop().time() - self.last_balance_update) > 300:
                await self.update_account_balances()
            
            if self.total_account_value <= 0:
                logger.warning("No account value available for position calculation")
                return {}
            
            allocations = {}
            
            # Calculate allocations for each currency pair
            for symbol, percentage in self.position_percentages.items():
                try:
                    # Determine tier
                    tier = self._get_tier_for_symbol(symbol)
                    
                    # Calculate position size based on percentage
                    recommended_position_usd = self.total_account_value * percentage
                    
                    # Apply risk management limits
                    max_position_usd = self.total_account_value * self.risk_management['max_position_percent']
                    min_position_usd = self.total_account_value * self.risk_management['min_position_percent']
                    
                    # Ensure position is within limits
                    recommended_position_usd = min(recommended_position_usd, max_position_usd)
                    recommended_position_usd = max(recommended_position_usd, min_position_usd)
                    
                    # Calculate risk and opportunity scores
                    risk_score = self._calculate_risk_score(symbol, tier)
                    opportunity_score = self._calculate_opportunity_score(symbol, tier)
                    
                    allocations[symbol] = PositionAllocation(
                        symbol=symbol,
                        tier=tier,
                        percentage=percentage,
                        recommended_position_usd=recommended_position_usd,
                        max_position_usd=max_position_usd,
                        min_position_usd=min_position_usd,
                        risk_score=risk_score,
                        opportunity_score=opportunity_score
                    )
                    
                except Exception as e:
                    logger.error(f"Error calculating allocation for {symbol}: {str(e)}")
                    continue
            
            logger.info(f"Calculated position allocations for {len(allocations)} symbols")
            return allocations
            
        except Exception as e:
            logger.error(f"Error calculating position allocations: {str(e)}")
            return {}
    
    def _get_tier_for_symbol(self, symbol: str) -> str:
        """Get tier for a symbol"""
        if symbol in self.config.TIER1_ASSETS:
            return 'tier1'
        elif symbol in self.config.TIER2_ASSETS:
            return 'tier2'
        elif symbol in self.config.TIER3_ASSETS:
            return 'tier3'
        elif symbol in self.config.TIER4_ASSETS:
            return 'tier4'
        else:
            return 'unknown'
    
    def _calculate_risk_score(self, symbol: str, tier: str) -> float:
        """Calculate risk score for a symbol (0-1, lower is better)"""
        try:
            # Base risk by tier
            tier_risk = {
                'tier1': 0.2,  # Lowest risk
                'tier2': 0.3,
                'tier3': 0.4,
                'tier4': 0.5,  # Highest risk
                'unknown': 0.6
            }
            
            base_risk = tier_risk.get(tier, 0.5)
            
            # Adjust based on position percentage
            position_percent = self.position_percentages.get(symbol, 0.05)
            if position_percent > 0.07:  # High allocation
                base_risk += 0.1
            elif position_percent < 0.04:  # Low allocation
                base_risk -= 0.1
            
            return max(0.0, min(1.0, base_risk))
            
        except Exception as e:
            logger.error(f"Error calculating risk score for {symbol}: {str(e)}")
            return 0.5
    
    def _calculate_opportunity_score(self, symbol: str, tier: str) -> float:
        """Calculate opportunity score for a symbol (0-1, higher is better)"""
        try:
            # Base opportunity by tier
            tier_opportunity = {
                'tier1': 0.9,  # Highest opportunity
                'tier2': 0.8,
                'tier3': 0.7,
                'tier4': 0.6,  # Lowest opportunity
                'unknown': 0.5
            }
            
            base_opportunity = tier_opportunity.get(tier, 0.5)
            
            # Adjust based on position percentage
            position_percent = self.position_percentages.get(symbol, 0.05)
            if position_percent > 0.07:  # High allocation
                base_opportunity += 0.1
            elif position_percent < 0.04:  # Low allocation
                base_opportunity -= 0.1
            
            return max(0.0, min(1.0, base_opportunity))
            
        except Exception as e:
            logger.error(f"Error calculating opportunity score for {symbol}: {str(e)}")
            return 0.5
    
    async def get_adaptive_position_size(self, symbol: str, spread_percent: float, 
                                      volatility: float = 0.02) -> float:
        """Get adaptive position size based on current conditions"""
        try:
            # Get base allocation
            allocations = await self.calculate_position_allocations()
            allocation = allocations.get(symbol)
            
            if not allocation:
                logger.warning(f"No allocation found for {symbol}")
                return 0.0
            
            base_position = allocation.recommended_position_usd
            
            # Adjust based on spread quality
            spread_multiplier = 1.0
            if spread_percent > 0.02:  # > 2% spread
                spread_multiplier = 1.2
            elif spread_percent > 0.015:  # > 1.5% spread
                spread_multiplier = 1.1
            elif spread_percent < 0.01:  # < 1% spread
                spread_multiplier = 0.8
            
            # Adjust based on volatility
            volatility_multiplier = 1.0
            if volatility > 0.05:  # High volatility
                volatility_multiplier = 0.8
            elif volatility < 0.02:  # Low volatility
                volatility_multiplier = 1.1
            
            # Calculate final position size
            final_position = base_position * spread_multiplier * volatility_multiplier
            
            # Ensure within limits
            final_position = min(final_position, allocation.max_position_usd)
            final_position = max(final_position, allocation.min_position_usd)
            
            logger.info(f"Adaptive position size for {symbol}: ${final_position:,.2f} "
                       f"(spread: {spread_percent:.3f}, volatility: {volatility:.3f})")
            
            return final_position
            
        except Exception as e:
            logger.error(f"Error calculating adaptive position size for {symbol}: {str(e)}")
            return 0.0
    
    async def get_total_exposure(self) -> float:
        """Get current total exposure as percentage of account value"""
        try:
            if self.total_account_value <= 0:
                return 0.0
            
            # Calculate current exposure from active trades
            # This would need to be implemented based on your trade tracking system
            current_exposure = 0.0  # Placeholder - implement based on active trades
            
            exposure_percent = current_exposure / self.total_account_value
            return exposure_percent
            
        except Exception as e:
            logger.error(f"Error calculating total exposure: {str(e)}")
            return 0.0
    
    async def can_open_new_position(self, symbol: str, position_size: float) -> bool:
        """Check if a new position can be opened"""
        try:
            # Check total exposure limit
            current_exposure = await self.get_total_exposure()
            if current_exposure + (position_size / self.total_account_value) > self.risk_management['max_total_exposure']:
                logger.warning(f"Total exposure limit would be exceeded for {symbol}")
                return False
            
            # Check position size limit
            max_position = self.total_account_value * self.risk_management['max_position_percent']
            if position_size > max_position:
                logger.warning(f"Position size limit exceeded for {symbol}")
                return False
            
            # Check minimum position size
            min_position = self.total_account_value * self.risk_management['min_position_percent']
            if position_size < min_position:
                logger.warning(f"Position size below minimum for {symbol}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking position limits for {symbol}: {str(e)}")
            return False
    
    def get_balance_summary(self) -> Dict:
        """Get balance summary for monitoring"""
        try:
            return {
                'total_account_value': self.total_account_value,
                'account_balances': {
                    exchange: {
                        'total_usd': balance.total_usd,
                        'available_for_trading': balance.available_for_trading,
                        'reserve_amount': balance.reserve_amount,
                        'crypto_holdings': balance.crypto_holdings,
                        'cash_holdings': balance.cash_holdings
                    }
                    for exchange, balance in self.account_balances.items()
                },
                'risk_management': self.risk_management,
                'position_percentages': self.position_percentages,
                'last_update': self.last_balance_update
            }
        except Exception as e:
            logger.error(f"Error getting balance summary: {str(e)}")
            return {}
    
    async def rebalance_positions(self) -> Dict:
        """Rebalance positions based on current account value"""
        try:
            logger.info("Starting position rebalancing...")
            
            # Update balances
            await self.update_account_balances()
            
            # Calculate new allocations
            allocations = await self.calculate_position_allocations()
            
            # Calculate rebalancing recommendations
            rebalance_recommendations = {}
            
            for symbol, allocation in allocations.items():
                # This would need to be implemented based on your current position tracking
                # For now, just return the recommended allocations
                rebalance_recommendations[symbol] = {
                    'recommended_position': allocation.recommended_position_usd,
                    'current_position': 0.0,  # Placeholder - implement based on current positions
                    'rebalance_amount': allocation.recommended_position_usd,
                    'action': 'buy' if allocation.recommended_position_usd > 0 else 'sell'
                }
            
            logger.info(f"Rebalancing complete for {len(rebalance_recommendations)} positions")
            return rebalance_recommendations
            
        except Exception as e:
            logger.error(f"Error rebalancing positions: {str(e)}")
            return {}
