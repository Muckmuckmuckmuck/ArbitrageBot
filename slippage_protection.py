import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class SlippageData:
    """Data class for slippage information"""
    symbol: str
    exchange: str
    expected_price: float
    actual_price: float
    slippage_percent: float
    order_size: float
    timestamp: float
    order_book_depth: float

@dataclass
class OrderBookLevel:
    """Data class for order book level"""
    price: float
    quantity: float
    cumulative_value: float

class SlippageProtection:
    """Real-time slippage protection system"""
    
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.slippage_history = {}
        self.order_book_cache = {}
        self.slippage_thresholds = {
            # Conservative thresholds by symbol
            'XRP/USDT': 0.5, 'XLM/USDT': 0.5, 'SOL/USDT': 0.5,
            'USDC/USDT': 0.1, 'USDT/USDC': 0.1, 'DAI/USDT': 0.1,
            'BNB/USDT': 0.3, 'LINK/USDT': 0.4, 'UNI/USDT': 0.4,
            'ADA/USDT': 0.3, 'DOT/USDT': 0.4, 'AVAX/USDT': 0.4,
            'TON/USDT': 0.6, 'MATIC/USDT': 0.4, 'EOS/USDT': 0.4,
            'TRX/USDT': 0.4, 'LTC/USDT': 0.3, 'DOGE/USDT': 0.4,
            'VET/USDT': 0.4, 'BCH/USDT': 0.4, 'XMR/USDT': 0.5,
            # Default for other symbols
            'default': 0.5
        }
        
    async def check_slippage_risk(self, symbol: str, exchange: str, side: str, 
                                 amount: float, expected_price: float) -> Tuple[bool, float]:
        """Check if order has acceptable slippage risk"""
        try:
            # Get order book
            order_book = await self._get_order_book(symbol, exchange)
            if not order_book:
                logger.warning(f"No order book data for {symbol} on {exchange}")
                return False, 0.0
            
            # Calculate expected slippage
            expected_slippage = await self._calculate_expected_slippage(
                order_book, side, amount, expected_price
            )
            
            # Get threshold for this symbol
            threshold = self.slippage_thresholds.get(symbol, self.slippage_thresholds['default'])
            
            # Check if slippage is acceptable
            is_acceptable = expected_slippage <= threshold
            
            # Log slippage analysis
            logger.info(f"Slippage analysis for {symbol} on {exchange}: "
                       f"Expected: {expected_slippage:.4f}%, Threshold: {threshold:.4f}%, "
                       f"Acceptable: {is_acceptable}")
            
            return is_acceptable, expected_slippage
            
        except Exception as e:
            logger.error(f"Error checking slippage risk for {symbol}: {str(e)}")
            return False, 0.0
    
    async def _get_order_book(self, symbol: str, exchange: str, depth: int = 20) -> Optional[Dict]:
        """Get order book data with caching"""
        try:
            cache_key = f"{exchange}_{symbol}"
            current_time = time.time()
            
            # Check cache (valid for 1 second)
            if (cache_key in self.order_book_cache and 
                current_time - self.order_book_cache[cache_key]['timestamp'] < 1.0):
                return self.order_book_cache[cache_key]['data']
            
            # Fetch fresh order book
            exchange_connector = self.exchange_manager.get_exchange(exchange)
            order_book = await exchange_connector.get_orderbook(symbol, depth)
            
            # Cache the data
            self.order_book_cache[cache_key] = {
                'data': order_book,
                'timestamp': current_time
            }
            
            return order_book
            
        except Exception as e:
            logger.error(f"Error getting order book for {symbol} on {exchange}: {str(e)}")
            return None
    
    async def _calculate_expected_slippage(self, order_book: Dict, side: str, 
                                         amount: float, expected_price: float) -> float:
        """Calculate expected slippage based on order book"""
        try:
            if side == 'buy':
                levels = order_book.get('asks', [])
                base_price = expected_price
            else:
                levels = order_book.get('bids', [])
                base_price = expected_price
            
            if not levels:
                return 100.0  # High slippage if no liquidity
            
            # Calculate cumulative value and find price impact
            cumulative_quantity = 0
            cumulative_value = 0
            target_price = None
            
            for level in levels:
                price, quantity = level
                level_value = price * quantity
                
                cumulative_quantity += quantity
                cumulative_value += level_value
                
                # Check if we've reached our target amount
                if cumulative_quantity >= amount:
                    # Calculate weighted average price
                    remaining_amount = amount - (cumulative_quantity - quantity)
                    target_value = cumulative_value - level_value + (remaining_amount * price)
                    target_price = target_value / amount
                    break
            
            # If we couldn't fill the order with available liquidity
            if target_price is None:
                return 100.0  # High slippage
            
            # Calculate slippage percentage
            slippage_percent = abs(target_price - base_price) / base_price * 100
            
            return slippage_percent
            
        except Exception as e:
            logger.error(f"Error calculating expected slippage: {str(e)}")
            return 100.0
    
    async def analyze_market_depth(self, symbol: str, exchanges: List[str]) -> Dict:
        """Analyze market depth across exchanges"""
        try:
            depth_analysis = {}
            
            for exchange in exchanges:
                order_book = await self._get_order_book(symbol, exchange, 50)
                if not order_book:
                    continue
                
                # Analyze bid depth
                bids = order_book.get('bids', [])
                ask_depth = sum(price * quantity for price, quantity in bids[:10])  # Top 10 levels
                
                # Analyze ask depth
                asks = order_book.get('asks', [])
                ask_depth = sum(price * quantity for price, quantity in asks[:10])  # Top 10 levels
                
                # Calculate total depth
                total_depth = ask_depth + ask_depth
                
                depth_analysis[exchange] = {
                    'bid_depth': ask_depth,
                    'ask_depth': ask_depth,
                    'total_depth': total_depth,
                    'levels_analyzed': min(len(bids + asks), 20)
                }
            
            return depth_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing market depth for {symbol}: {str(e)}")
            return {}
    
    async def optimize_order_size(self, symbol: str, exchange: str, side: str, 
                                 max_amount: float, max_slippage: float) -> float:
        """Optimize order size to stay within slippage limits"""
        try:
            order_book = await self._get_order_book(symbol, exchange, 100)
            if not order_book:
                return 0.0
            
            levels = order_book.get('asks' if side == 'buy' else 'bids', [])
            if not levels:
                return 0.0
            
            cumulative_quantity = 0
            cumulative_value = 0
            optimal_amount = 0.0
            
            for price, quantity in levels:
                level_value = price * quantity
                
                # Calculate new cumulative values
                new_cumulative_quantity = cumulative_quantity + quantity
                new_cumulative_value = cumulative_value + level_value
                
                # Calculate weighted average price
                new_avg_price = new_cumulative_value / new_cumulative_quantity
                
                # Calculate slippage
                first_price = levels[0][0]
                slippage = abs(new_avg_price - first_price) / first_price * 100
                
                # Check if slippage is within limits
                if slippage <= max_slippage:
                    optimal_amount = new_cumulative_quantity
                    cumulative_quantity = new_cumulative_quantity
                    cumulative_value = new_cumulative_value
                else:
                    break
            
            # Ensure we don't exceed maximum amount
            optimal_amount = min(optimal_amount, max_amount)
            
            logger.info(f"Optimized order size for {symbol} on {exchange}: "
                       f"{optimal_amount:.8f} (max: {max_amount:.8f}, "
                       f"slippage limit: {max_slippage:.2f}%)")
            
            return optimal_amount
            
        except Exception as e:
            logger.error(f"Error optimizing order size for {symbol}: {str(e)}")
            return 0.0
    
    def record_slippage(self, slippage_data: SlippageData):
        """Record slippage data for analysis"""
        try:
            symbol = slippage_data.symbol
            if symbol not in self.slippage_history:
                self.slippage_history[symbol] = []
            
            self.slippage_history[symbol].append(slippage_data)
            
            # Keep only recent history (last 1000 records)
            if len(self.slippage_history[symbol]) > 1000:
                self.slippage_history[symbol] = self.slippage_history[symbol][-1000:]
            
            # Log slippage
            logger.info(f"Slippage recorded for {symbol} on {slippage_data.exchange}: "
                       f"{slippage_data.slippage_percent:.4f}% "
                       f"(Expected: {slippage_data.expected_price:.8f}, "
                       f"Actual: {slippage_data.actual_price:.8f})")
            
        except Exception as e:
            logger.error(f"Error recording slippage: {str(e)}")
    
    def get_slippage_summary(self, symbol: str, hours: int = 24) -> Dict:
        """Get slippage summary for a symbol"""
        try:
            if symbol not in self.slippage_history:
                return {}
            
            current_time = time.time()
            cutoff_time = current_time - (hours * 3600)
            
            # Filter recent slippage data
            recent_slippage = [
                s for s in self.slippage_history[symbol] 
                if s.timestamp >= cutoff_time
            ]
            
            if not recent_slippage:
                return {}
            
            # Calculate statistics
            slippage_values = [s.slippage_percent for s in recent_slippage]
            
            summary = {
                'symbol': symbol,
                'total_records': len(recent_slippage),
                'avg_slippage': sum(slippage_values) / len(slippage_values),
                'max_slippage': max(slippage_values),
                'min_slippage': min(slippage_values),
                'time_period_hours': hours,
                'exchanges': list(set(s.exchange for s in recent_slippage))
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting slippage summary for {symbol}: {str(e)}")
            return {}
    
    def update_slippage_threshold(self, symbol: str, new_threshold: float):
        """Update slippage threshold for a symbol"""
        try:
            self.slippage_thresholds[symbol] = new_threshold
            logger.info(f"Updated slippage threshold for {symbol}: {new_threshold:.4f}%")
            
        except Exception as e:
            logger.error(f"Error updating slippage threshold: {str(e)}")
    
    async def monitor_slippage_trends(self, symbols: List[str]) -> Dict:
        """Monitor slippage trends across symbols"""
        try:
            trends = {}
            
            for symbol in symbols:
                # Get recent slippage data
                recent_data = self.slippage_history.get(symbol, [])
                if len(recent_data) < 10:
                    continue
                
                # Calculate trend (simple linear regression)
                recent_data = recent_data[-50:]  # Last 50 records
                timestamps = [d.timestamp for d in recent_data]
                slippage_values = [d.slippage_percent for d in recent_data]
                
                # Simple trend calculation
                if len(slippage_values) >= 2:
                    first_half = slippage_values[:len(slippage_values)//2]
                    second_half = slippage_values[len(slippage_values)//2:]
                    
                    first_avg = sum(first_half) / len(first_half)
                    second_avg = sum(second_half) / len(second_half)
                    
                    trend = second_avg - first_avg
                    trend_direction = "increasing" if trend > 0 else "decreasing" if trend < 0 else "stable"
                else:
                    trend = 0
                    trend_direction = "stable"
                
                trends[symbol] = {
                    'avg_slippage': sum(slippage_values) / len(slippage_values),
                    'trend': trend,
                    'trend_direction': trend_direction,
                    'records_analyzed': len(recent_data)
                }
            
            return trends
            
        except Exception as e:
            logger.error(f"Error monitoring slippage trends: {str(e)}")
            return {}

