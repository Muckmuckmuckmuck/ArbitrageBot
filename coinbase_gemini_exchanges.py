"""
Exchange Manager for Coinbase + Gemini
Handles all API interactions with both exchanges
"""

import ccxt
import logging
from typing import Dict, Optional, List
from coinbase_gemini_config import Config

logger = logging.getLogger(__name__)

class CoinbaseGeminiExchangeManager:
    """Manages connections to Coinbase and Gemini exchanges"""
    
    def __init__(self):
        """Initialize exchange connections"""
        self.coinbase = None
        self.gemini = None
        self.exchanges = {}
        
    async def initialize(self):
        """Initialize both exchanges with API keys"""
        logger.info("Initializing Coinbase + Gemini exchanges...")
        
        try:
            # Initialize Coinbase Advanced
            self.coinbase = ccxt.coinbase({
                'apiKey': Config.COINBASE_API_KEY,
                'secret': Config.COINBASE_SECRET_KEY,
                'password': Config.COINBASE_PASSPHRASE,
                **Config.EXCHANGE_CONFIGS['coinbase'],
            })
            
            # Set sandbox mode if enabled
            if Config.COINBASE_SANDBOX:
                self.coinbase.set_sandbox_mode(True)
                logger.info("Coinbase: Sandbox mode enabled")
            
            # Load markets (CCXT load_markets is synchronous)
            self.coinbase.load_markets()
            logger.info(f"✅ Coinbase initialized: {len(self.coinbase.markets)} markets")
            
        except Exception as e:
            logger.error(f"Failed to initialize Coinbase: {e}")
            raise
        
        try:
            # Initialize Gemini
            self.gemini = ccxt.gemini({
                'apiKey': Config.GEMINI_API_KEY,
                'secret': Config.GEMINI_SECRET_KEY,
                **Config.EXCHANGE_CONFIGS['gemini'],
            })
            
            # Set sandbox mode if enabled
            if Config.GEMINI_SANDBOX:
                self.gemini.set_sandbox_mode(True)
                logger.info("Gemini: Sandbox mode enabled")
            
            # Load markets (CCXT load_markets is synchronous)
            self.gemini.load_markets()
            logger.info(f"✅ Gemini initialized: {len(self.gemini.markets)} markets")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise
        
        # Store in dict for easy access
        self.exchanges = {
            'coinbase': self.coinbase,
            'gemini': self.gemini,
        }
        
        logger.info("✅ Both exchanges initialized successfully")
        
        return True
    
    def get_exchange(self, exchange_id: str):
        """Get exchange object by ID"""
        if exchange_id not in self.exchanges:
            raise ValueError(f"Unknown exchange: {exchange_id}")
        return self.exchanges[exchange_id]
    
    async def fetch_balance(self, exchange_id: str) -> Dict:
        """Fetch balance from exchange"""
        exchange = self.get_exchange(exchange_id)
        try:
            # CCXT fetch_balance can be sync or async depending on version
            result = exchange.fetch_balance()
            # Check if it's a coroutine (async) or direct result (sync)
            if hasattr(result, '__await__'):
                balance = await result
            else:
                balance = result
            return balance
        except Exception as e:
            logger.error(f"Error fetching balance from {exchange_id}: {e}")
            raise
    
    async def fetch_ticker(self, exchange_id: str, symbol: str) -> Dict:
        """Fetch ticker (price) from exchange"""
        exchange = self.get_exchange(exchange_id)
        try:
            # CCXT fetch_ticker can be sync or async depending on version
            result = exchange.fetch_ticker(symbol)
            # Check if it's a coroutine (async) or direct result (sync)
            if hasattr(result, '__await__'):
                ticker = await result
            else:
                ticker = result
            return ticker
        except Exception as e:
            logger.error(f"Error fetching ticker {symbol} from {exchange_id}: {e}")
            raise
    
    async def fetch_order_book(self, exchange_id: str, symbol: str, limit: int = 20) -> Dict:
        """Fetch order book from exchange"""
        exchange = self.get_exchange(exchange_id)
        try:
            # CCXT fetch_order_book can be sync or async
            result = exchange.fetch_order_book(symbol, limit)
            if hasattr(result, '__await__'):
                order_book = await result
            else:
                order_book = result
            return order_book
        except Exception as e:
            logger.error(f"Error fetching order book {symbol} from {exchange_id}: {e}")
            raise
    
    async def create_order(self, exchange_id: str, symbol: str, order_type: str, 
                          side: str, amount: float, price: Optional[float] = None) -> Dict:
        """Create order on exchange"""
        exchange = self.get_exchange(exchange_id)
        try:
            # CCXT create_order is synchronous, check if it returns awaitable
            order_result = exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
            )
            
            # Handle both sync and async responses
            if hasattr(order_result, '__await__'):
                order = await order_result
            else:
                order = order_result
            
            logger.info(f"✅ Order created on {exchange_id}: {side} {amount} {symbol} @ {price}")
            return order
        except Exception as e:
            logger.error(f"Error creating order on {exchange_id}: {e}")
            raise
    
    async def fetch_order(self, exchange_id: str, order_id: str, symbol: str) -> Dict:
        """Fetch order status"""
        exchange = self.get_exchange(exchange_id)
        try:
            # CCXT fetch_order is synchronous, check if it returns awaitable
            order_result = exchange.fetch_order(order_id, symbol)
            
            # Handle both sync and async responses
            if hasattr(order_result, '__await__'):
                order = await order_result
            else:
                order = order_result
            
            return order
        except Exception as e:
            logger.error(f"Error fetching order {order_id} from {exchange_id}: {e}")
            raise
    
    async def cancel_order(self, exchange_id: str, order_id: str, symbol: str) -> Dict:
        """Cancel order"""
        exchange = self.get_exchange(exchange_id)
        try:
            # CCXT cancel_order is synchronous, check if it returns awaitable
            result_obj = exchange.cancel_order(order_id, symbol)
            
            # Handle both sync and async responses
            if hasattr(result_obj, '__await__'):
                result = await result_obj
            else:
                result = result_obj
            
            logger.info(f"✅ Order cancelled on {exchange_id}: {order_id}")
            return result
        except Exception as e:
            logger.error(f"Error cancelling order {order_id} on {exchange_id}: {e}")
            raise
    
    async def fetch_deposit_address(self, exchange_id: str, currency: str) -> Dict:
        """Fetch deposit address for currency"""
        exchange = self.get_exchange(exchange_id)
        try:
            # CCXT fetch_deposit_address can be sync or async
            result = exchange.fetch_deposit_address(currency)
            if hasattr(result, '__await__'):
                address_info = await result
            else:
                address_info = result
            logger.info(f"✅ Deposit address for {currency} on {exchange_id}: {address_info.get('address', '')[:10]}...")
            return address_info
        except Exception as e:
            logger.error(f"Error fetching deposit address for {currency} on {exchange_id}: {e}")
            raise
    
    async def withdraw(self, exchange_id: str, currency: str, amount: float, 
                      address: str, tag: Optional[str] = None) -> Dict:
        """Withdraw crypto from exchange"""
        exchange = self.get_exchange(exchange_id)
        try:
            # Log withdrawal attempt
            logger.info(f"🔄 Initiating withdrawal from {exchange_id}:")
            logger.info(f"   Currency: {currency}")
            logger.info(f"   Amount: {amount}")
            logger.info(f"   Address: {address[:10]}...{address[-6:]}")
            if tag:
                logger.info(f"   Tag/Memo: {tag}")
            
            # Execute withdrawal (CCXT withdraw can be sync or async)
            result = exchange.withdraw(
                code=currency,
                amount=amount,
                address=address,
                tag=tag,
                params={}
            )
            
            # Handle both sync and async responses
            if hasattr(result, '__await__'):
                withdrawal = await result
            else:
                withdrawal = result
            
            logger.info(f"✅ Withdrawal initiated: {withdrawal.get('id', 'unknown')}")
            return withdrawal
            
        except Exception as e:
            logger.error(f"Error withdrawing {currency} from {exchange_id}: {e}")
            raise
    
    async def fetch_my_trades(self, exchange_id: str, symbol: Optional[str] = None, 
                             since: Optional[int] = None, limit: Optional[int] = None) -> List[Dict]:
        """Fetch user's trade history"""
        exchange = self.get_exchange(exchange_id)
        try:
            # CCXT fetch_my_trades can be sync or async
            result = exchange.fetch_my_trades(symbol, since, limit)
            if hasattr(result, '__await__'):
                trades = await result
            else:
                trades = result
            return trades
        except Exception as e:
            logger.error(f"Error fetching trades from {exchange_id}: {e}")
            raise
    
    async def fetch_trading_fees(self, exchange_id: str) -> Dict:
        """Fetch current trading fees"""
        exchange = self.get_exchange(exchange_id)
        try:
            # CCXT fetch_trading_fees can be sync or async
            result = exchange.fetch_trading_fees()
            if hasattr(result, '__await__'):
                fees = await result
            else:
                fees = result
            return fees
        except Exception as e:
            logger.warning(f"Could not fetch trading fees from {exchange_id}: {e}")
            # Return default fees from config
            return Config.EXCHANGE_FEES.get(exchange_id, {})
    
    def get_fee_for_trade(self, exchange_id: str, is_maker: bool = False) -> float:
        """Get fee for a trade (maker or taker)"""
        fees = Config.EXCHANGE_FEES.get(exchange_id, {})
        if is_maker:
            return fees.get('maker', 0.006)  # Default 0.6% if unknown
        else:
            return fees.get('taker', 0.006)  # Default 0.6% if unknown
    
    def get_withdrawal_fee(self, exchange_id: str, currency: str) -> float:
        """Get withdrawal fee for currency"""
        fees = Config.EXCHANGE_FEES.get(exchange_id, {})
        withdrawal_fees = fees.get('withdrawal', {})
        return withdrawal_fees.get(currency, withdrawal_fees.get('default', 0.0))
    
    async def close(self):
        """Close exchange connections"""
        try:
            if self.coinbase and hasattr(self.coinbase, 'close'):
                await self.coinbase.close()
        except Exception as e:
            logger.warning(f"Error closing Coinbase: {e}")
        
        try:
            if self.gemini and hasattr(self.gemini, 'close'):
                await self.gemini.close()
        except Exception as e:
            logger.warning(f"Error closing Gemini: {e}")
        
        logger.info("Exchange connections closed")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_base_currency(symbol: str) -> str:
    """Extract base currency from symbol (e.g., 'BTC/USD' -> 'BTC')"""
    return symbol.split('/')[0]

