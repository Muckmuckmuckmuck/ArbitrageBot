"""
Exchange Manager for Coinbase + Gemini
Handles all API interactions with both exchanges

EXCHANGE MARKERS:
    🔵 COINBASE - All Coinbase-specific code is marked with 🔵
    🟢 GEMINI - All Gemini-specific code is marked with 🟢
    ⚪ COMMON - Code that works for both exchanges
"""

import logging
import hmac
import hashlib
import base64
import time
import json
import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, Optional, List, Tuple, Any

import ccxt
from ccxt.base.errors import OrderNotFound, InvalidOrder, ExchangeError
from coinbase_gemini_config import Config

logger = logging.getLogger(__name__)

# ============================================================================
# EXCHANGE CONSTANTS
# ============================================================================
EXCHANGE_COINBASE = 'coinbase'
EXCHANGE_GEMINI = 'gemini'

class CoinbaseGeminiExchangeManager:
    """Manages connections to Coinbase and Gemini exchanges"""
    
    def __init__(self):
        """Initialize exchange connections"""
        self.coinbase = None
        self.gemini = None
        self.exchanges = {}
        self._price_cache: Dict[str, Dict[str, Tuple[float, float]]] = {}
        
    async def initialize(self):
        """Initialize both exchanges with API keys"""
        logger.info("Initializing Coinbase + Gemini exchanges...")
        
        # ====================================================================
        # 🔵 COINBASE INITIALIZATION
        # ====================================================================
        try:
            # 🔵 Initialize Coinbase - simplified to match working BTC script
            coinbase_config = {
                'apiKey': Config.COINBASE_API_KEY,
                'secret': Config.COINBASE_SECRET_KEY,
                'password': Config.COINBASE_PASSPHRASE,
                'options': {
                    'advanced': True  # Same as BTC script
                },
                'enableRateLimit': True,
                'verbose': False,
                **Config.EXCHANGE_CONFIGS['coinbase'],
            }
            
            self.coinbase = ccxt.coinbase(coinbase_config)
            
            # 🔵 Coinbase sandbox mode
            if Config.COINBASE_SANDBOX:
                self.coinbase.set_sandbox_mode(True)
            
            # 🔵 Load Coinbase markets - same as BTC script
            self.coinbase.load_markets()
            logger.info(f"✅ Coinbase initialized: {len(self.coinbase.markets)} markets")
            
        except Exception as e:
            logger.error(f"Failed to initialize Coinbase: {e}")
            raise
        
        # ====================================================================
        # 🟢 GEMINI INITIALIZATION (OPTIONAL - bot can run with Coinbase only)
        # ====================================================================
        self.gemini = None  # Initialize to None in case of failure
        try:
            # 🟢 Initialize Gemini
            self.gemini = ccxt.gemini({
                'apiKey': Config.GEMINI_API_KEY,
                'secret': Config.GEMINI_SECRET_KEY,
                **Config.EXCHANGE_CONFIGS['gemini'],
            })
            
            # 🟢 Gemini sandbox mode
            if Config.GEMINI_SANDBOX:
                self.gemini.set_sandbox_mode(True)
                logger.info("   🟢 Gemini: Sandbox mode enabled")
            
            # 🟢 Load Gemini markets (CCXT load_markets is synchronous)
            self.gemini.load_markets()
            logger.info(f"   ✅ Gemini initialized: {len(self.gemini.markets)} markets")
            
        except Exception as e:
            # 🔵 CRITICAL FIX: Don't crash if Gemini is unavailable - allow bot to run with Coinbase only
            error_msg = str(e)
            if "maintenance" in error_msg.lower() or "503" in error_msg or "OnMaintenance" in str(type(e).__name__):
                logger.warning(f"   ⚠️ Gemini is currently under maintenance - bot will run with Coinbase only")
                logger.warning(f"   💡 Check https://status.gemini.com/ for maintenance status")
            else:
                logger.warning(f"   ⚠️ Failed to initialize Gemini: {error_msg}")
                logger.warning(f"   💡 Bot will continue with Coinbase only")
            self.gemini = None  # Set to None so we can check availability later
        
        # ⚪ Store both exchanges in dict for easy access
        self.exchanges = {
            EXCHANGE_COINBASE: self.coinbase,  # 🔵 Coinbase exchange
            EXCHANGE_GEMINI: self.gemini,      # 🟢 Gemini exchange (may be None)
        }
        
        if self.gemini:
            logger.info("   ✅ Both exchanges initialized successfully")
        else:
            logger.info("   ✅ Coinbase initialized successfully (Gemini unavailable)")
        
        return True
    
    def get_exchange(self, exchange_id: str):
        """Get exchange object by ID"""
        if exchange_id not in self.exchanges:
            raise ValueError(f"Unknown exchange: {exchange_id}")
        exchange = self.exchanges[exchange_id]
        if exchange is None:
            exchange_marker = "🔵" if exchange_id == EXCHANGE_COINBASE else "🟢"
            raise ValueError(f"{exchange_marker} [{exchange_id.upper()}] Exchange not available (initialization failed or maintenance)")
        return exchange
    
    def is_exchange_available(self, exchange_id: str) -> bool:
        """Check if an exchange is available"""
        return exchange_id in self.exchanges and self.exchanges[exchange_id] is not None

    async def _get_price_in_usd(self, exchange_id: str, asset: str, visited: Optional[set] = None) -> Optional[float]:
        asset = asset.upper()
        stable_map = {
            'USD': 1.0,
            'USDC': 1.0,
            'USDT': 1.0,
            'GUSD': 1.0,
        }
        if asset in stable_map:
            return stable_map[asset]
        if visited is None:
            visited = set()
        key = (exchange_id, asset)
        if key in visited:
            return None
        visited.add(key)

        now = time.time()
        cache = self._price_cache.setdefault(exchange_id, {})
        if asset in cache:
            cached_price, cached_ts = cache[asset]
            if now - cached_ts < 30:
                return cached_price

        if not self.is_exchange_available(exchange_id):
            return None
        exchange = self.get_exchange(exchange_id)
        preferred_quotes = ['USD', 'USDC', 'USDT', 'GUSD']
        for quote in preferred_quotes:
            symbol = f"{asset}/{quote}"
            if symbol in exchange.markets:
                try:
                    ticker = await self.fetch_ticker(exchange_id, symbol)
                    price = ticker.get('last') or ticker.get('close') or ticker.get('bid') or ticker.get('ask')
                    if not price or price <= 0:
                        continue
                    if quote != 'USD':
                        quote_price = await self._get_price_in_usd(exchange_id, quote, visited)
                        if not quote_price:
                            continue
                        price *= quote_price
                    cache[asset] = (price, now)
                    return price
                except Exception as e:
                    logger.debug(f"   {exchange_id.upper()} pricing {asset}/{quote} failed: {e}")
                    continue

        # Fallback: try other exchange if available
        other_exchange = EXCHANGE_GEMINI if exchange_id == EXCHANGE_COINBASE else EXCHANGE_COINBASE
        if self.is_exchange_available(other_exchange):
            try:
                price = await self._get_price_in_usd(other_exchange, asset, visited)
                if price:
                    cache[asset] = (price, now)
                    return price
            except Exception:
                pass
        return None

    async def compute_portfolio_snapshot(self, exchange_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        exchanges_to_check = exchange_filter if exchange_filter else [EXCHANGE_COINBASE, EXCHANGE_GEMINI]
        snapshot: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_value_usd': 0.0,
            'exchanges': {}
        }
        for exchange_id in exchanges_to_check:
            if not self.is_exchange_available(exchange_id):
                continue
            try:
                balance = await self.fetch_balance(exchange_id)
            except Exception as e:
                logger.error(f"   Error computing snapshot for {exchange_id}: {e}")
                continue
            exchange_snapshot = {
                'total_value_usd': 0.0,
                'stable_value_usd': 0.0,
                'crypto_value_usd': 0.0,
                'assets': []
            }
            total_balances = balance.get('total', {}) or {}
            for asset, total_amount in total_balances.items():
                if not total_amount or total_amount == 0:
                    continue
                price_usd = await self._get_price_in_usd(exchange_id, asset)
                value_usd = price_usd * total_amount if price_usd else 0.0
                asset_entry = {
                    'asset': asset,
                    'amount': total_amount,
                    'price_usd': price_usd,
                    'value_usd': value_usd
                }
                exchange_snapshot['assets'].append(asset_entry)
                exchange_snapshot['total_value_usd'] += value_usd
                if asset.upper() in {'USD', 'USDC', 'USDT', 'GUSD'}:
                    exchange_snapshot['stable_value_usd'] += value_usd
                else:
                    exchange_snapshot['crypto_value_usd'] += value_usd
            snapshot['exchanges'][exchange_id] = exchange_snapshot
            snapshot['total_value_usd'] += exchange_snapshot['total_value_usd']
        return snapshot
    
    async def fetch_balance(self, exchange_id: str) -> Dict:
        """
        ⚪ COMMON: Fetch balance from exchange (works for both Coinbase and Gemini)
        
        Args:
            exchange_id: EXCHANGE_COINBASE or EXCHANGE_GEMINI
        """
        exchange = self.get_exchange(exchange_id)
        exchange_marker = "🔵" if exchange_id == EXCHANGE_COINBASE else "🟢"
        try:
            logger.debug(f"   {exchange_marker} [{exchange_id.upper()}] Fetching balance...")
            # CCXT fetch_balance can be sync or async depending on version
            result = exchange.fetch_balance()
            # Check if it's a coroutine (async) or direct result (sync)
            if hasattr(result, '__await__'):
                balance = await result
            else:
                balance = result
            logger.debug(f"   {exchange_marker} [{exchange_id.upper()}] Balance fetched successfully")
            return balance
        except Exception as e:
            logger.error(f"   {exchange_marker} [{exchange_id.upper()}] Error fetching balance: {e}")
            raise
    
    async def fetch_ticker(self, exchange_id: str, symbol: str) -> Dict:
        """
        ⚪ COMMON: Fetch ticker (price) from exchange (works for both Coinbase and Gemini)
        
        Args:
            exchange_id: EXCHANGE_COINBASE or EXCHANGE_GEMINI
        """
        exchange = self.get_exchange(exchange_id)
        exchange_marker = "🔵" if exchange_id == EXCHANGE_COINBASE else "🟢"
        try:
            logger.debug(f"   {exchange_marker} [{exchange_id.upper()}] Fetching ticker for {symbol}...")
            # CCXT fetch_ticker can be sync or async depending on version
            result = exchange.fetch_ticker(symbol)
            # Check if it's a coroutine (async) or direct result (sync)
            if hasattr(result, '__await__'):
                ticker = await result
            else:
                ticker = result
            logger.debug(f"   {exchange_marker} [{exchange_id.upper()}] Ticker fetched for {symbol}: ${ticker.get('last', 0):.8f}")
            return ticker
        except Exception as e:
            logger.error(f"   {exchange_marker} [{exchange_id.upper()}] Error fetching ticker {symbol}: {e}")
            raise
    
    async def fetch_order_book(self, exchange_id: str, symbol: str, limit: int = 20) -> Dict:
        """
        ⚪ COMMON: Fetch order book from exchange (works for both Coinbase and Gemini)
        
        Args:
            exchange_id: EXCHANGE_COINBASE or EXCHANGE_GEMINI
        """
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
                          side: str, amount: float, price: Optional[float] = None, 
                          params: Optional[Dict] = None) -> Dict:
        """
        Create order on exchange - simplified to match working BTC purchase script
        Uses exact same approach that worked for BTC/USDC purchase
        
        CRITICAL: 🟢 Gemini only supports limit orders, not market orders
        """
        exchange = self.get_exchange(exchange_id)
        
        # ====================================================================
        # 🟢 GEMINI-SPECIFIC: Market order conversion
        # ====================================================================
        # 🟢 CRITICAL FIX: Gemini doesn't support market orders - convert to limit
        if exchange_id == EXCHANGE_GEMINI and order_type == 'market':
            logger.warning(f"   ⚠️ Gemini doesn't support market orders - converting to limit order")
            # Get current price for limit order
            ticker = await self.fetch_ticker(exchange_id, symbol)
            current_price = ticker.get('bid' if side == 'sell' else 'ask') or ticker.get('last', 0)
            if current_price <= 0:
                raise ValueError(f"Cannot convert market order to limit: no price available for {symbol}")
            # Use limit order slightly worse than market to ensure fill
            if side == 'buy':
                price = current_price * 1.001  # 0.1% above market
            else:
                price = current_price * 0.999  # 0.1% below market
            order_type = 'limit'
            logger.info(f"   💡 Converted to limit order: {side} @ ${price:.4f}")
        
        # ====================================================================
        # 🔵 COINBASE-SPECIFIC: Parameter cleanup
        # ====================================================================
        # 🔵 For Coinbase, remove invalid params (same as BTC script approach)
        if exchange_id == EXCHANGE_COINBASE and params:
            order_params = params.copy()
            # 🔵 Remove params that cause errors (same approach as BTC script)
            order_params.pop('portfolio_id', None)
            order_params.pop('retail_portfolio_id', None)
        else:
            order_params = params
        
        # ====================================================================
        # ⚪ COMMON: Precision and validation (works for both exchanges)
        # ====================================================================
        # ⚪ Apply precision requirements from market info
        market_info = exchange.markets.get(symbol, {})
        if market_info:
            precision = market_info.get('precision', {})
            
            # 🔵 COINBASE and 🟢 GEMINI: Handle precision correctly
            # CCXT precision can be:
            # - int: decimal places (e.g., 2 = 2 decimal places)
            # - float: step size (e.g., 0.01 = step of 0.01)
            # - None/0: use default
            amount_precision_val = precision.get('amount')
            price_precision_val = precision.get('price')
            
            # Convert to int for decimal places, but ensure minimum precision
            # ⚠️ CRITICAL: Never use 0 precision for prices (would round $0.059 to $0.00)
            if amount_precision_val is not None and amount_precision_val != 0:
                amount_precision = int(amount_precision_val)
            else:
                amount_precision = 8  # Default to 8 decimal places
            
            if price_precision_val is not None and price_precision_val != 0:
                price_precision = int(price_precision_val)
            else:
                # 🔵 COINBASE: Default to 8 decimal places for prices
                # 🟢 GEMINI: Default to 8 decimal places for prices
                price_precision = 8  # Never use 0 - would break prices like $0.059960
            
            # Store original values for logging and validation
            original_amount = amount
            original_price = price
            
            # Calculate order value BEFORE rounding (for validation)
            if price is not None:
                order_value_before_rounding = amount * price
            
            # Round amount and price to exchange precision
            # ⚠️ CRITICAL: Ensure precision is valid (>= 0 and reasonable)
            amount = round(amount, amount_precision) if amount_precision > 0 else amount
            if price is not None:
                # 🔵 COINBASE / 🟢 GEMINI: Never round price to 0 decimal places
                price = round(price, price_precision) if price_precision > 0 else price
                
                # Safety check: if price becomes 0 after rounding, use original
                if price == 0 and original_price > 0:
                    logger.warning(f"   ⚠️ [{exchange_id.upper()}] Price rounded to 0! Using original: ${original_price:.8f}")
                    price = original_price
            
            # Validate minimum order size AFTER rounding
            if price is not None:
                # 🔵 CRITICAL FIX: Validate inputs before calculation
                if amount is None or price is None:
                    exchange_marker = "🔵" if exchange_id == EXCHANGE_COINBASE else "🟢"
                    logger.error(f"   {exchange_marker} [{exchange_id.upper()}] ❌ Invalid order parameters: amount={amount}, price={price}")
                    raise ValueError(f"Invalid order parameters: amount={amount}, price={price}")
                
                min_order_value = amount * price
                # Check market minimums (typically $5-10 for most exchanges)
                # 🔵 CRITICAL FIX: Handle None values in min_cost
                limits = market_info.get('limits', {}) or {}
                cost_limits = limits.get('cost', {}) or {}
                min_cost = cost_limits.get('min', 5.0) or 5.0
                
                # Ensure min_cost is a valid number
                if min_cost is None or not isinstance(min_cost, (int, float)) or min_cost <= 0:
                    min_cost = 5.0  # Default minimum
                    logger.debug(f"   [{exchange_id.upper()}] Using default min_cost: ${min_cost:.2f}")
                
                # 🔵 COINBASE and 🟢 GEMINI have different minimums - log for debugging
                # 🔵 CRITICAL FIX: Ensure both values are valid before comparison
                if min_order_value is not None and min_cost is not None and min_order_value < min_cost:
                    # 🔵 COINBASE / 🟢 GEMINI: Comprehensive logging with exchange marker
                    logger.error(f"   ❌ [{exchange_id.upper()}] Order validation failed for {symbol}:")
                    logger.error(f"      Exchange: {exchange_id.upper()}")
                    logger.error(f"      Symbol: {symbol}")
                    logger.error(f"      Amount before rounding: {original_amount:.8f}")
                    logger.error(f"      Amount after rounding: {amount:.8f} (precision: {amount_precision})")
                    logger.error(f"      Price before rounding: ${original_price:.8f}")
                    logger.error(f"      Price after rounding: ${price:.8f} (precision: {price_precision})")
                    logger.error(f"      Order value before rounding: ${order_value_before_rounding:.2f}")
                    logger.error(f"      Order value after rounding: ${min_order_value:.2f}")
                    logger.error(f"      Required minimum: ${min_cost:.2f}")
                    
                    # If rounding caused the issue, warn and suggest fix
                    if order_value_before_rounding >= min_cost and min_order_value < min_cost:
                        logger.error(f"   ⚠️ [{exchange_id.upper()}] Rounding caused order value to drop below minimum!")
                        logger.error(f"   💡 Consider increasing order size or using different precision")
                        logger.error(f"   💡 Price precision: {price_precision}, Amount precision: {amount_precision}")
                    
                    raise ValueError(f"[{exchange_id.upper()}] Order value ${min_order_value:.2f} < minimum ${min_cost:.2f} for {symbol}")
        else:
            # If no market info, still validate if price is provided
            if price is not None:
                min_order_value = amount * price
                if min_order_value < 5.0:  # Default minimum
                    logger.error(f"   ❌ Order validation failed (no market info): ${min_order_value:.2f} < $5.00")
                    raise ValueError(f"Order value ${min_order_value:.2f} < minimum $5.00 for {symbol}")
        
        # ====================================================================
        # ⚪ COMMON: Final validation before order creation
        # ====================================================================
        # 🔵 CRITICAL FIX: Validate all parameters before API call
        exchange_marker = "🔵" if exchange_id == EXCHANGE_COINBASE else "🟢"
        
        if amount is None or amount <= 0:
            logger.error(f"   {exchange_marker} [{exchange_id.upper()}] ❌ Invalid amount: {amount}")
            raise ValueError(f"Invalid amount: {amount}")
        
        if order_type == 'limit' and (price is None or price <= 0):
            logger.error(f"   {exchange_marker} [{exchange_id.upper()}] ❌ Invalid price for limit order: {price}")
            raise ValueError(f"Invalid price for limit order: {price}")
        
        # ====================================================================
        # ⚪ COMMON: Order creation (works for both exchanges)
        # ====================================================================
        # 🔵 COINBASE / 🟢 GEMINI: Create order with comprehensive logging
        logger.info(f"   {exchange_marker} [{exchange_id.upper()}] 📝 Creating {side} {order_type} order:")
        logger.info(f"      {exchange_marker} [{exchange_id.upper()}] Symbol: {symbol}")
        logger.info(f"      {exchange_marker} [{exchange_id.upper()}] Type: {order_type}")
        logger.info(f"      {exchange_marker} [{exchange_id.upper()}] Amount: {amount:.8f}")
        if price:
            logger.info(f"      {exchange_marker} [{exchange_id.upper()}] Price: ${price:.8f}")
        else:
            logger.info(f"      {exchange_marker} [{exchange_id.upper()}] Price: MARKET")
        
        # ⚪ Simple direct call - exactly like BTC script that worked
        try:
            # 🔵 CRITICAL FIX: Log exact parameters being sent
            logger.debug(f"   {exchange_marker} [{exchange_id.upper()}] Order parameters:")
            logger.debug(f"      {exchange_marker} [{exchange_id.upper()}] symbol={symbol}")
            logger.debug(f"      {exchange_marker} [{exchange_id.upper()}] type={order_type}")
            logger.debug(f"      {exchange_marker} [{exchange_id.upper()}] side={side}")
            logger.debug(f"      {exchange_marker} [{exchange_id.upper()}] amount={amount}")
            logger.debug(f"      {exchange_marker} [{exchange_id.upper()}] price={price}")
            if order_params:
                logger.debug(f"      {exchange_marker} [{exchange_id.upper()}] params={order_params}")
            
            if order_params:
                order = exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
                    params=order_params
                )
            else:
                order = exchange.create_order(
                    symbol=symbol,
                    type=order_type,
                    side=side,
                    amount=amount,
                    price=price
                )
            
            # CCXT returns sync result, but handle async just in case
            if hasattr(order, '__await__'):
                order_result = await order
            else:
                order_result = order
            
            # 🔵 CRITICAL FIX: Log full order response for debugging
            logger.debug(f"   {exchange_marker} [{exchange_id.upper()}] Order response: {order_result}")
            
            order_id = order_result.get('id') if order_result else None
            if order_id:
                logger.info(f"   {exchange_marker} [{exchange_id.upper()}] ✅✅✅ ORDER CREATED SUCCESSFULLY: ID={order_id}")
                price_str = f"${price:.8f}" if price else "MARKET"
                logger.info(f"   {exchange_marker} [{exchange_id.upper()}] Order details: {symbol} {side} {amount:.8f} @ {price_str}")
            else:
                logger.warning(f"   {exchange_marker} [{exchange_id.upper()}] ⚠️ Order created but no ID returned: {order_result}")
            
            return order_result
            
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            logger.error(f"   {exchange_marker} [{exchange_id.upper()}] ❌❌❌ ERROR CREATING ORDER:")
            logger.error(f"   {exchange_marker} [{exchange_id.upper()}]    Error Type: {error_type}")
            logger.error(f"   {exchange_marker} [{exchange_id.upper()}]    Error Message: {error_msg}")
            logger.error(f"   {exchange_marker} [{exchange_id.upper()}]    Symbol: {symbol}")
            logger.error(f"   {exchange_marker} [{exchange_id.upper()}]    Order Type: {order_type}")
            logger.error(f"   {exchange_marker} [{exchange_id.upper()}]    Side: {side}")
            logger.error(f"   {exchange_marker} [{exchange_id.upper()}]    Amount: {amount}")
            logger.error(f"   {exchange_marker} [{exchange_id.upper()}]    Price: {price}")
            import traceback
            logger.error(f"   {exchange_marker} [{exchange_id.upper()}]    Traceback: {traceback.format_exc()}")
            
            # ================================================================
            # 🔵 COINBASE-SPECIFIC: Error handling
            # ================================================================
            # 🔵 If it's "account is not available", provide detailed diagnostics
            if "account is not available" in error_msg.lower() and exchange_id == EXCHANGE_COINBASE:
                logger.error(f"   {exchange_marker} [{exchange_id.upper()}] ⚠️ Possible causes:")
                logger.error(f"   {exchange_marker} [{exchange_id.upper()}]      1. Account not enabled for {symbol.split('/')[1]} trading")
                logger.error(f"   {exchange_marker} [{exchange_id.upper()}]      2. Account restrictions on EUR/GBP pairs")
                logger.error(f"   {exchange_marker} [{exchange_id.upper()}]      3. KYC verification incomplete")
                logger.error(f"   {exchange_marker} [{exchange_id.upper()}]      4. Account type limitations (Business vs Retail)")
                logger.error(f"   {exchange_marker} [{exchange_id.upper()}]      5. Trading permissions not enabled for this currency pair")
                logger.error(f"   {exchange_marker} [{exchange_id.upper()}]   💡 Check Coinbase account settings and trading permissions")
            
            raise
    
    async def convert_currency(self, exchange_id: str, from_currency: str, to_currency: str, amount: float) -> bool:
        """
        Convert currency - simplified for USD/USDC/USDT only
        
        Note: USD, USDC, and USDT are interchangeable at 1:1 rate
        No actual conversion needed - just return True if currencies are compatible
        
        Returns True if conversion successful (or not needed)
        """
        # USD/USDC/USDT are interchangeable - no conversion needed
        if from_currency in ['USD', 'USDC', 'USDT'] and to_currency in ['USD', 'USDC', 'USDT']:
            logger.debug(f"   ✅ USD/USDC/USDT are interchangeable - no conversion needed")
            return True
        
        if from_currency == to_currency:
            return True
        
        # For other currencies, conversion is not supported
        logger.warning(f"   ⚠️ Currency conversion not supported: {from_currency} → {to_currency}")
        logger.warning(f"   💡 Only USD/USDC/USDT pairs are supported for intra-exchange arbitrage")
        return False
    
    def get_conversion_cost_percent(self, exchange_id: str) -> float:
        """
        Get the estimated conversion cost as a percentage
        For USD/USDC/USDT: No conversion cost (they're interchangeable at 1:1)
        
        Returns conversion cost as decimal (always 0.0 for USD/USDC/USDT)
        """
        # USD/USDC/USDT are interchangeable - no conversion cost
        return 0.0
    
    # ============================================================================
    # 🔵 COINBASE-SPECIFIC: Conversion API (not used currently)
    # ============================================================================
    async def _try_coinbase_conversion_api(
        self, exchange, from_currency: str, to_currency: str, amount: float
    ) -> bool:
        """
        🔵 Try Coinbase conversion API endpoint
        Note: This may only work with Coinbase Exchange API (Pro), not Advanced Trade
        """
        try:
            # Check if CCXT has conversion method
            if hasattr(exchange, 'convert_currency'):
                result = exchange.convert_currency(from_currency, to_currency, amount)
                if hasattr(result, '__await__'):
                    result = await result
                if result:
                    logger.info(f"   ✅ Conversion API successful via CCXT")
                    return True
            
            # Try direct API call if CCXT doesn't support it
            # Note: This requires Advanced Trade API credentials
            if hasattr(exchange, 'privatePostConversions'):
                params = {
                    'from': from_currency,
                    'to': to_currency,
                    'amount': str(amount)
                }
                result = exchange.privatePostConversions(params)
                if hasattr(result, '__await__'):
                    result = await result
                if result:
                    logger.info(f"   ✅ Conversion API successful via direct call")
                    return True
        except Exception as e:
            logger.debug(f"   Conversion API not available: {e}")
        
        return False
    
    # REMOVED: Bridge currency conversion methods (BTC bridge)
    # These methods were used for EUR/GBP conversion but are no longer needed
    # since we only support USD/USDC/USDT pairs now
    # Keeping them could cause unintended BTC purchases
    
    async def fetch_order(self, exchange_id: str, order_id: str, symbol: str) -> Dict:
        """
        ⚪ COMMON: Fetch order status (works for both Coinbase and Gemini)
        
        Args:
            exchange_id: EXCHANGE_COINBASE or EXCHANGE_GEMINI
        """
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
        """
        ⚪ COMMON: Cancel order (works for both Coinbase and Gemini)
        
        Args:
            exchange_id: EXCHANGE_COINBASE or EXCHANGE_GEMINI
        """
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
        except (OrderNotFound, InvalidOrder) as e:
            logger.warning(f"⚠️ Order {order_id} already closed on {exchange_id}: {e}")
            return {'status': 'already_closed', 'order_id': order_id, 'symbol': symbol}
        except ExchangeError as e:
            message = str(e).lower()
            ignorable_keywords = ['order not found', 'already done', 'cancelorders() has failed']
            if any(keyword in message for keyword in ignorable_keywords):
                logger.warning(f"⚠️ Treating cancel error as benign for {order_id} on {exchange_id}: {e}")
                return {'status': 'already_closed', 'order_id': order_id, 'symbol': symbol}
            logger.error(f"Error cancelling order {order_id} on {exchange_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error cancelling order {order_id} on {exchange_id}: {e}")
            raise
    
    async def fetch_open_orders(self, exchange_id: str, symbol: Optional[str] = None) -> List[Dict]:
        """Fetch open orders, optionally filtered by symbol."""
        exchange = self.get_exchange(exchange_id)
        try:
            if symbol:
                result = exchange.fetch_open_orders(symbol)
            else:
                result = exchange.fetch_open_orders()
            if hasattr(result, '__await__'):
                orders = await result
            else:
                orders = result
            return orders or []
        except Exception as e:
            logger.error(f"Error fetching open orders on {exchange_id} ({symbol or 'ALL'}): {e}")
            raise
    
    async def fetch_deposit_address(self, exchange_id: str, currency: str, 
                                    network: Optional[str] = None, params: Optional[Dict] = None) -> Dict:
        """Fetch deposit address for currency
        
        Args:
            exchange_id: 'coinbase' or 'gemini'
            currency: Currency code (e.g., 'API3', 'ZEC', 'XRP')
            network: 🔵 Network parameter (e.g., 'ETH', 'ZEC', 'XRP') - required for ERC-20 tokens on Coinbase
            params: Additional parameters dict (will be merged with network)
        """
        exchange = self.get_exchange(exchange_id)
        
        # ====================================================================
        # 🔵 COINBASE-SPECIFIC: Network parameter handling
        # ====================================================================
        fetch_params: Dict[str, Any] = {}
            if params:
                fetch_params.update(params)
            
        # 🔵 Add network if provided (required for ERC-20 tokens on Coinbase)
        if exchange_id == EXCHANGE_COINBASE and network:
                fetch_params['network'] = network
                logger.info(f"   Using network: {network}")
            
        # ====================================================================
        # ⚪ COMMON: Fetch deposit address (works for both exchanges)
        # ====================================================================
        try:
            # CCXT fetch_deposit_address can be sync or async
            if fetch_params:
                result = exchange.fetch_deposit_address(currency, fetch_params)
            else:
                result = exchange.fetch_deposit_address(currency)
                
            if hasattr(result, '__await__'):
                address_info = await result
            else:
                address_info = result
            
            # 🔵 Check if address_info is None (Coinbase may return None if address needs to be generated)
            if address_info is None and exchange_id == EXCHANGE_COINBASE:
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
            
            # ⚪ Validate address_info is a dict (works for both exchanges)
            if not isinstance(address_info, dict):
                raise ValueError(f"{exchange_id} returned invalid deposit address format: {type(address_info)} (expected dict)")
            
            # ⚪ Check if address key exists (works for both exchanges)
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
    
    # ============================================================================
    # 🔵 COINBASE-SPECIFIC: Exchange API signature generation
    # ============================================================================
    def _generate_coinbase_exchange_signature(self, timestamp: str, method: str, 
                                             request_path: str, body: str = '') -> str:
        """🔵 Generate Coinbase Exchange API signature
        
        Args:
            timestamp: Unix timestamp as string
            method: HTTP method (GET, POST, etc.)
            request_path: API endpoint path (e.g., '/withdrawals/crypto')
            body: Request body as string (empty for GET requests)
        
        Returns:
            Base64-encoded HMAC-SHA256 signature
        """
        message = timestamp + method + request_path + body
        secret = base64.b64decode(Config.COINBASE_SECRET_KEY)
        signature = hmac.new(secret, message.encode('utf-8'), hashlib.sha256)
        return base64.b64encode(signature.digest()).decode('utf-8')
    
    async def _coinbase_exchange_withdraw(self, currency: str, amount: float,
                                         address: str, tag: Optional[str] = None,
                                         network: Optional[str] = None) -> Dict:
        """🔵 Withdraw crypto using Coinbase Exchange API directly
        
        Since CCXT uses api.coinbase.com for trading (which works), we should
        check if the same authentication works for Exchange API endpoints.
        If not, we may need to use CCXT's authentication method.
        
        Args:
            currency: Currency code (e.g., 'API3', 'ZEC', 'XRP')
            amount: Amount to withdraw
            address: Destination address
            tag: Tag/memo (optional, for XRP and similar)
            network: Network parameter (e.g., 'ETH', 'ZEC', 'XRP')
        
        Returns:
            Withdrawal response dict
        """
        # USER INSIGHT: Exchange API keys are the same as Main API keys with all permissions
        # If trading works, Exchange API should work too - let's test Exchange API authentication first
        # Then try Exchange API endpoint for withdrawals
        
        logger.info(f"   Testing Exchange API authentication with same keys as trading...")
        logger.info(f"   Currency: {currency}, Amount: {amount}, Address: {address[:10]}...")
        
        # First, test if Exchange API accepts our keys with a simple GET request
        exchange_base_url = 'https://api.exchange.coinbase.com'
        test_endpoint = '/accounts'
        
        timestamp = str(int(time.time()))
        method = 'GET'
        message = timestamp + method + test_endpoint
        
        secret = base64.b64decode(Config.COINBASE_SECRET_KEY)
        signature_obj = hmac.new(secret, message.encode('utf-8'), hashlib.sha256)
        signature = base64.b64encode(signature_obj.digest()).decode('utf-8')
        
        test_headers = {
            'CB-ACCESS-KEY': Config.COINBASE_API_KEY,
            'CB-ACCESS-SIGN': signature,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-PASSPHRASE': Config.COINBASE_PASSPHRASE,
            'Content-Type': 'application/json'
        }
        
        # Test Exchange API authentication
        async with aiohttp.ClientSession() as session:
            async with session.get(exchange_base_url + test_endpoint, headers=test_headers) as test_response:
                if test_response.status == 401:
                    logger.error(f"   ❌ Exchange API authentication failed: 401")
                    logger.error(f"   This means Exchange API doesn't accept Main API keys")
                    logger.error(f"   Even with 'all permissions', Exchange API may require separate keys")
                    raise Exception("Exchange API authentication failed - keys may not be compatible")
                elif test_response.status == 200:
                    logger.info(f"   ✅ Exchange API authentication successful!")
                    logger.info(f"   Keys work for Exchange API - proceeding with withdrawal")
                else:
                    logger.warning(f"   ⚠️  Exchange API test returned status {test_response.status}")
        
        # If authentication works, proceed with Exchange API withdrawal
        base_url = 'https://api.exchange.coinbase.com'
        endpoint = '/withdrawals/crypto'
        url = base_url + endpoint
        
        logger.info(f"   Using Exchange API (/withdrawals/crypto)")
        logger.info(f"   Network: {network}")
        
        # Build request body for Exchange API
        body = {
            'amount': str(amount),
            'currency': currency,
            'crypto_address': address
        }
        
        if network:
            body['network'] = network
            logger.info(f"   Network: {network}")
        
        if tag:
            if currency == 'XRP':
                body['destination_tag'] = tag
                logger.info(f"   Destination Tag: {tag}")
            else:
                body['tag'] = tag
                logger.info(f"   Tag/Memo: {tag}")
        
        body_json = json.dumps(body)
        
        # Generate Exchange API signature
        timestamp = str(int(time.time()))
        message = timestamp + 'POST' + endpoint + body_json
        
        secret = base64.b64decode(Config.COINBASE_SECRET_KEY)
        signature_obj = hmac.new(secret, message.encode('utf-8'), hashlib.sha256)
        signature = base64.b64encode(signature_obj.digest()).decode('utf-8')
        
        # Exchange API headers
        headers = {
            'CB-ACCESS-KEY': Config.COINBASE_API_KEY,
            'CB-ACCESS-SIGN': signature,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-PASSPHRASE': Config.COINBASE_PASSPHRASE,
            'Content-Type': 'application/json'
        }
        
        logger.info(f"   Timestamp: {timestamp}")
        
        # Make withdrawal request to Exchange API
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=body_json) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ Exchange API withdrawal successful!")
                    logger.info(f"   Withdrawal ID: {result.get('id', 'unknown')}")
                    return result
                else:
                    try:
                        error_data = await response.json()
                        error_msg = json.dumps(error_data, indent=2)
                    except:
                        error_msg = response_text
                    
                    correlation_id = response.headers.get('x-correlation-id') or response.headers.get('X-Correlation-ID')
                    
                    logger.error(f"❌ Exchange API withdrawal failed")
                    logger.error(f"   Status: {response.status}")
                    logger.error(f"   Response: {error_msg}")
                    if correlation_id:
                        logger.error(f"   Correlation ID: {correlation_id}")
                    
                    raise Exception(f"Coinbase Exchange API withdrawal failed: Status {response.status}, Response: {error_msg}")
    
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
        try:
            # Log withdrawal attempt
            logger.info(f"🔄 Initiating withdrawal from {exchange_id}:")
            logger.info(f"   Currency: {currency}")
            logger.info(f"   Amount: {amount}")
            logger.info(f"   Address: {address[:10]}...{address[-6:]}")
            
            # ====================================================================
            # 🔵 COINBASE-SPECIFIC: Use Exchange API directly
            # ====================================================================
            # 🔵 For Coinbase, use Exchange API directly (bypasses CCXT's Send Money API)
            if exchange_id == EXCHANGE_COINBASE:
                # Use Exchange API for withdrawals
                return await self._coinbase_exchange_withdraw(
                    currency=currency,
                    amount=amount,
                    address=address,
                    tag=tag,
                    network=network
                )
            
            # ====================================================================
            # 🟢 GEMINI-SPECIFIC: Use CCXT withdrawal
            # ====================================================================
            # 🟢 For Gemini, use CCXT (it uses the correct endpoint)
            exchange = self.get_exchange(exchange_id)
            
            # Build params dict
            withdraw_params = {}
            if params:
                withdraw_params.update(params)
            
            # ⚪ Add network if provided (works for both exchanges)
            if network:
                withdraw_params['network'] = network
                logger.info(f"   Network: {network}")
            
            # ⚪ Add tag to params (works for both exchanges)
            if tag:
                withdraw_params['tag'] = tag
                logger.info(f"   Tag/Memo: {tag}")
            
            # Execute withdrawal (CCXT withdraw can be sync or async)
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
            logger.error(f"     Exception type: {type(e).__name__}")
            logger.error(f"     Exception class: {type(e).__module__}.{type(e).__name__}")
            
            # Try dir() to see all attributes
            try:
                all_attrs = dir(e)
                logger.error(f"     All attributes ({len(all_attrs)}): {', '.join(all_attrs[:20])}...")
            except:
                pass
            
            # Check __dict__ if it exists
            if hasattr(e, '__dict__'):
                try:
                    attrs_dict = e.__dict__
                    logger.error(f"     __dict__ has {len(attrs_dict)} items")
                    for key, value in attrs_dict.items():
                        try:
                            value_str = str(value)[:200]
                            value_type = type(value).__name__
                            logger.error(f"       {key}: {value_type} = {value_str}")
                        except:
                            logger.error(f"       {key}: {type(value).__name__} = [could not stringify]")
                except Exception as dict_error:
                    logger.error(f"     Could not access __dict__: {dict_error}")
            else:
                logger.error("     No __dict__ attribute")
            
            # Try to get common CCXT attributes directly
            for attr in ['status', 'code', 'message', 'response', 'headers', 'statusCode', 'httpStatus', 'request', 'responseText', 'responseBody']:
                if hasattr(e, attr):
                    try:
                        value = getattr(e, attr)
                        value_str = str(value)[:200] if value else "None"
                        logger.error(f"     ✅ {attr}: {type(value).__name__} = {value_str}")
                        
                        # If it's a response object, try to get headers from it
                        if attr == 'response' and value:
                            try:
                                if hasattr(value, 'headers'):
                                    headers = value.headers
                                    logger.error(f"       Response headers: {headers}")
                                    if isinstance(headers, dict):
                                        for h_name in ['x-correlation-id', 'X-Correlation-ID', 'correlation-id', 'x-request-id']:
                                            if h_name in headers:
                                                error_details['correlation_id'] = headers[h_name]
                                                logger.error(f"       ✅✅ Correlation ID found: {headers[h_name]}")
                            except:
                                pass
                    except Exception as attr_error:
                        logger.error(f"     ⚠️ Could not access {attr}: {attr_error}")
            
            # Try to access CCXT's internal structures
            # CCXT might store response in exception.args or other locations
            try:
                import inspect
                # Get all attributes including private ones
                all_members = inspect.getmembers(e)
                for name, value in all_members:
                    if not name.startswith('__') and ('response' in name.lower() or 'header' in name.lower() or 'http' in name.lower()):
                        try:
                            logger.error(f"     🔍 {name}: {type(value).__name__} = {str(value)[:150]}")
                            if isinstance(value, dict) and 'correlation' in str(value).lower():
                                logger.error(f"       ⚠️ Potential correlation ID in {name}")
                        except:
                            pass
            except Exception as inspect_error:
                logger.warning(f"     Could not inspect exception members: {inspect_error}")
            
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
            # 🔵 Close Coinbase connection
            if self.coinbase and hasattr(self.coinbase, 'close'):
                await self.coinbase.close()
        except Exception as e:
            logger.warning(f"Error closing Coinbase: {e}")
        
        try:
            # 🟢 Close Gemini connection
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


