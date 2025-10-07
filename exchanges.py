import ccxt
import asyncio
import time
from typing import Dict, List, Optional, Tuple
from config import Config
from error_handler import ErrorHandler, ErrorType
import logging

logger = logging.getLogger(__name__)

class ExchangeConnector:
    """Base class for exchange connectors"""
    
    def __init__(self, exchange_name: str, config: Dict):
        self.exchange_name = exchange_name
        self.exchange = None
        self.config = config
        self.last_price_update = {}
        self.balances = {}
        self.error_handler = ErrorHandler()
        self.rate_limit_delay = 0
        self.last_request_time = 0
        
    async def initialize(self):
        """Initialize exchange connection"""
        try:
            if self.exchange_name == 'binance':
                self.exchange = ccxt.binance(self.config)
            elif self.exchange_name == 'okx':
                self.exchange = ccxt.okx(self.config)
            else:
                raise ValueError(f"Unsupported exchange: {self.exchange_name}")
            
            # Test connection
            await self.test_connection()
            logger.info(f"Successfully connected to {self.exchange_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.exchange_name}: {str(e)}")
            raise
    
    async def test_connection(self):
        """Test exchange connection"""
        try:
            # Test API access
            balance = await self.get_balance()
            logger.info(f"{self.exchange_name} connection test successful")
            return True
        except Exception as e:
            logger.error(f"{self.exchange_name} connection test failed: {str(e)}")
            raise
    
    async def get_balance(self) -> Dict:
        """Get account balance"""
        try:
            balance = await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.fetch_balance
            )
            self.balances = balance
            return balance
        except Exception as e:
            logger.error(f"Failed to get balance from {self.exchange_name}: {str(e)}")
            raise
    
    async def _rate_limit_check(self):
        """Check and enforce rate limits"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last_request
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()

    async def get_ticker(self, symbol: str) -> Dict:
        """Get ticker information for a symbol with error handling"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await self._rate_limit_check()
                
                ticker = await asyncio.get_event_loop().run_in_executor(
                    None, self.exchange.fetch_ticker, symbol
                )
                self.last_price_update[symbol] = time.time()
                self.rate_limit_delay = 0  # Reset delay on success
                return ticker
            except Exception as e:
                should_retry = await self.error_handler.handle_api_error(e, self.exchange_name, symbol)
                if not should_retry or attempt == max_retries - 1:
                    logger.error(f"Failed to get ticker for {symbol} from {self.exchange_name}: {str(e)}")
                    raise
                
                # Increase rate limit delay on rate limit errors
                if "rate limit" in str(e).lower():
                    self.rate_limit_delay = min(self.rate_limit_delay + 0.1, 1.0)
    
    async def get_orderbook(self, symbol: str, limit: int = 5) -> Dict:
        """Get order book for a symbol"""
        try:
            orderbook = await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.fetch_order_book, symbol, limit
            )
            return orderbook
        except Exception as e:
            logger.error(f"Failed to get orderbook for {symbol} from {self.exchange_name}: {str(e)}")
            raise
    
    async def place_market_order(self, symbol: str, side: str, amount: float) -> Dict:
        """Place a market order with error handling"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                await self._rate_limit_check()
                
                order = await asyncio.get_event_loop().run_in_executor(
                    None, self.exchange.create_market_order, symbol, side, amount
                )
                logger.info(f"Market order placed on {self.exchange_name}: {side} {amount} {symbol}")
                return order
            except Exception as e:
                should_retry = await self.error_handler.handle_order_error(e, self.exchange_name, symbol)
                if not should_retry or attempt == max_retries - 1:
                    logger.error(f"Failed to place market order on {self.exchange_name}: {str(e)}")
                    raise
    
    async def place_limit_order(self, symbol: str, side: str, amount: float, price: float) -> Dict:
        """Place a limit order"""
        try:
            order = await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.create_limit_order, symbol, side, amount, price
            )
            logger.info(f"Limit order placed on {self.exchange_name}: {side} {amount} {symbol} @ {price}")
            return order
        except Exception as e:
            logger.error(f"Failed to place limit order on {self.exchange_name}: {str(e)}")
            raise
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.cancel_order, order_id, symbol
            )
            logger.info(f"Order {order_id} cancelled on {self.exchange_name}")
            return result
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id} on {self.exchange_name}: {str(e)}")
            raise
    
    async def get_order_status(self, order_id: str, symbol: str) -> Dict:
        """Get order status"""
        try:
            order = await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.fetch_order, order_id, symbol
            )
            return order
        except Exception as e:
            logger.error(f"Failed to get order status for {order_id} on {self.exchange_name}: {str(e)}")
            raise
    
    async def withdraw(self, currency: str, amount: float, address: str, tag: str = None) -> Dict:
        """Withdraw funds to external address with error handling"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                await self._rate_limit_check()
                
                params = {}
                if tag:
                    params['tag'] = tag
                
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self.exchange.withdraw, currency, amount, address, None, params
                )
                logger.info(f"Withdrawal initiated on {self.exchange_name}: {amount} {currency} to {address}")
                return result
            except Exception as e:
                should_retry = await self.error_handler.handle_transfer_error(
                    e, currency, self.exchange_name, "external"
                )
                if not should_retry or attempt == max_retries - 1:
                    logger.error(f"Failed to withdraw from {self.exchange_name}: {str(e)}")
                    raise
    
    def get_symbol(self, base: str, quote: str = 'USDT') -> str:
        """Get exchange-specific symbol format"""
        if self.exchange_name == 'binance':
            return f"{base}/{quote}"
        elif self.exchange_name == 'okx':
            return f"{base}/{quote}"
        else:
            return f"{base}/{quote}"
    
    def get_fee(self, symbol: str) -> float:
        """Get trading fee for a symbol"""
        try:
            markets = self.exchange.load_markets()
            if symbol in markets:
                return markets[symbol].get('taker', 0.001)
            return 0.001  # Default fee
        except:
            return 0.001

