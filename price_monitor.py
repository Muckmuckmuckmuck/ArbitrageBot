import asyncio
import time
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass
from exchanges import ExchangeManager
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class PriceData:
    """Data class for price information"""
    symbol: str
    exchange: str
    price: float
    timestamp: float
    volume: float = 0.0
    bid: float = 0.0
    ask: float = 0.0

class PriceMonitor:
    """Real-time price monitoring for multiple exchanges and symbols"""
    
    def __init__(self, exchange_manager: ExchangeManager):
        self.exchange_manager = exchange_manager
        self.price_data: Dict[str, Dict[str, PriceData]] = {}
        self.subscribers: List[Callable] = []
        self.running = False
        self.monitoring_tasks = {}
        
    def subscribe(self, callback: Callable):
        """Subscribe to price updates"""
        self.subscribers.append(callback)
        logger.info(f"Added price update subscriber: {callback.__name__}")
    
    def unsubscribe(self, callback: Callable):
        """Unsubscribe from price updates"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
            logger.info(f"Removed price update subscriber: {callback.__name__}")
    
    async def _notify_subscribers(self, price_data: PriceData):
        """Notify all subscribers of price updates"""
        for callback in self.subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(price_data)
                else:
                    callback(price_data)
            except Exception as e:
                logger.error(f"Error in price update subscriber {callback.__name__}: {str(e)}")
    
    async def _monitor_symbol(self, symbol: str):
        """Monitor prices for a specific symbol across all exchanges"""
        logger.info(f"Starting price monitoring for {symbol}")
        
        while self.running:
            try:
                # Get prices from all exchanges
                prices = await self.exchange_manager.get_prices(symbol)
                
                # Update price data
                for exchange_name, price in prices.items():
                    if price is not None:
                        if symbol not in self.price_data:
                            self.price_data[symbol] = {}
                        
                        # Get additional ticker data
                        try:
                            exchange = self.exchange_manager.get_exchange(exchange_name)
                            ticker = await exchange.get_ticker(symbol)
                            
                            price_data = PriceData(
                                symbol=symbol,
                                exchange=exchange_name,
                                price=price,
                                timestamp=time.time(),
                                volume=ticker.get('baseVolume', 0.0),
                                bid=ticker.get('bid', price),
                                ask=ticker.get('ask', price)
                            )
                            
                            self.price_data[symbol][exchange_name] = price_data
                            
                            # Notify subscribers
                            await self._notify_subscribers(price_data)
                            
                        except Exception as e:
                            logger.error(f"Error getting ticker data for {symbol} on {exchange_name}: {str(e)}")
                
                # Wait before next update
                await asyncio.sleep(1)  # Update every second
                
            except Exception as e:
                logger.error(f"Error monitoring {symbol}: {str(e)}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def start_monitoring(self, symbols: List[str]):
        """Start monitoring prices for given symbols"""
        if self.running:
            logger.warning("Price monitoring is already running")
            return
        
        self.running = True
        logger.info(f"Starting price monitoring for symbols: {symbols}")
        
        # Start monitoring tasks for each symbol
        for symbol in symbols:
            task = asyncio.create_task(self._monitor_symbol(symbol))
            self.monitoring_tasks[symbol] = task
        
        # Wait for all monitoring tasks
        await asyncio.gather(*self.monitoring_tasks.values())
    
    async def stop_monitoring(self):
        """Stop price monitoring"""
        if not self.running:
            logger.warning("Price monitoring is not running")
            return
        
        self.running = False
        logger.info("Stopping price monitoring")
        
        # Cancel all monitoring tasks
        for symbol, task in self.monitoring_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"Price monitoring task for {symbol} cancelled")
        
        self.monitoring_tasks.clear()
        logger.info("Price monitoring stopped")
    
    def get_latest_price(self, symbol: str, exchange: str) -> Optional[PriceData]:
        """Get latest price data for a symbol from a specific exchange"""
        if symbol in self.price_data and exchange in self.price_data[symbol]:
            return self.price_data[symbol][exchange]
        return None
    
    def get_all_prices(self, symbol: str) -> Dict[str, PriceData]:
        """Get latest prices for a symbol from all exchanges"""
        return self.price_data.get(symbol, {})
    
    def get_price_spread(self, symbol: str) -> Dict[str, float]:
        """Calculate price spreads between exchanges for a symbol"""
        prices = self.get_all_prices(symbol)
        spreads = {}
        
        if len(prices) < 2:
            return spreads
        
        exchange_names = list(prices.keys())
        for i in range(len(exchange_names)):
            for j in range(i + 1, len(exchange_names)):
                exchange1 = exchange_names[i]
                exchange2 = exchange_names[j]
                
                price1 = prices[exchange1].price
                price2 = prices[exchange2].price
                
                # Calculate spread percentage
                spread_percent = abs(price1 - price2) / min(price1, price2) * 100
                
                spreads[f"{exchange1}_{exchange2}"] = {
                    'spread_percent': spread_percent,
                    'price1': price1,
                    'price2': price2,
                    'exchange1': exchange1,
                    'exchange2': exchange2,
                    'higher_price_exchange': exchange1 if price1 > price2 else exchange2,
                    'lower_price_exchange': exchange2 if price1 > price2 else exchange1
                }
        
        return spreads
    
    async def get_historical_prices(self, symbol: str, exchange: str, timeframe: str = '1m', limit: int = 100) -> List[Dict]:
        """Get historical price data"""
        try:
            exchange_connector = self.exchange_manager.get_exchange(exchange)
            ohlcv = await asyncio.get_event_loop().run_in_executor(
                None, exchange_connector.exchange.fetch_ohlcv, symbol, timeframe, None, limit
            )
            return ohlcv
        except Exception as e:
            logger.error(f"Error getting historical prices for {symbol} on {exchange}: {str(e)}")
            return []

class ArbitrageDetector:
    """Detects arbitrage opportunities based on price spreads"""
    
    def __init__(self, price_monitor: PriceMonitor, min_spread_percent: float = 0.8):
        self.price_monitor = price_monitor
        self.min_spread_percent = min_spread_percent
        self.arbitrage_opportunities = {}
        
    def check_arbitrage_opportunity(self, symbol: str) -> Optional[Dict]:
        """Check for arbitrage opportunity for a symbol"""
        spreads = self.price_monitor.get_price_spread(symbol)
        
        if not spreads:
            return None
        
        # Find the maximum spread
        max_spread = max(spreads.values(), key=lambda x: x['spread_percent'])
        
        if max_spread['spread_percent'] >= self.min_spread_percent:
            opportunity = {
                'symbol': symbol,
                'spread_percent': max_spread['spread_percent'],
                'buy_exchange': max_spread['lower_price_exchange'],
                'sell_exchange': max_spread['higher_price_exchange'],
                'buy_price': max_spread['lower_price_exchange'] == max_spread['exchange1'] and max_spread['price1'] or max_spread['price2'],
                'sell_price': max_spread['higher_price_exchange'] == max_spread['exchange1'] and max_spread['price1'] or max_spread['price2'],
                'timestamp': time.time()
            }
            
            self.arbitrage_opportunities[symbol] = opportunity
            return opportunity
        
        return None
    
    async def monitor_arbitrage_opportunities(self, symbols: List[str], callback: Callable):
        """Monitor for arbitrage opportunities and call callback when found"""
        def price_update_handler(price_data: PriceData):
            opportunity = self.check_arbitrage_opportunity(price_data.symbol)
            if opportunity:
                asyncio.create_task(callback(opportunity))
        
        # Subscribe to price updates
        self.price_monitor.subscribe(price_update_handler)
        
        logger.info(f"Started arbitrage monitoring for symbols: {symbols}")

