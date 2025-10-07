import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class MarketSession:
    """Data class for market session analysis"""
    session_name: str
    start_hour: int
    end_hour: int
    timezone: str
    volatility_multiplier: float
    volume_multiplier: float
    competition_level: float
    opportunity_score: float

@dataclass
class TradingWindow:
    """Data class for optimal trading windows"""
    window_name: str
    start_time: int
    end_time: int
    priority: int
    expected_spread: float
    expected_volume: float
    competition_level: float
    confidence: float

@dataclass
class MarketConditions:
    """Data class for current market conditions"""
    timestamp: float
    hour: int
    day_of_week: int
    session: str
    volatility_level: float
    volume_level: float
    competition_level: float
    opportunity_score: float
    recommended_action: str

class MarketTimingOptimizer:
    """Market timing optimization system"""
    
    def __init__(self):
        self.market_sessions = self._initialize_market_sessions()
        self.trading_windows = self._initialize_trading_windows()
        self.performance_history = {}
        self.market_conditions_history = {}
        
        # Market session definitions
        self.market_sessions_data = {
            'asian': {
                'start_hour': 0, 'end_hour': 8,
                'volatility_multiplier': 0.8, 'volume_multiplier': 0.6,
                'competition_level': 0.3, 'timezone': 'Asia/Tokyo'
            },
            'european': {
                'start_hour': 8, 'end_hour': 16,
                'volatility_multiplier': 1.2, 'volume_multiplier': 1.1,
                'competition_level': 0.6, 'timezone': 'Europe/London'
            },
            'us_european_overlap': {
                'start_hour': 13, 'end_hour': 16,
                'volatility_multiplier': 1.5, 'volume_multiplier': 1.4,
                'competition_level': 0.8, 'timezone': 'America/New_York'
            },
            'us': {
                'start_hour': 16, 'end_hour': 24,
                'volatility_multiplier': 1.3, 'volume_multiplier': 1.2,
                'competition_level': 0.7, 'timezone': 'America/New_York'
            }
        }
        
        # Optimal trading windows
        self.trading_windows_data = {
            'low_competition': {
                'start_time': 2, 'end_time': 6,
                'priority': 8, 'expected_spread': 1.2, 'expected_volume': 0.7,
                'competition_level': 0.2, 'confidence': 0.8
            },
            'high_volatility': {
                'start_time': 13, 'end_time': 17,
                'priority': 9, 'expected_spread': 1.5, 'expected_volume': 1.3,
                'competition_level': 0.7, 'confidence': 0.9
            },
            'high_volume': {
                'start_time': 9, 'end_time': 16,
                'priority': 7, 'expected_spread': 1.0, 'expected_volume': 1.4,
                'competition_level': 0.6, 'confidence': 0.7
            },
            'news_events': {
                'start_time': 8, 'end_time': 10,
                'priority': 6, 'expected_spread': 1.8, 'expected_volume': 1.1,
                'competition_level': 0.9, 'confidence': 0.6
            },
            'weekend_low': {
                'start_time': 0, 'end_time': 8,
                'priority': 5, 'expected_spread': 0.8, 'expected_volume': 0.4,
                'competition_level': 0.1, 'confidence': 0.5
            }
        }
        
        # Day of week patterns
        self.day_patterns = {
            0: {'name': 'Monday', 'volatility': 1.1, 'volume': 1.0, 'competition': 0.7},
            1: {'name': 'Tuesday', 'volatility': 1.0, 'volume': 1.0, 'competition': 0.6},
            2: {'name': 'Wednesday', 'volatility': 1.0, 'volume': 1.0, 'competition': 0.6},
            3: {'name': 'Thursday', 'volatility': 1.0, 'volume': 1.0, 'competition': 0.6},
            4: {'name': 'Friday', 'volatility': 1.2, 'volume': 1.1, 'competition': 0.8},
            5: {'name': 'Saturday', 'volatility': 0.8, 'volume': 0.6, 'competition': 0.3},
            6: {'name': 'Sunday', 'volatility': 0.9, 'volume': 0.7, 'competition': 0.4}
        }
        
    def _initialize_market_sessions(self) -> Dict[str, MarketSession]:
        """Initialize market session objects"""
        sessions = {}
        for name, data in self.market_sessions_data.items():
            sessions[name] = MarketSession(
                session_name=name,
                start_hour=data['start_hour'],
                end_hour=data['end_hour'],
                timezone=data['timezone'],
                volatility_multiplier=data['volatility_multiplier'],
                volume_multiplier=data['volume_multiplier'],
                competition_level=data['competition_level'],
                opportunity_score=0.0
            )
        return sessions
    
    def _initialize_trading_windows(self) -> Dict[str, TradingWindow]:
        """Initialize trading window objects"""
        windows = {}
        for name, data in self.trading_windows_data.items():
            windows[name] = TradingWindow(
                window_name=name,
                start_time=data['start_time'],
                end_time=data['end_time'],
                priority=data['priority'],
                expected_spread=data['expected_spread'],
                expected_volume=data['expected_volume'],
                competition_level=data['competition_level'],
                confidence=data['confidence']
            )
        return windows
    
    async def analyze_current_market_conditions(self) -> MarketConditions:
        """Analyze current market conditions"""
        try:
            current_time = time.time()
            dt = datetime.fromtimestamp(current_time)
            hour = dt.hour
            day_of_week = dt.weekday()
            
            # Determine current session
            current_session = self._get_current_session(hour)
            
            # Calculate market metrics
            volatility_level = self._calculate_volatility_level(hour, day_of_week)
            volume_level = self._calculate_volume_level(hour, day_of_week)
            competition_level = self._calculate_competition_level(hour, day_of_week)
            
            # Calculate opportunity score
            opportunity_score = self._calculate_opportunity_score(
                volatility_level, volume_level, competition_level, current_session
            )
            
            # Determine recommended action
            recommended_action = self._get_recommended_action(opportunity_score, competition_level)
            
            conditions = MarketConditions(
                timestamp=current_time,
                hour=hour,
                day_of_week=day_of_week,
                session=current_session,
                volatility_level=volatility_level,
                volume_level=volume_level,
                competition_level=competition_level,
                opportunity_score=opportunity_score,
                recommended_action=recommended_action
            )
            
            # Store in history
            self.market_conditions_history[current_time] = conditions
            
            # Keep only recent history (last 1000 records)
            if len(self.market_conditions_history) > 1000:
                oldest_key = min(self.market_conditions_history.keys())
                del self.market_conditions_history[oldest_key]
            
            logger.info(f"Market conditions: {current_session} session, "
                       f"Opportunity score: {opportunity_score:.3f}, "
                       f"Action: {recommended_action}")
            
            return conditions
            
        except Exception as e:
            logger.error(f"Error analyzing market conditions: {str(e)}")
            return MarketConditions(
                timestamp=time.time(),
                hour=0,
                day_of_week=0,
                session='unknown',
                volatility_level=0.5,
                volume_level=0.5,
                competition_level=0.5,
                opportunity_score=0.5,
                recommended_action='hold'
            )
    
    def _get_current_session(self, hour: int) -> str:
        """Get current market session based on hour"""
        for session_name, session in self.market_sessions.items():
            if session.start_hour <= hour < session.end_hour:
                return session_name
        
        # Default to Asian session if no match
        return 'asian'
    
    def _calculate_volatility_level(self, hour: int, day_of_week: int) -> float:
        """Calculate current volatility level"""
        try:
            # Base volatility from session
            current_session = self._get_current_session(hour)
            session_volatility = self.market_sessions[current_session].volatility_multiplier
            
            # Day of week adjustment
            day_volatility = self.day_patterns[day_of_week]['volatility']
            
            # Hour-specific adjustments
            hour_adjustments = {
                0: 0.8, 1: 0.7, 2: 0.6, 3: 0.6, 4: 0.7, 5: 0.8,  # Low activity hours
                6: 0.9, 7: 1.0, 8: 1.1, 9: 1.2, 10: 1.3, 11: 1.4,  # Building activity
                12: 1.5, 13: 1.6, 14: 1.7, 15: 1.8, 16: 1.7, 17: 1.6,  # Peak activity
                18: 1.4, 19: 1.2, 20: 1.0, 21: 0.9, 22: 0.8, 23: 0.7  # Declining activity
            }
            
            hour_volatility = hour_adjustments.get(hour, 1.0)
            
            # Combine all factors
            total_volatility = session_volatility * day_volatility * hour_volatility
            
            return min(2.0, max(0.1, total_volatility))  # Clamp between 0.1 and 2.0
            
        except Exception as e:
            logger.error(f"Error calculating volatility level: {str(e)}")
            return 1.0
    
    def _calculate_volume_level(self, hour: int, day_of_week: int) -> float:
        """Calculate current volume level"""
        try:
            # Base volume from session
            current_session = self._get_current_session(hour)
            session_volume = self.market_sessions[current_session].volume_multiplier
            
            # Day of week adjustment
            day_volume = self.day_patterns[day_of_week]['volume']
            
            # Hour-specific adjustments
            hour_adjustments = {
                0: 0.4, 1: 0.3, 2: 0.2, 3: 0.2, 4: 0.3, 5: 0.4,  # Very low activity
                6: 0.6, 7: 0.8, 8: 1.0, 9: 1.2, 10: 1.3, 11: 1.4,  # Building activity
                12: 1.5, 13: 1.6, 14: 1.7, 15: 1.8, 16: 1.7, 17: 1.6,  # Peak activity
                18: 1.4, 19: 1.2, 20: 1.0, 21: 0.8, 22: 0.6, 23: 0.5  # Declining activity
            }
            
            hour_volume = hour_adjustments.get(hour, 1.0)
            
            # Combine all factors
            total_volume = session_volume * day_volume * hour_volume
            
            return min(2.0, max(0.1, total_volume))  # Clamp between 0.1 and 2.0
            
        except Exception as e:
            logger.error(f"Error calculating volume level: {str(e)}")
            return 1.0
    
    def _calculate_competition_level(self, hour: int, day_of_week: int) -> float:
        """Calculate current competition level"""
        try:
            # Base competition from session
            current_session = self._get_current_session(hour)
            session_competition = self.market_sessions[current_session].competition_level
            
            # Day of week adjustment
            day_competition = self.day_patterns[day_of_week]['competition']
            
            # Hour-specific adjustments
            hour_adjustments = {
                0: 0.1, 1: 0.1, 2: 0.1, 3: 0.1, 4: 0.1, 5: 0.1,  # Very low competition
                6: 0.3, 7: 0.4, 8: 0.5, 9: 0.6, 10: 0.7, 11: 0.8,  # Building competition
                12: 0.9, 13: 1.0, 14: 1.0, 15: 1.0, 16: 0.9, 17: 0.8,  # Peak competition
                18: 0.7, 19: 0.6, 20: 0.5, 21: 0.4, 22: 0.3, 23: 0.2  # Declining competition
            }
            
            hour_competition = hour_adjustments.get(hour, 0.5)
            
            # Combine all factors
            total_competition = session_competition * day_competition * hour_competition
            
            return min(1.0, max(0.0, total_competition))  # Clamp between 0.0 and 1.0
            
        except Exception as e:
            logger.error(f"Error calculating competition level: {str(e)}")
            return 0.5
    
    def _calculate_opportunity_score(self, volatility: float, volume: float, 
                                   competition: float, session: str) -> float:
        """Calculate opportunity score for trading"""
        try:
            # Base score from session
            session_score = self.market_sessions[session].opportunity_score
            
            # Volatility contributes positively (more opportunities)
            volatility_score = min(1.0, volatility * 0.6)
            
            # Volume contributes positively (better liquidity)
            volume_score = min(1.0, volume * 0.4)
            
            # Competition contributes negatively (fewer opportunities)
            competition_score = max(0.0, 1.0 - competition * 0.8)
            
            # Combine scores
            opportunity_score = (volatility_score + volume_score + competition_score) / 3
            
            return min(1.0, max(0.0, opportunity_score))
            
        except Exception as e:
            logger.error(f"Error calculating opportunity score: {str(e)}")
            return 0.5
    
    def _get_recommended_action(self, opportunity_score: float, competition_level: float) -> str:
        """Get recommended trading action"""
        try:
            if opportunity_score > 0.8 and competition_level < 0.3:
                return 'aggressive'
            elif opportunity_score > 0.6 and competition_level < 0.5:
                return 'moderate'
            elif opportunity_score > 0.4 and competition_level < 0.7:
                return 'conservative'
            else:
                return 'hold'
                
        except Exception as e:
            logger.error(f"Error getting recommended action: {str(e)}")
            return 'hold'
    
    async def get_optimal_trading_windows(self, hours_ahead: int = 24) -> List[TradingWindow]:
        """Get optimal trading windows for the next hours_ahead hours"""
        try:
            current_time = time.time()
            current_hour = datetime.fromtimestamp(current_time).hour
            current_day = datetime.fromtimestamp(current_time).weekday()
            
            optimal_windows = []
            
            # Check each hour for the next hours_ahead hours
            for hour_offset in range(hours_ahead):
                check_hour = (current_hour + hour_offset) % 24
                check_day = (current_day + (current_hour + hour_offset) // 24) % 7
                
                # Calculate conditions for this hour
                volatility = self._calculate_volatility_level(check_hour, check_day)
                volume = self._calculate_volume_level(check_hour, check_day)
                competition = self._calculate_competition_level(check_hour, check_day)
                
                # Calculate opportunity score
                session = self._get_current_session(check_hour)
                opportunity_score = self._calculate_opportunity_score(
                    volatility, volume, competition, session
                )
                
                # Determine if this is an optimal window
                if opportunity_score > 0.6:  # Threshold for optimal window
                    window = TradingWindow(
                        window_name=f"optimal_{check_hour:02d}",
                        start_time=check_hour,
                        end_time=check_hour + 1,
                        priority=int(opportunity_score * 10),
                        expected_spread=volatility * 0.8,
                        expected_volume=volume,
                        competition_level=competition,
                        confidence=opportunity_score
                    )
                    optimal_windows.append(window)
            
            # Sort by priority (highest first)
            optimal_windows.sort(key=lambda x: x.priority, reverse=True)
            
            logger.info(f"Found {len(optimal_windows)} optimal trading windows in the next {hours_ahead} hours")
            return optimal_windows
            
        except Exception as e:
            logger.error(f"Error getting optimal trading windows: {str(e)}")
            return []
    
    def get_current_trading_recommendations(self) -> Dict:
        """Get current trading recommendations"""
        try:
            current_conditions = asyncio.create_task(self.analyze_current_market_conditions())
            optimal_windows = asyncio.create_task(self.get_optimal_trading_windows(24))
            
            conditions = asyncio.run(current_conditions)
            windows = asyncio.run(optimal_windows)
            
            # Get next optimal window
            next_optimal = windows[0] if windows else None
            
            recommendations = {
                'current_conditions': {
                    'session': conditions.session,
                    'opportunity_score': conditions.opportunity_score,
                    'volatility_level': conditions.volatility_level,
                    'volume_level': conditions.volume_level,
                    'competition_level': conditions.competition_level,
                    'recommended_action': conditions.recommended_action
                },
                'next_optimal_window': {
                    'start_time': next_optimal.start_time if next_optimal else None,
                    'end_time': next_optimal.end_time if next_optimal else None,
                    'priority': next_optimal.priority if next_optimal else 0,
                    'expected_spread': next_optimal.expected_spread if next_optimal else 0.0,
                    'confidence': next_optimal.confidence if next_optimal else 0.0
                },
                'all_optimal_windows': [
                    {
                        'start_time': w.start_time,
                        'end_time': w.end_time,
                        'priority': w.priority,
                        'expected_spread': w.expected_spread,
                        'confidence': w.confidence
                    } for w in windows[:5]  # Top 5 windows
                ]
            }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting trading recommendations: {str(e)}")
            return {}
    
    def record_trading_performance(self, timestamp: float, profit: float, success: bool, 
                                 session: str, action_taken: str):
        """Record trading performance for learning"""
        try:
            if timestamp not in self.performance_history:
                self.performance_history[timestamp] = {
                    'profit': profit,
                    'success': success,
                    'session': session,
                    'action_taken': action_taken,
                    'timestamp': timestamp
                }
            
            # Keep only recent history (last 1000 records)
            if len(self.performance_history) > 1000:
                oldest_key = min(self.performance_history.keys())
                del self.performance_history[oldest_key]
            
            logger.debug(f"Recorded trading performance: "
                        f"Session={session}, Action={action_taken}, "
                        f"Profit=${profit:.2f}, Success={success}")
            
        except Exception as e:
            logger.error(f"Error recording trading performance: {str(e)}")
    
    def get_performance_summary(self, days: int = 30) -> Dict:
        """Get performance summary by market conditions"""
        try:
            current_time = time.time()
            cutoff_time = current_time - (days * 24 * 3600)
            
            # Filter recent performance
            recent_performance = {
                k: v for k, v in self.performance_history.items()
                if k >= cutoff_time
            }
            
            if not recent_performance:
                return {}
            
            # Group by session
            session_performance = {}
            for record in recent_performance.values():
                session = record['session']
                if session not in session_performance:
                    session_performance[session] = {
                        'total_trades': 0,
                        'successful_trades': 0,
                        'total_profit': 0.0,
                        'avg_profit': 0.0
                    }
                
                session_performance[session]['total_trades'] += 1
                if record['success']:
                    session_performance[session]['successful_trades'] += 1
                session_performance[session]['total_profit'] += record['profit']
            
            # Calculate averages
            for session, stats in session_performance.items():
                if stats['total_trades'] > 0:
                    stats['success_rate'] = stats['successful_trades'] / stats['total_trades'] * 100
                    stats['avg_profit'] = stats['total_profit'] / stats['total_trades']
                else:
                    stats['success_rate'] = 0.0
                    stats['avg_profit'] = 0.0
            
            # Group by action
            action_performance = {}
            for record in recent_performance.values():
                action = record['action_taken']
                if action not in action_performance:
                    action_performance[action] = {
                        'total_trades': 0,
                        'successful_trades': 0,
                        'total_profit': 0.0,
                        'avg_profit': 0.0
                    }
                
                action_performance[action]['total_trades'] += 1
                if record['success']:
                    action_performance[action]['successful_trades'] += 1
                action_performance[action]['total_profit'] += record['profit']
            
            # Calculate averages for actions
            for action, stats in action_performance.items():
                if stats['total_trades'] > 0:
                    stats['success_rate'] = stats['successful_trades'] / stats['total_trades'] * 100
                    stats['avg_profit'] = stats['total_profit'] / stats['total_trades']
                else:
                    stats['success_rate'] = 0.0
                    stats['avg_profit'] = 0.0
            
            summary = {
                'time_period_days': days,
                'total_trades': len(recent_performance),
                'session_performance': session_performance,
                'action_performance': action_performance,
                'best_session': max(session_performance.keys(), 
                                  key=lambda k: session_performance[k]['avg_profit']) if session_performance else None,
                'best_action': max(action_performance.keys(), 
                                 key=lambda k: action_performance[k]['avg_profit']) if action_performance else None
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {str(e)}")
            return {}
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get optimization recommendations based on performance"""
        try:
            recommendations = []
            
            # Get performance summary
            performance_summary = self.get_performance_summary(30)
            
            if not performance_summary:
                return ["No performance data available for recommendations"]
            
            # Session-based recommendations
            session_performance = performance_summary.get('session_performance', {})
            if session_performance:
                best_session = performance_summary.get('best_session')
                worst_session = min(session_performance.keys(), 
                                  key=lambda k: session_performance[k]['avg_profit'])
                
                if best_session and worst_session:
                    recommendations.append(f"Best performing session: {best_session} "
                                        f"(avg profit: ${session_performance[best_session]['avg_profit']:.2f})")
                    recommendations.append(f"Consider reducing activity during {worst_session} session")
            
            # Action-based recommendations
            action_performance = performance_summary.get('action_performance', {})
            if action_performance:
                best_action = performance_summary.get('best_action')
                if best_action:
                    recommendations.append(f"Most profitable action: {best_action} "
                                        f"(avg profit: ${action_performance[best_action]['avg_profit']:.2f})")
            
            # Time-based recommendations
            current_hour = datetime.now().hour
            if current_hour in [2, 3, 4, 5]:
                recommendations.append("Current time is optimal for low-competition trading")
            elif current_hour in [13, 14, 15, 16]:
                recommendations.append("Current time is optimal for high-opportunity trading")
            else:
                recommendations.append("Consider waiting for optimal trading windows")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting optimization recommendations: {str(e)}")
            return ["Error generating recommendations"]
    
    def should_trade_now(self, minimum_opportunity_score: float = 0.6) -> Tuple[bool, str]:
        """Determine if we should trade now based on market conditions"""
        try:
            current_conditions = asyncio.run(self.analyze_current_market_conditions())
            
            if current_conditions.opportunity_score >= minimum_opportunity_score:
                return True, f"Good opportunity (score: {current_conditions.opportunity_score:.3f})"
            else:
                return False, f"Low opportunity (score: {current_conditions.opportunity_score:.3f})"
                
        except Exception as e:
            logger.error(f"Error determining if should trade now: {str(e)}")
            return False, "Error analyzing market conditions"
    
    def get_next_optimal_trade_time(self, hours_ahead: int = 24) -> Optional[Dict]:
        """Get the next optimal time to trade"""
        try:
            optimal_windows = asyncio.run(self.get_optimal_trading_windows(hours_ahead))
            
            if not optimal_windows:
                return None
            
            next_window = optimal_windows[0]
            
            # Calculate time until next window
            current_time = datetime.now()
            next_trade_time = current_time.replace(
                hour=next_window.start_time, minute=0, second=0, microsecond=0
            )
            
            # If the time has passed today, move to tomorrow
            if next_trade_time <= current_time:
                next_trade_time += timedelta(days=1)
            
            time_until_trade = (next_trade_time - current_time).total_seconds()
            
            return {
                'next_trade_time': next_trade_time.isoformat(),
                'hours_until_trade': time_until_trade / 3600,
                'expected_spread': next_window.expected_spread,
                'confidence': next_window.confidence,
                'priority': next_window.priority
            }
            
        except Exception as e:
            logger.error(f"Error getting next optimal trade time: {str(e)}")
            return None

