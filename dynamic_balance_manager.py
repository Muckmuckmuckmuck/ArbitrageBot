import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class AccountBalance:
    """Data class for account balance"""
    exchange: str
    currency: str
    free: float
    used: float
    total: float
    timestamp: float

@dataclass
class PositionAllocation:
    """Data class for position allocation"""
    symbol: str
    base_currency: str
    quote_currency: str
    available_base: float
    available_quote: float
    max_position_usd: float
    recommended_position_usd: float
    position_ratio: float
    risk_level: str

@dataclass
class BalanceOptimization:
    """Data class for balance optimization"""
    total_usd_value: float
    available_usd: float
    allocated_usd: float
    optimization_score: float
    rebalancing_needed: bool
    recommendations: List[str]

class DynamicBalanceManager:
    """Dynamic balance and position sizing manager"""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.account_balances = {}
        self.position_allocations = {}
        self.balance_history = {}
        self.performance_tracking = {}
        
        # Balance management parameters - consistent strategy
        self.balance_config = {
            'min_account_balance_usd': 100,  # Minimum $100 to start trading
            'max_position_percent': 0.15,    # Max 15% of total balance per position
            'reserve_percent': 0.20,         # Keep 20% in reserve
            'rebalance_threshold': 0.10,     # Rebalance when 10% off target
            'min_position_usd': 50,          # Minimum $50 position
            'max_position_usd': 5000,        # Maximum $5000 position (consistent limit)
            'target_allocation': {           # Target allocation by asset tier
                'tier1': 0.60,  # 60% in ultra-fast assets
                'tier2': 0.25,  # 25% in fast assets
                'tier3': 0.15   # 15% in acceptable assets
            }
        }
        
        # Currency priorities (preferred currencies for trading)
        self.currency_priorities = {
            'USDT': 1, 'USDC': 1, 'BUSD': 1, 'DAI': 1,  # Stablecoins - highest priority
            'BTC': 2, 'ETH': 2, 'BNB': 2,  # Major cryptocurrencies
            'XRP': 3, 'XLM': 3, 'SOL': 3, 'ADA': 3, 'DOT': 3,  # Liquid altcoins
            'default': 4  # Other currencies
        }
        
        # Performance tracking
        self.performance_metrics = {}
        self.balance_growth_history = {}
        
    async def update_account_balances(self) -> Dict[str, AccountBalance]:
        """Update account balances from all exchanges"""
        try:
            balances = {}
            
            # Get balances from both exchanges
            for exchange_name in ['binance', 'kraken']:
                try:
                    exchange = self.exchange_manager.get_exchange(exchange_name)
                    exchange_balances = await exchange.get_balances()
                    
                    for currency, balance_data in exchange_balances.items():
                        balance = AccountBalance(
                            exchange=exchange_name,
                            currency=currency,
                            free=balance_data.get('free', 0),
                            used=balance_data.get('used', 0),
                            total=balance_data.get('total', 0),
                            timestamp=time.time()
                        )
                        
                        key = f"{exchange_name}_{currency}"
                        balances[key] = balance
                        
                except Exception as e:
                    logger.error(f"Error getting balances from {exchange_name}: {str(e)}")
                    continue
            
            # Store balances
            self.account_balances = balances
            
            # Update balance history
            current_time = time.time()
            if current_time not in self.balance_history:
                self.balance_history[current_time] = balances.copy()
            
            # Keep only recent history (last 1000 records)
            if len(self.balance_history) > 1000:
                oldest_key = min(self.balance_history.keys())
                del self.balance_history[oldest_key]
            
            logger.info(f"Updated balances from {len(balances)} accounts")
            return balances
            
        except Exception as e:
            logger.error(f"Error updating account balances: {str(e)}")
            return {}
    
    async def calculate_position_allocations(self) -> Dict[str, PositionAllocation]:
        """Calculate position allocations based on current balances"""
        try:
            # Update balances first
            await self.update_account_balances()
            
            # Get current USD values
            total_usd_value = await self._calculate_total_usd_value()
            available_usd = await self._calculate_available_usd()
            
            allocations = {}
            
            # Calculate allocations for each trading pair
            for symbol in Config.CURRENCY_PAIRS:
                try:
                    allocation = await self._calculate_symbol_allocation(symbol, total_usd_value, available_usd)
                    if allocation:
                        allocations[symbol] = allocation
                        
                except Exception as e:
                    logger.error(f"Error calculating allocation for {symbol}: {str(e)}")
                    continue
            
            # Store allocations
            self.position_allocations = allocations
            
            logger.info(f"Calculated position allocations for {len(allocations)} symbols")
            return allocations
            
        except Exception as e:
            logger.error(f"Error calculating position allocations: {str(e)}")
            return {}
    
    async def _calculate_symbol_allocation(self, symbol: str, total_usd_value: float, 
                                         available_usd: float) -> Optional[PositionAllocation]:
        """Calculate allocation for a specific symbol"""
        try:
            base_currency = symbol.split('/')[0]
            quote_currency = symbol.split('/')[1]
            
            # Get available balances
            available_base = await self._get_available_balance(base_currency)
            available_quote = await self._get_available_balance(quote_currency)
            
            # Calculate max position size based on balance and config
            max_position_percent = self.balance_config['max_position_percent']
            max_position_usd = min(
                total_usd_value * max_position_percent,
                self.balance_config['max_position_usd']
            )
            
            # Use consistent position sizing regardless of balance
            available_for_trading = available_usd * (1 - self.balance_config['reserve_percent'])
            max_position_usd = min(max_position_usd, available_for_trading)
            
            # Get tier-based allocation
            tier = self._get_symbol_tier(symbol)
            tier_allocation = self.balance_config['target_allocation'].get(tier, 0.15)
            
            # Calculate recommended position size - consistent percentage
            recommended_position_usd = available_for_trading * tier_allocation
            
            # Ensure minimum position size
            recommended_position_usd = max(
                recommended_position_usd,
                self.balance_config['min_position_usd']
            )
            
            # Ensure maximum position size (consistent limit)
            recommended_position_usd = min(
                recommended_position_usd,
                max_position_usd
            )
            
            # Calculate position ratio (how much of available balance to use)
            position_ratio = recommended_position_usd / available_usd if available_usd > 0 else 0
            
            # Determine risk level
            risk_level = self._determine_risk_level(position_ratio, tier)
            
            return PositionAllocation(
                symbol=symbol,
                base_currency=base_currency,
                quote_currency=quote_currency,
                available_base=available_base,
                available_quote=available_quote,
                max_position_usd=max_position_usd,
                recommended_position_usd=recommended_position_usd,
                position_ratio=position_ratio,
                risk_level=risk_level
            )
            
        except Exception as e:
            logger.error(f"Error calculating symbol allocation for {symbol}: {str(e)}")
            return None
    
    async def _calculate_total_usd_value(self) -> float:
        """Calculate total USD value of all holdings"""
        try:
            total_value = 0.0
            
            # Get current prices for all currencies
            for key, balance in self.account_balances.items():
                if balance.total > 0:
                    currency = balance.currency
                    
                    # Skip if already in USD
                    if currency in ['USDT', 'USDC', 'BUSD', 'DAI']:
                        total_value += balance.total
                        continue
                    
                    # Get USD price for currency
                    usd_price = await self._get_usd_price(currency)
                    if usd_price > 0:
                        total_value += balance.total * usd_price
            
            return total_value
            
        except Exception as e:
            logger.error(f"Error calculating total USD value: {str(e)}")
            return 0.0
    
    async def _calculate_available_usd(self) -> float:
        """Calculate available USD for trading"""
        try:
            available_value = 0.0
            
            # Get available balances
            for key, balance in self.account_balances.items():
                if balance.free > 0:
                    currency = balance.currency
                    
                    # Skip if already in USD
                    if currency in ['USDT', 'USDC', 'BUSD', 'DAI']:
                        available_value += balance.free
                        continue
                    
                    # Get USD price for currency
                    usd_price = await self._get_usd_price(currency)
                    if usd_price > 0:
                        available_value += balance.free * usd_price
            
            return available_value
            
        except Exception as e:
            logger.error(f"Error calculating available USD: {str(e)}")
            return 0.0
    
    async def _get_available_balance(self, currency: str) -> float:
        """Get available balance for a currency across all exchanges"""
        try:
            total_available = 0.0
            
            for key, balance in self.account_balances.items():
                if balance.currency == currency:
                    total_available += balance.free
            
            return total_available
            
        except Exception as e:
            logger.error(f"Error getting available balance for {currency}: {str(e)}")
            return 0.0
    
    async def _get_usd_price(self, currency: str) -> float:
        """Get USD price for a currency"""
        try:
            # Try to get price from exchanges
            for exchange_name in ['binance', 'kraken']:
                try:
                    exchange = self.exchange_manager.get_exchange(exchange_name)
                    symbol = f"{currency}/USDT"
                    ticker = await exchange.get_ticker(symbol)
                    if ticker and 'last' in ticker:
                        return float(ticker['last'])
                except:
                    continue
            
            # Fallback to hardcoded prices for major currencies
            fallback_prices = {
                'BTC': 45000, 'ETH': 3000, 'BNB': 300, 'ADA': 0.5, 'DOT': 7,
                'XRP': 0.6, 'XLM': 0.12, 'SOL': 100, 'AVAX': 25, 'MATIC': 0.8,
                'UNI': 6, 'LINK': 15, 'LTC': 70, 'BCH': 250, 'XMR': 150
            }
            
            return fallback_prices.get(currency, 0.0)
            
        except Exception as e:
            logger.error(f"Error getting USD price for {currency}: {str(e)}")
            return 0.0
    
    def _get_symbol_tier(self, symbol: str) -> str:
        """Get tier for a symbol"""
        if symbol in Config.TIER1_ASSETS:
            return 'tier1'
        elif symbol in Config.TIER2_ASSETS:
            return 'tier2'
        elif symbol in Config.TIER3_ASSETS:
            return 'tier3'
        else:
            return 'tier3'  # Default to tier3
    
    def _determine_risk_level(self, position_ratio: float, tier: str) -> str:
        """Determine risk level for position"""
        try:
            # Base risk on position ratio and tier
            if position_ratio > 0.1:  # > 10% of balance
                return 'high'
            elif position_ratio > 0.05:  # > 5% of balance
                return 'medium'
            else:
                return 'low'
                
        except Exception as e:
            logger.error(f"Error determining risk level: {str(e)}")
            return 'medium'
    
    async def optimize_balance_allocation(self) -> BalanceOptimization:
        """Optimize balance allocation across exchanges and currencies"""
        try:
            # Get current allocations
            allocations = await self.calculate_position_allocations()
            
            # Calculate total values
            total_usd_value = await self._calculate_total_usd_value()
            available_usd = await self._calculate_available_usd()
            allocated_usd = sum(alloc.recommended_position_usd for alloc in allocations.values())
            
            # Calculate optimization score
            optimization_score = self._calculate_optimization_score(allocations, total_usd_value)
            
            # Check if rebalancing is needed
            rebalancing_needed = self._check_rebalancing_needed(allocations)
            
            # Generate recommendations
            recommendations = self._generate_balance_recommendations(allocations, total_usd_value)
            
            optimization = BalanceOptimization(
                total_usd_value=total_usd_value,
                available_usd=available_usd,
                allocated_usd=allocated_usd,
                optimization_score=optimization_score,
                rebalancing_needed=rebalancing_needed,
                recommendations=recommendations
            )
            
            logger.info(f"Balance optimization: Score={optimization_score:.3f}, "
                       f"Total=${total_usd_value:.2f}, Available=${available_usd:.2f}")
            
            return optimization
            
        except Exception as e:
            logger.error(f"Error optimizing balance allocation: {str(e)}")
            return BalanceOptimization(
                total_usd_value=0, available_usd=0, allocated_usd=0,
                optimization_score=0, rebalancing_needed=False, recommendations=[]
            )
    
    def _calculate_optimization_score(self, allocations: Dict[str, PositionAllocation], 
                                    total_usd_value: float) -> float:
        """Calculate optimization score (0-1, higher is better)"""
        try:
            if total_usd_value == 0:
                return 0.0
            
            # Score based on allocation efficiency
            allocated_usd = sum(alloc.recommended_position_usd for alloc in allocations.values())
            allocation_efficiency = allocated_usd / total_usd_value
            
            # Score based on tier distribution
            tier_distribution_score = self._calculate_tier_distribution_score(allocations)
            
            # Score based on risk distribution
            risk_distribution_score = self._calculate_risk_distribution_score(allocations)
            
            # Combine scores
            optimization_score = (
                allocation_efficiency * 0.4 +
                tier_distribution_score * 0.3 +
                risk_distribution_score * 0.3
            )
            
            return min(1.0, max(0.0, optimization_score))
            
        except Exception as e:
            logger.error(f"Error calculating optimization score: {str(e)}")
            return 0.0
    
    def _calculate_tier_distribution_score(self, allocations: Dict[str, PositionAllocation]) -> float:
        """Calculate tier distribution score"""
        try:
            target_allocation = self.balance_config['target_allocation']
            tier_values = {'tier1': 0, 'tier2': 0, 'tier3': 0}
            
            for allocation in allocations.values():
                tier = self._get_symbol_tier(allocation.symbol)
                tier_values[tier] += allocation.recommended_position_usd
            
            total_allocated = sum(tier_values.values())
            if total_allocated == 0:
                return 0.0
            
            # Calculate deviation from target
            total_deviation = 0.0
            for tier, target_percent in target_allocation.items():
                actual_percent = tier_values[tier] / total_allocated
                deviation = abs(actual_percent - target_percent)
                total_deviation += deviation
            
            # Score based on deviation (lower deviation = higher score)
            return max(0.0, 1.0 - total_deviation)
            
        except Exception as e:
            logger.error(f"Error calculating tier distribution score: {str(e)}")
            return 0.0
    
    def _calculate_risk_distribution_score(self, allocations: Dict[str, PositionAllocation]) -> float:
        """Calculate risk distribution score"""
        try:
            risk_counts = {'low': 0, 'medium': 0, 'high': 0}
            
            for allocation in allocations.values():
                risk_counts[allocation.risk_level] += 1
            
            total_allocations = len(allocations)
            if total_allocations == 0:
                return 0.0
            
            # Ideal distribution: 60% low, 30% medium, 10% high risk
            ideal_distribution = {'low': 0.6, 'medium': 0.3, 'high': 0.1}
            
            total_deviation = 0.0
            for risk_level, ideal_percent in ideal_distribution.items():
                actual_percent = risk_counts[risk_level] / total_allocations
                deviation = abs(actual_percent - ideal_percent)
                total_deviation += deviation
            
            return max(0.0, 1.0 - total_deviation)
            
        except Exception as e:
            logger.error(f"Error calculating risk distribution score: {str(e)}")
            return 0.0
    
    def _check_rebalancing_needed(self, allocations: Dict[str, PositionAllocation]) -> bool:
        """Check if rebalancing is needed"""
        try:
            # Check if any allocation is significantly off target
            for allocation in allocations.values():
                if allocation.position_ratio > self.balance_config['rebalance_threshold']:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking rebalancing need: {str(e)}")
            return False
    
    def _generate_balance_recommendations(self, allocations: Dict[str, PositionAllocation], 
                                        total_usd_value: float) -> List[str]:
        """Generate balance optimization recommendations"""
        try:
            recommendations = []
            
            # Check minimum balance
            if total_usd_value < self.balance_config['min_account_balance_usd']:
                recommendations.append(f"Account balance (${total_usd_value:.2f}) below minimum "
                                     f"(${self.balance_config['min_account_balance_usd']}). "
                                     "Consider adding funds to start trading.")
            
            # Check tier distribution
            tier_values = {'tier1': 0, 'tier2': 0, 'tier3': 0}
            for allocation in allocations.values():
                tier = self._get_symbol_tier(allocation.symbol)
                tier_values[tier] += allocation.recommended_position_usd
            
            total_allocated = sum(tier_values.values())
            if total_allocated > 0:
                for tier, target_percent in self.balance_config['target_allocation'].items():
                    actual_percent = tier_values[tier] / total_allocated
                    if actual_percent < target_percent * 0.8:  # 20% below target
                        recommendations.append(f"Increase allocation to {tier} assets "
                                             f"(currently {actual_percent:.1%}, target {target_percent:.1%})")
            
            # Check risk distribution
            high_risk_count = sum(1 for alloc in allocations.values() if alloc.risk_level == 'high')
            if high_risk_count > len(allocations) * 0.2:  # More than 20% high risk
                recommendations.append("Reduce high-risk positions to improve portfolio stability")
            
            # Check reserve amount
            available_usd = sum(alloc.available_quote for alloc in allocations.values() 
                              if alloc.quote_currency in ['USDT', 'USDC', 'BUSD', 'DAI'])
            reserve_percent = (total_usd_value - sum(alloc.recommended_position_usd for alloc in allocations.values())) / total_usd_value
            if reserve_percent < self.balance_config['reserve_percent'] * 0.8:
                recommendations.append(f"Increase reserve amount (currently {reserve_percent:.1%}, "
                                     f"target {self.balance_config['reserve_percent']:.1%})")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating balance recommendations: {str(e)}")
            return ["Error generating recommendations"]
    
    async def scale_positions_with_balance(self, symbol: str, base_position_size: float) -> float:
        """Scale position size based on current balance"""
        try:
            # Get current allocation for symbol
            allocations = await self.calculate_position_allocations()
            allocation = allocations.get(symbol)
            
            if not allocation:
                return min(base_position_size, self.balance_config['min_position_usd'])
            
            # Scale based on available balance and risk level
            if allocation.risk_level == 'high':
                scale_factor = 0.5  # Reduce high-risk positions
            elif allocation.risk_level == 'medium':
                scale_factor = 0.75  # Moderate scaling
            else:
                scale_factor = 1.0  # Full scaling for low-risk positions
            
            # Apply scaling
            scaled_position = base_position_size * scale_factor
            
            # Ensure within bounds
            scaled_position = max(scaled_position, self.balance_config['min_position_usd'])
            scaled_position = min(scaled_position, allocation.recommended_position_usd)
            
            return scaled_position
            
        except Exception as e:
            logger.error(f"Error scaling position for {symbol}: {str(e)}")
            return min(base_position_size, self.balance_config['min_position_usd'])
    
    def track_performance(self, symbol: str, position_size: float, profit: float, success: bool):
        """Track performance for balance optimization"""
        try:
            if symbol not in self.performance_tracking:
                self.performance_tracking[symbol] = {
                    'trades': [], 'total_profit': 0, 'successful_trades': 0
                }
            
            # Record trade
            trade_record = {
                'position_size': position_size,
                'profit': profit,
                'success': success,
                'timestamp': time.time()
            }
            
            self.performance_tracking[symbol]['trades'].append(trade_record)
            self.performance_tracking[symbol]['total_profit'] += profit
            if success:
                self.performance_tracking[symbol]['successful_trades'] += 1
            
            # Keep only recent trades (last 100)
            if len(self.performance_tracking[symbol]['trades']) > 100:
                self.performance_tracking[symbol]['trades'] = self.performance_tracking[symbol]['trades'][-100:]
            
            logger.debug(f"Tracked performance for {symbol}: Position=${position_size:.2f}, "
                        f"Profit=${profit:.2f}, Success={success}")
            
        except Exception as e:
            logger.error(f"Error tracking performance: {str(e)}")
    
    def get_balance_summary(self) -> Dict:
        """Get balance summary and recommendations"""
        try:
            total_usd_value = sum(
                await self._calculate_total_usd_value() for _ in [1]
            )
            
            allocations = self.position_allocations
            optimization = asyncio.run(self.optimize_balance_allocation())
            
            # Calculate performance metrics
            performance_metrics = {}
            for symbol, data in self.performance_tracking.items():
                if data['trades']:
                    success_rate = data['successful_trades'] / len(data['trades'])
                    avg_profit = data['total_profit'] / len(data['trades'])
                    
                    performance_metrics[symbol] = {
                        'success_rate': success_rate,
                        'avg_profit': avg_profit,
                        'total_trades': len(data['trades']),
                        'total_profit': data['total_profit']
                    }
            
            summary = {
                'total_usd_value': total_usd_value,
                'available_usd': optimization.available_usd,
                'allocated_usd': optimization.allocated_usd,
                'optimization_score': optimization.optimization_score,
                'rebalancing_needed': optimization.rebalancing_needed,
                'recommendations': optimization.recommendations,
                'position_allocations': {
                    symbol: {
                        'recommended_position_usd': alloc.recommended_position_usd,
                        'max_position_usd': alloc.max_position_usd,
                        'position_ratio': alloc.position_ratio,
                        'risk_level': alloc.risk_level
                    } for symbol, alloc in allocations.items()
                },
                'performance_metrics': performance_metrics
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting balance summary: {str(e)}")
            return {}
