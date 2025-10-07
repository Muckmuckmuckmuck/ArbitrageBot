import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class CompetitionSignal:
    """Data class for competition signals"""
    signal_type: str
    strength: float
    confidence: float
    timestamp: float
    symbol: str
    details: Dict

@dataclass
class BotActivity:
    """Data class for bot activity detection"""
    activity_type: str
    frequency: float
    pattern: str
    confidence: float
    timestamp: float
    symbol: str

@dataclass
class CompetitionAnalysis:
    """Data class for competition analysis"""
    symbol: str
    competition_level: float
    bot_count_estimate: int
    dominant_strategy: str
    risk_level: str
    recommended_action: str
    timestamp: float

class CompetitionDetector:
    """Competition detection and avoidance system"""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.price_history = {}
        self.order_book_history = {}
        self.trade_history = {}
        self.competition_signals = {}
        self.bot_activity_patterns = {}
        
        # Competition detection parameters
        self.detection_thresholds = {
            'price_velocity': 0.5,      # Price changes per second
            'order_book_churn': 0.3,    # Order book changes per second
            'trade_frequency': 2.0,     # Trades per second
            'pattern_consistency': 0.8,  # Pattern matching threshold
            'timing_precision': 0.1     # Timing precision in seconds
        }
        
        # Bot activity patterns
        self.bot_patterns = {
            'rapid_price_changes': {
                'description': 'Rapid, consistent price changes',
                'threshold': 0.3,
                'timeframe': 60
            },
            'order_book_manipulation': {
                'description': 'Systematic order book manipulation',
                'threshold': 0.4,
                'timeframe': 120
            },
            'timing_patterns': {
                'description': 'Consistent timing patterns',
                'threshold': 0.7,
                'timeframe': 300
            },
            'volume_patterns': {
                'description': 'Unusual volume patterns',
                'threshold': 0.5,
                'timeframe': 180
            },
            'spread_manipulation': {
                'description': 'Systematic spread manipulation',
                'threshold': 0.6,
                'timeframe': 240
            }
        }
        
        # Competition response strategies
        self.response_strategies = {
            'low': 'aggressive',
            'medium': 'moderate',
            'high': 'conservative',
            'very_high': 'avoid'
        }
        
        # Performance tracking
        self.detection_accuracy = {}
        self.competition_history = {}
        
    async def analyze_competition(self, symbol: str) -> CompetitionAnalysis:
        """Analyze competition level for a symbol"""
        try:
            # Collect data
            await self._collect_market_data(symbol)
            
            # Detect competition signals
            signals = await self._detect_competition_signals(symbol)
            
            # Analyze bot activity
            bot_activity = await self._analyze_bot_activity(symbol)
            
            # Calculate competition level
            competition_level = self._calculate_competition_level(signals, bot_activity)
            
            # Estimate number of bots
            bot_count = self._estimate_bot_count(signals, bot_activity)
            
            # Identify dominant strategy
            dominant_strategy = self._identify_dominant_strategy(signals, bot_activity)
            
            # Assess risk level
            risk_level = self._assess_risk_level(competition_level, bot_count)
            
            # Get recommended action
            recommended_action = self._get_recommended_action(risk_level, competition_level)
            
            analysis = CompetitionAnalysis(
                symbol=symbol,
                competition_level=competition_level,
                bot_count_estimate=bot_count,
                dominant_strategy=dominant_strategy,
                risk_level=risk_level,
                recommended_action=recommended_action,
                timestamp=time.time()
            )
            
            # Store analysis
            self.competition_history[symbol] = analysis
            
            logger.info(f"Competition analysis for {symbol}: "
                       f"Level={competition_level:.3f}, Bots={bot_count}, "
                       f"Risk={risk_level}, Action={recommended_action}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing competition for {symbol}: {str(e)}")
            return CompetitionAnalysis(
                symbol=symbol,
                competition_level=0.5,
                bot_count_estimate=1,
                dominant_strategy='unknown',
                risk_level='medium',
                recommended_action='moderate',
                timestamp=time.time()
            )
    
    async def _collect_market_data(self, symbol: str):
        """Collect market data for competition analysis"""
        try:
            current_time = time.time()
            
            # Get current prices
            binance_exchange = self.exchange_manager.get_exchange('binance')
            kraken_exchange = self.exchange_manager.get_exchange('kraken')
            
            binance_ticker = await binance_exchange.get_ticker(symbol)
            kraken_ticker = await kraken_exchange.get_ticker(symbol)
            
            if binance_ticker and kraken_ticker:
                # Store price data
                if symbol not in self.price_history:
                    self.price_history[symbol] = []
                
                price_data = {
                    'timestamp': current_time,
                    'binance_price': binance_ticker['last'],
                    'kraken_price': kraken_ticker['last'],
                    'spread': abs(binance_ticker['last'] - kraken_ticker['last']) / ((binance_ticker['last'] + kraken_ticker['last']) / 2) * 100
                }
                
                self.price_history[symbol].append(price_data)
                
                # Keep only recent history (last 1000 records)
                if len(self.price_history[symbol]) > 1000:
                    self.price_history[symbol] = self.price_history[symbol][-1000:]
            
            # Get order book data
            binance_orderbook = await binance_exchange.get_orderbook(symbol, 20)
            kraken_orderbook = await kraken_exchange.get_orderbook(symbol, 20)
            
            if binance_orderbook and kraken_orderbook:
                # Store order book data
                if symbol not in self.order_book_history:
                    self.order_book_history[symbol] = []
                
                orderbook_data = {
                    'timestamp': current_time,
                    'binance_best_bid': binance_orderbook.get('bids', [[0, 0]])[0][0],
                    'binance_best_ask': binance_orderbook.get('asks', [[0, 0]])[0][0],
                    'kraken_best_bid': kraken_orderbook.get('bids', [[0, 0]])[0][0],
                    'kraken_best_ask': kraken_orderbook.get('asks', [[0, 0]])[0][0],
                    'binance_bid_size': binance_orderbook.get('bids', [[0, 0]])[0][1],
                    'binance_ask_size': binance_orderbook.get('asks', [[0, 0]])[0][1],
                    'kraken_bid_size': kraken_orderbook.get('bids', [[0, 0]])[0][1],
                    'kraken_ask_size': kraken_orderbook.get('asks', [[0, 0]])[0][1]
                }
                
                self.order_book_history[symbol].append(orderbook_data)
                
                # Keep only recent history (last 1000 records)
                if len(self.order_book_history[symbol]) > 1000:
                    self.order_book_history[symbol] = self.order_book_history[symbol][-1000:]
            
        except Exception as e:
            logger.error(f"Error collecting market data for {symbol}: {str(e)}")
    
    async def _detect_competition_signals(self, symbol: str) -> List[CompetitionSignal]:
        """Detect competition signals from market data"""
        try:
            signals = []
            
            if symbol not in self.price_history or len(self.price_history[symbol]) < 10:
                return signals
            
            price_data = self.price_history[symbol][-100:]  # Last 100 records
            orderbook_data = self.order_book_history.get(symbol, [])[-100:]  # Last 100 records
            
            # Signal 1: Rapid price changes
            price_velocity_signal = self._detect_rapid_price_changes(price_data, symbol)
            if price_velocity_signal:
                signals.append(price_velocity_signal)
            
            # Signal 2: Order book manipulation
            orderbook_signal = self._detect_order_book_manipulation(orderbook_data, symbol)
            if orderbook_signal:
                signals.append(orderbook_signal)
            
            # Signal 3: Timing patterns
            timing_signal = self._detect_timing_patterns(price_data, symbol)
            if timing_signal:
                signals.append(timing_signal)
            
            # Signal 4: Volume patterns
            volume_signal = self._detect_volume_patterns(orderbook_data, symbol)
            if volume_signal:
                signals.append(volume_signal)
            
            # Signal 5: Spread manipulation
            spread_signal = self._detect_spread_manipulation(price_data, symbol)
            if spread_signal:
                signals.append(spread_signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error detecting competition signals for {symbol}: {str(e)}")
            return []
    
    def _detect_rapid_price_changes(self, price_data: List[Dict], symbol: str) -> Optional[CompetitionSignal]:
        """Detect rapid price changes indicative of bot activity"""
        try:
            if len(price_data) < 10:
                return None
            
            # Calculate price velocity
            price_changes = []
            for i in range(1, len(price_data)):
                prev_spread = price_data[i-1]['spread']
                curr_spread = price_data[i]['spread']
                time_diff = price_data[i]['timestamp'] - price_data[i-1]['timestamp']
                
                if time_diff > 0:
                    price_change = abs(curr_spread - prev_spread) / time_diff
                    price_changes.append(price_change)
            
            if not price_changes:
                return None
            
            avg_velocity = sum(price_changes) / len(price_changes)
            threshold = self.detection_thresholds['price_velocity']
            
            if avg_velocity > threshold:
                strength = min(1.0, avg_velocity / threshold)
                confidence = min(0.9, strength * 0.8)
                
                return CompetitionSignal(
                    signal_type='rapid_price_changes',
                    strength=strength,
                    confidence=confidence,
                    timestamp=time.time(),
                    symbol=symbol,
                    details={'avg_velocity': avg_velocity, 'threshold': threshold}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting rapid price changes: {str(e)}")
            return None
    
    def _detect_order_book_manipulation(self, orderbook_data: List[Dict], symbol: str) -> Optional[CompetitionSignal]:
        """Detect order book manipulation patterns"""
        try:
            if len(orderbook_data) < 10:
                return None
            
            # Calculate order book churn
            bid_changes = 0
            ask_changes = 0
            total_changes = 0
            
            for i in range(1, len(orderbook_data)):
                prev_data = orderbook_data[i-1]
                curr_data = orderbook_data[i]
                time_diff = curr_data['timestamp'] - prev_data['timestamp']
                
                if time_diff > 0:
                    # Check bid changes
                    if abs(curr_data['binance_best_bid'] - prev_data['binance_best_bid']) > 0.0001:
                        bid_changes += 1
                    if abs(curr_data['kraken_best_bid'] - prev_data['kraken_best_bid']) > 0.0001:
                        bid_changes += 1
                    
                    # Check ask changes
                    if abs(curr_data['binance_best_ask'] - prev_data['binance_best_ask']) > 0.0001:
                        ask_changes += 1
                    if abs(curr_data['kraken_best_ask'] - prev_data['kraken_best_ask']) > 0.0001:
                        ask_changes += 1
                    
                    total_changes += 1
            
            if total_changes == 0:
                return None
            
            churn_rate = (bid_changes + ask_changes) / total_changes
            threshold = self.detection_thresholds['order_book_churn']
            
            if churn_rate > threshold:
                strength = min(1.0, churn_rate / threshold)
                confidence = min(0.9, strength * 0.7)
                
                return CompetitionSignal(
                    signal_type='order_book_manipulation',
                    strength=strength,
                    confidence=confidence,
                    timestamp=time.time(),
                    symbol=symbol,
                    details={'churn_rate': churn_rate, 'threshold': threshold}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting order book manipulation: {str(e)}")
            return None
    
    def _detect_timing_patterns(self, price_data: List[Dict], symbol: str) -> Optional[CompetitionSignal]:
        """Detect consistent timing patterns"""
        try:
            if len(price_data) < 20:
                return None
            
            # Analyze time intervals between significant changes
            significant_changes = []
            for i in range(1, len(price_data)):
                prev_spread = price_data[i-1]['spread']
                curr_spread = price_data[i]['spread']
                time_diff = price_data[i]['timestamp'] - price_data[i-1]['timestamp']
                
                if abs(curr_spread - prev_spread) > 0.1:  # Significant change
                    significant_changes.append(time_diff)
            
            if len(significant_changes) < 5:
                return None
            
            # Look for patterns in timing
            timing_patterns = {}
            for interval in significant_changes:
                rounded_interval = round(interval, 1)  # Round to 0.1 seconds
                timing_patterns[rounded_interval] = timing_patterns.get(rounded_interval, 0) + 1
            
            # Find most common pattern
            if timing_patterns:
                most_common_interval = max(timing_patterns.keys(), key=lambda k: timing_patterns[k])
                pattern_frequency = timing_patterns[most_common_interval] / len(significant_changes)
                
                threshold = self.detection_thresholds['pattern_consistency']
                
                if pattern_frequency > threshold:
                    strength = min(1.0, pattern_frequency / threshold)
                    confidence = min(0.9, strength * 0.6)
                    
                    return CompetitionSignal(
                        signal_type='timing_patterns',
                        strength=strength,
                        confidence=confidence,
                        timestamp=time.time(),
                        symbol=symbol,
                        details={'pattern_frequency': pattern_frequency, 'most_common_interval': most_common_interval}
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting timing patterns: {str(e)}")
            return None
    
    def _detect_volume_patterns(self, orderbook_data: List[Dict], symbol: str) -> Optional[CompetitionSignal]:
        """Detect unusual volume patterns"""
        try:
            if len(orderbook_data) < 10:
                return None
            
            # Analyze volume changes
            volume_changes = []
            for i in range(1, len(orderbook_data)):
                prev_data = orderbook_data[i-1]
                curr_data = orderbook_data[i]
                
                # Calculate total volume change
                prev_volume = prev_data['binance_bid_size'] + prev_data['binance_ask_size'] + prev_data['kraken_bid_size'] + prev_data['kraken_ask_size']
                curr_volume = curr_data['binance_bid_size'] + curr_data['binance_ask_size'] + curr_data['kraken_bid_size'] + curr_data['kraken_ask_size']
                
                if prev_volume > 0:
                    volume_change = abs(curr_volume - prev_volume) / prev_volume
                    volume_changes.append(volume_change)
            
            if not volume_changes:
                return None
            
            avg_volume_change = sum(volume_changes) / len(volume_changes)
            threshold = 0.5  # 50% volume change threshold
            
            if avg_volume_change > threshold:
                strength = min(1.0, avg_volume_change / threshold)
                confidence = min(0.9, strength * 0.5)
                
                return CompetitionSignal(
                    signal_type='volume_patterns',
                    strength=strength,
                    confidence=confidence,
                    timestamp=time.time(),
                    symbol=symbol,
                    details={'avg_volume_change': avg_volume_change, 'threshold': threshold}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting volume patterns: {str(e)}")
            return None
    
    def _detect_spread_manipulation(self, price_data: List[Dict], symbol: str) -> Optional[CompetitionSignal]:
        """Detect systematic spread manipulation"""
        try:
            if len(price_data) < 20:
                return None
            
            # Analyze spread patterns
            spreads = [data['spread'] for data in price_data]
            
            # Look for systematic spread manipulation
            spread_changes = []
            for i in range(1, len(spreads)):
                spread_change = abs(spreads[i] - spreads[i-1])
                spread_changes.append(spread_change)
            
            if not spread_changes:
                return None
            
            # Check for consistent manipulation patterns
            manipulation_score = 0
            
            # Pattern 1: Consistent spread widening/narrowing
            consistent_changes = sum(1 for change in spread_changes if change > 0.1)
            if consistent_changes > len(spread_changes) * 0.7:
                manipulation_score += 0.3
            
            # Pattern 2: Rapid spread changes
            rapid_changes = sum(1 for change in spread_changes if change > 0.5)
            if rapid_changes > len(spread_changes) * 0.3:
                manipulation_score += 0.4
            
            # Pattern 3: Spread volatility
            spread_volatility = sum(spread_changes) / len(spread_changes)
            if spread_volatility > 0.3:
                manipulation_score += 0.3
            
            threshold = 0.6
            if manipulation_score > threshold:
                strength = min(1.0, manipulation_score / threshold)
                confidence = min(0.9, strength * 0.7)
                
                return CompetitionSignal(
                    signal_type='spread_manipulation',
                    strength=strength,
                    confidence=confidence,
                    timestamp=time.time(),
                    symbol=symbol,
                    details={'manipulation_score': manipulation_score, 'threshold': threshold}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting spread manipulation: {str(e)}")
            return None
    
    async def _analyze_bot_activity(self, symbol: str) -> List[BotActivity]:
        """Analyze bot activity patterns"""
        try:
            activities = []
            
            if symbol not in self.price_history or len(self.price_history[symbol]) < 10:
                return activities
            
            price_data = self.price_history[symbol][-100:]  # Last 100 records
            
            # Activity 1: High frequency trading
            if len(price_data) > 50:
                time_span = price_data[-1]['timestamp'] - price_data[0]['timestamp']
                if time_span > 0:
                    frequency = len(price_data) / time_span
                    if frequency > self.detection_thresholds['trade_frequency']:
                        activity = BotActivity(
                            activity_type='high_frequency_trading',
                            frequency=frequency,
                            pattern='continuous',
                            confidence=min(0.9, frequency / self.detection_thresholds['trade_frequency']),
                            timestamp=time.time(),
                            symbol=symbol
                        )
                        activities.append(activity)
            
            # Activity 2: Systematic arbitrage
            spreads = [data['spread'] for data in price_data]
            if len(spreads) > 10:
                # Look for consistent arbitrage patterns
                profitable_spreads = sum(1 for spread in spreads if spread > 0.5)
                if profitable_spreads > len(spreads) * 0.6:
                    activity = BotActivity(
                        activity_type='systematic_arbitrage',
                        frequency=profitable_spreads / len(spreads),
                        pattern='consistent',
                        confidence=min(0.8, profitable_spreads / len(spreads)),
                        timestamp=time.time(),
                        symbol=symbol
                    )
                    activities.append(activity)
            
            return activities
            
        except Exception as e:
            logger.error(f"Error analyzing bot activity for {symbol}: {str(e)}")
            return []
    
    def _calculate_competition_level(self, signals: List[CompetitionSignal], 
                                   activities: List[BotActivity]) -> float:
        """Calculate overall competition level"""
        try:
            if not signals and not activities:
                return 0.0
            
            # Weight signals by confidence
            signal_score = 0.0
            total_signal_weight = 0.0
            
            for signal in signals:
                weight = signal.confidence
                signal_score += signal.strength * weight
                total_signal_weight += weight
            
            # Weight activities by confidence
            activity_score = 0.0
            total_activity_weight = 0.0
            
            for activity in activities:
                weight = activity.confidence
                activity_score += activity.frequency * weight
                total_activity_weight += weight
            
            # Calculate weighted average
            if total_signal_weight > 0:
                avg_signal_score = signal_score / total_signal_weight
            else:
                avg_signal_score = 0.0
            
            if total_activity_weight > 0:
                avg_activity_score = activity_score / total_activity_weight
            else:
                avg_activity_score = 0.0
            
            # Combine scores
            competition_level = (avg_signal_score + avg_activity_score) / 2
            
            return min(1.0, max(0.0, competition_level))
            
        except Exception as e:
            logger.error(f"Error calculating competition level: {str(e)}")
            return 0.5
    
    def _estimate_bot_count(self, signals: List[CompetitionSignal], 
                          activities: List[BotActivity]) -> int:
        """Estimate number of competing bots"""
        try:
            bot_count = 0
            
            # Estimate based on signal diversity
            signal_types = set(signal.signal_type for signal in signals)
            bot_count += len(signal_types)
            
            # Estimate based on activity patterns
            activity_types = set(activity.activity_type for activity in activities)
            bot_count += len(activity_types)
            
            # Minimum estimate
            if bot_count == 0:
                bot_count = 1
            
            # Maximum estimate
            bot_count = min(bot_count, 10)
            
            return bot_count
            
        except Exception as e:
            logger.error(f"Error estimating bot count: {str(e)}")
            return 1
    
    def _identify_dominant_strategy(self, signals: List[CompetitionSignal], 
                                  activities: List[BotActivity]) -> str:
        """Identify dominant trading strategy"""
        try:
            strategy_scores = {}
            
            # Analyze signals
            for signal in signals:
                if signal.signal_type == 'rapid_price_changes':
                    strategy_scores['scalping'] = strategy_scores.get('scalping', 0) + signal.strength
                elif signal.signal_type == 'order_book_manipulation':
                    strategy_scores['market_making'] = strategy_scores.get('market_making', 0) + signal.strength
                elif signal.signal_type == 'timing_patterns':
                    strategy_scores['algorithmic'] = strategy_scores.get('algorithmic', 0) + signal.strength
                elif signal.signal_type == 'spread_manipulation':
                    strategy_scores['arbitrage'] = strategy_scores.get('arbitrage', 0) + signal.strength
            
            # Analyze activities
            for activity in activities:
                if activity.activity_type == 'high_frequency_trading':
                    strategy_scores['scalping'] = strategy_scores.get('scalping', 0) + activity.frequency
                elif activity.activity_type == 'systematic_arbitrage':
                    strategy_scores['arbitrage'] = strategy_scores.get('arbitrage', 0) + activity.frequency
            
            # Find dominant strategy
            if strategy_scores:
                dominant_strategy = max(strategy_scores.keys(), key=lambda k: strategy_scores[k])
                return dominant_strategy
            else:
                return 'unknown'
                
        except Exception as e:
            logger.error(f"Error identifying dominant strategy: {str(e)}")
            return 'unknown'
    
    def _assess_risk_level(self, competition_level: float, bot_count: int) -> str:
        """Assess risk level based on competition"""
        try:
            if competition_level < 0.3 and bot_count <= 2:
                return 'low'
            elif competition_level < 0.6 and bot_count <= 4:
                return 'medium'
            elif competition_level < 0.8 and bot_count <= 6:
                return 'high'
            else:
                return 'very_high'
                
        except Exception as e:
            logger.error(f"Error assessing risk level: {str(e)}")
            return 'medium'
    
    def _get_recommended_action(self, risk_level: str, competition_level: float) -> str:
        """Get recommended action based on risk level and competition"""
        try:
            if risk_level == 'low':
                return 'aggressive'
            elif risk_level == 'medium':
                return 'moderate'
            elif risk_level == 'high':
                return 'conservative'
            else:
                return 'avoid'
                
        except Exception as e:
            logger.error(f"Error getting recommended action: {str(e)}")
            return 'moderate'
    
    def get_competition_summary(self, symbol: str = None, days: int = 7) -> Dict:
        """Get competition summary"""
        try:
            if symbol:
                # Get specific symbol summary
                if symbol not in self.competition_history:
                    return {}
                
                recent_analyses = [
                    analysis for analysis in self.competition_history[symbol]
                    if time.time() - analysis.timestamp <= days * 24 * 3600
                ]
                
                if not recent_analyses:
                    return {}
                
                avg_competition = sum(a.competition_level for a in recent_analyses) / len(recent_analyses)
                avg_bot_count = sum(a.bot_count_estimate for a in recent_analyses) / len(recent_analyses)
                
                # Count risk levels
                risk_counts = {}
                for analysis in recent_analyses:
                    risk_counts[analysis.risk_level] = risk_counts.get(analysis.risk_level, 0) + 1
                
                summary = {
                    'symbol': symbol,
                    'avg_competition_level': avg_competition,
                    'avg_bot_count': avg_bot_count,
                    'risk_distribution': risk_counts,
                    'total_analyses': len(recent_analyses),
                    'time_period_days': days
                }
                
                return summary
            else:
                # Get all symbols summary
                summary = {}
                for sym in self.competition_history.keys():
                    sym_summary = self.get_competition_summary(sym, days)
                    if sym_summary:
                        summary[sym] = sym_summary
                
                return summary
                
        except Exception as e:
            logger.error(f"Error getting competition summary: {str(e)}")
            return {}
    
    def get_optimization_recommendations(self, symbol: str) -> List[str]:
        """Get optimization recommendations based on competition analysis"""
        try:
            recommendations = []
            
            if symbol not in self.competition_history:
                return ["No competition data available for recommendations"]
            
            latest_analysis = self.competition_history[symbol]
            
            # Competition level recommendations
            if latest_analysis.competition_level > 0.8:
                recommendations.append("Very high competition - consider avoiding this symbol")
            elif latest_analysis.competition_level > 0.6:
                recommendations.append("High competition - use conservative position sizing")
            elif latest_analysis.competition_level < 0.3:
                recommendations.append("Low competition - good opportunity for aggressive trading")
            
            # Bot count recommendations
            if latest_analysis.bot_count_estimate > 5:
                recommendations.append("Many competing bots - consider timing optimization")
            elif latest_analysis.bot_count_estimate <= 2:
                recommendations.append("Few competing bots - good opportunity window")
            
            # Strategy recommendations
            if latest_analysis.dominant_strategy == 'arbitrage':
                recommendations.append("Arbitrage competition detected - consider faster execution")
            elif latest_analysis.dominant_strategy == 'scalping':
                recommendations.append("Scalping competition detected - consider longer timeframes")
            elif latest_analysis.dominant_strategy == 'market_making':
                recommendations.append("Market making competition detected - consider alternative strategies")
            
            # Risk-based recommendations
            if latest_analysis.risk_level == 'very_high':
                recommendations.append("Very high risk - consider pausing trading on this symbol")
            elif latest_analysis.risk_level == 'high':
                recommendations.append("High risk - reduce position sizes and increase spreads")
            elif latest_analysis.risk_level == 'low':
                recommendations.append("Low risk - good opportunity for larger positions")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting optimization recommendations: {str(e)}")
            return ["Error generating recommendations"]

