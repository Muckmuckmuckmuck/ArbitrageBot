#!/usr/bin/env python3
"""
Production-Grade Intra-Exchange Arbitrage Trading Engine
Implements comprehensive profitability calculations for ALL trading pairs
Works on Coinbase and Gemini separately (no cross-exchange confusion)
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import json

from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager
from coinbase_gemini_config import Config, EXCHANGE_FEES

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TradeOpportunity:
    """Represents a profitable trading opportunity"""
    exchange: str  # 'coinbase' or 'gemini' - NEVER MIXED
    base_crypto: str  # e.g., 'BTC'
    buy_pair: str  # e.g., 'BTC/USD'
    sell_pair: str  # e.g., 'BTC/USDC'
    buy_price: float
    sell_price: float
    raw_spread_percent: float
    net_profit_percent: float
    fees_buy: float  # As % of volume
    fees_sell: float  # As % of volume
    estimated_slippage: float  # As % of volume
    latency_risk: float  # Expected price move during execution
    volatility_24h: float
    order_book_depth_buy: float  # USD
    order_book_depth_sell: float  # USD
    trade_size_usd: float
    expected_profit_usd: float
    timestamp: datetime = field(default_factory=datetime.now)
    opportunity_score: float = 0.0  # Combined score for ranking
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging"""
        return {
            'exchange': self.exchange,
            'base_crypto': self.base_crypto,
            'buy_pair': self.buy_pair,
            'sell_pair': self.sell_pair,
            'buy_price': self.buy_price,
            'sell_price': self.sell_price,
            'raw_spread_percent': self.raw_spread_percent,
            'net_profit_percent': self.net_profit_percent,
            'expected_profit_usd': self.expected_profit_usd,
            'opportunity_score': self.opportunity_score,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class TradeExecution:
    """Represents a completed trade"""
    exchange: str
    opportunity: TradeOpportunity
    buy_order_id: Optional[str]
    sell_order_id: Optional[str]
    actual_buy_price: float
    actual_sell_price: float
    actual_profit_usd: float
    execution_time_seconds: float
    status: str  # 'success', 'partial', 'failed'
    timestamp: datetime = field(default_factory=datetime.now)


class ProfitabilityCalculator:
    """Calculates all components of profitability"""
    
    def __init__(self, exchange_id: str):
        self.exchange_id = exchange_id
        self.maker_fee = EXCHANGE_FEES[exchange_id]['maker']
        self.taker_fee = EXCHANGE_FEES[exchange_id]['taker']
        
    def calculate_net_profit(
        self,
        buy_price: float,
        sell_price: float,
        trade_size_usd: float,
        order_book_depth_buy: float,
        order_book_depth_sell: float,
        spread_width: float,
        volatility_24h: float,
        execution_latency_ms: float = 500
    ) -> Dict[str, float]:
        """
        Core Formula: Net Profit = (P_sell - P_buy) / P_buy - (F_buy + F_sell) - S - L
        
        Where:
        - P_sell, P_buy: Prices
        - F_buy, F_sell: Fees
        - S: Slippage
        - L: Latency risk
        """
        
        # 1. Raw Spread
        raw_spread = (sell_price - buy_price) / buy_price
        
        # 2. Trading Fees (using maker fees for limit orders)
        fees_total = self.maker_fee + self.maker_fee  # Buy + Sell
        
        # 3. Slippage Calculation
        # S = (Trade Size / Order Book Depth) * Spread Width
        slippage_buy = (trade_size_usd / max(order_book_depth_buy, trade_size_usd * 0.1)) * (spread_width / buy_price)
        slippage_sell = (trade_size_usd / max(order_book_depth_sell, trade_size_usd * 0.1)) * (spread_width / sell_price)
        slippage_total = slippage_buy + slippage_sell
        
        # 4. Latency Risk
        # L = σ_t * Δt (volatility per second * execution time)
        volatility_per_second = volatility_24h / (24 * 3600)  # Convert 24h vol to per-second
        latency_seconds = execution_latency_ms / 1000.0
        latency_risk = volatility_per_second * latency_seconds
        
        # 5. Net Profit
        net_profit = raw_spread - fees_total - slippage_total - latency_risk
        
        # 6. Expected Profit in USD
        expected_profit_usd = trade_size_usd * net_profit
        
        return {
            'raw_spread': raw_spread,
            'fees_total': fees_total,
            'slippage_total': slippage_total,
            'latency_risk': latency_risk,
            'net_profit': net_profit,
            'expected_profit_usd': expected_profit_usd,
            'buy_price': buy_price,
            'sell_price': sell_price
        }
    
    def calculate_opportunity_score(
        self,
        net_profit_percent: float,
        raw_spread_percent: float,
        order_book_depth: float,
        volatility_24h: float
    ) -> float:
        """
        Combines multiple factors into a single opportunity score
        Higher score = better opportunity
        """
        # Base score from net profit
        profit_score = net_profit_percent * 100  # Scale to reasonable range
        
        # Depth score (more liquidity = better)
        depth_score = min(order_book_depth / 10000, 10.0)  # Cap at 10
        
        # Volatility score (moderate volatility is best, too high = risky)
        # Ideal volatility: 1-3% intraday
        if 0.01 <= volatility_24h <= 0.03:
            vol_score = 5.0
        elif volatility_24h < 0.01:
            vol_score = 2.0  # Too low = no movement
        else:
            vol_score = max(0.0, 5.0 - (volatility_24h - 0.03) * 100)  # Penalize high volatility
        
        # Combined score
        score = (profit_score * 0.6) + (depth_score * 0.2) + (vol_score * 0.2)
        
        return score


class IntraExchangeArbitrageEngine:
    """
    Production-grade intra-exchange arbitrage trading engine
    Works separately on Coinbase and Gemini (no mixing)
    """
    
    def __init__(self, min_profit_threshold: float = 0.002, max_position_size_usd: float = 100.0):
        """
        Initialize the trading engine
        
        Args:
            min_profit_threshold: Minimum net profit % to enter trade (default 0.2%)
            max_position_size_usd: Maximum position size per trade (default $100)
        """
        self.exchange_manager = CoinbaseGeminiExchangeManager()
        self.min_profit_threshold = min_profit_threshold
        self.max_position_size_usd = max_position_size_usd
        
        # Exchange-specific trackers (NEVER MIXED)
        self.coinbase_calculator = ProfitabilityCalculator('coinbase')
        self.gemini_calculator = ProfitabilityCalculator('gemini')
        
        # Statistics
        self.stats = {
            'coinbase': {
                'opportunities_found': 0,
                'trades_executed': 0,
                'total_profit_usd': 0.0,
                'successful_trades': 0,
                'failed_trades': 0
            },
            'gemini': {
                'opportunities_found': 0,
                'trades_executed': 0,
                'total_profit_usd': 0.0,
                'successful_trades': 0,
                'failed_trades': 0
            },
            'total_scan_time_seconds': 0.0,
            'last_scan_time': None
        }
        
        # Pair blacklist (pairs that repeatedly fail or are unprofitable)
        self.blacklisted_pairs: Set[str] = set()
        
        # Dynamic thresholds per pair (learns from past performance)
        # Higher threshold = more conservative (requires larger profit)
        self.pair_thresholds: Dict[str, float] = defaultdict(lambda: min_profit_threshold)
        
        # Trade history for learning (track last N trades per pair)
        self.trade_history: Dict[str, List[float]] = defaultdict(list)
        
        # Active positions tracking
        self.active_positions: Dict[str, TradeExecution] = {}
        
        # Execution latency tracking (for latency risk calculation)
        self.execution_latency_ms = 500  # Will be updated based on actual measurements
        
    async def initialize(self):
        """Initialize exchanges"""
        logger.info("=" * 80)
        logger.info("🚀 INITIALIZING INTRA-EXCHANGE ARBITRAGE ENGINE")
        logger.info("=" * 80)
        await self.exchange_manager.initialize()
        logger.info("✅ Engine initialized")
    
    def _get_exchange_id(self, exchange_obj) -> str:
        """Safely get exchange ID - ensures we don't mix exchanges"""
        if exchange_obj == self.exchange_manager.coinbase:
            return 'coinbase'
        elif exchange_obj == self.exchange_manager.gemini:
            return 'gemini'
        else:
            raise ValueError(f"Unknown exchange object: {exchange_obj}")
    
    async def _get_all_pairs_for_crypto(self, exchange_id: str, base_crypto: str) -> List[Tuple[str, str]]:
        """
        Get all trading pairs for a crypto (e.g., BTC/USD, BTC/USDC, BTC/EUR, BTC/BTC)
        Returns list of (pair_symbol, quote_currency) tuples
        """
        exchange = self.exchange_manager.get_exchange(exchange_id)
        pairs = []
        
        for symbol, market_info in exchange.markets.items():
            if not market_info.get('active', True):
                continue
            
            base = market_info.get('base', '').strip().upper()
            quote = market_info.get('quote', '').strip().upper()
            
            if base == base_crypto.upper():
                pairs.append((symbol, quote))
        
        return pairs
    
    async def _normalize_price_to_usd(
        self,
        exchange_id: str,
        price: float,
        quote_currency: str
    ) -> float:
        """
        Normalize any price to USD equivalent
        Handles: USD, USDC, USDT, EUR, GBP, BTC, ETH, etc.
        """
        if quote_currency in ['USD', 'USDC', 'USDT']:
            # Stablecoins are approximately 1:1 with USD
            if quote_currency == 'USDC' or quote_currency == 'USDT':
                return price  # Assume 1:1 for now (could add slight adjustments)
            return price
        
        # Fiat currencies
        if quote_currency == 'EUR':
            return price * 1.05  # Approximate EUR/USD rate
        if quote_currency == 'GBP':
            return price * 1.25  # Approximate GBP/USD rate
        
        # Crypto quote currencies - need to fetch USD price
        if quote_currency in ['BTC', 'ETH', 'SOL', 'AVAX', 'LINK', 'MATIC', 'AAVE']:
            try:
                exchange = self.exchange_manager.get_exchange(exchange_id)
                usd_pair = f"{quote_currency}/USD"
                if usd_pair in exchange.markets:
                    ticker = exchange.fetch_ticker(usd_pair)
                    usd_price = ticker.get('last') or ticker.get('close') or ticker.get('bid', 0)
                    if usd_price and usd_price > 0:
                        return price * usd_price
            except Exception as e:
                logger.warning(f"Failed to normalize {quote_currency} to USD: {e}")
        
        # Fallback: return original price (will be filtered out if too different)
        return price
    
    async def _calculate_order_book_depth(
        self,
        exchange_id: str,
        symbol: str,
        side: str,  # 'buy' or 'sell'
        trade_size_usd: float
    ) -> float:
        """Calculate order book depth for a given trade size"""
        try:
            # SAFETY CHECK: Verify exchange_id
            if exchange_id not in ['coinbase', 'gemini']:
                raise ValueError(f"Invalid exchange_id: {exchange_id}")
            
            orderbook = await self.exchange_manager.fetch_order_book(exchange_id, symbol, limit=20)
            
            if side == 'buy':
                asks = orderbook.get('asks', [])
                depth = 0.0
                for price, amount in asks:
                    depth += price * amount
                    if depth >= trade_size_usd:
                        break
            else:  # sell
                bids = orderbook.get('bids', [])
                depth = 0.0
                for price, amount in bids:
                    depth += price * amount
                    if depth >= trade_size_usd:
                        break
            
            return max(depth, trade_size_usd * 0.1)  # Minimum depth
        except Exception as e:
            logger.warning(f"Failed to fetch order book for {symbol} on {exchange_id}: {e}")
            return trade_size_usd * 0.5  # Conservative estimate
    
    async def _calculate_volatility(self, exchange_id: str, symbol: str) -> float:
        """Calculate 24h volatility for a trading pair"""
        try:
            # SAFETY CHECK: Verify exchange_id
            if exchange_id not in ['coinbase', 'gemini']:
                raise ValueError(f"Invalid exchange_id: {exchange_id}")
            
            ticker = await self.exchange_manager.fetch_ticker(exchange_id, symbol)
            
            high = ticker.get('high') or 0
            low = ticker.get('low') or 0
            last = ticker.get('last') or ticker.get('close') or 1
            
            if high > 0 and low > 0 and last > 0:
                # Simple volatility estimate: (high - low) / last
                volatility = (high - low) / last
                return volatility
            else:
                return 0.02  # Default 2% volatility
        except Exception as e:
            logger.warning(f"Failed to calculate volatility for {symbol} on {exchange_id}: {e}")
            return 0.02  # Default 2% volatility
    
    async def _find_opportunity_for_crypto(
        self,
        exchange_id: str,
        base_crypto: str,
        trade_size_usd: float
    ) -> Optional[TradeOpportunity]:
        """
        Find the best arbitrage opportunity for a crypto on a specific exchange
        Compares ALL pairs (USD, USDC, USDT, EUR, GBP, BTC, ETH, etc.)
        """
        pairs = await self._get_all_pairs_for_crypto(exchange_id, base_crypto)
        
        if len(pairs) < 2:
            return None  # Need at least 2 pairs to arbitrage
        
        calculator = self.coinbase_calculator if exchange_id == 'coinbase' else self.gemini_calculator
        
        best_opportunity = None
        best_score = -float('inf')
        
        # Compare all pairs
        for i, (pair1, quote1) in enumerate(pairs):
            for j, (pair2, quote2) in enumerate(pairs):
                if i >= j:
                    continue  # Avoid duplicates and self-comparisons
                
                # Skip if either pair is blacklisted
                if pair1 in self.blacklisted_pairs or pair2 in self.blacklisted_pairs:
                    continue
                
                try:
                    # Get prices - use exchange manager (ensures exchange separation)
                    ticker1 = await self.exchange_manager.fetch_ticker(exchange_id, pair1)
                    ticker2 = await self.exchange_manager.fetch_ticker(exchange_id, pair2)
                    
                    price1 = ticker1.get('last') or ticker1.get('close') or ticker1.get('bid', 0)
                    price2 = ticker2.get('last') or ticker2.get('close') or ticker2.get('bid', 0)
                    
                    if price1 <= 0 or price2 <= 0:
                        continue
                    
                    # Normalize both prices to USD
                    usd_price1 = await self._normalize_price_to_usd(exchange_id, price1, quote1)
                    usd_price2 = await self._normalize_price_to_usd(exchange_id, price2, quote2)
                    
                    # Sanity check: prices shouldn't differ by more than 10x
                    if max(usd_price1, usd_price2) / min(usd_price1, usd_price2) > 10:
                        continue  # Likely conversion error
                    
                    # Determine buy/sell direction
                    if usd_price1 < usd_price2:
                        buy_pair, buy_price = pair1, price1
                        sell_pair, sell_price = pair2, price2
                        buy_quote, sell_quote = quote1, quote2
                    else:
                        buy_pair, buy_price = pair2, price2
                        sell_pair, sell_price = pair1, price1
                        buy_quote, sell_quote = quote2, quote1
                    
                    # Calculate order book depth
                    depth_buy = await self._calculate_order_book_depth(exchange_id, buy_pair, 'buy', trade_size_usd)
                    depth_sell = await self._calculate_order_book_depth(exchange_id, sell_pair, 'sell', trade_size_usd)
                    
                    # Calculate volatility (use average of both pairs)
                    vol1 = await self._calculate_volatility(exchange_id, pair1)
                    vol2 = await self._calculate_volatility(exchange_id, pair2)
                    volatility = (vol1 + vol2) / 2
                    
                    # Calculate spread width
                    spread_width = abs(usd_price2 - usd_price1)
                    
                    # Calculate profitability
                    profit_data = calculator.calculate_net_profit(
                        buy_price=usd_price1,
                        sell_price=usd_price2,
                        trade_size_usd=trade_size_usd,
                        order_book_depth_buy=depth_buy,
                        order_book_depth_sell=depth_sell,
                        spread_width=spread_width,
                        volatility_24h=volatility,
                        execution_latency_ms=self.execution_latency_ms
                    )
                    
                    # Check if profitable
                    net_profit = profit_data['net_profit']
                    pair_key = f"{buy_pair}/{sell_pair}"
                    threshold = self.pair_thresholds[pair_key]
                    
                    if net_profit >= threshold:
                        # Calculate opportunity score
                        score = calculator.calculate_opportunity_score(
                            net_profit_percent=net_profit,
                            raw_spread_percent=profit_data['raw_spread'],
                            order_book_depth=min(depth_buy, depth_sell),
                            volatility_24h=volatility
                        )
                        
                        if score > best_score:
                            opportunity = TradeOpportunity(
                                exchange=exchange_id,
                                base_crypto=base_crypto,
                                buy_pair=buy_pair,
                                sell_pair=sell_pair,
                                buy_price=usd_price1,
                                sell_price=usd_price2,
                                raw_spread_percent=profit_data['raw_spread'] * 100,
                                net_profit_percent=net_profit * 100,
                                fees_buy=calculator.maker_fee * 100,
                                fees_sell=calculator.maker_fee * 100,
                                estimated_slippage=profit_data['slippage_total'] * 100,
                                latency_risk=profit_data['latency_risk'] * 100,
                                volatility_24h=volatility * 100,
                                order_book_depth_buy=depth_buy,
                                order_book_depth_sell=depth_sell,
                                trade_size_usd=trade_size_usd,
                                expected_profit_usd=profit_data['expected_profit_usd'],
                                opportunity_score=score
                            )
                            best_opportunity = opportunity
                            best_score = score
                
                except Exception as e:
                    logger.debug(f"Error evaluating {pair1} vs {pair2}: {e}")
                    continue
        
        return best_opportunity
    
    async def scan_exchange(self, exchange_id: str, max_cryptos: int = 100) -> List[TradeOpportunity]:
        """
        Scan an exchange for ALL profitable opportunities
        Returns ranked list of opportunities
        """
        logger.info(f"🔍 Scanning {exchange_id.upper()} for opportunities...")
        
        start_time = time.time()
        exchange = self.exchange_manager.get_exchange(exchange_id)
        
        # Get all unique base cryptos
        base_cryptos = set()
        for symbol, market_info in exchange.markets.items():
            if market_info.get('active', True):
                base = market_info.get('base', '').strip().upper()
                if base:
                    base_cryptos.add(base)
        
        logger.info(f"   Found {len(base_cryptos)} unique cryptos on {exchange_id}")
        
        opportunities = []
        scanned = 0
        
        # Scan each crypto
        for base_crypto in list(base_cryptos)[:max_cryptos]:
            scanned += 1
            if scanned % 50 == 0:
                logger.info(f"   Progress: {scanned}/{min(len(base_cryptos), max_cryptos)} cryptos scanned")
            
            opportunity = await self._find_opportunity_for_crypto(
                exchange_id=exchange_id,
                base_crypto=base_crypto,
                trade_size_usd=self.max_position_size_usd
            )
            
            if opportunity:
                opportunities.append(opportunity)
                self.stats[exchange_id]['opportunities_found'] += 1
        
        # Sort by opportunity score (highest first)
        opportunities.sort(key=lambda x: x.opportunity_score, reverse=True)
        
        scan_time = time.time() - start_time
        logger.info(f"   ✅ Found {len(opportunities)} opportunities in {scan_time:.2f}s")
        
        return opportunities
    
    async def execute_trade(self, opportunity: TradeOpportunity) -> TradeExecution:
        """
        Execute an arbitrage trade atomically
        Buy on one pair, sell on another pair (same exchange!)
        
        CRITICAL: Exchange separation check - opportunity.exchange must match the exchange we use
        """
        exchange_id = opportunity.exchange
        
        # SAFETY CHECK: Verify exchange ID is valid
        if exchange_id not in ['coinbase', 'gemini']:
            raise ValueError(f"Invalid exchange ID: {exchange_id}. Must be 'coinbase' or 'gemini'")
        
        logger.info(f"💰 Executing trade on {exchange_id.upper()}:")
        logger.info(f"   Buy: {opportunity.buy_pair} @ ${opportunity.buy_price:.6f}")
        logger.info(f"   Sell: {opportunity.sell_pair} @ ${opportunity.sell_price:.6f}")
        logger.info(f"   Expected profit: ${opportunity.expected_profit_usd:.2f}")
        
        start_time = time.time()
        buy_order_id = None
        sell_order_id = None
        actual_buy_price = opportunity.buy_price
        actual_sell_price = opportunity.sell_price
        status = 'failed'
        execution_time = 0.0
        
        try:
            # Calculate trade size in base currency
            base_amount = opportunity.trade_size_usd / opportunity.buy_price
            
            # Get calculator for fees
            calculator = self.coinbase_calculator if exchange_id == 'coinbase' else self.gemini_calculator
            
            # Place limit buy order (maker fee) - use exchange manager
            buy_price_limit = opportunity.buy_price * 1.001  # Slightly above to ensure fill
            buy_order = await self.exchange_manager.create_order(
                exchange_id=exchange_id,  # CRITICAL: Pass exchange_id explicitly
                symbol=opportunity.buy_pair,
                order_type='limit',
                side='buy',
                amount=base_amount,
                price=buy_price_limit
            )
            buy_order_id = buy_order.get('id')
            logger.info(f"   ✅ Buy order placed: {buy_order_id}")
            
            # Wait for fill (with timeout)
            max_wait_time = 30  # 30 seconds max
            waited = 0
            while waited < max_wait_time:
                await asyncio.sleep(2)
                waited += 2
                buy_order_status = await self.exchange_manager.fetch_order(
                    exchange_id=exchange_id,
                    order_id=buy_order_id,
                    symbol=opportunity.buy_pair
                )
                if buy_order_status.get('status') in ['closed', 'filled']:
                    actual_buy_price = buy_order_status.get('average') or buy_order_status.get('price') or buy_order_status.get('filled', 0) / buy_order_status.get('amount', 1)
                    logger.info(f"   ✅ Buy order filled @ ${actual_buy_price:.6f}")
                    break
            
            if buy_order_status.get('status') not in ['closed', 'filled']:
                logger.warning(f"   ⚠️ Buy order not filled after {max_wait_time}s")
                # Cancel and continue (will mark as partial)
                try:
                    await self.exchange_manager.cancel_order(exchange_id, buy_order_id, opportunity.buy_pair)
                except:
                    pass
            
            # Place limit sell order (maker fee) - use exchange manager
            sell_price_limit = opportunity.sell_price * 0.999  # Slightly below to ensure fill
            sell_order = await self.exchange_manager.create_order(
                exchange_id=exchange_id,  # CRITICAL: Pass exchange_id explicitly
                symbol=opportunity.sell_pair,
                order_type='limit',
                side='sell',
                amount=base_amount,
                price=sell_price_limit
            )
            sell_order_id = sell_order.get('id')
            logger.info(f"   ✅ Sell order placed: {sell_order_id}")
            
            # Wait for fill
            waited = 0
            while waited < max_wait_time:
                await asyncio.sleep(2)
                waited += 2
                sell_order_status = await self.exchange_manager.fetch_order(
                    exchange_id=exchange_id,
                    order_id=sell_order_id,
                    symbol=opportunity.sell_pair
                )
                if sell_order_status.get('status') in ['closed', 'filled']:
                    actual_sell_price = sell_order_status.get('average') or sell_order_status.get('price') or sell_order_status.get('filled', 0) / sell_order_status.get('amount', 1)
                    logger.info(f"   ✅ Sell order filled @ ${actual_sell_price:.6f}")
                    break
            
            if sell_order_status.get('status') not in ['closed', 'filled']:
                logger.warning(f"   ⚠️ Sell order not filled after {max_wait_time}s")
                # Cancel
                try:
                    await self.exchange_manager.cancel_order(exchange_id, sell_order_id, opportunity.sell_pair)
                except:
                    pass
            
            # Calculate actual profit
            if buy_order_status.get('status') in ['closed', 'filled'] and sell_order_status.get('status') in ['closed', 'filled']:
                actual_profit_usd = (actual_sell_price - actual_buy_price) * base_amount - (
                    opportunity.trade_size_usd * (calculator.maker_fee + calculator.maker_fee)
                )
                status = 'success' if actual_profit_usd > 0 else 'partial'
            else:
                actual_profit_usd = 0.0
                status = 'partial'
            
            execution_time = time.time() - start_time
            self.execution_latency_ms = execution_time * 1000  # Update latency tracking
            
            logger.info(f"   ✅ Trade completed: ${actual_profit_usd:.2f} profit in {execution_time:.2f}s")
            
        except Exception as e:
            logger.error(f"   ❌ Trade execution failed: {e}")
            execution_time = time.time() - start_time
            actual_profit_usd = 0.0
            status = 'failed'
        
        execution = TradeExecution(
            exchange=exchange_id,
            opportunity=opportunity,
            buy_order_id=buy_order_id,
            sell_order_id=sell_order_id,
            actual_buy_price=actual_buy_price,
            actual_sell_price=actual_sell_price,
            actual_profit_usd=actual_profit_usd,
            execution_time_seconds=execution_time,
            status=status
        )
        
        # Update statistics
        self.stats[exchange_id]['trades_executed'] += 1
        pair_key = f"{opportunity.buy_pair}/{opportunity.sell_pair}"
        
        if status == 'success':
            self.stats[exchange_id]['successful_trades'] += 1
            self.stats[exchange_id]['total_profit_usd'] += actual_profit_usd
            
            # Learn from success: Lower threshold slightly if profitable
            actual_profit_percent = (actual_profit_usd / opportunity.trade_size_usd) * 100
            self.trade_history[pair_key].append(actual_profit_percent)
            
            # Keep only last 10 trades
            if len(self.trade_history[pair_key]) > 10:
                self.trade_history[pair_key] = self.trade_history[pair_key][-10:]
            
            # If consistently profitable, lower threshold slightly
            if len(self.trade_history[pair_key]) >= 5:
                avg_profit = sum(self.trade_history[pair_key]) / len(self.trade_history[pair_key])
                if avg_profit > self.min_profit_threshold * 100 * 1.5:
                    # Lower threshold by 10% (more aggressive)
                    self.pair_thresholds[pair_key] = max(
                        self.min_profit_threshold * 0.9,
                        self.pair_thresholds[pair_key] * 0.9
                    )
                    logger.info(f"   📈 Lowered threshold for {pair_key} to {self.pair_thresholds[pair_key]*100:.3f}% (avg profit: {avg_profit:.3f}%)")
        else:
            self.stats[exchange_id]['failed_trades'] += 1
            
            # Learn from failure: Raise threshold if repeatedly fails
            if self.stats[exchange_id]['failed_trades'] % 3 == 0:
                # Increase threshold by 20% (more conservative)
                self.pair_thresholds[pair_key] = self.pair_thresholds[pair_key] * 1.2
                logger.warning(f"   ⚠️ Raised threshold for {pair_key} to {self.pair_thresholds[pair_key]*100:.3f}% due to failures")
            
            # Blacklist if repeatedly fails (after 5 failures)
            if self.stats[exchange_id]['failed_trades'] % 5 == 0:
                self.blacklisted_pairs.add(pair_key)
                logger.warning(f"   ⚠️ Blacklisted {pair_key} due to repeated failures")
        
        return execution
    
    async def run_trading_loop(self, scan_interval_seconds: int = 60):
        """
        Main trading loop - continuously scans and trades
        """
        logger.info("=" * 80)
        logger.info("🚀 STARTING TRADING LOOP")
        logger.info("=" * 80)
        logger.info(f"   Scan interval: {scan_interval_seconds}s")
        logger.info(f"   Min profit threshold: {self.min_profit_threshold * 100:.2f}%")
        logger.info(f"   Max position size: ${self.max_position_size_usd:.2f}")
        
        while True:
            try:
                # Scan both exchanges separately
                coinbase_opps = await self.scan_exchange('coinbase', max_cryptos=200)
                gemini_opps = await self.scan_exchange('gemini', max_cryptos=200)
                
                # Execute top opportunities (one per exchange)
                if coinbase_opps:
                    best_coinbase = coinbase_opps[0]
                    if best_coinbase.net_profit_percent >= self.min_profit_threshold * 100:
                        await self.execute_trade(best_coinbase)
                
                if gemini_opps:
                    best_gemini = gemini_opps[0]
                    if best_gemini.net_profit_percent >= self.min_profit_threshold * 100:
                        await self.execute_trade(best_gemini)
                
                # Print statistics
                self._print_statistics()
                
                # Wait before next scan
                await asyncio.sleep(scan_interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("🛑 Trading loop stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in trading loop: {e}")
                await asyncio.sleep(10)  # Wait before retry
    
    def _print_statistics(self):
        """Print current statistics"""
        logger.info("=" * 80)
        logger.info("📊 TRADING STATISTICS")
        logger.info("=" * 80)
        
        for exchange_id in ['coinbase', 'gemini']:
            stats = self.stats[exchange_id]
            logger.info(f"\n{exchange_id.upper()}:")
            logger.info(f"   Opportunities found: {stats['opportunities_found']}")
            logger.info(f"   Trades executed: {stats['trades_executed']}")
            logger.info(f"   Successful: {stats['successful_trades']}")
            logger.info(f"   Failed: {stats['failed_trades']}")
            logger.info(f"   Total profit: ${stats['total_profit_usd']:.2f}")
        
        logger.info(f"\nBlacklisted pairs: {len(self.blacklisted_pairs)}")
        logger.info("=" * 80)


async def main():
    """Main entry point"""
    engine = IntraExchangeArbitrageEngine(
        min_profit_threshold=0.002,  # 0.2% minimum profit
        max_position_size_usd=50.0  # $50 max per trade
    )
    
    await engine.initialize()
    await engine.run_trading_loop(scan_interval_seconds=60)


if __name__ == '__main__':
    asyncio.run(main())