def get_quote_currency(symbol: str) -> str:
    """Extract quote currency from symbol (e.g., 'BTC/USD' -> 'USD')"""
    return symbol.split('/')[1]

def calculate_total_fees(buy_exchange: str, sell_exchange: str, 
                        is_maker_buy: bool = False, is_maker_sell: bool = False) -> float:
    """Calculate total fees for a round-trip trade"""
    buy_fee = Config.EXCHANGE_FEES[buy_exchange]['maker' if is_maker_buy else 'taker']
    sell_fee = Config.EXCHANGE_FEES[sell_exchange]['maker' if is_maker_sell else 'taker']
    return buy_fee + sell_fee

def calculate_min_profitable_spread(buy_exchange: str, sell_exchange: str, 
                                   slippage: float = 0.001) -> float:
    """Calculate minimum spread needed for profitability"""
    total_fees = calculate_total_fees(buy_exchange, sell_exchange)
    min_spread = total_fees + slippage + 0.001  # +0.1% buffer
    return min_spread

if __name__ == "__main__":
    print("=" * 80)
    print("COINBASE + GEMINI EXCHANGE MANAGER")
    print("=" * 80)
    print()
    
    print("Configuration:")
    print(f"  Exchange 1: {Config.EXCHANGE_1_ID}")
    print(f"  Exchange 2: {Config.EXCHANGE_2_ID}")
    print()
    
    print("Fee Calculation Examples:")
    print()
    
    # Example 1: Buy on Coinbase, sell on Gemini
    total_fees_1 = calculate_total_fees('coinbase', 'gemini')
    min_spread_1 = calculate_min_profitable_spread('coinbase', 'gemini')
    print(f"Buy on Coinbase, Sell on Gemini:")
    print(f"  Total fees: {total_fees_1*100:.2f}%")
    print(f"  Min profitable spread: {min_spread_1*100:.2f}%")
    print()
    
    # Example 2: Buy on Gemini, sell on Coinbase
    total_fees_2 = calculate_total_fees('gemini', 'coinbase')
    min_spread_2 = calculate_min_profitable_spread('gemini', 'coinbase')
    print(f"Buy on Gemini, Sell on Coinbase:")
    print(f"  Total fees: {total_fees_2*100:.2f}%")
    print(f"  Min profitable spread: {min_spread_2*100:.2f}%")
    print()
    
    print("Withdrawal Fees:")
    print(f"  Coinbase: FREE for all cryptos")
    print(f"  Gemini: FREE (10 per month)")
    print()
    
    print("✅ Exchange manager ready!")


