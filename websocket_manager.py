import asyncio
import websockets
import json
import time
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class WebSocketMessage:
    """Data class for WebSocket messages"""
    exchange: str
    symbol: str
    price: float
    volume: float
    timestamp: float
    message_type: str = "ticker"

class WebSocketManager:
    """WebSocket manager for real-time price feeds"""
    
    def __init__(self):
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.subscribers: List[Callable] = []
        self.running = False
        self.reconnect_delays = {}
        self.max_reconnect_delay = 60
        self.message_queue = asyncio.Queue()
        self.last_prices = {}
        self.price_history = {}
        
        # WebSocket endpoints
        self.endpoints = {
            'binance': 'wss://stream.binance.com:9443/ws/',
            'kraken': 'wss://ws.kraken.com/'
        }
        
    def subscribe(self, callback: Callable):
        """Subscribe to price updates"""
        self.subscribers.append(callback)
        logger.info(f"Added WebSocket subscriber: {callback.__name__}")
    
    def unsubscribe(self, callback: Callable):
        """Unsubscribe from price updates"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
            logger.info(f"Removed WebSocket subscriber: {callback.__name__}")
    
    async def _notify_subscribers(self, message: WebSocketMessage):
        """Notify all subscribers of price updates"""
        for callback in self.subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                logger.error(f"Error in WebSocket subscriber {callback.__name__}: {str(e)}")
    
    async def _connect_binance(self, symbols: List[str]):
        """Connect to Binance WebSocket"""
        try:
            # Create stream names for symbols
            streams = []
            for symbol in symbols:
                binance_symbol = symbol.replace('/USDT', 'usdt').lower()
                streams.append(f"{binance_symbol}@ticker")
            
            stream_url = f"{self.endpoints['binance']}{'/'.join(streams)}"
            
            async with websockets.connect(stream_url) as websocket:
                self.connections['binance'] = websocket
                logger.info(f"Connected to Binance WebSocket for {len(symbols)} symbols")
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        
                        # Handle multiple streams
                        if isinstance(data, dict) and 'stream' in data:
                            stream_data = data['data']
                            symbol = stream_data['s']  # Symbol like BTCUSDT
                            
                            # Convert to our format
                            formatted_symbol = f"{symbol[:-4]}/USDT" if symbol.endswith('USDT') else symbol
                            
                            ws_message = WebSocketMessage(
                                exchange='binance',
                                symbol=formatted_symbol,
                                price=float(stream_data['c']),  # Close price
                                volume=float(stream_data['v']),  # Volume
                                timestamp=time.time(),
                                message_type='ticker'
                            )
                            
                            await self._process_message(ws_message)
                            
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON received from Binance WebSocket")
                    except Exception as e:
                        logger.error(f"Error processing Binance WebSocket message: {str(e)}")
                        
        except Exception as e:
            logger.error(f"Binance WebSocket connection error: {str(e)}")
            await self._handle_reconnection('binance', symbols)
    
    async def _connect_kraken(self, symbols: List[str]):
        """Connect to Kraken WebSocket"""
        try:
            async with websockets.connect(self.endpoints['kraken']) as websocket:
                self.connections['kraken'] = websocket
                logger.info(f"Connected to Kraken WebSocket for {len(symbols)} symbols")
                
                # Subscribe to ticker data
                for symbol in symbols:
                    kraken_symbol = symbol.replace('/USDT', 'USDT')
                    subscribe_msg = {
                        "event": "subscribe",
                        "pair": [kraken_symbol],
                        "subscription": {"name": "ticker"}
                    }
                    await websocket.send(json.dumps(subscribe_msg))
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        
                        # Handle ticker data
                        if isinstance(data, list) and len(data) >= 4:
                            channel_name = data[2] if len(data) > 2 else None
                            ticker_data = data[1] if len(data) > 1 else None
                            
                            if channel_name and ticker_data and 'c' in ticker_data:
                                # Extract symbol from channel name
                                symbol = channel_name.replace('USDT', '/USDT')
                                
                                ws_message = WebSocketMessage(
                                    exchange='kraken',
                                    symbol=symbol,
                                    price=float(ticker_data['c'][0]),  # Close price
                                    volume=0.0,  # Kraken doesn't provide volume in ticker
                                    timestamp=time.time(),
                                    message_type='ticker'
                                )
                                
                                await self._process_message(ws_message)
                                
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON received from Kraken WebSocket")
                    except Exception as e:
                        logger.error(f"Error processing Kraken WebSocket message: {str(e)}")
                        
        except Exception as e:
            logger.error(f"Kraken WebSocket connection error: {str(e)}")
            await self._handle_reconnection('kraken', symbols)
    
    async def _process_message(self, message: WebSocketMessage):
        """Process incoming WebSocket message"""
        try:
            # Update last prices
            key = f"{message.exchange}_{message.symbol}"
            self.last_prices[key] = message
            
            # Store in price history (keep last 1000 messages per symbol)
            if message.symbol not in self.price_history:
                self.price_history[message.symbol] = []
            
            self.price_history[message.symbol].append(message)
            
            # Keep only recent history
            if len(self.price_history[message.symbol]) > 1000:
                self.price_history[message.symbol] = self.price_history[message.symbol][-1000:]
            
            # Add to message queue for processing
            await self.message_queue.put(message)
            
            # Notify subscribers
            await self._notify_subscribers(message)
            
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {str(e)}")
    
    async def _handle_reconnection(self, exchange: str, symbols: List[str]):
        """Handle WebSocket reconnection with exponential backoff"""
        try:
            if exchange in self.reconnect_delays:
                delay = min(self.reconnect_delays[exchange] * 2, self.max_reconnect_delay)
            else:
                delay = 1
            
            self.reconnect_delays[exchange] = delay
            
            logger.info(f"Reconnecting to {exchange} WebSocket in {delay} seconds...")
            await asyncio.sleep(delay)
            
            if exchange == 'binance':
                await self._connect_binance(symbols)
            elif exchange == 'kraken':
                await self._connect_kraken(symbols)
                
        except Exception as e:
            logger.error(f"Error reconnecting to {exchange} WebSocket: {str(e)}")
    
    async def start(self, symbols: List[str]):
        """Start WebSocket connections for all exchanges"""
        if self.running:
            logger.warning("WebSocket manager is already running")
            return
        
        self.running = True
        logger.info(f"Starting WebSocket manager for symbols: {symbols}")
        
        # Start connections for all exchanges
        tasks = []
        
        # Start Binance connection
        binance_task = asyncio.create_task(self._connect_binance(symbols))
        tasks.append(binance_task)
        
        # Start Kraken connection
        kraken_task = asyncio.create_task(self._connect_kraken(symbols))
        tasks.append(kraken_task)
        
        # Start message processor
        processor_task = asyncio.create_task(self._process_message_queue())
        tasks.append(processor_task)
        
        # Wait for all tasks
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop(self):
        """Stop WebSocket connections"""
        if not self.running:
            logger.warning("WebSocket manager is not running")
            return
        
        self.running = False
        logger.info("Stopping WebSocket manager")
        
        # Close all connections
        for exchange, connection in self.connections.items():
            try:
                await connection.close()
                logger.info(f"Closed {exchange} WebSocket connection")
            except Exception as e:
                logger.error(f"Error closing {exchange} WebSocket: {str(e)}")
        
        self.connections.clear()
        logger.info("WebSocket manager stopped")
    
    async def _process_message_queue(self):
        """Process messages from the queue"""
        while self.running:
            try:
                # Wait for message with timeout
                try:
                    message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                    # Message already processed in _process_message
                    self.message_queue.task_done()
                except asyncio.TimeoutError:
                    continue
                    
            except Exception as e:
                logger.error(f"Error processing message queue: {str(e)}")
                await asyncio.sleep(1)
    
    def get_latest_price(self, exchange: str, symbol: str) -> Optional[WebSocketMessage]:
        """Get latest price for a symbol from an exchange"""
        key = f"{exchange}_{symbol}"
        return self.last_prices.get(key)
    
    def get_price_history(self, symbol: str, limit: int = 100) -> List[WebSocketMessage]:
        """Get price history for a symbol"""
        if symbol not in self.price_history:
            return []
        
        return self.price_history[symbol][-limit:]
    
    def get_spread(self, symbol: str) -> Optional[Dict]:
        """Calculate spread between exchanges for a symbol"""
        try:
            binance_price = self.get_latest_price('binance', symbol)
            kraken_price = self.get_latest_price('kraken', symbol)
            
            if not binance_price or not kraken_price:
                return None
            
            # Calculate spread
            price_diff = abs(binance_price.price - kraken_price.price)
            avg_price = (binance_price.price + kraken_price.price) / 2
            spread_percent = (price_diff / avg_price) * 100
            
            return {
                'symbol': symbol,
                'binance_price': binance_price.price,
                'kraken_price': kraken_price.price,
                'spread_percent': spread_percent,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error calculating spread for {symbol}: {str(e)}")
            return None
    
    def get_connection_status(self) -> Dict:
        """Get WebSocket connection status"""
        return {
            'running': self.running,
            'connections': {
                exchange: connection.open if connection else False 
                for exchange, connection in self.connections.items()
            },
            'subscribers': len(self.subscribers),
            'queued_messages': self.message_queue.qsize()
        }

