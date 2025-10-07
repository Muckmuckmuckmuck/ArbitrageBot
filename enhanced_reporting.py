import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class PerformanceReport:
    """Data class for performance reporting"""
    timestamp: float
    symbol: str
    trade_count: int
    successful_trades: int
    total_profit: float
    avg_profit: float
    success_rate: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    loss_rate: float
    profit_factor: float

@dataclass
class SystemHealthReport:
    """Data class for system health reporting"""
    timestamp: float
    uptime: float
    memory_usage: float
    cpu_usage: float
    api_calls_per_minute: int
    error_rate: float
    connection_status: Dict[str, bool]
    active_trades: int
    pending_transfers: int

class EnhancedReporter:
    """Enhanced reporting system for Render deployment"""
    
    def __init__(self):
        self.trade_history = []
        self.performance_metrics = {}
        self.system_metrics = {}
        self.error_log = []
        self.start_time = time.time()
        
    def log_trade_execution(self, trade_data: Dict):
        """Log trade execution with enhanced details"""
        try:
            log_entry = {
                'timestamp': time.time(),
                'level': 'INFO',
                'event': 'trade_execution',
                'symbol': trade_data.get('symbol', ''),
                'buy_exchange': trade_data.get('buy_exchange', ''),
                'sell_exchange': trade_data.get('sell_exchange', ''),
                'amount': trade_data.get('amount', 0),
                'buy_price': trade_data.get('buy_price', 0),
                'sell_price': trade_data.get('sell_price', 0),
                'spread': trade_data.get('spread', 0),
                'profit': trade_data.get('profit', 0),
                'strategy': trade_data.get('strategy', ''),
                'execution_time': trade_data.get('execution_time', 0),
                'status': trade_data.get('status', '')
            }
            
            # Log to console for Render
            logger.info(f"TRADE_EXECUTED: {json.dumps(log_entry)}")
            
            # Store for reporting
            self.trade_history.append(log_entry)
            
            # Keep only recent history (last 1000 trades)
            if len(self.trade_history) > 1000:
                self.trade_history = self.trade_history[-1000:]
                
        except Exception as e:
            logger.error(f"Error logging trade execution: {str(e)}")
    
    def log_arbitrage_opportunity(self, opportunity_data: Dict):
        """Log arbitrage opportunity detection"""
        try:
            log_entry = {
                'timestamp': time.time(),
                'level': 'INFO',
                'event': 'arbitrage_opportunity',
                'symbol': opportunity_data.get('symbol', ''),
                'spread_percent': opportunity_data.get('spread_percent', 0),
                'buy_exchange': opportunity_data.get('buy_exchange', ''),
                'sell_exchange': opportunity_data.get('sell_exchange', ''),
                'buy_price': opportunity_data.get('buy_price', 0),
                'sell_price': opportunity_data.get('sell_price', 0),
                'estimated_profit': opportunity_data.get('estimated_profit', 0),
                'competition_level': opportunity_data.get('competition_level', 0),
                'volume_ratio': opportunity_data.get('volume_ratio', 0),
                'volatility': opportunity_data.get('volatility', 0)
            }
            
            logger.info(f"ARBITRAGE_OPPORTUNITY: {json.dumps(log_entry)}")
            
        except Exception as e:
            logger.error(f"Error logging arbitrage opportunity: {str(e)}")
    
    def log_system_event(self, event_type: str, event_data: Dict):
        """Log system events with enhanced details"""
        try:
            log_entry = {
                'timestamp': time.time(),
                'level': 'INFO',
                'event': event_type,
                'data': event_data
            }
            
            logger.info(f"SYSTEM_EVENT: {json.dumps(log_entry)}")
            
        except Exception as e:
            logger.error(f"Error logging system event: {str(e)}")
    
    def log_error(self, error_type: str, error_message: str, context: Dict = None):
        """Log errors with enhanced context"""
        try:
            log_entry = {
                'timestamp': time.time(),
                'level': 'ERROR',
                'event': 'error',
                'error_type': error_type,
                'message': error_message,
                'context': context or {}
            }
            
            logger.error(f"ERROR: {json.dumps(log_entry)}")
            
            # Store for reporting
            self.error_log.append(log_entry)
            
            # Keep only recent errors (last 100)
            if len(self.error_log) > 100:
                self.error_log = self.error_log[-100:]
                
        except Exception as e:
            logger.error(f"Error logging error: {str(e)}")
    
    def generate_performance_report(self, symbol: str = None) -> PerformanceReport:
        """Generate performance report for a symbol or overall"""
        try:
            if symbol:
                # Filter trades for specific symbol
                symbol_trades = [t for t in self.trade_history if t.get('symbol') == symbol]
            else:
                # Use all trades
                symbol_trades = self.trade_history
            
            if not symbol_trades:
                return self._get_empty_performance_report(symbol)
            
            # Calculate metrics
            total_trades = len(symbol_trades)
            successful_trades = len([t for t in symbol_trades if t.get('profit', 0) > 0])
            total_profit = sum(t.get('profit', 0) for t in symbol_trades)
            avg_profit = total_profit / total_trades if total_trades > 0 else 0
            success_rate = successful_trades / total_trades if total_trades > 0 else 0
            
            # Calculate additional metrics
            profits = [t.get('profit', 0) for t in symbol_trades]
            win_rate = len([p for p in profits if p > 0]) / len(profits) if profits else 0
            loss_rate = len([p for p in profits if p < 0]) / len(profits) if profits else 0
            
            # Calculate profit factor
            total_wins = sum(p for p in profits if p > 0)
            total_losses = abs(sum(p for p in profits if p < 0))
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
            
            # Calculate max drawdown
            max_drawdown = self._calculate_max_drawdown(profits)
            
            # Calculate Sharpe ratio (simplified)
            sharpe_ratio = self._calculate_sharpe_ratio(profits)
            
            return PerformanceReport(
                timestamp=time.time(),
                symbol=symbol or 'ALL',
                trade_count=total_trades,
                successful_trades=successful_trades,
                total_profit=total_profit,
                avg_profit=avg_profit,
                success_rate=success_rate,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                win_rate=win_rate,
                loss_rate=loss_rate,
                profit_factor=profit_factor
            )
            
        except Exception as e:
            logger.error(f"Error generating performance report: {str(e)}")
            return self._get_empty_performance_report(symbol)
    
    def generate_system_health_report(self) -> SystemHealthReport:
        """Generate system health report"""
        try:
            # Calculate uptime
            uptime = time.time() - self.start_time
            
            # Get system metrics (simplified for Render)
            memory_usage = self._get_memory_usage()
            cpu_usage = self._get_cpu_usage()
            
            # Calculate API calls per minute
            api_calls_per_minute = self._calculate_api_calls_per_minute()
            
            # Calculate error rate
            error_rate = self._calculate_error_rate()
            
            # Connection status
            connection_status = {
                'binance': True,  # Simplified
                'kraken': True    # Simplified
            }
            
            # Active trades and transfers
            active_trades = len([t for t in self.trade_history if t.get('status') == 'active'])
            pending_transfers = 0  # Would be tracked separately
            
            return SystemHealthReport(
                timestamp=time.time(),
                uptime=uptime,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage,
                api_calls_per_minute=api_calls_per_minute,
                error_rate=error_rate,
                connection_status=connection_status,
                active_trades=active_trades,
                pending_transfers=pending_transfers
            )
            
        except Exception as e:
            logger.error(f"Error generating system health report: {str(e)}")
            return self._get_empty_system_health_report()
    
    def _calculate_max_drawdown(self, profits: List[float]) -> float:
        """Calculate maximum drawdown"""
        try:
            if not profits:
                return 0.0
            
            cumulative_profits = []
            running_total = 0
            for profit in profits:
                running_total += profit
                cumulative_profits.append(running_total)
            
            peak = cumulative_profits[0]
            max_drawdown = 0
            
            for value in cumulative_profits:
                if value > peak:
                    peak = value
                drawdown = peak - value
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            return max_drawdown
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {str(e)}")
            return 0.0
    
    def _calculate_sharpe_ratio(self, profits: List[float]) -> float:
        """Calculate Sharpe ratio (simplified)"""
        try:
            if len(profits) < 2:
                return 0.0
            
            mean_return = sum(profits) / len(profits)
            variance = sum((p - mean_return) ** 2 for p in profits) / len(profits)
            std_dev = variance ** 0.5
            
            if std_dev == 0:
                return 0.0
            
            # Assume risk-free rate of 0 for simplicity
            sharpe_ratio = mean_return / std_dev
            return sharpe_ratio
            
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {str(e)}")
            return 0.0
    
    def _get_memory_usage(self) -> float:
        """Get memory usage percentage"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            return 50.0  # Default value
    
    def _get_cpu_usage(self) -> float:
        """Get CPU usage percentage"""
        try:
            import psutil
            return psutil.cpu_percent()
        except ImportError:
            return 25.0  # Default value
    
    def _calculate_api_calls_per_minute(self) -> int:
        """Calculate API calls per minute"""
        try:
            # Count API calls in the last minute
            current_time = time.time()
            minute_ago = current_time - 60
            
            api_calls = 0
            for trade in self.trade_history:
                if trade.get('timestamp', 0) > minute_ago:
                    api_calls += 2  # Buy and sell orders
            
            return api_calls
            
        except Exception as e:
            logger.error(f"Error calculating API calls per minute: {str(e)}")
            return 0
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate"""
        try:
            if not self.error_log:
                return 0.0
            
            # Calculate errors in the last hour
            current_time = time.time()
            hour_ago = current_time - 3600
            
            recent_errors = len([e for e in self.error_log if e.get('timestamp', 0) > hour_ago])
            recent_trades = len([t for t in self.trade_history if t.get('timestamp', 0) > hour_ago])
            
            if recent_trades == 0:
                return 0.0
            
            error_rate = recent_errors / recent_trades
            return min(error_rate, 1.0)  # Cap at 100%
            
        except Exception as e:
            logger.error(f"Error calculating error rate: {str(e)}")
            return 0.0
    
    def _get_empty_performance_report(self, symbol: str = None) -> PerformanceReport:
        """Get empty performance report"""
        return PerformanceReport(
            timestamp=time.time(),
            symbol=symbol or 'ALL',
            trade_count=0,
            successful_trades=0,
            total_profit=0.0,
            avg_profit=0.0,
            success_rate=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            win_rate=0.0,
            loss_rate=0.0,
            profit_factor=0.0
        )
    
    def _get_empty_system_health_report(self) -> SystemHealthReport:
        """Get empty system health report"""
        return SystemHealthReport(
            timestamp=time.time(),
            uptime=0.0,
            memory_usage=0.0,
            cpu_usage=0.0,
            api_calls_per_minute=0,
            error_rate=0.0,
            connection_status={'binance': False, 'kraken': False},
            active_trades=0,
            pending_transfers=0
        )
    
    def log_daily_summary(self):
        """Log daily summary report"""
        try:
            # Generate reports
            overall_performance = self.generate_performance_report()
            system_health = self.generate_system_health_report()
            
            # Create summary
            summary = {
                'timestamp': time.time(),
                'date': datetime.now().strftime('%Y-%m-%d'),
                'performance': asdict(overall_performance),
                'system_health': asdict(system_health),
                'top_performing_symbols': self._get_top_performing_symbols(),
                'error_summary': self._get_error_summary()
            }
            
            logger.info(f"DAILY_SUMMARY: {json.dumps(summary)}")
            
        except Exception as e:
            logger.error(f"Error logging daily summary: {str(e)}")
    
    def _get_top_performing_symbols(self) -> List[Dict]:
        """Get top performing symbols"""
        try:
            symbol_performance = {}
            
            for trade in self.trade_history:
                symbol = trade.get('symbol', '')
                if symbol not in symbol_performance:
                    symbol_performance[symbol] = {'trades': 0, 'profit': 0}
                
                symbol_performance[symbol]['trades'] += 1
                symbol_performance[symbol]['profit'] += trade.get('profit', 0)
            
            # Sort by profit
            sorted_symbols = sorted(
                symbol_performance.items(),
                key=lambda x: x[1]['profit'],
                reverse=True
            )
            
            # Return top 5
            return [
                {
                    'symbol': symbol,
                    'trades': data['trades'],
                    'total_profit': data['profit'],
                    'avg_profit': data['profit'] / data['trades'] if data['trades'] > 0 else 0
                }
                for symbol, data in sorted_symbols[:5]
            ]
            
        except Exception as e:
            logger.error(f"Error getting top performing symbols: {str(e)}")
            return []
    
    def _get_error_summary(self) -> Dict:
        """Get error summary"""
        try:
            if not self.error_log:
                return {'total_errors': 0, 'error_types': {}}
            
            error_types = {}
            for error in self.error_log:
                error_type = error.get('error_type', 'unknown')
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            return {
                'total_errors': len(self.error_log),
                'error_types': error_types,
                'recent_errors': len([e for e in self.error_log if e.get('timestamp', 0) > time.time() - 3600])
            }
            
        except Exception as e:
            logger.error(f"Error getting error summary: {str(e)}")
            return {'total_errors': 0, 'error_types': {}}
    
    def get_realtime_metrics(self) -> Dict:
        """Get real-time metrics for monitoring"""
        try:
            current_time = time.time()
            
            # Recent trades (last hour)
            recent_trades = [t for t in self.trade_history if t.get('timestamp', 0) > current_time - 3600]
            
            # Recent opportunities (last hour)
            recent_opportunities = len([t for t in self.trade_history if t.get('event') == 'arbitrage_opportunity' and t.get('timestamp', 0) > current_time - 3600])
            
            # Recent errors (last hour)
            recent_errors = [e for e in self.error_log if e.get('timestamp', 0) > current_time - 3600]
            
            return {
                'timestamp': current_time,
                'recent_trades': len(recent_trades),
                'recent_opportunities': recent_opportunities,
                'recent_errors': len(recent_errors),
                'total_trades': len(self.trade_history),
                'uptime': current_time - self.start_time,
                'success_rate': len([t for t in recent_trades if t.get('profit', 0) > 0]) / len(recent_trades) if recent_trades else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting realtime metrics: {str(e)}")
            return {'timestamp': time.time(), 'error': str(e)}