class BinanceConnector(ExchangeConnector):
    """Binance-specific connector"""
    
    def __init__(self):
        super().__init__('binance', Config.EXCHANGE_CONFIGS['binance'])
    
    async def get_deposit_address(self, currency: str) -> str:
        """Get deposit address for a currency"""
        try:
            addresses = await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.fetch_deposit_address, currency
            )
            return addresses['address']
        except Exception as e:
            logger.error(f"Failed to get deposit address for {currency} on Binance: {str(e)}")
            raise

class OKXConnector(ExchangeConnector):
    """OKX-specific connector"""
    
    def __init__(self):
        super().__init__('okx', Config.EXCHANGE_CONFIGS['okx'])
    
    async def get_deposit_address(self, currency: str) -> str:
        """Get deposit address for a currency"""
        try:
            addresses = await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.fetch_deposit_address, currency
            )
            return addresses['address']
        except Exception as e:
            logger.error(f"Failed to get deposit address for {currency} on OKX: {str(e)}")
            raise

class ExchangeManager:
    """Manager class for handling multiple exchanges"""
    
    def __init__(self):
        self.binance = BinanceConnector()
        self.okx = OKXConnector()
        self.exchanges = {
            'binance': self.binance,
            'okx': self.okx
        }
    
    async def initialize_all(self):
        """Initialize all exchange connections"""
        tasks = []
        for exchange in self.exchanges.values():
            tasks.append(exchange.initialize())
        
        await asyncio.gather(*tasks)
        logger.info("All exchanges initialized successfully")
    
    def get_exchange(self, name: str) -> ExchangeConnector:
        """Get exchange connector by name"""
        return self.exchanges.get(name)
    
    async def get_prices(self, symbol: str) -> Dict[str, float]:
        """Get prices from all exchanges for a symbol"""
        prices = {}
        tasks = []
        
        for name, exchange in self.exchanges.items():
            tasks.append(self._get_price_safe(exchange, symbol, name, prices))
        
        await asyncio.gather(*tasks)
        return prices
    
    async def _get_price_safe(self, exchange: ExchangeConnector, symbol: str, name: str, prices: Dict):
        """Safely get price from exchange"""
        try:
            ticker = await exchange.get_ticker(symbol)
            prices[name] = ticker['last']
        except Exception as e:
            logger.error(f"Failed to get price from {name} for {symbol}: {str(e)}")
            prices[name] = None
