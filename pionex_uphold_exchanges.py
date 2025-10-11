import ccxt
import logging
from typing import Dict, Any, Optional
from pionex_uphold_config import PionexUpholdConfig

logger = logging.getLogger(__name__)

class PionexUpholdExchangeManager:
    """
    Exchange manager for Pionex.US and Uphold
    Handles all exchange interactions with proper error handling and rate limiting
    """
    
    def __init__(self):
        self.config = PionexUpholdConfig
        self.exchanges = {}
        self._initialize_exchanges()
    
    def _initialize_exchanges(self):
        """Initialize exchange connections"""
        try:
            # Initialize Pionex.US
            # Note: Pionex.US uses the standard ccxt 'pionex' exchange
            self.exchanges['pionex'] = ccxt.pionex({
                'apiKey': self.config.PIONEX_API_KEY,
                'secret': self.config.PIONEX_SECRET_KEY,
                'enableRateLimit': True,
                'rateLimit': self.config.EXCHANGE_CONFIGS['pionex']['rateLimit'],
                'options': {
                    'defaultType': 'spot',
                },
            })
            
            if self.config.PIONEX_TESTNET:
                self.exchanges['pionex'].set_sandbox_mode(True)
                logger.info("Pionex.US initialized in TESTNET mode")
            else:
                logger.info("Pionex.US initialized in PRODUCTION mode")
            
            # Initialize Uphold
            # Note: Uphold might need custom implementation as it's not natively supported by ccxt
            # For now, we'll use a placeholder
            try:
                self.exchanges['uphold'] = ccxt.uphold({
                    'apiKey': self.config.UPHOLD_API_KEY,
                    'secret': self.config.UPHOLD_SECRET_KEY,
                    'enableRateLimit': True,
                    'rateLimit': self.config.EXCHANGE_CONFIGS['uphold']['rateLimit'],
                })
                
                if self.config.UPHOLD_SANDBOX:
                    self.exchanges['uphold'].set_sandbox_mode(True)
                    logger.info("Uphold initialized in TESTNET mode")
                else:
                    logger.info("Uphold initialized in PRODUCTION mode")
            except Exception as e:
                logger.warning(f"Uphold not natively supported by ccxt: {e}")
                logger.warning("You'll need to implement custom Uphold API integration")
                # Create a placeholder for Uphold
                self.exchanges['uphold'] = None
            
        except Exception as e:
            logger.error(f"Error initializing exchanges: {str(e)}")
            raise
    
    def get_exchange(self, exchange_name: str):
        """Get exchange instance by name"""
        if exchange_name not in self.exchanges:
            raise ValueError(f"Exchange {exchange_name} not configured")
        
        if self.exchanges[exchange_name] is None:
            raise ValueError(f"Exchange {exchange_name} not properly initialized")
        
        return self.exchanges[exchange_name]
    
    async def fetch_ticker(self, exchange_name: str, symbol: str) -> Dict[str, Any]:
        """Fetch ticker data from exchange"""
        try:
            exchange = self.get_exchange(exchange_name)
            ticker = await exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol} on {exchange_name}: {str(e)}")
            raise
    
    async def fetch_balance(self, exchange_name: str) -> Dict[str, Any]:
        """Fetch account balance from exchange"""
        try:
            exchange = self.get_exchange(exchange_name)
            balance = await exchange.fetch_balance()
            return balance
        except Exception as e:
            logger.error(f"Error fetching balance from {exchange_name}: {str(e)}")
            raise
    
    async def create_order(self, exchange_name: str, symbol: str, order_type: str, 
                          side: str, amount: float, price: Optional[float] = None) -> Dict[str, Any]:
        """Create an order on the exchange"""
        try:
            exchange = self.get_exchange(exchange_name)
            
            if order_type == 'market':
                order = await exchange.create_market_order(symbol, side, amount)
            elif order_type == 'limit':
                if price is None:
                    raise ValueError("Price required for limit orders")
                order = await exchange.create_limit_order(symbol, side, amount, price)
            else:
                raise ValueError(f"Unsupported order type: {order_type}")
            
            logger.info(f"Order created on {exchange_name}: {symbol} {side} {amount} @ {price if price else 'market'}")
            return order
        except Exception as e:
            logger.error(f"Error creating order on {exchange_name}: {str(e)}")
            raise
    
    async def withdraw(self, exchange_name: str, currency: str, amount: float, 
                      address: str, tag: Optional[str] = None) -> Dict[str, Any]:
        """Withdraw cryptocurrency to external address"""
        try:
            exchange = self.get_exchange(exchange_name)
            
            params = {}
            if tag:
                params['tag'] = tag
            
            withdrawal = await exchange.withdraw(currency, amount, address, params)
            logger.info(f"Withdrawal initiated from {exchange_name}: {amount} {currency} to {address}")
            return withdrawal
        except Exception as e:
            logger.error(f"Error withdrawing from {exchange_name}: {str(e)}")
            raise
    
    async def get_deposit_address(self, exchange_name: str, currency: str) -> Dict[str, Any]:
        """Get deposit address for a currency"""
        try:
            exchange = self.get_exchange(exchange_name)
            deposit_address = await exchange.fetch_deposit_address(currency)
            return deposit_address
        except Exception as e:
            logger.error(f"Error fetching deposit address from {exchange_name}: {str(e)}")
            raise
    
    async def fetch_order_book(self, exchange_name: str, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """Fetch order book for a symbol"""
        try:
            exchange = self.get_exchange(exchange_name)
            order_book = await exchange.fetch_order_book(symbol, limit)
            return order_book
        except Exception as e:
            logger.error(f"Error fetching order book for {symbol} on {exchange_name}: {str(e)}")
            raise
    
    async def fetch_trades(self, exchange_name: str, symbol: str, limit: int = 50) -> list:
        """Fetch recent trades for a symbol"""
        try:
            exchange = self.get_exchange(exchange_name)
            trades = await exchange.fetch_trades(symbol, limit=limit)
            return trades
        except Exception as e:
            logger.error(f"Error fetching trades for {symbol} on {exchange_name}: {str(e)}")
            raise
    
    async def cancel_order(self, exchange_name: str, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel an order"""
        try:
            exchange = self.get_exchange(exchange_name)
            result = await exchange.cancel_order(order_id, symbol)
            logger.info(f"Order {order_id} canceled on {exchange_name}")
            return result
        except Exception as e:
            logger.error(f"Error canceling order {order_id} on {exchange_name}: {str(e)}")
            raise
    
    async def fetch_my_trades(self, exchange_name: str, symbol: str, since: Optional[int] = None, 
                             limit: Optional[int] = None) -> list:
        """Fetch user's trade history"""
        try:
            exchange = self.get_exchange(exchange_name)
            trades = await exchange.fetch_my_trades(symbol, since, limit)
            return trades
        except Exception as e:
            logger.error(f"Error fetching trade history from {exchange_name}: {str(e)}")
            raise
    
    async def fetch_open_orders(self, exchange_name: str, symbol: Optional[str] = None) -> list:
        """Fetch open orders"""
        try:
            exchange = self.get_exchange(exchange_name)
            orders = await exchange.fetch_open_orders(symbol)
            return orders
        except Exception as e:
            logger.error(f"Error fetching open orders from {exchange_name}: {str(e)}")
            raise
    
    def close_all(self):
        """Close all exchange connections"""
        for exchange_name, exchange in self.exchanges.items():
            if exchange is not None:
                try:
                    exchange.close()
                    logger.info(f"Closed connection to {exchange_name}")
                except Exception as e:
                    logger.error(f"Error closing {exchange_name}: {str(e)}")

