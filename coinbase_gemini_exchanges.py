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
            'coinbase': self.coinbase,  # Keep 'coinbase' as internal key for compatibility
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
    
    async def fetch_deposit_address(self, exchange_id: str, currency: str, 
                                    network: Optional[str] = None, params: Optional[Dict] = None) -> Dict:
        """Fetch deposit address for currency
        
        Args:
            exchange_id: 'coinbase' or 'gemini'
            currency: Currency code (e.g., 'API3', 'ZEC', 'XRP')
            network: Network parameter (e.g., 'ETH', 'ZEC', 'XRP') - required for ERC-20 tokens on Coinbase
            params: Additional parameters dict (will be merged with network)
        """
        exchange = self.get_exchange(exchange_id)
        try:
            # Build params dict
            fetch_params = {}
            if params:
                fetch_params.update(params)
            
            # Add network if provided (required for ERC-20 tokens on Coinbase)
            if network:
                fetch_params['network'] = network
                logger.info(f"   Using network: {network}")
            
            # CCXT fetch_deposit_address can be sync or async
            if fetch_params:
                result = exchange.fetch_deposit_address(currency, fetch_params)
            else:
                result = exchange.fetch_deposit_address(currency)
                
            if hasattr(result, '__await__'):
                address_info = await result
            else:
                address_info = result
            
            # Check if address_info is None (Coinbase may return None if address needs to be generated)
            if address_info is None:
                logger.warning(f"⚠️ {exchange_id} returned None for {currency} deposit address")
                logger.warning(f"   This may mean:")
                logger.warning(f"   1. Deposit address needs to be generated first (check Coinbase UI)")
                logger.warning(f"   2. Network parameter '{network}' may not be correct")
                logger.warning(f"   3. Trying without network parameter as fallback...")
                
                # Try without network parameter as fallback
                try:
                    fallback_result = exchange.fetch_deposit_address(currency)
                    if hasattr(fallback_result, '__await__'):
                        address_info = await fallback_result
                    else:
                        address_info = fallback_result
                    
                    if address_info is None:
                        raise ValueError(f"{exchange_id} returned None for {currency} deposit address. You may need to generate a deposit address in the {exchange_id} UI first.")
                except Exception as fallback_error:
                    raise ValueError(f"Failed to get {currency} deposit address from {exchange_id} (with and without network parameter): {fallback_error}")
            
            # Validate address_info is a dict
            if not isinstance(address_info, dict):
                raise ValueError(f"{exchange_id} returned invalid deposit address format: {type(address_info)} (expected dict)")
            
            # Check if address key exists
            if 'address' not in address_info:
                raise ValueError(f"{exchange_id} deposit address response missing 'address' key: {address_info}")
            
            address = address_info.get('address', '')
            if not address:
                raise ValueError(f"{exchange_id} returned empty address for {currency}")
            
            logger.info(f"✅ Deposit address for {currency} on {exchange_id}: {address[:10]}...")
            return address_info
        except Exception as e:
            logger.error(f"Error fetching deposit address for {currency} on {exchange_id}: {e}")
            raise
    
    async def withdraw(self, exchange_id: str, currency: str, amount: float, 
                      address: str, tag: Optional[str] = None, 
                      network: Optional[str] = None, params: Optional[Dict] = None) -> Dict:
        """Withdraw crypto from exchange
        
        Args:
            exchange_id: 'coinbase' or 'gemini'
            currency: Currency code (e.g., 'API3', 'ZEC', 'XRP')
            amount: Amount to withdraw
            address: Destination address
            tag: Tag/memo (optional, for XRP and similar)
            network: Network parameter (e.g., 'ETH', 'ZEC', 'XRP')
            params: Additional parameters dict (will be merged with network/tag)
        """
        exchange = self.get_exchange(exchange_id)
        try:
            # Log withdrawal attempt
            logger.info(f"🔄 Initiating withdrawal from {exchange_id}:")
            logger.info(f"   Currency: {currency}")
            logger.info(f"   Amount: {amount}")
            logger.info(f"   Address: {address[:10]}...{address[-6:]}")
            
            # Build params dict (following successful pattern from mini_transfer_test.py)
            withdraw_params = {}
            if params:
                withdraw_params.update(params)
            
            # Add network if provided (required for Coinbase ERC-20 tokens)
            if network:
                withdraw_params['network'] = network
                logger.info(f"   Network: {network}")
            
            # Add tag to params (some exchanges require tag in params, not as separate arg)
            # For Coinbase XRP, use 'destination_tag'; for others use 'tag'
            if tag:
                if exchange_id == 'coinbase' and currency == 'XRP':
                    withdraw_params['destination_tag'] = tag
                    logger.info(f"   Destination Tag: {tag}")
                else:
                    withdraw_params['tag'] = tag
                    logger.info(f"   Tag/Memo: {tag}")
            
            # Execute withdrawal (CCXT withdraw can be sync or async)
            # Note: For some exchanges, tag should be in params, not as separate parameter
            # Following successful pattern: pass tag inside params
            result = exchange.withdraw(
                code=currency,
                amount=amount,
                address=address,
                tag=None,  # Don't pass tag separately - it's in params
                params=withdraw_params
            )
            
            # Handle both sync and async responses
            if hasattr(result, '__await__'):
                withdrawal = await result
            else:
                withdrawal = result
            
            withdrawal_id = withdrawal.get('id', 'unknown')
            logger.info(f"✅ Withdrawal initiated: {withdrawal_id}")
            return withdrawal
            
        except Exception as e:
            # Extract detailed error information
            from datetime import datetime
            error_details = {
                'timestamp': datetime.now().isoformat(),
                'error_message': str(e),
                'error_type': type(e).__name__,
                'exchange': exchange_id,
                'currency': currency,
                'amount': amount,
                'address': address[:10] + '...' + address[-6:] if len(address) > 16 else address,
                'network': network,
                'tag': tag
            }
            
            # Try to extract correlation ID, request ID, or other details from exception
            error_str = str(e)
            
            # Check exception attributes
            if hasattr(e, 'args') and e.args:
                for arg in e.args:
                    if isinstance(arg, dict):
                        # Check for correlation ID, request ID, or error details
                        if 'correlation_id' in arg:
                            error_details['correlation_id'] = arg['correlation_id']
                        if 'request_id' in arg:
                            error_details['request_id'] = arg['request_id']
                        if 'id' in arg:
                            error_details['error_id'] = arg['id']
                        if 'message' in arg:
                            error_details['api_message'] = arg['message']
                        # Store full error dict if available
                        error_details['full_error_dict'] = arg
                    elif isinstance(arg, str):
                        # Sometimes error details are in string format
                        if 'correlation' in arg.lower():
                            error_details['raw_error_string'] = arg
            
            # Log ALL exception attributes for debugging
            logger.error("   Exception attributes:")
            if hasattr(e, '__dict__'):
                for key, value in e.__dict__.items():
                    logger.error(f"     {key}: {type(value).__name__} = {str(value)[:200]}")
            
            # Check if CCXT exception has response attribute
            if hasattr(e, 'response'):
                try:
                    response = e.response
                    logger.error(f"   Response object type: {type(response).__name__}")
                    if hasattr(response, 'headers'):
                        # Check headers for correlation ID (case-insensitive)
                        headers = response.headers
                        header_dict = dict(headers) if not isinstance(headers, dict) else headers
                        
                        # Check various header name variations
                        for header_name in ['x-correlation-id', 'X-Correlation-ID', 'correlation-id', 'Correlation-ID', 'x-request-id', 'X-Request-ID', 'request-id']:
                            if header_name in header_dict:
                                error_details['correlation_id'] = header_dict[header_name]
                                logger.error(f"   ✅ Correlation ID found in headers: {header_dict[header_name]}")
                                break
                        
                        error_details['response_headers'] = header_dict
                        logger.error(f"   All response headers: {header_dict}")
                    if hasattr(response, 'status_code'):
                        error_details['http_status_code'] = response.status_code
                        logger.error(f"   HTTP Status Code: {response.status_code}")
                    if hasattr(response, 'status'):
                        error_details['http_status_code'] = response.status
                        logger.error(f"   HTTP Status: {response.status}")
                    if hasattr(response, 'text'):
                        error_details['response_body'] = response.text
                        logger.error(f"   Response Body: {response.text}")
                except Exception as header_error:
                    logger.warning(f"   Could not extract response details: {header_error}")
                    import traceback
                    logger.warning(f"   Traceback: {traceback.format_exc()}")
            
            # Check CCXT-specific attributes
            for attr_name in ['status', 'statusCode', 'code', 'httpStatus', 'httpStatusCode']:
                if hasattr(e, attr_name):
                    value = getattr(e, attr_name)
                    error_details[f'http_status_{attr_name}'] = value
                    logger.error(f"   HTTP Status ({attr_name}): {value}")
            
            # Check for headers in various locations
            for attr_name in ['headers', 'responseHeaders', 'httpHeaders']:
                if hasattr(e, attr_name):
                    headers = getattr(e, attr_name)
                    if headers:
                        header_dict = dict(headers) if not isinstance(headers, dict) else headers
                        error_details['response_headers'] = header_dict
                        logger.error(f"   Headers found in {attr_name}: {header_dict}")
                        
                        # Check for correlation ID
                        for header_name in ['x-correlation-id', 'X-Correlation-ID', 'correlation-id', 'Correlation-ID', 'x-request-id', 'X-Request-ID', 'request-id']:
                            if header_name in header_dict:
                                error_details['correlation_id'] = header_dict[header_name]
                                logger.error(f"   ✅ Correlation ID found: {header_dict[header_name]}")
                                break
            
            # Check exception attributes for correlation-related fields
            if hasattr(e, '__dict__'):
                for key, value in e.__dict__.items():
                    if 'correlation' in key.lower() or 'request_id' in key.lower() or 'requestId' in key:
                        error_details[key] = value
                        logger.error(f"   ✅ Found in exception: {key} = {value}")
            
            # Check if CCXT wraps the error in a specific format
            for attr_name in ['message', 'msg', 'body', 'responseBody']:
                if hasattr(e, attr_name):
                    error_msg = getattr(e, attr_name)
                    if isinstance(error_msg, dict):
                        if 'correlation_id' in error_msg:
                            error_details['correlation_id'] = error_msg['correlation_id']
                            logger.error(f"   ✅ Correlation ID in {attr_name}: {error_msg['correlation_id']}")
                        if 'request_id' in error_msg:
                            error_details['request_id'] = error_msg['request_id']
                            logger.error(f"   ✅ Request ID in {attr_name}: {error_msg['request_id']}")
                        if 'errors' in error_msg:
                            # Check if correlation ID is in errors array
                            errors = error_msg.get('errors', [])
                            if isinstance(errors, list):
                                for error_item in errors:
                                    if isinstance(error_item, dict):
                                        if 'correlation_id' in error_item:
                                            error_details['correlation_id'] = error_item['correlation_id']
                                            logger.error(f"   ✅ Correlation ID in errors: {error_item['correlation_id']}")
            
            # Log detailed error information
            logger.error("=" * 80)
            logger.error(f"❌ ERROR DETAILS - Withdrawal Failed")
            logger.error("=" * 80)
            logger.error(f"Timestamp: {error_details['timestamp']}")
            logger.error(f"Error Type: {error_details['error_type']}")
            logger.error(f"Error Message: {error_details['error_message']}")
            logger.error("")
            if 'correlation_id' in error_details:
                logger.error(f"Correlation ID: {error_details['correlation_id']}")
            if 'request_id' in error_details:
                logger.error(f"Request ID: {error_details['request_id']}")
            if 'error_id' in error_details:
                logger.error(f"Error ID: {error_details['error_id']}")
            if 'http_status_code' in error_details:
                logger.error(f"HTTP Status Code: {error_details['http_status_code']}")
            logger.error("")
            logger.error("Request Details:")
            logger.error(f"  Exchange: {exchange_id}")
            logger.error(f"  Currency: {currency}")
            logger.error(f"  Amount: {amount}")
            logger.error(f"  Network: {network}")
            logger.error(f"  Address: {error_details['address']}")
            if tag:
                logger.error(f"  Tag: {tag}")
            logger.error("")
            if 'response_headers' in error_details:
                logger.error(f"Response Headers: {error_details['response_headers']}")
            if 'response_body' in error_details:
                logger.error(f"Response Body: {error_details['response_body']}")
            if 'http_status_code' in error_details:
                logger.error(f"HTTP Status Code: {error_details['http_status_code']}")
            if 'full_error_dict' in error_details:
                logger.error(f"Full Error Dict: {error_details['full_error_dict']}")
            logger.error("")
            logger.error("NOTE: Correlation ID is a unique request identifier, NOT the error code.")
            logger.error("      It helps Coinbase track the request in their logs.")
            logger.error("      If not shown above, Coinbase can find it using the timestamp.")
            logger.error("=" * 80)
            
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

