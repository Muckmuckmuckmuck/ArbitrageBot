import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class MarketConditions:
    """Data class for market conditions"""
    symbol: str
    volatility: float
    volume: float
    spread: float
    order_book_depth: float
    competition_level: float
    timestamp: float
    hour_of_day: int
    day_of_week: int

@dataclass
class SpreadThreshold:
    """Data class for spread threshold"""
    symbol: str
    base_threshold: float
    dynamic_threshold: float
    adjustment_factors: Dict[str, float]
    timestamp: float

class DynamicSpreadOptimizer:
    """Dynamic spread threshold optimization system"""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.market_conditions_history = {}
        self.spread_thresholds = {}
        self.performance_tracking = {}
        
        # Base thresholds by symbol
        self.base_thresholds = {
            # Tier 1 assets - lower thresholds due to high liquidity
            'XRP/USDT': 0.6, 'XLM/USDT': 0.6, 'SOL/USDT': 0.6, 'BNB/USDT': 0.5,
            'USDC/USDT': 0.2, 'USDT/USDC': 0.2, 'DAI/USDT': 0.3, 'BUSD/USDT': 0.2,
            'UNI/USDT': 0.6, 'LINK/USDT': 0.6, 'ADA/USDT': 0.5, 'DOT/USDT': 0.6,
            'AVAX/USDT': 0.6, 'TON/USDT': 0.8, 'MATIC/USDT': 0.6, 'EOS/USDT': 0.6,
            'TRX/USDT': 0.6,
            
            # Tier 2 assets - medium thresholds
            'XTZ/USDT': 0.7, 'MKR/USDT': 0.8, 'FIL/USDT': 0.8, 'ATOM/USDT': 0.7,
            'AAVE/USDT': 0.8, 'COMP/USDT': 0.8, 'CRV/USDT': 0.8, 'SNX/USDT': 0.8,
            'YFI/USDT': 0.9, '1INCH/USDT': 0.8,
            
            # Tier 3 assets - higher thresholds
            'LTC/USDT': 0.6, 'DOGE/USDT': 0.8, 'VET/USDT': 0.7, 'BCH/USDT': 0.7, 'XMR/USDT': 0.8,
        }
        
        # Adjustment factors
        self.adjustment_factors = {
            'volatility': {
                'low': 0.0,      # < 2%
                'medium': 0.1,   # 2-5%
                'high': 0.3,     # 5-10%
                'extreme': 0.5   # > 10%
            },
            'volume': {
                'very_low': 0.3,  # < 100K
                'low': 0.2,       # 100K-500K
                'medium': 0.0,    # 500K-2M
                'high': -0.1,     # 2M-10M
                'very_high': -0.2 # > 10M
            },
            'competition': {
                'low': -0.1,      # < 0.3
                'medium': 0.0,    # 0.3-0.7
                'high': 0.2,      # 0.7-0.9
                'very_high': 0.4  # > 0.9
            },
            'time_of_day': {
                'low_activity': -0.1,  # 0-6 AM
                'medium_activity': 0.0, # 6-12 PM
                'high_activity': 0.1,   # 12-18 PM
                'peak_activity': 0.2    # 18-24 PM
            },
            'day_of_week': {
                'weekday': 0.0,
                'weekend': -0.05
            }
        }
        
        # Performance tracking
        self.performance_history = {}
        self.threshold_effectiveness = {}
        
    async def analyze_market_conditions(self, symbol: str) -> MarketConditions:
        """Analyze current market conditions for a symbol"""
        try:
            # Get current time
            current_time = time.time()
            dt = datetime.fromtimestamp(current_time)
            
            # Get price data from both exchanges
            binance_exchange = self.exchange_manager.get_exchange('binance')
            kraken_exchange = self.exchange_manager.get_exchange('kraken')
            
            binance_ticker = await binance_exchange.get_ticker(symbol)
            kraken_ticker = await kraken_exchange.get_ticker(symbol)
            
            if not binance_ticker or not kraken_ticker:
                return None
            
            # Calculate spread
            binance_price = binance_ticker['last']
            kraken_price = kraken_ticker['last']
            spread = abs(binance_price - kraken_price) / ((binance_price + kraken_price) / 2) * 100
            
            # Get volume data
            binance_volume = binance_ticker.get('quoteVolume', 0) / binance_price
            kraken_volume = kraken_ticker.get('quoteVolume', 0) / kraken_price
            total_volume = (binance_volume + kraken_volume) / 2
            
            # Calculate volatility (simplified - using price difference as proxy)
            volatility = spread * 2  # Rough estimate
            
            # Get order book depth
            try:
                binance_orderbook = await binance_exchange.get_orderbook(symbol, 10)
                kraken_orderbook = await kraken_exchange.get_orderbook(symbol, 10)
                
                binance_depth = sum(price * qty for price, qty in binance_orderbook.get('asks', [])[:5])
                kraken_depth = sum(price * qty for price, qty in kraken_orderbook.get('asks', [])[:5])
                order_book_depth = (binance_depth + kraken_depth) / 2
            except:
                order_book_depth = 100000  # Default value
            
            # Estimate competition level (simplified)
            competition_level = await self._estimate_competition_level(symbol)
            
            conditions = MarketConditions(
                symbol=symbol,
                volatility=volatility,
                volume=total_volume,
                spread=spread,
                order_book_depth=order_book_depth,
                competition_level=competition_level,
                timestamp=current_time,
                hour_of_day=dt.hour,
                day_of_week=dt.weekday()
            )
            
            # Store in history
            if symbol not in self.market_conditions_history:
                self.market_conditions_history[symbol] = []
            
            self.market_conditions_history[symbol].append(conditions)
            
            # Keep only recent history (last 1000 records)
            if len(self.market_conditions_history[symbol]) > 1000:
                self.market_conditions_history[symbol] = self.market_conditions_history[symbol][-1000:]
            
            return conditions
            
        except Exception as e:
            logger.error(f"Error analyzing market conditions for {symbol}: {str(e)}")
            return None
    
    async def _estimate_competition_level(self, symbol: str) -> float:
        """Estimate competition level from recent trading activity"""
        try:
            if symbol not in self.market_conditions_history:
                return 0.5  # Default medium competition
            
            recent_conditions = self.market_conditions_history[symbol][-50:]  # Last 50 records
            if not recent_conditions:
                return 0.5
            
            # Analyze spread patterns to detect bot activity
            spreads = [c.spread for c in recent_conditions]
            
            # Look for patterns indicating bot competition
            rapid_changes = sum(1 for i in range(1, len(spreads)) 
                              if abs(spreads[i] - spreads[i-1]) > 0.5) / len(spreads)
            
            # Look for consistent small spreads (indicating active arbitrage)
            small_spreads = sum(1 for s in spreads if s < 0.5) / len(spreads)
            
            # Calculate competition score
            competition_score = min(1.0, rapid_changes * 2 + small_spreads * 1.5)
            
            return competition_score
            
        except Exception as e:
            logger.error(f"Error estimating competition level: {str(e)}")
            return 0.5
    
    def calculate_dynamic_threshold(self, conditions: MarketConditions) -> SpreadThreshold:
        """Calculate dynamic spread threshold based on market conditions"""
        try:
            symbol = conditions.symbol
            base_threshold = self.base_thresholds.get(symbol, 0.8)
            
            # Calculate adjustments
            adjustments = {}
            
            # Volatility adjustment
            volatility = conditions.volatility
            if volatility < 2:
                adjustments['volatility'] = self.adjustment_factors['volatility']['low']
            elif volatility < 5:
                adjustments['volatility'] = self.adjustment_factors['volatility']['medium']
            elif volatility < 10:
                adjustments['volatility'] = self.adjustment_factors['volatility']['high']
            else:
                adjustments['volatility'] = self.adjustment_factors['volatility']['extreme']
            
            # Volume adjustment
            volume = conditions.volume
            if volume < 100000:
                adjustments['volume'] = self.adjustment_factors['volume']['very_low']
            elif volume < 500000:
                adjustments['volume'] = self.adjustment_factors['volume']['low']
            elif volume < 2000000:
                adjustments['volume'] = self.adjustment_factors['volume']['medium']
            elif volume < 10000000:
                adjustments['volume'] = self.adjustment_factors['volume']['high']
            else:
                adjustments['volume'] = self.adjustment_factors['volume']['very_high']
            
            # Competition adjustment
            competition = conditions.competition_level
            if competition < 0.3:
                adjustments['competition'] = self.adjustment_factors['competition']['low']
            elif competition < 0.7:
                adjustments['competition'] = self.adjustment_factors['competition']['medium']
            elif competition < 0.9:
                adjustments['competition'] = self.adjustment_factors['competition']['high']
            else:
                adjustments['competition'] = self.adjustment_factors['competition']['very_high']
            
            # Time of day adjustment
            hour = conditions.hour_of_day
            if 0 <= hour < 6:
                adjustments['time_of_day'] = self.adjustment_factors['time_of_day']['low_activity']
            elif 6 <= hour < 12:
                adjustments['time_of_day'] = self.adjustment_factors['time_of_day']['medium_activity']
            elif 12 <= hour < 18:
                adjustments['time_of_day'] = self.adjustment_factors['time_of_day']['high_activity']
            else:
                adjustments['time_of_day'] = self.adjustment_factors['time_of_day']['peak_activity']
            
            # Day of week adjustment
            if conditions.day_of_week < 5:  # Weekday
                adjustments['day_of_week'] = self.adjustment_factors['day_of_week']['weekday']
            else:  # Weekend
                adjustments['day_of_week'] = self.adjustment_factors['day_of_week']['weekend']
            
            # Calculate total adjustment
            total_adjustment = sum(adjustments.values())
            
            # Apply adjustment to base threshold
            dynamic_threshold = base_threshold + (base_threshold * total_adjustment)
            
            # Ensure minimum and maximum bounds
            dynamic_threshold = max(0.3, min(dynamic_threshold, 2.0))
            
            threshold = SpreadThreshold(
                symbol=symbol,
                base_threshold=base_threshold,
                dynamic_threshold=dynamic_threshold,
                adjustment_factors=adjustments,
                timestamp=time.time()
            )
            
            # Store threshold
            self.spread_thresholds[symbol] = threshold
            
            logger.info(f"Dynamic threshold for {symbol}: {dynamic_threshold:.3f}% "
                       f"(base: {base_threshold:.3f}%, adjustment: {total_adjustment:+.2f})")
            
            return threshold
            
        except Exception as e:
            logger.error(f"Error calculating dynamic threshold: {str(e)}")
            # Return base threshold as fallback
            return SpreadThreshold(
                symbol=conditions.symbol,
                base_threshold=self.base_thresholds.get(conditions.symbol, 0.8),
                dynamic_threshold=self.base_thresholds.get(conditions.symbol, 0.8),
                adjustment_factors={},
                timestamp=time.time()
            )
    
    async def get_optimal_threshold(self, symbol: str) -> float:
        """Get the optimal spread threshold for a symbol"""
        try:
            # Analyze current market conditions
            conditions = await self.analyze_market_conditions(symbol)
            if not conditions:
                return self.base_thresholds.get(symbol, 0.8)
            
            # Calculate dynamic threshold
            threshold = self.calculate_dynamic_threshold(conditions)
            
            return threshold.dynamic_threshold
            
        except Exception as e:
            logger.error(f"Error getting optimal threshold for {symbol}: {str(e)}")
            return self.base_thresholds.get(symbol, 0.8)
    
    def track_threshold_performance(self, symbol: str, threshold_used: float, 
                                  trade_profit: float, trade_success: bool):
        """Track performance of different thresholds"""
        try:
            if symbol not in self.performance_history:
                self.performance_history[symbol] = []
            
            performance_record = {
                'threshold': threshold_used,
                'profit': trade_profit,
                'success': trade_success,
                'timestamp': time.time()
            }
            
            self.performance_history[symbol].append(performance_record)
            
            # Keep only recent history (last 1000 records)
            if len(self.performance_history[symbol]) > 1000:
                self.performance_history[symbol] = self.performance_history[symbol][-1000:]
            
            # Update threshold effectiveness
            self._update_threshold_effectiveness(symbol)
            
        except Exception as e:
            logger.error(f"Error tracking threshold performance: {str(e)}")
    
    def _update_threshold_effectiveness(self, symbol: str):
        """Update threshold effectiveness based on performance history"""
        try:
            if symbol not in self.performance_history:
                return
            
            history = self.performance_history[symbol]
            if len(history) < 10:
                return
            
            # Group by threshold ranges
            threshold_ranges = {
                'low': (0.0, 0.6),
                'medium': (0.6, 1.0),
                'high': (1.0, 1.5),
                'very_high': (1.5, 2.0)
            }
            
            effectiveness = {}
            
            for range_name, (min_thresh, max_thresh) in threshold_ranges.items():
                range_records = [
                    record for record in history
                    if min_thresh <= record['threshold'] < max_thresh
                ]
                
                if range_records:
                    success_rate = sum(1 for r in range_records if r['success']) / len(range_records)
                    avg_profit = sum(r['profit'] for r in range_records) / len(range_records)
                    
                    effectiveness[range_name] = {
                        'success_rate': success_rate,
                        'avg_profit': avg_profit,
                        'sample_count': len(range_records)
                    }
            
            self.threshold_effectiveness[symbol] = effectiveness
            
        except Exception as e:
            logger.error(f"Error updating threshold effectiveness: {str(e)}")
    
    def get_threshold_effectiveness(self, symbol: str) -> Dict:
        """Get threshold effectiveness analysis"""
        return self.threshold_effectiveness.get(symbol, {})
    
    def get_market_conditions_summary(self, symbol: str, hours: int = 24) -> Dict:
        """Get market conditions summary for a symbol"""
        try:
            if symbol not in self.market_conditions_history:
                return {}
            
            current_time = time.time()
            cutoff_time = current_time - (hours * 3600)
            
            recent_conditions = [
                c for c in self.market_conditions_history[symbol]
                if c.timestamp >= cutoff_time
            ]
            
            if not recent_conditions:
                return {}
            
            # Calculate statistics
            volatilities = [c.volatility for c in recent_conditions]
            volumes = [c.volume for c in recent_conditions]
            spreads = [c.spread for c in recent_conditions]
            competition_levels = [c.competition_level for c in recent_conditions]
            
            summary = {
                'symbol': symbol,
                'time_period_hours': hours,
                'sample_count': len(recent_conditions),
                'avg_volatility': sum(volatilities) / len(volatilities),
                'avg_volume': sum(volumes) / len(volumes),
                'avg_spread': sum(spreads) / len(spreads),
                'avg_competition': sum(competition_levels) / len(competition_levels),
                'min_spread': min(spreads),
                'max_spread': max(spreads),
                'current_threshold': self.spread_thresholds.get(symbol, {}).get('dynamic_threshold', 0.8)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting market conditions summary: {str(e)}")
            return {}
    
    def get_optimization_recommendations(self, symbol: str) -> List[str]:
        """Get optimization recommendations for a symbol"""
        try:
            recommendations = []
            
            # Get current market conditions
            current_time = time.time()
            if symbol in self.market_conditions_history:
                recent_conditions = self.market_conditions_history[symbol][-10:]
                if recent_conditions:
                    latest = recent_conditions[-1]
                    
                    # Volatility recommendations
                    if latest.volatility > 8:
                        recommendations.append("High volatility detected - consider increasing threshold by 0.2%")
                    elif latest.volatility < 2:
                        recommendations.append("Low volatility detected - consider decreasing threshold by 0.1%")
                    
                    # Volume recommendations
                    if latest.volume < 500000:
                        recommendations.append("Low volume detected - consider increasing threshold by 0.3%")
                    elif latest.volume > 5000000:
                        recommendations.append("High volume detected - consider decreasing threshold by 0.1%")
                    
                    # Competition recommendations
                    if latest.competition_level > 0.8:
                        recommendations.append("High competition detected - consider increasing threshold by 0.2%")
                    elif latest.competition_level < 0.3:
                        recommendations.append("Low competition detected - consider decreasing threshold by 0.1%")
            
            # Time-based recommendations
            current_hour = datetime.now().hour
            if current_hour in [0, 1, 2, 3, 4, 5]:
                recommendations.append("Low activity hours - consider decreasing threshold by 0.1%")
            elif current_hour in [13, 14, 15, 16, 17]:
                recommendations.append("High activity hours - consider increasing threshold by 0.1%")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting optimization recommendations: {str(e)}")
            return []
    
    async def optimize_all_symbols(self, symbols: List[str]) -> Dict[str, float]:
        """Optimize thresholds for all symbols"""
        try:
            optimized_thresholds = {}
            
            for symbol in symbols:
                threshold = await self.get_optimal_threshold(symbol)
                optimized_thresholds[symbol] = threshold
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)
            
            logger.info(f"Optimized thresholds for {len(symbols)} symbols")
            return optimized_thresholds
            
        except Exception as e:
            logger.error(f"Error optimizing all symbols: {str(e)}")
            return {}

