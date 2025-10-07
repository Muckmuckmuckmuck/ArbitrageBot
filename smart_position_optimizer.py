import asyncio
import time
import statistics
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class PositionSizingData:
    """Data class for position sizing calculations"""
    symbol: str
    spread: float
    market_depth: float
    volatility: float
    kelly_fraction: float
    risk_adjusted_size: float
    optimal_size: float
    confidence: float
    timestamp: float

@dataclass
class TradePerformance:
    """Data class for trade performance tracking"""
    symbol: str
    position_size: float
    profit: float
    success: bool
    spread: float
    execution_time: float
    timestamp: float

class SmartPositionOptimizer:
    """Smart position sizing using Kelly criterion and market depth analysis"""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.trade_history = {}
        self.performance_metrics = {}
        self.kelly_parameters = {}
        self.market_depth_cache = {}
        
        # Kelly criterion parameters by symbol
        self.kelly_params = {
            # Tier 1 assets - more aggressive due to high liquidity
            'XRP/USDT': {'win_rate': 0.70, 'avg_win': 0.85, 'avg_loss': 0.25},
            'XLM/USDT': {'win_rate': 0.68, 'avg_win': 0.80, 'avg_loss': 0.30},
            'SOL/USDT': {'win_rate': 0.72, 'avg_win': 0.90, 'avg_loss': 0.28},
            'BNB/USDT': {'win_rate': 0.75, 'avg_win': 0.88, 'avg_loss': 0.22},
            'USDC/USDT': {'win_rate': 0.85, 'avg_win': 0.95, 'avg_loss': 0.15},
            'USDT/USDC': {'win_rate': 0.85, 'avg_win': 0.95, 'avg_loss': 0.15},
            'DAI/USDT': {'win_rate': 0.80, 'avg_win': 0.90, 'avg_loss': 0.20},
            'BUSD/USDT': {'win_rate': 0.82, 'avg_win': 0.92, 'avg_loss': 0.18},
            'UNI/USDT': {'win_rate': 0.68, 'avg_win': 0.82, 'avg_loss': 0.32},
            'LINK/USDT': {'win_rate': 0.70, 'avg_win': 0.85, 'avg_loss': 0.28},
            'ADA/USDT': {'win_rate': 0.72, 'avg_win': 0.88, 'avg_loss': 0.25},
            'DOT/USDT': {'win_rate': 0.68, 'avg_win': 0.80, 'avg_loss': 0.30},
            'AVAX/USDT': {'win_rate': 0.70, 'avg_win': 0.85, 'avg_loss': 0.28},
            'TON/USDT': {'win_rate': 0.65, 'avg_win': 0.78, 'avg_loss': 0.35},
            'MATIC/USDT': {'win_rate': 0.72, 'avg_win': 0.88, 'avg_loss': 0.25},
            'EOS/USDT': {'win_rate': 0.68, 'avg_win': 0.82, 'avg_loss': 0.32},
            'TRX/USDT': {'win_rate': 0.70, 'avg_win': 0.85, 'avg_loss': 0.28},
            
            # Tier 2 assets - moderate parameters
            'XTZ/USDT': {'win_rate': 0.65, 'avg_win': 0.75, 'avg_loss': 0.35},
            'MKR/USDT': {'win_rate': 0.62, 'avg_win': 0.72, 'avg_loss': 0.38},
            'FIL/USDT': {'win_rate': 0.63, 'avg_win': 0.75, 'avg_loss': 0.37},
            'ATOM/USDT': {'win_rate': 0.68, 'avg_win': 0.80, 'avg_loss': 0.32},
            'AAVE/USDT': {'win_rate': 0.65, 'avg_win': 0.78, 'avg_loss': 0.35},
            'COMP/USDT': {'win_rate': 0.63, 'avg_win': 0.75, 'avg_loss': 0.37},
            'CRV/USDT': {'win_rate': 0.62, 'avg_win': 0.72, 'avg_loss': 0.38},
            'SNX/USDT': {'win_rate': 0.64, 'avg_win': 0.76, 'avg_loss': 0.36},
            'YFI/USDT': {'win_rate': 0.60, 'avg_win': 0.70, 'avg_loss': 0.40},
            '1INCH/USDT': {'win_rate': 0.63, 'avg_win': 0.75, 'avg_loss': 0.37},
            
            # Tier 3 assets - conservative parameters
            'LTC/USDT': {'win_rate': 0.70, 'avg_win': 0.85, 'avg_loss': 0.28},
            'DOGE/USDT': {'win_rate': 0.65, 'avg_win': 0.78, 'avg_loss': 0.35},
            'VET/USDT': {'win_rate': 0.68, 'avg_win': 0.80, 'avg_loss': 0.32},
            'BCH/USDT': {'win_rate': 0.70, 'avg_win': 0.85, 'avg_loss': 0.28},
            'XMR/USDT': {'win_rate': 0.65, 'avg_win': 0.75, 'avg_loss': 0.35},
        }
        
        # Risk parameters
        self.risk_parameters = {
            'max_kelly_fraction': 0.25,  # Maximum 25% of capital per trade
            'min_position_size': 100,    # Minimum $100 position
            'max_position_size': 10000,  # Maximum $10,000 position
            'volatility_adjustment': 0.8, # Reduce size for high volatility
            'market_depth_factor': 0.1,   # Use 10% of available liquidity
            'confidence_threshold': 0.6,  # Minimum confidence for Kelly sizing
        }
        
    async def calculate_optimal_position_size(self, symbol: str, spread: float, 
                                            current_price: float) -> PositionSizingData:
        """Calculate optimal position size using Kelly criterion and market depth"""
        try:
            # Get Kelly parameters for symbol
            kelly_params = self.kelly_params.get(symbol, {
                'win_rate': 0.65, 'avg_win': 0.80, 'avg_loss': 0.30
            })
            
            # Calculate Kelly fraction
            kelly_fraction = self._calculate_kelly_fraction(kelly_params, spread)
            
            # Get market depth
            market_depth = await self._get_market_depth(symbol)
            
            # Calculate volatility
            volatility = await self._get_volatility(symbol)
            
            # Risk adjustment
            risk_adjustment = self._calculate_risk_adjustment(volatility, market_depth)
            
            # Calculate optimal size
            base_size = self._calculate_base_position_size(
                kelly_fraction, market_depth, current_price
            )
            
            # Apply risk adjustment
            risk_adjusted_size = base_size * risk_adjustment
            
            # Apply position limits
            optimal_size = self._apply_position_limits(risk_adjusted_size, symbol)
            
            # Calculate confidence
            confidence = self._calculate_confidence(kelly_params, volatility, market_depth)
            
            sizing_data = PositionSizingData(
                symbol=symbol,
                spread=spread,
                market_depth=market_depth,
                volatility=volatility,
                kelly_fraction=kelly_fraction,
                risk_adjusted_size=risk_adjusted_size,
                optimal_size=optimal_size,
                confidence=confidence,
                timestamp=time.time()
            )
            
            logger.info(f"Position sizing for {symbol}: {optimal_size:.2f} units "
                       f"(Kelly: {kelly_fraction:.3f}, Confidence: {confidence:.3f})")
            
            return sizing_data
            
        except Exception as e:
            logger.error(f"Error calculating optimal position size for {symbol}: {str(e)}")
            # Return conservative fallback
            return PositionSizingData(
                symbol=symbol,
                spread=spread,
                market_depth=10000,
                volatility=0.05,
                kelly_fraction=0.1,
                risk_adjusted_size=1000,
                optimal_size=1000,
                confidence=0.5,
                timestamp=time.time()
            )
    
    def _calculate_kelly_fraction(self, kelly_params: Dict, spread: float) -> float:
        """Calculate Kelly fraction for position sizing"""
        try:
            win_rate = kelly_params['win_rate']
            avg_win = kelly_params['avg_win']
            avg_loss = kelly_params['avg_loss']
            
            # Adjust for spread
            adjusted_avg_win = avg_win * spread
            adjusted_avg_loss = avg_loss * spread
            
            # Kelly formula: f = (bp - q) / b
            # where b = odds (avg_win / avg_loss), p = win_rate, q = (1 - win_rate)
            if adjusted_avg_loss == 0:
                return 0.0
            
            b = adjusted_avg_win / adjusted_avg_loss
            p = win_rate
            q = 1 - win_rate
            
            kelly_fraction = (b * p - q) / b
            
            # Ensure positive and within limits
            kelly_fraction = max(0.0, min(kelly_fraction, self.risk_parameters['max_kelly_fraction']))
            
            return kelly_fraction
            
        except Exception as e:
            logger.error(f"Error calculating Kelly fraction: {str(e)}")
            return 0.1  # Conservative fallback
    
    async def _get_market_depth(self, symbol: str) -> float:
        """Get market depth for position sizing"""
        try:
            # Check cache first
            cache_key = f"{symbol}_depth"
            if (cache_key in self.market_depth_cache and 
                time.time() - self.market_depth_cache[cache_key]['timestamp'] < 30):
                return self.market_depth_cache[cache_key]['depth']
            
            # Get order book from both exchanges
            binance_exchange = self.exchange_manager.get_exchange('binance')
            kraken_exchange = self.exchange_manager.get_exchange('kraken')
            
            binance_orderbook = await binance_exchange.get_orderbook(symbol, 20)
            kraken_orderbook = await kraken_exchange.get_orderbook(symbol, 20)
            
            if not binance_orderbook or not kraken_orderbook:
                return 50000  # Default depth
            
            # Calculate depth for top 20 levels
            binance_depth = sum(price * qty for price, qty in binance_orderbook.get('asks', [])[:20])
            kraken_depth = sum(price * qty for price, qty in kraken_orderbook.get('asks', [])[:20])
            
            # Use the smaller depth to be conservative
            market_depth = min(binance_depth, kraken_depth)
            
            # Cache the result
            self.market_depth_cache[cache_key] = {
                'depth': market_depth,
                'timestamp': time.time()
            }
            
            return market_depth
            
        except Exception as e:
            logger.error(f"Error getting market depth for {symbol}: {str(e)}")
            return 50000  # Default depth
    
    async def _get_volatility(self, symbol: str) -> float:
        """Get volatility estimate for risk adjustment"""
        try:
            # Get recent price history
            if symbol in self.trade_history:
                recent_trades = self.trade_history[symbol][-50:]  # Last 50 trades
                if len(recent_trades) > 10:
                    spreads = [trade.spread for trade in recent_trades]
                    volatility = statistics.stdev(spreads) if len(spreads) > 1 else 0.05
                    return min(volatility, 0.2)  # Cap at 20%
            
            # Default volatility based on symbol
            default_volatilities = {
                'USDC/USDT': 0.001, 'USDT/USDC': 0.001, 'DAI/USDT': 0.002, 'BUSD/USDT': 0.001,
                'XRP/USDT': 0.03, 'XLM/USDT': 0.03, 'SOL/USDT': 0.04, 'BNB/USDT': 0.03,
                'LTC/USDT': 0.04, 'DOGE/USDT': 0.05, 'VET/USDT': 0.04, 'BCH/USDT': 0.04,
            }
            
            return default_volatilities.get(symbol, 0.05)  # Default 5%
            
        except Exception as e:
            logger.error(f"Error getting volatility for {symbol}: {str(e)}")
            return 0.05  # Default 5%
    
    def _calculate_risk_adjustment(self, volatility: float, market_depth: float) -> float:
        """Calculate risk adjustment factor"""
        try:
            # Volatility adjustment
            volatility_factor = 1.0 - (volatility * self.risk_parameters['volatility_adjustment'])
            volatility_factor = max(0.5, min(volatility_factor, 1.0))
            
            # Market depth adjustment
            depth_factor = min(1.0, market_depth / 100000)  # Normalize to 100K
            depth_factor = max(0.3, depth_factor)  # Minimum 30%
            
            # Combined adjustment
            risk_adjustment = (volatility_factor + depth_factor) / 2
            
            return risk_adjustment
            
        except Exception as e:
            logger.error(f"Error calculating risk adjustment: {str(e)}")
            return 0.8  # Conservative fallback
    
    def _calculate_base_position_size(self, kelly_fraction: float, market_depth: float, 
                                    current_price: float) -> float:
        """Calculate base position size"""
        try:
            # Calculate size based on Kelly fraction and market depth
            kelly_size = kelly_fraction * 10000  # Assume $10K capital
            
            # Limit by market depth
            depth_limit = market_depth * self.risk_parameters['market_depth_factor']
            
            # Use the smaller of the two
            base_size = min(kelly_size, depth_limit)
            
            # Convert to units
            position_units = base_size / current_price
            
            return position_units
            
        except Exception as e:
            logger.error(f"Error calculating base position size: {str(e)}")
            return 1000  # Conservative fallback
    
    def _apply_position_limits(self, position_size: float, symbol: str) -> float:
        """Apply position limits based on symbol and risk parameters"""
        try:
            # Get symbol-specific limits
            symbol_limits = Config.POSITION_LIMITS.get(symbol, 5000)
            
            # Apply global limits
            min_size = self.risk_parameters['min_position_size']
            max_size = min(self.risk_parameters['max_position_size'], symbol_limits)
            
            # Apply limits
            limited_size = max(min_size, min(position_size, max_size))
            
            return limited_size
            
        except Exception as e:
            logger.error(f"Error applying position limits: {str(e)}")
            return 1000  # Conservative fallback
    
    def _calculate_confidence(self, kelly_params: Dict, volatility: float, market_depth: float) -> float:
        """Calculate confidence in position sizing"""
        try:
            # Base confidence from Kelly parameters
            base_confidence = kelly_params['win_rate']
            
            # Adjust for volatility (lower volatility = higher confidence)
            volatility_adjustment = 1.0 - (volatility * 2)
            volatility_adjustment = max(0.5, min(volatility_adjustment, 1.0))
            
            # Adjust for market depth (higher depth = higher confidence)
            depth_adjustment = min(1.0, market_depth / 100000)
            depth_adjustment = max(0.3, depth_adjustment)
            
            # Combined confidence
            confidence = base_confidence * volatility_adjustment * depth_adjustment
            
            return max(0.0, min(confidence, 1.0))
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {str(e)}")
            return 0.5  # Neutral confidence
    
    def record_trade_performance(self, symbol: str, position_size: float, profit: float, 
                               success: bool, spread: float, execution_time: float):
        """Record trade performance for learning"""
        try:
            if symbol not in self.trade_history:
                self.trade_history[symbol] = []
            
            trade_record = TradePerformance(
                symbol=symbol,
                position_size=position_size,
                profit=profit,
                success=success,
                spread=spread,
                execution_time=execution_time,
                timestamp=time.time()
            )
            
            self.trade_history[symbol].append(trade_record)
            
            # Keep only recent history (last 1000 records)
            if len(self.trade_history[symbol]) > 1000:
                self.trade_history[symbol] = self.trade_history[symbol][-1000:]
            
            # Update Kelly parameters based on performance
            self._update_kelly_parameters(symbol)
            
            logger.debug(f"Recorded trade performance for {symbol}: "
                        f"Size={position_size:.2f}, Profit=${profit:.2f}, Success={success}")
            
        except Exception as e:
            logger.error(f"Error recording trade performance: {str(e)}")
    
    def _update_kelly_parameters(self, symbol: str):
        """Update Kelly parameters based on recent performance"""
        try:
            if symbol not in self.trade_history:
                return
            
            recent_trades = self.trade_history[symbol][-100:]  # Last 100 trades
            if len(recent_trades) < 20:
                return
            
            # Calculate new parameters
            successful_trades = [t for t in recent_trades if t.success]
            failed_trades = [t for t in recent_trades if not t.success]
            
            if len(successful_trades) == 0 or len(failed_trades) == 0:
                return
            
            # Calculate new win rate
            new_win_rate = len(successful_trades) / len(recent_trades)
            
            # Calculate new average win/loss
            avg_win = sum(t.profit for t in successful_trades) / len(successful_trades)
            avg_loss = abs(sum(t.profit for t in failed_trades) / len(failed_trades))
            
            # Smooth the updates (weighted average with existing parameters)
            existing_params = self.kelly_params.get(symbol, {
                'win_rate': 0.65, 'avg_win': 0.80, 'avg_loss': 0.30
            })
            
            # Update with 20% weight for new data
            updated_params = {
                'win_rate': existing_params['win_rate'] * 0.8 + new_win_rate * 0.2,
                'avg_win': existing_params['avg_win'] * 0.8 + avg_win * 0.2,
                'avg_loss': existing_params['avg_loss'] * 0.8 + avg_loss * 0.2
            }
            
            # Ensure reasonable bounds
            updated_params['win_rate'] = max(0.3, min(updated_params['win_rate'], 0.9))
            updated_params['avg_win'] = max(0.1, min(updated_params['avg_win'], 2.0))
            updated_params['avg_loss'] = max(0.1, min(updated_params['avg_loss'], 1.0))
            
            # Update parameters
            self.kelly_params[symbol] = updated_params
            
            logger.info(f"Updated Kelly parameters for {symbol}: "
                       f"Win rate: {updated_params['win_rate']:.3f}, "
                       f"Avg win: {updated_params['avg_win']:.3f}, "
                       f"Avg loss: {updated_params['avg_loss']:.3f}")
            
        except Exception as e:
            logger.error(f"Error updating Kelly parameters: {str(e)}")
    
    def get_performance_summary(self, symbol: str = None, days: int = 30) -> Dict:
        """Get performance summary for position sizing"""
        try:
            current_time = time.time()
            cutoff_time = current_time - (days * 24 * 3600)
            
            if symbol:
                # Get specific symbol summary
                if symbol not in self.trade_history:
                    return {}
                
                recent_trades = [
                    t for t in self.trade_history[symbol]
                    if t.timestamp >= cutoff_time
                ]
                
                if not recent_trades:
                    return {}
                
                successful_trades = [t for t in recent_trades if t.success]
                
                summary = {
                    'symbol': symbol,
                    'total_trades': len(recent_trades),
                    'successful_trades': len(successful_trades),
                    'success_rate': len(successful_trades) / len(recent_trades) * 100,
                    'avg_profit': sum(t.profit for t in recent_trades) / len(recent_trades),
                    'avg_position_size': sum(t.position_size for t in recent_trades) / len(recent_trades),
                    'avg_execution_time': sum(t.execution_time for t in recent_trades) / len(recent_trades),
                    'kelly_parameters': self.kelly_params.get(symbol, {}),
                    'time_period_days': days
                }
                
                return summary
            else:
                # Get all symbols summary
                summary = {}
                for sym in self.trade_history.keys():
                    sym_summary = self.get_performance_summary(sym, days)
                    if sym_summary:
                        summary[sym] = sym_summary
                
                return summary
                
        except Exception as e:
            logger.error(f"Error getting performance summary: {str(e)}")
            return {}
    
    def get_optimization_recommendations(self, symbol: str) -> List[str]:
        """Get optimization recommendations for position sizing"""
        try:
            recommendations = []
            
            if symbol not in self.trade_history:
                return ["No historical data available for recommendations"]
            
            recent_trades = self.trade_history[symbol][-50:]  # Last 50 trades
            if len(recent_trades) < 10:
                return ["Insufficient data for recommendations"]
            
            # Analyze performance
            successful_trades = [t for t in recent_trades if t.success]
            success_rate = len(successful_trades) / len(recent_trades)
            
            # Success rate recommendations
            if success_rate > 0.8:
                recommendations.append("High success rate - consider increasing position size by 20%")
            elif success_rate < 0.5:
                recommendations.append("Low success rate - consider decreasing position size by 30%")
            
            # Profit analysis
            avg_profit = sum(t.profit for t in recent_trades) / len(recent_trades)
            if avg_profit > 0:
                recommendations.append("Positive average profit - current sizing appears optimal")
            else:
                recommendations.append("Negative average profit - review position sizing strategy")
            
            # Execution time analysis
            avg_execution_time = sum(t.execution_time for t in recent_trades) / len(recent_trades)
            if avg_execution_time > 5.0:  # 5 seconds
                recommendations.append("Slow execution - consider reducing position size for faster fills")
            
            # Volatility analysis
            spreads = [t.spread for t in recent_trades]
            if len(spreads) > 1:
                spread_volatility = statistics.stdev(spreads)
                if spread_volatility > 0.5:
                    recommendations.append("High spread volatility - consider more conservative sizing")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting optimization recommendations: {str(e)}")
            return ["Error generating recommendations"]