def get_network_for_currency(currency: str) -> Optional[str]:
    """Get network parameter for a currency
    
    Returns network parameter required for Coinbase withdrawals.
    ERC-20 tokens require 'ETH' network, native tokens use their own network.
    
    Args:
        currency: Currency code (e.g., 'API3', 'ZEC', 'XRP')
    
    Returns:
        Network string (e.g., 'ETH', 'ZEC', 'XRP') or None if unknown
    """
    # Network mapping based on Coinbase documentation
    network_map = {
        # Native blockchains
        'XRP': 'XRP',  # XRP Ledger
        'ZEC': 'ZEC',  # Zcash Network
        'SOL': 'SOL',  # Solana
        
        # ERC-20 tokens on Ethereum
        'BAT': 'ETH',   # Basic Attention Token
        'COMP': 'ETH',  # Compound
        'QNT': 'ETH',   # Quant
        'AMP': 'ETH',   # Amp
        'INJ': 'ETH',   # Injective Protocol
        'API3': 'ETH',  # API3
        'IMX': 'ETH',   # Immutable X
        
        # Add more ERC-20 tokens as needed
        'USDC': 'ETH',  # USD Coin (usually ERC-20)
        'USDT': 'ETH',  # Tether (check specific network needed)
        'LINK': 'ETH',  # Chainlink
        'UNI': 'ETH',   # Uniswap
        'AAVE': 'ETH',  # Aave
    }
    
    return network_map.get(currency.upper())

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


