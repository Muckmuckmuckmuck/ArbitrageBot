import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class OrderBookLevel:
    """Data class for order book level"""
    price: float
    quantity: float
    cumulative_quantity: float
    cumulative_value: float

@dataclass
class OrderBook:
    """Data class for order book"""
    symbol: str
    exchange: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    timestamp: float
    spread: float
    mid_price: float

@dataclass
class SmartOrder:
    """Data class for smart order"""
    symbol: str
    side: str
    quantity: float
    order_type: str
    limit_price: Optional[float]
    stop_price: Optional[float]
    time_in_force: str
    exchange: str
    expected_fill_price: float
    expected_slippage: float
    confidence: float

@dataclass
class OrderExecution:
    """Data class for order execution"""
    order_id: str
    symbol: str
    side: str
    quantity: float
    executed_quantity: float
    average_price: float
    execution_time: float
    slippage: float
    success: bool
    error_message: Optional[str]

class SmartOrderRouter:
    """Smart order routing and slippage reduction system"""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.order_book_cache = {}
        self.execution_history = {}
        self.slippage_history = {}
        
        # Order routing strategies
        self.routing_strategies = {
            'twap': self._execute_twap_order,
            'vwap': self._execute_vwap_order,
            'iceberg': self._execute_iceberg_order,
            'limit': self._execute_limit_order,
            'market': self._execute_market_order
        }
        
        # Slippage protection parameters
        self.slippage_limits = {
            'XRP/USDT': 0.5, 'XLM/USDT': 0.5, 'SOL/USDT': 0.5,
            'USDC/USDT': 0.1, 'USDT/USDC': 0.1, 'DAI/USDT': 0.1,
            'BNB/USDT': 0.3, 'LINK/USDT': 0.4, 'UNI/USDT': 0.4,
            'ADA/USDT': 0.3, 'DOT/USDT': 0.4, 'AVAX/USDT': 0.4,
            'TON/USDT': 0.6, 'MATIC/USDT': 0.4, 'EOS/USDT': 0.4,
            'TRX/USDT': 0.4, 'LTC/USDT': 0.3, 'DOGE/USDT': 0.4,
            'VET/USDT': 0.4, 'BCH/USDT': 0.4, 'XMR/USDT': 0.5,
            'default': 0.5
        }
        
        # Order size thresholds for strategy selection
        self.strategy_thresholds = {
            'small': 1000,      # < $1K - use market orders
            'medium': 5000,     # $1K-$5K - use limit orders
            'large': 20000,     # $5K-$20K - use TWAP
            'very_large': 50000 # > $20K - use VWAP or Iceberg
        }
        
        # Performance tracking
        self.performance_metrics = {}
        self.strategy_success_rates = {}
        
    async def route_order(self, symbol: str, side: str, quantity: float, 
                         price: Optional[float] = None, strategy: str = 'auto') -> SmartOrder:
        """Route an order using smart order routing"""
        try:
            # Get current order book
            order_book = await self._get_order_book(symbol)
            if not order_book:
                logger.error(f"Could not get order book for {symbol}")
                return None
            
            # Calculate order value
            mid_price = order_book.mid_price
            order_value = quantity * mid_price
            
            # Select optimal strategy
            if strategy == 'auto':
                strategy = self._select_optimal_strategy(symbol, side, quantity, order_value, order_book)
            
            # Calculate expected execution parameters
            expected_fill_price, expected_slippage = self._calculate_execution_parameters(
                symbol, side, quantity, order_book, strategy
            )
            
            # Check slippage limits
            max_slippage = self.slippage_limits.get(symbol, self.slippage_limits['default'])
            if expected_slippage > max_slippage:
                logger.warning(f"Expected slippage {expected_slippage:.3f}% exceeds limit {max_slippage:.3f}% for {symbol}")
                # Adjust order size or strategy
                quantity = self._adjust_order_size_for_slippage(symbol, side, quantity, order_book, max_slippage)
                if quantity <= 0:
                    return None
                expected_fill_price, expected_slippage = self._calculate_execution_parameters(
                    symbol, side, quantity, order_book, strategy
                )
            
            # Create smart order
            smart_order = SmartOrder(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=self._get_order_type_for_strategy(strategy),
                limit_price=self._calculate_limit_price(symbol, side, quantity, order_book, strategy),
                stop_price=None,
                time_in_force='GTC',
                exchange='binance',  # Default exchange
                expected_fill_price=expected_fill_price,
                expected_slippage=expected_slippage,
                confidence=self._calculate_execution_confidence(symbol, side, quantity, order_book, strategy)
            )
            
            logger.info(f"Routed {side} order for {quantity:.4f} {symbol}: "
                       f"Strategy={strategy}, Expected price={expected_fill_price:.6f}, "
                       f"Slippage={expected_slippage:.3f}%, Confidence={smart_order.confidence:.3f}")
            
            return smart_order
            
        except Exception as e:
            logger.error(f"Error routing order for {symbol}: {str(e)}")
            return None
    
    async def _get_order_book(self, symbol: str) -> Optional[OrderBook]:
        """Get order book for a symbol"""
        try:
            # Check cache first
            cache_key = f"{symbol}_orderbook"
            if (cache_key in self.order_book_cache and 
                time.time() - self.order_book_cache[cache_key]['timestamp'] < 1.0):
                return self.order_book_cache[cache_key]['data']
            
            # Get order book from both exchanges
            binance_exchange = self.exchange_manager.get_exchange('binance')
            kraken_exchange = self.exchange_manager.get_exchange('kraken')
            
            binance_orderbook = await binance_exchange.get_orderbook(symbol, 50)
            kraken_orderbook = await kraken_exchange.get_orderbook(symbol, 50)
            
            if not binance_orderbook or not kraken_orderbook:
                return None
            
            # Process Binance order book
            binance_bids = self._process_order_book_levels(binance_orderbook.get('bids', []), 'bid')
            binance_asks = self._process_order_book_levels(binance_orderbook.get('asks', []), 'ask')
            
            # Process Kraken order book
            kraken_bids = self._process_order_book_levels(kraken_orderbook.get('bids', []), 'bid')
            kraken_asks = self._process_order_book_levels(kraken_orderbook.get('asks', []), 'ask')
            
            # Combine order books (use Binance as primary)
            combined_bids = binance_bids
            combined_asks = binance_asks
            
            # Calculate spread and mid price
            if combined_bids and combined_asks:
                best_bid = combined_bids[0].price
                best_ask = combined_asks[0].price
                mid_price = (best_bid + best_ask) / 2
                spread = (best_ask - best_bid) / mid_price * 100
            else:
                mid_price = 0.0
                spread = 0.0
            
            order_book = OrderBook(
                symbol=symbol,
                exchange='combined',
                bids=combined_bids,
                asks=combined_asks,
                timestamp=time.time(),
                spread=spread,
                mid_price=mid_price
            )
            
            # Cache the result
            self.order_book_cache[cache_key] = {
                'data': order_book,
                'timestamp': time.time()
            }
            
            return order_book
            
        except Exception as e:
            logger.error(f"Error getting order book for {symbol}: {str(e)}")
            return None
    
    def _process_order_book_levels(self, levels: List[List], side: str) -> List[OrderBookLevel]:
        """Process raw order book levels"""
        try:
            processed_levels = []
            cumulative_quantity = 0
            cumulative_value = 0
            
            for level in levels:
                if len(level) >= 2:
                    price = float(level[0])
                    quantity = float(level[1])
                    
                    cumulative_quantity += quantity
                    cumulative_value += price * quantity
                    
                    processed_level = OrderBookLevel(
                        price=price,
                        quantity=quantity,
                        cumulative_quantity=cumulative_quantity,
                        cumulative_value=cumulative_value
                    )
                    
                    processed_levels.append(processed_level)
            
            return processed_levels
            
        except Exception as e:
            logger.error(f"Error processing order book levels: {str(e)}")
            return []
    
    def _select_optimal_strategy(self, symbol: str, side: str, quantity: float, 
                               order_value: float, order_book: OrderBook) -> str:
        """Select optimal order routing strategy"""
        try:
            # Strategy selection based on order size
            if order_value < self.strategy_thresholds['small']:
                return 'market'
            elif order_value < self.strategy_thresholds['medium']:
                return 'limit'
            elif order_value < self.strategy_thresholds['large']:
                return 'twap'
            elif order_value < self.strategy_thresholds['very_large']:
                return 'vwap'
            else:
                return 'iceberg'
                
        except Exception as e:
            logger.error(f"Error selecting optimal strategy: {str(e)}")
            return 'market'
    
    def _calculate_execution_parameters(self, symbol: str, side: str, quantity: float, 
                                      order_book: OrderBook, strategy: str) -> Tuple[float, float]:
        """Calculate expected execution parameters"""
        try:
            if side == 'buy':
                levels = order_book.asks
                best_price = levels[0].price if levels else 0.0
            else:
                levels = order_book.bids
                best_price = levels[0].price if levels else 0.0
            
            if not levels:
                return 0.0, 100.0  # High slippage if no liquidity
            
            # Calculate expected fill price based on strategy
            if strategy == 'market':
                expected_price = self._calculate_market_fill_price(quantity, levels)
            elif strategy == 'limit':
                expected_price = best_price
            elif strategy == 'twap':
                expected_price = self._calculate_twap_fill_price(quantity, levels)
            elif strategy == 'vwap':
                expected_price = self._calculate_vwap_fill_price(quantity, levels)
            elif strategy == 'iceberg':
                expected_price = self._calculate_iceberg_fill_price(quantity, levels)
            else:
                expected_price = best_price
            
            # Calculate slippage
            slippage = abs(expected_price - best_price) / best_price * 100
            
            return expected_price, slippage
            
        except Exception as e:
            logger.error(f"Error calculating execution parameters: {str(e)}")
            return 0.0, 100.0
    
    def _calculate_market_fill_price(self, quantity: float, levels: List[OrderBookLevel]) -> float:
        """Calculate expected fill price for market order"""
        try:
            remaining_quantity = quantity
            total_value = 0.0
            
            for level in levels:
                if remaining_quantity <= 0:
                    break
                
                fill_quantity = min(remaining_quantity, level.quantity)
                total_value += fill_quantity * level.price
                remaining_quantity -= fill_quantity
            
            if remaining_quantity > 0:
                # Not enough liquidity
                return 0.0
            
            return total_value / quantity
            
        except Exception as e:
            logger.error(f"Error calculating market fill price: {str(e)}")
            return 0.0
    
    def _calculate_twap_fill_price(self, quantity: float, levels: List[OrderBookLevel]) -> float:
        """Calculate expected fill price for TWAP order"""
        try:
            # TWAP assumes uniform execution over time
            # Use average of top 10 levels
            top_levels = levels[:10]
            if not top_levels:
                return 0.0
            
            avg_price = sum(level.price for level in top_levels) / len(top_levels)
            return avg_price
            
        except Exception as e:
            logger.error(f"Error calculating TWAP fill price: {str(e)}")
            return 0.0
    
    def _calculate_vwap_fill_price(self, quantity: float, levels: List[OrderBookLevel]) -> float:
        """Calculate expected fill price for VWAP order"""
        try:
            # VWAP weights by volume
            total_volume = 0.0
            weighted_price = 0.0
            
            for level in levels:
                if total_volume >= quantity:
                    break
                
                level_volume = min(level.quantity, quantity - total_volume)
                weighted_price += level.price * level_volume
                total_volume += level_volume
            
            if total_volume == 0:
                return 0.0
            
            return weighted_price / total_volume
            
        except Exception as e:
            logger.error(f"Error calculating VWAP fill price: {str(e)}")
            return 0.0
    
    def _calculate_iceberg_fill_price(self, quantity: float, levels: List[OrderBookLevel]) -> float:
        """Calculate expected fill price for iceberg order"""
        try:
            # Iceberg order executes in small chunks
            # Use average of top 5 levels with some market impact
            top_levels = levels[:5]
            if not top_levels:
                return 0.0
            
            base_price = sum(level.price for level in top_levels) / len(top_levels)
            
            # Add market impact based on order size
            impact_factor = min(0.01, quantity / 1000000)  # Max 1% impact
            market_impact = base_price * impact_factor
            
            return base_price + market_impact
            
        except Exception as e:
            logger.error(f"Error calculating iceberg fill price: {str(e)}")
            return 0.0
    
    def _get_order_type_for_strategy(self, strategy: str) -> str:
        """Get order type for strategy"""
        strategy_order_types = {
            'market': 'market',
            'limit': 'limit',
            'twap': 'limit',
            'vwap': 'limit',
            'iceberg': 'limit'
        }
        
        return strategy_order_types.get(strategy, 'market')
    
    def _calculate_limit_price(self, symbol: str, side: str, quantity: float, 
                             order_book: OrderBook, strategy: str) -> Optional[float]:
        """Calculate optimal limit price"""
        try:
            if strategy == 'market':
                return None
            
            if side == 'buy':
                # For buy orders, use slightly above best bid
                best_bid = order_book.bids[0].price if order_book.bids else 0.0
                if best_bid > 0:
                    return best_bid * 1.001  # 0.1% above best bid
            else:
                # For sell orders, use slightly below best ask
                best_ask = order_book.asks[0].price if order_book.asks else 0.0
                if best_ask > 0:
                    return best_ask * 0.999  # 0.1% below best ask
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating limit price: {str(e)}")
            return None
    
    def _calculate_execution_confidence(self, symbol: str, side: str, quantity: float, 
                                      order_book: OrderBook, strategy: str) -> float:
        """Calculate confidence in order execution"""
        try:
            # Base confidence
            base_confidence = 0.8
            
            # Adjust for order book depth
            if side == 'buy':
                levels = order_book.asks
            else:
                levels = order_book.bids
            
            if not levels:
                return 0.0
            
            # Check if we can fill the order
            total_available = sum(level.quantity for level in levels[:10])  # Top 10 levels
            fill_ratio = min(1.0, total_available / quantity)
            
            # Adjust confidence based on fill ratio
            confidence = base_confidence * fill_ratio
            
            # Adjust for spread
            spread_factor = max(0.5, 1.0 - order_book.spread / 10.0)  # Reduce confidence for wide spreads
            confidence *= spread_factor
            
            # Adjust for strategy
            strategy_confidence = {
                'market': 0.9,
                'limit': 0.7,
                'twap': 0.8,
                'vwap': 0.8,
                'iceberg': 0.6
            }
            
            confidence *= strategy_confidence.get(strategy, 0.8)
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            logger.error(f"Error calculating execution confidence: {str(e)}")
            return 0.5
    
    def _adjust_order_size_for_slippage(self, symbol: str, side: str, quantity: float, 
                                      order_book: OrderBook, max_slippage: float) -> float:
        """Adjust order size to stay within slippage limits"""
        try:
            if side == 'buy':
                levels = order_book.asks
            else:
                levels = order_book.bids
            
            if not levels:
                return 0.0
            
            best_price = levels[0].price
            adjusted_quantity = 0.0
            
            for level in levels:
                # Calculate slippage for this level
                slippage = abs(level.price - best_price) / best_price * 100
                
                if slippage <= max_slippage:
                    adjusted_quantity += level.quantity
                else:
                    break
            
            # Return 80% of adjusted quantity for safety
            return adjusted_quantity * 0.8
            
        except Exception as e:
            logger.error(f"Error adjusting order size for slippage: {str(e)}")
            return 0.0
    
    async def execute_order(self, smart_order: SmartOrder) -> OrderExecution:
        """Execute a smart order"""
        try:
            start_time = time.time()
            
            # Get exchange
            exchange = self.exchange_manager.get_exchange(smart_order.exchange)
            
            # Execute based on order type
            if smart_order.order_type == 'market':
                result = await exchange.place_market_order(
                    smart_order.symbol, smart_order.side, smart_order.quantity
                )
            else:
                result = await exchange.place_limit_order(
                    smart_order.symbol, smart_order.side, smart_order.quantity, smart_order.limit_price
                )
            
            execution_time = time.time() - start_time
            
            if result and 'id' in result:
                # Calculate actual slippage
                actual_slippage = abs(result.get('average_price', 0) - smart_order.expected_fill_price) / smart_order.expected_fill_price * 100
                
                execution = OrderExecution(
                    order_id=result['id'],
                    symbol=smart_order.symbol,
                    side=smart_order.side,
                    quantity=smart_order.quantity,
                    executed_quantity=result.get('executed_quantity', 0),
                    average_price=result.get('average_price', 0),
                    execution_time=execution_time,
                    slippage=actual_slippage,
                    success=True,
                    error_message=None
                )
                
                # Record execution for learning
                self._record_execution(execution, smart_order)
                
                logger.info(f"Order executed successfully: {result['id']}, "
                           f"Slippage: {actual_slippage:.3f}%, Time: {execution_time:.3f}s")
                
                return execution
            else:
                # Order failed
                execution = OrderExecution(
                    order_id='',
                    symbol=smart_order.symbol,
                    side=smart_order.side,
                    quantity=smart_order.quantity,
                    executed_quantity=0,
                    average_price=0,
                    execution_time=execution_time,
                    slippage=0,
                    success=False,
                    error_message=result.get('error', 'Unknown error') if result else 'No result'
                )
                
                logger.error(f"Order execution failed: {execution.error_message}")
                return execution
            
        except Exception as e:
            logger.error(f"Error executing order: {str(e)}")
            return OrderExecution(
                order_id='',
                symbol=smart_order.symbol,
                side=smart_order.side,
                quantity=smart_order.quantity,
                executed_quantity=0,
                average_price=0,
                execution_time=0,
                slippage=0,
                success=False,
                error_message=str(e)
            )
    
    def _record_execution(self, execution: OrderExecution, smart_order: SmartOrder):
        """Record order execution for learning"""
        try:
            symbol = execution.symbol
            
            if symbol not in self.execution_history:
                self.execution_history[symbol] = []
            
            execution_record = {
                'timestamp': time.time(),
                'execution': execution,
                'smart_order': smart_order
            }
            
            self.execution_history[symbol].append(execution_record)
            
            # Keep only recent history (last 1000 records)
            if len(self.execution_history[symbol]) > 1000:
                self.execution_history[symbol] = self.execution_history[symbol][-1000:]
            
            # Update strategy success rates
            strategy = self._get_strategy_from_order(smart_order)
            if strategy not in self.strategy_success_rates:
                self.strategy_success_rates[strategy] = {'successes': 0, 'total': 0}
            
            self.strategy_success_rates[strategy]['total'] += 1
            if execution.success:
                self.strategy_success_rates[strategy]['successes'] += 1
            
            logger.debug(f"Recorded execution for {symbol}: "
                        f"Strategy={strategy}, Success={execution.success}, "
                        f"Slippage={execution.slippage:.3f}%")
            
        except Exception as e:
            logger.error(f"Error recording execution: {str(e)}")
    
    def _get_strategy_from_order(self, smart_order: SmartOrder) -> str:
        """Get strategy name from smart order"""
        # This would be determined by the order characteristics
        # For now, return based on order type
        if smart_order.order_type == 'market':
            return 'market'
        else:
            return 'limit'
    
    def get_execution_summary(self, symbol: str = None, days: int = 30) -> Dict:
        """Get execution performance summary"""
        try:
            current_time = time.time()
            cutoff_time = current_time - (days * 24 * 3600)
            
            if symbol:
                # Get specific symbol summary
                if symbol not in self.execution_history:
                    return {}
                
                recent_executions = [
                    record for record in self.execution_history[symbol]
                    if record['timestamp'] >= cutoff_time
                ]
                
                if not recent_executions:
                    return {}
                
                successful_executions = [r for r in recent_executions if r['execution'].success]
                
                summary = {
                    'symbol': symbol,
                    'total_executions': len(recent_executions),
                    'successful_executions': len(successful_executions),
                    'success_rate': len(successful_executions) / len(recent_executions) * 100,
                    'avg_slippage': sum(r['execution'].slippage for r in recent_executions) / len(recent_executions),
                    'avg_execution_time': sum(r['execution'].execution_time for r in recent_executions) / len(recent_executions),
                    'time_period_days': days
                }
                
                return summary
            else:
                # Get all symbols summary
                summary = {}
                for sym in self.execution_history.keys():
                    sym_summary = self.get_execution_summary(sym, days)
                    if sym_summary:
                        summary[sym] = sym_summary
                
                return summary
                
        except Exception as e:
            logger.error(f"Error getting execution summary: {str(e)}")
            return {}
    
    def get_strategy_performance(self) -> Dict:
        """Get strategy performance summary"""
        try:
            strategy_performance = {}
            
            for strategy, stats in self.strategy_success_rates.items():
                success_rate = stats['successes'] / stats['total'] if stats['total'] > 0 else 0
                strategy_performance[strategy] = {
                    'success_rate': success_rate,
                    'total_executions': stats['total'],
                    'successful_executions': stats['successes']
                }
            
            return strategy_performance
            
        except Exception as e:
            logger.error(f"Error getting strategy performance: {str(e)}")
            return {}
    
    def get_optimization_recommendations(self, symbol: str) -> List[str]:
        """Get optimization recommendations for order routing"""
        try:
            recommendations = []
            
            # Get execution summary
            execution_summary = self.get_execution_summary(symbol, 30)
            if not execution_summary:
                return ["No execution data available for recommendations"]
            
            # Success rate recommendations
            success_rate = execution_summary['success_rate']
            if success_rate < 80:
                recommendations.append("Low success rate - consider using more conservative order types")
            elif success_rate > 95:
                recommendations.append("High success rate - current strategy appears optimal")
            
            # Slippage recommendations
            avg_slippage = execution_summary['avg_slippage']
            if avg_slippage > 1.0:
                recommendations.append("High slippage - consider using limit orders or reducing order size")
            elif avg_slippage < 0.1:
                recommendations.append("Low slippage - current routing appears optimal")
            
            # Execution time recommendations
            avg_execution_time = execution_summary['avg_execution_time']
            if avg_execution_time > 5.0:
                recommendations.append("Slow execution - consider using market orders for faster fills")
            
            # Strategy recommendations
            strategy_performance = self.get_strategy_performance()
            if strategy_performance:
                best_strategy = max(strategy_performance.keys(), 
                                  key=lambda k: strategy_performance[k]['success_rate'])
                recommendations.append(f"Best performing strategy: {best_strategy}")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting optimization recommendations: {str(e)}")
            return ["Error generating recommendations"]

