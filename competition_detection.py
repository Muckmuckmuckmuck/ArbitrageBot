import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class CompetitionAnalysis:
    """Data class for competition analysis results"""
    symbol: str
    competition_level: float  # 0-1, where 1 is high competition
    bot_count_estimate: int
    response_time_avg: float
    spread_closure_rate: float
    opportunity_frequency: float
    market_efficiency: float
    competition_patterns: Dict[str, float]

class CompetitionDetector:
    """Detect and analyze competition from other arbitrage bots"""
    
    def __init__(self):
        self.opportunity_tracking = {}
        self.spread_history = {}
        self.response_times = {}
        self.competition_patterns = {}
        
    def analyze_competition(self, symbol: str, current_opportunity: Dict) -> CompetitionAnalysis:
        """Analyze competition level for a given symbol"""
        try:
            # Track opportunity
            self._track_opportunity(symbol, current_opportunity)
            
            # Calculate competition metrics
            competition_level = self._calculate_competition_level(symbol)
            bot_count_estimate = self._estimate_bot_count(symbol)
            response_time_avg = self._calculate_avg_response_time(symbol)
            spread_closure_rate = self._calculate_spread_closure_rate(symbol)
            opportunity_frequency = self._calculate_opportunity_frequency(symbol)
            market_efficiency = self._calculate_market_efficiency(symbol)
            competition_patterns = self._analyze_competition_patterns(symbol)
            
            return CompetitionAnalysis(
                symbol=symbol,
                competition_level=competition_level,
                bot_count_estimate=bot_count_estimate,
                response_time_avg=response_time_avg,
                spread_closure_rate=spread_closure_rate,
                opportunity_frequency=opportunity_frequency,
                market_efficiency=market_efficiency,
                competition_patterns=competition_patterns
            )
            
        except Exception as e:
            logger.error(f"Error analyzing competition for {symbol}: {str(e)}")
            return self._get_default_competition_analysis(symbol)
    
    def _track_opportunity(self, symbol: str, opportunity: Dict):
        """Track arbitrage opportunities for competition analysis"""
        try:
            if symbol not in self.opportunity_tracking:
                self.opportunity_tracking[symbol] = []
            
            self.opportunity_tracking[symbol].append({
                'timestamp': time.time(),
                'spread': opportunity.get('spread_percent', 0),
                'buy_exchange': opportunity.get('buy_exchange', ''),
                'sell_exchange': opportunity.get('sell_exchange', ''),
                'price1': opportunity.get('buy_price', 0),
                'price2': opportunity.get('sell_price', 0)
            })
            
            # Keep only recent opportunities (last 100)
            if len(self.opportunity_tracking[symbol]) > 100:
                self.opportunity_tracking[symbol] = self.opportunity_tracking[symbol][-100:]
                
        except Exception as e:
            logger.error(f"Error tracking opportunity for {symbol}: {str(e)}")
    
    def _calculate_competition_level(self, symbol: str) -> float:
        """Calculate overall competition level (0-1)"""
        try:
            if symbol not in self.opportunity_tracking or len(self.opportunity_tracking[symbol]) < 5:
                return 0.5  # Default medium competition
            
            opportunities = self.opportunity_tracking[symbol]
            recent_opportunities = opportunities[-20:]  # Last 20 opportunities
            
            # Calculate metrics
            spread_closure_rate = self._calculate_spread_closure_rate(symbol)
            response_time_avg = self._calculate_avg_response_time(symbol)
            opportunity_frequency = self._calculate_opportunity_frequency(symbol)
            
            # Competition indicators
            # 1. High spread closure rate = high competition
            closure_score = min(spread_closure_rate * 2, 1.0)
            
            # 2. Fast response times = high competition
            response_score = min(response_time_avg / 10, 1.0)  # Normalize to 0-1
            
            # 3. High opportunity frequency = high competition
            frequency_score = min(opportunity_frequency / 10, 1.0)  # Normalize to 0-1
            
            # 4. Consistent spread patterns = high competition
            consistency_score = self._calculate_spread_consistency(symbol)
            
            # Weighted average
            competition_level = (
                closure_score * 0.3 +
                response_score * 0.2 +
                frequency_score * 0.2 +
                consistency_score * 0.3
            )
            
            return min(max(competition_level, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating competition level for {symbol}: {str(e)}")
            return 0.5
    
    def _estimate_bot_count(self, symbol: str) -> int:
        """Estimate number of competing bots"""
        try:
            if symbol not in self.opportunity_tracking or len(self.opportunity_tracking[symbol]) < 10:
                return 2  # Default estimate
            
            opportunities = self.opportunity_tracking[symbol]
            recent_opportunities = opportunities[-30:]  # Last 30 opportunities
            
            # Analyze patterns to estimate bot count
            # 1. Response time clustering
            response_times = []
            for i in range(1, len(recent_opportunities)):
                time_diff = recent_opportunities[i]['timestamp'] - recent_opportunities[i-1]['timestamp']
                response_times.append(time_diff)
            
            # 2. Spread pattern analysis
            spreads = [opp['spread'] for opp in recent_opportunities]
            spread_variance = self._calculate_variance(spreads)
            
            # 3. Exchange preference patterns
            exchange_preferences = self._analyze_exchange_preferences(symbol)
            
            # Estimate based on patterns
            if spread_variance < 0.001:  # Very consistent spreads
                bot_count = 5
            elif spread_variance < 0.005:  # Moderately consistent
                bot_count = 3
            else:  # Variable spreads
                bot_count = 2
            
            # Adjust based on response times
            avg_response_time = sum(response_times) / len(response_times) if response_times else 10
            if avg_response_time < 5:  # Very fast responses
                bot_count += 2
            elif avg_response_time < 15:  # Fast responses
                bot_count += 1
            
            return min(max(bot_count, 1), 10)  # Between 1 and 10 bots
            
        except Exception as e:
            logger.error(f"Error estimating bot count for {symbol}: {str(e)}")
            return 2
    
    def _calculate_avg_response_time(self, symbol: str) -> float:
        """Calculate average response time to opportunities"""
        try:
            if symbol not in self.opportunity_tracking or len(self.opportunity_tracking[symbol]) < 2:
                return 10.0  # Default 10 seconds
            
            opportunities = self.opportunity_tracking[symbol]
            response_times = []
            
            for i in range(1, len(opportunities)):
                time_diff = opportunities[i]['timestamp'] - opportunities[i-1]['timestamp']
                if time_diff < 300:  # Only consider opportunities within 5 minutes
                    response_times.append(time_diff)
            
            if not response_times:
                return 10.0
            
            return sum(response_times) / len(response_times)
            
        except Exception as e:
            logger.error(f"Error calculating avg response time for {symbol}: {str(e)}")
            return 10.0
    
    def _calculate_spread_closure_rate(self, symbol: str) -> float:
        """Calculate how quickly spreads close (indicates competition)"""
        try:
            if symbol not in self.opportunity_tracking or len(self.opportunity_tracking[symbol]) < 5:
                return 0.3  # Default moderate closure rate
            
            opportunities = self.opportunity_tracking[symbol]
            recent_opportunities = opportunities[-20:]  # Last 20 opportunities
            
            closure_count = 0
            total_opportunities = len(recent_opportunities)
            
            for i in range(1, len(recent_opportunities)):
                current_spread = recent_opportunities[i]['spread']
                previous_spread = recent_opportunities[i-1]['spread']
                time_diff = recent_opportunities[i]['timestamp'] - recent_opportunities[i-1]['timestamp']
                
                # If spread decreases significantly within short time, it's likely closed by competition
                if time_diff < 60 and current_spread < previous_spread * 0.5:
                    closure_count += 1
            
            return closure_count / total_opportunities if total_opportunities > 0 else 0.3
            
        except Exception as e:
            logger.error(f"Error calculating spread closure rate for {symbol}: {str(e)}")
            return 0.3
    
    def _calculate_opportunity_frequency(self, symbol: str) -> float:
        """Calculate frequency of arbitrage opportunities"""
        try:
            if symbol not in self.opportunity_tracking or len(self.opportunity_tracking[symbol]) < 2:
                return 5.0  # Default 5 opportunities per hour
            
            opportunities = self.opportunity_tracking[symbol]
            
            if len(opportunities) < 2:
                return 5.0
            
            # Calculate opportunities per hour
            time_span = opportunities[-1]['timestamp'] - opportunities[0]['timestamp']
            if time_span == 0:
                return 5.0
            
            opportunities_per_second = len(opportunities) / time_span
            opportunities_per_hour = opportunities_per_second * 3600
            
            return opportunities_per_hour
            
        except Exception as e:
            logger.error(f"Error calculating opportunity frequency for {symbol}: {str(e)}")
            return 5.0
    
    def _calculate_market_efficiency(self, symbol: str) -> float:
        """Calculate market efficiency (how quickly spreads close)"""
        try:
            if symbol not in self.opportunity_tracking or len(self.opportunity_tracking[symbol]) < 5:
                return 0.5  # Default medium efficiency
            
            opportunities = self.opportunity_tracking[symbol]
            recent_opportunities = opportunities[-20:]  # Last 20 opportunities
            
            # Calculate average time for spreads to close
            closure_times = []
            for i in range(1, len(recent_opportunities)):
                current_spread = recent_opportunities[i]['spread']
                previous_spread = recent_opportunities[i-1]['spread']
                time_diff = recent_opportunities[i]['timestamp'] - recent_opportunities[i-1]['timestamp']
                
                # If spread decreases significantly, record closure time
                if current_spread < previous_spread * 0.7:
                    closure_times.append(time_diff)
            
            if not closure_times:
                return 0.5  # Default medium efficiency
            
            avg_closure_time = sum(closure_times) / len(closure_times)
            
            # Convert to efficiency score (0-1)
            # Faster closure = higher efficiency
            if avg_closure_time < 10:  # Less than 10 seconds
                efficiency = 0.9
            elif avg_closure_time < 30:  # Less than 30 seconds
                efficiency = 0.7
            elif avg_closure_time < 60:  # Less than 1 minute
                efficiency = 0.5
            else:  # More than 1 minute
                efficiency = 0.3
            
            return efficiency
            
        except Exception as e:
            logger.error(f"Error calculating market efficiency for {symbol}: {str(e)}")
            return 0.5
    
    def _calculate_spread_consistency(self, symbol: str) -> float:
        """Calculate consistency of spread patterns (indicates bot behavior)"""
        try:
            if symbol not in self.opportunity_tracking or len(self.opportunity_tracking[symbol]) < 10:
                return 0.5  # Default medium consistency
            
            opportunities = self.opportunity_tracking[symbol]
            recent_opportunities = opportunities[-30:]  # Last 30 opportunities
            
            spreads = [opp['spread'] for opp in recent_opportunities]
            
            # Calculate coefficient of variation
            if not spreads:
                return 0.5
            
            mean_spread = sum(spreads) / len(spreads)
            if mean_spread == 0:
                return 0.5
            
            variance = self._calculate_variance(spreads)
            std_dev = variance ** 0.5
            coefficient_of_variation = std_dev / mean_spread
            
            # Convert to consistency score (0-1)
            # Lower coefficient of variation = higher consistency
            if coefficient_of_variation < 0.1:  # Very consistent
                consistency = 0.9
            elif coefficient_of_variation < 0.2:  # Moderately consistent
                consistency = 0.7
            elif coefficient_of_variation < 0.3:  # Somewhat consistent
                consistency = 0.5
            else:  # Inconsistent
                consistency = 0.3
            
            return consistency
            
        except Exception as e:
            logger.error(f"Error calculating spread consistency for {symbol}: {str(e)}")
            return 0.5
    
    def _analyze_exchange_preferences(self, symbol: str) -> Dict[str, float]:
        """Analyze exchange preferences (indicates bot patterns)"""
        try:
            if symbol not in self.opportunity_tracking or len(self.opportunity_tracking[symbol]) < 5:
                return {'binance': 0.5, 'kraken': 0.5}
            
            opportunities = self.opportunity_tracking[symbol]
            recent_opportunities = opportunities[-20:]  # Last 20 opportunities
            
            exchange_counts = {'binance': 0, 'kraken': 0}
            total_opportunities = len(recent_opportunities)
            
            for opp in recent_opportunities:
                if opp['buy_exchange'] == 'binance':
                    exchange_counts['binance'] += 1
                elif opp['buy_exchange'] == 'kraken':
                    exchange_counts['kraken'] += 1
            
            # Convert to percentages
            if total_opportunities > 0:
                exchange_counts['binance'] /= total_opportunities
                exchange_counts['kraken'] /= total_opportunities
            else:
                exchange_counts = {'binance': 0.5, 'kraken': 0.5}
            
            return exchange_counts
            
        except Exception as e:
            logger.error(f"Error analyzing exchange preferences for {symbol}: {str(e)}")
            return {'binance': 0.5, 'kraken': 0.5}
    
    def _analyze_competition_patterns(self, symbol: str) -> Dict[str, float]:
        """Analyze specific competition patterns"""
        try:
            if symbol not in self.opportunity_tracking or len(self.opportunity_tracking[symbol]) < 10:
                return {'pattern_consistency': 0.5, 'timing_patterns': 0.5, 'spread_targeting': 0.5}
            
            opportunities = self.opportunity_tracking[symbol]
            recent_opportunities = opportunities[-30:]  # Last 30 opportunities
            
            # Pattern consistency
            pattern_consistency = self._calculate_spread_consistency(symbol)
            
            # Timing patterns (do opportunities occur at regular intervals?)
            timing_patterns = self._analyze_timing_patterns(recent_opportunities)
            
            # Spread targeting (do competitors target specific spread ranges?)
            spread_targeting = self._analyze_spread_targeting(recent_opportunities)
            
            return {
                'pattern_consistency': pattern_consistency,
                'timing_patterns': timing_patterns,
                'spread_targeting': spread_targeting
            }
            
        except Exception as e:
            logger.error(f"Error analyzing competition patterns for {symbol}: {str(e)}")
            return {'pattern_consistency': 0.5, 'timing_patterns': 0.5, 'spread_targeting': 0.5}
    
    def _analyze_timing_patterns(self, opportunities: List[Dict]) -> float:
        """Analyze timing patterns in opportunities"""
        try:
            if len(opportunities) < 5:
                return 0.5
            
            intervals = []
            for i in range(1, len(opportunities)):
                interval = opportunities[i]['timestamp'] - opportunities[i-1]['timestamp']
                intervals.append(interval)
            
            # Calculate coefficient of variation for intervals
            if not intervals:
                return 0.5
            
            mean_interval = sum(intervals) / len(intervals)
            if mean_interval == 0:
                return 0.5
            
            variance = self._calculate_variance(intervals)
            std_dev = variance ** 0.5
            coefficient_of_variation = std_dev / mean_interval
            
            # Convert to pattern score (0-1)
            if coefficient_of_variation < 0.2:  # Very regular patterns
                return 0.9
            elif coefficient_of_variation < 0.4:  # Moderately regular
                return 0.7
            else:  # Irregular patterns
                return 0.3
            
        except Exception as e:
            logger.error(f"Error analyzing timing patterns: {str(e)}")
            return 0.5
    
    def _analyze_spread_targeting(self, opportunities: List[Dict]) -> float:
        """Analyze if competitors target specific spread ranges"""
        try:
            if len(opportunities) < 10:
                return 0.5
            
            spreads = [opp['spread'] for opp in opportunities]
            
            # Check if spreads cluster around specific values
            # This indicates bots with specific spread thresholds
            
            # Group spreads into ranges
            spread_ranges = {}
            for spread in spreads:
                range_key = round(spread * 100) / 100  # Round to 2 decimal places
                spread_ranges[range_key] = spread_ranges.get(range_key, 0) + 1
            
            # Calculate concentration
            total_spreads = len(spreads)
            max_concentration = max(spread_ranges.values()) if spread_ranges else 0
            concentration_ratio = max_concentration / total_spreads if total_spreads > 0 else 0
            
            # Convert to targeting score (0-1)
            if concentration_ratio > 0.6:  # High concentration
                return 0.9
            elif concentration_ratio > 0.4:  # Medium concentration
                return 0.7
            else:  # Low concentration
                return 0.3
            
        except Exception as e:
            logger.error(f"Error analyzing spread targeting: {str(e)}")
            return 0.5
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values"""
        try:
            if not values:
                return 0.0
            
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            return variance
            
        except Exception as e:
            logger.error(f"Error calculating variance: {str(e)}")
            return 0.0
    
    def _get_default_competition_analysis(self, symbol: str) -> CompetitionAnalysis:
        """Get default competition analysis when calculation fails"""
        return CompetitionAnalysis(
            symbol=symbol,
            competition_level=0.5,
            bot_count_estimate=2,
            response_time_avg=10.0,
            spread_closure_rate=0.3,
            opportunity_frequency=5.0,
            market_efficiency=0.5,
            competition_patterns={
                'pattern_consistency': 0.5,
                'timing_patterns': 0.5,
                'spread_targeting': 0.5
            }
        )
    
    def get_competition_summary(self) -> Dict:
        """Get competition analysis summary for all symbols"""
        try:
            summary = {}
            
            for symbol in Config.CURRENCY_PAIRS:
                if symbol in self.opportunity_tracking:
                    analysis = self.analyze_competition(symbol, {})
                    summary[symbol] = {
                        'competition_level': analysis.competition_level,
                        'bot_count_estimate': analysis.bot_count_estimate,
                        'response_time_avg': analysis.response_time_avg,
                        'spread_closure_rate': analysis.spread_closure_rate,
                        'opportunity_frequency': analysis.opportunity_frequency,
                        'market_efficiency': analysis.market_efficiency,
                        'opportunity_count': len(self.opportunity_tracking[symbol])
                    }
                else:
                    summary[symbol] = {
                        'competition_level': 0.5,
                        'bot_count_estimate': 2,
                        'response_time_avg': 10.0,
                        'spread_closure_rate': 0.3,
                        'opportunity_frequency': 5.0,
                        'market_efficiency': 0.5,
                        'opportunity_count': 0
                    }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting competition summary: {str(e)}")
            return {}

