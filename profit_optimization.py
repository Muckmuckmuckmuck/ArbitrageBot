import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProfitOptimization:
    """Data class for profit optimization results"""
    symbol: str
    current_profit: float
    optimal_exit_price: float
    optimal_exit_time: float
    risk_reward_ratio: float
    profit_target: float
    stop_loss_price: float
    take_profit_strategy: str
    optimization_score: float

class ProfitOptimizer:
    """Optimize profit taking and exit strategies"""
    
    def __init__(self):
        self.profit_history = {}
        self.exit_strategies = {}
        self.performance_tracking = {}
        
    def optimize_profit_strategy(self, symbol: str, trade_data: Dict) -> ProfitOptimization:
        """Optimize profit strategy for a given trade"""
        try:
            # Get current trade data
            current_price = trade_data.get('current_price', 0)
            entry_price = trade_data.get('entry_price', 0)
            spread = trade_data.get('spread', 0)
            amount = trade_data.get('amount', 0)
            
            # Calculate current profit
            current_profit = (current_price - entry_price) * amount
            
            # Determine optimal exit strategy
            take_profit_strategy = self._determine_take_profit_strategy(symbol, trade_data)
            
            # Calculate optimal exit parameters
            optimal_exit_price = self._calculate_optimal_exit_price(symbol, trade_data, take_profit_strategy)
            optimal_exit_time = self._calculate_optimal_exit_time(symbol, trade_data, take_profit_strategy)
            
            # Calculate risk metrics
            risk_reward_ratio = self._calculate_risk_reward_ratio(symbol, trade_data)
            profit_target = self._calculate_profit_target(symbol, trade_data)
            stop_loss_price = self._calculate_stop_loss_price(symbol, trade_data)
            
            # Calculate optimization score
            optimization_score = self._calculate_optimization_score(symbol, trade_data, current_profit)
            
            # Track performance
            self._track_performance(symbol, trade_data, current_profit)
            
            return ProfitOptimization(
                symbol=symbol,
                current_profit=current_profit,
                optimal_exit_price=optimal_exit_price,
                optimal_exit_time=optimal_exit_time,
                risk_reward_ratio=risk_reward_ratio,
                profit_target=profit_target,
                stop_loss_price=stop_loss_price,
                take_profit_strategy=take_profit_strategy,
                optimization_score=optimization_score
            )
            
        except Exception as e:
            logger.error(f"Error optimizing profit strategy for {symbol}: {str(e)}")
            return self._get_default_profit_optimization(symbol, trade_data)
    
    def _determine_take_profit_strategy(self, symbol: str, trade_data: Dict) -> str:
        """Determine optimal take-profit strategy"""
        try:
            # Get market conditions
            spread = trade_data.get('spread', 0)
            volatility = trade_data.get('volatility', 0.02)
            volume_ratio = trade_data.get('volume_ratio', 1.0)
            competition_level = trade_data.get('competition_level', 0.5)
            
            # Strategy selection logic
            if spread > 0.02:  # High spread (>2%)
                if volatility < 0.02:  # Low volatility
                    return 'immediate'  # Take profit immediately
                else:  # High volatility
                    return 'trailing'  # Use trailing stop
            
            elif spread > 0.01:  # Medium spread (1-2%)
                if competition_level > 0.7:  # High competition
                    return 'immediate'  # Take profit quickly
                else:  # Low competition
                    return 'partial'  # Partial profit taking
            
            else:  # Low spread (<1%)
                if volume_ratio > 1.5:  # High volume
                    return 'trailing'  # Let it run
                else:  # Low volume
                    return 'immediate'  # Take profit quickly
            
        except Exception as e:
            logger.error(f"Error determining take-profit strategy for {symbol}: {str(e)}")
            return 'immediate'
    
    def _calculate_optimal_exit_price(self, symbol: str, trade_data: Dict, strategy: str) -> float:
        """Calculate optimal exit price based on strategy"""
        try:
            entry_price = trade_data.get('entry_price', 0)
            current_price = trade_data.get('current_price', 0)
            spread = trade_data.get('spread', 0)
            
            if strategy == 'immediate':
                # Take profit immediately at current price
                return current_price
            
            elif strategy == 'partial':
                # Take partial profit at 50% of spread
                target_profit = spread * 0.5
                return entry_price * (1 + target_profit)
            
            elif strategy == 'trailing':
                # Use trailing stop at 80% of spread
                target_profit = spread * 0.8
                return entry_price * (1 + target_profit)
            
            elif strategy == 'scaled':
                # Scale out at multiple levels
                target_profit = spread * 0.6
                return entry_price * (1 + target_profit)
            
            else:
                # Default to immediate
                return current_price
                
        except Exception as e:
            logger.error(f"Error calculating optimal exit price for {symbol}: {str(e)}")
            return trade_data.get('current_price', 0)
    
    def _calculate_optimal_exit_time(self, symbol: str, trade_data: Dict, strategy: str) -> float:
        """Calculate optimal exit time based on strategy"""
        try:
            # Get market conditions
            volatility = trade_data.get('volatility', 0.02)
            competition_level = trade_data.get('competition_level', 0.5)
            volume_ratio = trade_data.get('volume_ratio', 1.0)
            
            # Base time calculations
            if strategy == 'immediate':
                return 30  # 30 seconds
            elif strategy == 'partial':
                return 120  # 2 minutes
            elif strategy == 'trailing':
                return 300  # 5 minutes
            elif strategy == 'scaled':
                return 600  # 10 minutes
            
            # Adjust based on market conditions
            time_multiplier = 1.0
            
            # High volatility = shorter time
            if volatility > 0.05:
                time_multiplier *= 0.5
            elif volatility > 0.03:
                time_multiplier *= 0.7
            
            # High competition = shorter time
            if competition_level > 0.7:
                time_multiplier *= 0.6
            elif competition_level > 0.5:
                time_multiplier *= 0.8
            
            # Low volume = shorter time
            if volume_ratio < 0.7:
                time_multiplier *= 0.8
            
            return 120 * time_multiplier  # Default 2 minutes adjusted
            
        except Exception as e:
            logger.error(f"Error calculating optimal exit time for {symbol}: {str(e)}")
            return 120  # Default 2 minutes
    
    def _calculate_risk_reward_ratio(self, symbol: str, trade_data: Dict) -> float:
        """Calculate risk-reward ratio for the trade"""
        try:
            spread = trade_data.get('spread', 0)
            volatility = trade_data.get('volatility', 0.02)
            
            # Potential reward (spread)
            potential_reward = spread
            
            # Potential risk (volatility)
            potential_risk = volatility
            
            # Risk-reward ratio
            if potential_risk > 0:
                risk_reward_ratio = potential_reward / potential_risk
            else:
                risk_reward_ratio = 1.0
            
            return min(max(risk_reward_ratio, 0.1), 10.0)  # Cap between 0.1 and 10
            
        except Exception as e:
            logger.error(f"Error calculating risk-reward ratio for {symbol}: {str(e)}")
            return 1.0
    
    def _calculate_profit_target(self, symbol: str, trade_data: Dict) -> float:
        """Calculate profit target for the trade"""
        try:
            entry_price = trade_data.get('entry_price', 0)
            amount = trade_data.get('amount', 0)
            spread = trade_data.get('spread', 0)
            
            # Calculate profit target based on spread and amount
            profit_target = entry_price * amount * spread
            
            return profit_target
            
        except Exception as e:
            logger.error(f"Error calculating profit target for {symbol}: {str(e)}")
            return 0.0
    
    def _calculate_stop_loss_price(self, symbol: str, trade_data: Dict) -> float:
        """Calculate stop-loss price for the trade"""
        try:
            entry_price = trade_data.get('entry_price', 0)
            volatility = trade_data.get('volatility', 0.02)
            
            # Stop loss at 2x volatility below entry
            stop_loss_percent = volatility * 2
            stop_loss_price = entry_price * (1 - stop_loss_percent)
            
            return stop_loss_price
            
        except Exception as e:
            logger.error(f"Error calculating stop-loss price for {symbol}: {str(e)}")
            return trade_data.get('entry_price', 0) * 0.95  # Default 5% stop loss
    
    def _calculate_optimization_score(self, symbol: str, trade_data: Dict, current_profit: float) -> float:
        """Calculate optimization score for the trade"""
        try:
            # Get performance metrics
            risk_reward_ratio = self._calculate_risk_reward_ratio(symbol, trade_data)
            spread = trade_data.get('spread', 0)
            volatility = trade_data.get('volatility', 0.02)
            volume_ratio = trade_data.get('volume_ratio', 1.0)
            
            # Calculate score components
            spread_score = min(spread * 100, 10.0) / 10.0  # Normalize to 0-1
            risk_score = min(risk_reward_ratio / 5.0, 1.0)  # Normalize to 0-1
            volatility_score = max(0, 1 - (volatility * 20))  # Lower volatility = higher score
            volume_score = min(volume_ratio, 2.0) / 2.0  # Normalize to 0-1
            
            # Weighted average
            optimization_score = (
                spread_score * 0.3 +
                risk_score * 0.3 +
                volatility_score * 0.2 +
                volume_score * 0.2
            )
            
            return min(max(optimization_score, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating optimization score for {symbol}: {str(e)}")
            return 0.5
    
    def _track_performance(self, symbol: str, trade_data: Dict, current_profit: float):
        """Track performance for optimization"""
        try:
            if symbol not in self.profit_history:
                self.profit_history[symbol] = []
            
            self.profit_history[symbol].append({
                'timestamp': time.time(),
                'profit': current_profit,
                'spread': trade_data.get('spread', 0),
                'volatility': trade_data.get('volatility', 0.02),
                'volume_ratio': trade_data.get('volume_ratio', 1.0),
                'competition_level': trade_data.get('competition_level', 0.5)
            })
            
            # Keep only recent history (last 100 trades)
            if len(self.profit_history[symbol]) > 100:
                self.profit_history[symbol] = self.profit_history[symbol][-100:]
                
        except Exception as e:
            logger.error(f"Error tracking performance for {symbol}: {str(e)}")
    
    def _get_default_profit_optimization(self, symbol: str, trade_data: Dict) -> ProfitOptimization:
        """Get default profit optimization when calculation fails"""
        entry_price = trade_data.get('entry_price', 0)
        current_price = trade_data.get('current_price', entry_price)
        amount = trade_data.get('amount', 0)
        
        return ProfitOptimization(
            symbol=symbol,
            current_profit=(current_price - entry_price) * amount,
            optimal_exit_price=current_price,
            optimal_exit_time=120,
            risk_reward_ratio=1.0,
            profit_target=entry_price * amount * 0.01,  # 1% target
            stop_loss_price=entry_price * 0.95,  # 5% stop loss
            take_profit_strategy='immediate',
            optimization_score=0.5
        )
    
    def get_profit_summary(self) -> Dict:
        """Get profit optimization summary for all symbols"""
        try:
            summary = {}
            
            for symbol in Config.CURRENCY_PAIRS:
                if symbol in self.profit_history:
                    history = self.profit_history[symbol]
                    
                    # Calculate metrics
                    total_trades = len(history)
                    profitable_trades = sum(1 for h in history if h['profit'] > 0)
                    total_profit = sum(h['profit'] for h in history)
                    avg_profit = total_profit / total_trades if total_trades > 0 else 0
                    success_rate = profitable_trades / total_trades if total_trades > 0 else 0
                    
                    # Calculate strategy effectiveness
                    strategies = {}
                    for h in history:
                        strategy = h.get('strategy', 'immediate')
                        if strategy not in strategies:
                            strategies[strategy] = {'count': 0, 'profit': 0}
                        strategies[strategy]['count'] += 1
                        strategies[strategy]['profit'] += h['profit']
                    
                    summary[symbol] = {
                        'total_trades': total_trades,
                        'profitable_trades': profitable_trades,
                        'success_rate': success_rate,
                        'total_profit': total_profit,
                        'avg_profit': avg_profit,
                        'strategies': strategies
                    }
                else:
                    summary[symbol] = {
                        'total_trades': 0,
                        'profitable_trades': 0,
                        'success_rate': 0,
                        'total_profit': 0,
                        'avg_profit': 0,
                        'strategies': {}
                    }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting profit summary: {str(e)}")
            return {}
    
    def should_take_profit(self, symbol: str, current_profit: float, target_profit: float) -> bool:
        """Determine if profit should be taken based on current conditions"""
        try:
            if symbol not in self.profit_history:
                return current_profit >= target_profit
            
            history = self.profit_history[symbol]
            if not history:
                return current_profit >= target_profit
            
            # Get recent performance
            recent_trades = history[-10:]  # Last 10 trades
            recent_profits = [h['profit'] for h in recent_trades]
            avg_recent_profit = sum(recent_profits) / len(recent_profits) if recent_profits else 0
            
            # Take profit if:
            # 1. Current profit exceeds target
            # 2. Current profit is significantly above recent average
            # 3. Risk of holding is too high
            
            if current_profit >= target_profit:
                return True
            
            if current_profit > avg_recent_profit * 1.5:  # 50% above recent average
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error determining if should take profit for {symbol}: {str(e)}")
            return current_profit >= target_profit

