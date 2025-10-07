import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class DynamicSpreadConfig:
    """Configuration for dynamic spread management"""
    symbol: str
    base_min_spread: float
    current_min_spread: float
    volatility_multiplier: float
    volume_multiplier: float
    competition_multiplier: float
    time_multiplier: float
    market_conditions: Dict[str, float]

class DynamicSpreadManager:
    """Dynamic spread threshold management based on market conditions"""
    
    def __init__(self):
        self.spread_history = {}
        self.market_conditions = {}
        self.competition_levels = {}
        self.volatility_cache = {}
        
    def calculate_dynamic_spread(self, symbol: str, market_data: Dict) -> DynamicSpreadConfig:
        """Calculate dynamic minimum spread based on current market conditions"""
        try:
            # Get base configuration
            base_config = Config.TRANSFER_SPEEDS.get(symbol, {})
            base_min_spread = base_config.get('min_spread', Config.MIN_SPREAD_PERCENT)
            
            # Get current market conditions
            volatility = market_data.get('volatility', 0.02)
            volume_ratio = market_data.get('volume_ratio', 1.0)
            competition_level = market_data.get('competition_level', 0.5)
            time_of_day = market_data.get('time_of_day', 12)  # 0-23 hours
            
            # Calculate multipliers
            volatility_multiplier = self._calculate_volatility_multiplier(volatility)
            volume_multiplier = self._calculate_volume_multiplier(volume_ratio)
            competition_multiplier = self._calculate_competition_multiplier(competition_level)
            time_multiplier = self._calculate_time_multiplier(time_of_day)
            
            # Calculate dynamic spread
            dynamic_spread = base_min_spread * volatility_multiplier * volume_multiplier * competition_multiplier * time_multiplier
            
            # Apply bounds
            min_bound = base_min_spread * 0.5  # Minimum 50% of base
            max_bound = base_min_spread * 3.0  # Maximum 300% of base
            dynamic_spread = max(min(dynamic_spread, max_bound), min_bound)
            
            return DynamicSpreadConfig(
                symbol=symbol,
                base_min_spread=base_min_spread,
                current_min_spread=dynamic_spread,
                volatility_multiplier=volatility_multiplier,
                volume_multiplier=volume_multiplier,
                competition_multiplier=competition_multiplier,
                time_multiplier=time_multiplier,
                market_conditions={
                    'volatility': volatility,
                    'volume_ratio': volume_ratio,
                    'competition_level': competition_level,
                    'time_of_day': time_of_day
                }
            )
            
        except Exception as e:
            logger.error(f"Error calculating dynamic spread for {symbol}: {str(e)}")
            return self._get_default_spread_config(symbol)
    
    def _calculate_volatility_multiplier(self, volatility: float) -> float:
        """Calculate volatility-based multiplier for spread threshold"""
        try:
            # Higher volatility = higher spread threshold
            # Low volatility (0-2%): 0.8x multiplier
            # Medium volatility (2-5%): 1.0x multiplier
            # High volatility (5-10%): 1.5x multiplier
            # Very high volatility (10%+): 2.0x multiplier
            
            if volatility <= 0.02:
                return 0.8
            elif volatility <= 0.05:
                return 1.0
            elif volatility <= 0.10:
                return 1.5
            else:
                return 2.0
                
        except Exception as e:
            logger.error(f"Error calculating volatility multiplier: {str(e)}")
            return 1.0
    
    def _calculate_volume_multiplier(self, volume_ratio: float) -> float:
        """Calculate volume-based multiplier for spread threshold"""
        try:
            # Higher volume = lower spread threshold (more opportunities)
            # Lower volume = higher spread threshold (fewer opportunities)
            
            if volume_ratio >= 2.0:  # Very high volume
                return 0.7
            elif volume_ratio >= 1.5:  # High volume
                return 0.8
            elif volume_ratio >= 1.0:  # Normal volume
                return 1.0
            elif volume_ratio >= 0.7:  # Low volume
                return 1.2
            else:  # Very low volume
                return 1.5
                
        except Exception as e:
            logger.error(f"Error calculating volume multiplier: {str(e)}")
            return 1.0
    
    def _calculate_competition_multiplier(self, competition_level: float) -> float:
        """Calculate competition-based multiplier for spread threshold"""
        try:
            # Higher competition = higher spread threshold
            # Lower competition = lower spread threshold
            
            if competition_level >= 0.8:  # Very high competition
                return 1.8
            elif competition_level >= 0.6:  # High competition
                return 1.4
            elif competition_level >= 0.4:  # Medium competition
                return 1.0
            elif competition_level >= 0.2:  # Low competition
                return 0.8
            else:  # Very low competition
                return 0.6
                
        except Exception as e:
            logger.error(f"Error calculating competition multiplier: {str(e)}")
            return 1.0
    
    def _calculate_time_multiplier(self, time_of_day: int) -> float:
        """Calculate time-based multiplier for spread threshold"""
        try:
            # Market hours: 9 AM - 4 PM EST (14:00 - 21:00 UTC)
            # Asian hours: 9 PM - 6 AM EST (02:00 - 11:00 UTC)
            # European hours: 3 AM - 12 PM EST (08:00 - 17:00 UTC)
            
            # Convert to UTC (assuming input is in UTC)
            utc_hour = time_of_day
            
            # Overlap periods (more activity = lower spread threshold)
            if (8 <= utc_hour <= 11) or (14 <= utc_hour <= 17):  # European overlap
                return 0.8
            elif (2 <= utc_hour <= 6) or (21 <= utc_hour <= 23):  # Asian hours
                return 1.2
            else:  # Quiet hours
                return 1.5
                
        except Exception as e:
            logger.error(f"Error calculating time multiplier: {str(e)}")
            return 1.0
    
    def _get_default_spread_config(self, symbol: str) -> DynamicSpreadConfig:
        """Get default spread configuration when calculation fails"""
        base_config = Config.TRANSFER_SPEEDS.get(symbol, {})
        base_min_spread = base_config.get('min_spread', Config.MIN_SPREAD_PERCENT)
        
        return DynamicSpreadConfig(
            symbol=symbol,
            base_min_spread=base_min_spread,
            current_min_spread=base_min_spread,
            volatility_multiplier=1.0,
            volume_multiplier=1.0,
            competition_multiplier=1.0,
            time_multiplier=1.0,
            market_conditions={
                'volatility': 0.02,
                'volume_ratio': 1.0,
                'competition_level': 0.5,
                'time_of_day': 12
            }
        )
    
    def update_spread_history(self, symbol: str, spread_data: Dict):
        """Update spread history for trend analysis"""
        try:
            if symbol not in self.spread_history:
                self.spread_history[symbol] = []
            
            self.spread_history[symbol].append({
                'timestamp': spread_data.get('timestamp', 0),
                'spread': spread_data.get('spread', 0),
                'min_threshold': spread_data.get('min_threshold', 0),
                'market_conditions': spread_data.get('market_conditions', {})
            })
            
            # Keep only recent history (last 100 entries)
            if len(self.spread_history[symbol]) > 100:
                self.spread_history[symbol] = self.spread_history[symbol][-100:]
                
        except Exception as e:
            logger.error(f"Error updating spread history for {symbol}: {str(e)}")
    
    def analyze_spread_trends(self, symbol: str) -> Dict:
        """Analyze spread trends for a symbol"""
        try:
            if symbol not in self.spread_history or len(self.spread_history[symbol]) < 10:
                return {'trend': 'stable', 'volatility': 0.0, 'efficiency': 0.5}
            
            history = self.spread_history[symbol]
            recent_spreads = [h['spread'] for h in history[-20:]]  # Last 20 entries
            
            # Calculate trend
            if len(recent_spreads) >= 2:
                trend_slope = np.polyfit(range(len(recent_spreads)), recent_spreads, 1)[0]
                if trend_slope > 0.001:
                    trend = 'increasing'
                elif trend_slope < -0.001:
                    trend = 'decreasing'
                else:
                    trend = 'stable'
            else:
                trend = 'stable'
            
            # Calculate volatility
            spread_volatility = np.std(recent_spreads) / np.mean(recent_spreads) if np.mean(recent_spreads) > 0 else 0
            
            # Calculate efficiency (how often spreads exceed threshold)
            threshold_exceeded = sum(1 for h in history[-20:] if h['spread'] > h['min_threshold'])
            efficiency = threshold_exceeded / min(len(history[-20:]), 20) if len(history[-20:]) > 0 else 0.5
            
            return {
                'trend': trend,
                'volatility': spread_volatility,
                'efficiency': efficiency,
                'avg_spread': np.mean(recent_spreads),
                'min_spread': np.min(recent_spreads),
                'max_spread': np.max(recent_spreads)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing spread trends for {symbol}: {str(e)}")
            return {'trend': 'stable', 'volatility': 0.0, 'efficiency': 0.5}
    
    def get_optimal_spread_threshold(self, symbol: str, current_market_data: Dict) -> float:
        """Get optimal spread threshold for current market conditions"""
        try:
            # Calculate dynamic spread
            spread_config = self.calculate_dynamic_spread(symbol, current_market_data)
            
            # Get trend analysis
            trend_analysis = self.analyze_spread_trends(symbol)
            
            # Adjust based on trend
            trend_adjustment = 1.0
            if trend_analysis['trend'] == 'increasing':
                trend_adjustment = 0.9  # Lower threshold for increasing spreads
            elif trend_analysis['trend'] == 'decreasing':
                trend_adjustment = 1.1  # Higher threshold for decreasing spreads
            
            # Adjust based on efficiency
            efficiency_adjustment = 1.0
            if trend_analysis['efficiency'] > 0.8:
                efficiency_adjustment = 1.1  # Higher threshold if too many opportunities
            elif trend_analysis['efficiency'] < 0.3:
                efficiency_adjustment = 0.9  # Lower threshold if too few opportunities
            
            # Calculate final threshold
            final_threshold = spread_config.current_min_spread * trend_adjustment * efficiency_adjustment
            
            # Apply bounds
            min_bound = spread_config.base_min_spread * 0.3
            max_bound = spread_config.base_min_spread * 5.0
            final_threshold = max(min(final_threshold, max_bound), min_bound)
            
            return final_threshold
            
        except Exception as e:
            logger.error(f"Error getting optimal spread threshold for {symbol}: {str(e)}")
            return Config.MIN_SPREAD_PERCENT
    
    def get_spread_summary(self) -> Dict:
        """Get spread analysis summary for all symbols"""
        try:
            summary = {}
            
            for symbol in Config.CURRENCY_PAIRS:
                trend_analysis = self.analyze_spread_trends(symbol)
                
                summary[symbol] = {
                    'trend': trend_analysis['trend'],
                    'volatility': trend_analysis['volatility'],
                    'efficiency': trend_analysis['efficiency'],
                    'avg_spread': trend_analysis.get('avg_spread', 0),
                    'min_spread': trend_analysis.get('min_spread', 0),
                    'max_spread': trend_analysis.get('max_spread', 0),
                    'history_count': len(self.spread_history.get(symbol, []))
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting spread summary: {str(e)}")
            return {}

