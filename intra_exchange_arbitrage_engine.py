#!/usr/bin/env python3
"""
Production-Grade Intra-Exchange Arbitrage Trading Engine
Implements comprehensive profitability calculations for USD/USDC/USDT pairs only
Works on Coinbase and Gemini separately (no cross-exchange confusion)
Only supports USD/USDC/USDT quote currencies (no EUR/GBP for simplicity and reliability)

EXCHANGE USAGE:
    🔵 COINBASE - Primary exchange for intra-exchange arbitrage
    🟢 GEMINI - Can also run arbitrage, but currently only Coinbase is used in main_dual_strategy.py
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
        
        # 🔵 IMPROVEMENT: Failed pairs cache (skip recently failed pairs for 5 minutes)
        self.failed_pairs_cache: Dict[str, float] = {}  # pair_key -> timestamp
        
        # Dynamic thresholds per pair (learns from past performance)
        # Higher threshold = more conservative (requires larger profit)
        self.pair_thresholds: Dict[str, float] = defaultdict(lambda: min_profit_threshold)
        
        # Trade history for learning (track last N trades per pair)
        self.trade_history: Dict[str, List[float]] = defaultdict(list)
        
        # Active positions tracking
        self.active_positions: Dict[str, TradeExecution] = {}
        
        # Execution latency tracking (for latency risk calculation)
        self.execution_latency_ms = 500  # Will be updated based on actual measurements
        
        # Robustness settings - OPTIMIZED FOR SPEED
        self.max_order_wait_seconds = 10  # Reduced from 30s - opportunities disappear fast!
        self.price_chase_start_seconds = 2  # Start chasing after 2s (was 10s)
        self.price_chase_increment = 0.001  # 0.1% price adjustment if not filling
        self.max_price_chase_percent = 0.005  # Max 0.5% price chase
        self.opportunity_timeout_seconds = 5  # Reduced from 10s - faster validation
        self.max_slippage_percent = 0.01  # 1% max slippage before canceling
        self.circuit_breaker_loss_threshold = -50.0  # Stop if lose $50 in session
        self.circuit_breaker_enabled = True
        self.session_loss = 0.0  # Track cumulative loss
        
        # Aggressive execution settings
        self.max_concurrent_trades_per_exchange = 3  # Execute 3 trades simultaneously
        self.market_order_fallback_enabled = True  # Use market orders if limit doesn't fill
        self.market_order_threshold = 0.005  # Use market order if spread > 0.5%
        self.dynamic_position_sizing = True  # Scale position with opportunity quality
        self.min_position_size_usd = 5.0  # Minimum position size (lowered from $25 to allow smaller trades)
        self.max_position_size_usd = max_position_size_usd  # Maximum position size
        
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
        Get all trading pairs for a crypto (e.g., BTC/USD, BTC/USDC, BTC/USDT)
        Returns list of (pair_symbol, quote_currency) tuples
        Excludes futures, swaps, and other derivative markets
        Only USD/USDC/USDT pairs for simple intra-exchange arbitrage
        """
        exchange = self.exchange_manager.get_exchange(exchange_id)
        pairs = []
        
        # Only allow USD/USDC/USDT pairs - no EUR/GBP to avoid conversion issues
        allowed_quotes = ['USD', 'USDC', 'USDT']
        
        for symbol, market_info in exchange.markets.items():
            if not market_info.get('active', True):
                continue
            
            # Skip futures/derivatives markets
            # Futures markets are marked with 'future' or 'swap' field, or have ':' in symbol
            if market_info.get('future', False) or market_info.get('swap', False):
                continue
            
            # Skip markets with ':' in symbol (futures contracts like DOGE/USD:USD-251226)
            if ':' in symbol:
                continue
            
            base = market_info.get('base', '').strip().upper()
            quote = market_info.get('quote', '').strip().upper()
            
            # Only include pairs with allowed quote currencies (USD/USDC/USDT)
            if base == base_crypto.upper() and quote in allowed_quotes:
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
        Handles: USD, USDC, USDT (no EUR/GBP - removed for simplicity)
        CRITICAL: This must be accurate for crypto-to-crypto pairs
        """
        if quote_currency == 'USD':
            return price
        
        # USDC/USDT - fetch real rates (they're close but not exactly 1:1)
        if quote_currency in ['USDC', 'USDT']:
            try:
                # Try to get real rate from exchange
                exchange = self.exchange_manager.get_exchange(exchange_id)
                stable_pair = f"{quote_currency}/USD"
                if stable_pair in exchange.markets and ':' not in stable_pair:
                    ticker = await self.exchange_manager.fetch_ticker(exchange_id, stable_pair)
                    rate = ticker.get('last') or ticker.get('close') or ticker.get('bid', 1.0)
                    if rate and 0.99 < rate < 1.01:  # Sanity check
                        return price * rate
            except Exception as e:
                logger.debug(f"Could not fetch {quote_currency}/USD rate: {e}")
            # Fallback: assume 1:1 (very close)
            return price
        
        # Crypto quote currencies - MUST fetch USD price for accuracy
        # This is critical for crypto-to-crypto pairs (e.g., BTC/ETH)
        try:
            exchange = self.exchange_manager.get_exchange(exchange_id)
            usd_pair = f"{quote_currency}/USD"
            
            # Try USD pair first (skip futures markets)
            if usd_pair in exchange.markets and ':' not in usd_pair:
                ticker = await self.exchange_manager.fetch_ticker(exchange_id, usd_pair)
                usd_price = ticker.get('last') or ticker.get('close') or ticker.get('bid', 0)
                if usd_price and usd_price > 0:
                    return price * usd_price
            
            # Fallback: Try USDC pair (skip futures markets)
            usdc_pair = f"{quote_currency}/USDC"
            if usdc_pair in exchange.markets and ':' not in usdc_pair:
                ticker = await self.exchange_manager.fetch_ticker(exchange_id, usdc_pair)
                usdc_price = ticker.get('last') or ticker.get('close') or ticker.get('bid', 0)
                if usdc_price and usdc_price > 0:
                    # USDC ≈ USD, so use directly
                    return price * usdc_price
                    
        except Exception as e:
            logger.warning(f"Failed to normalize {quote_currency} to USD: {e}")
        
        # Last resort: return original (will be filtered by sanity check)
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
            
            # Skip futures markets (they have ':' in symbol)
            if ':' in symbol:
                return 0.02  # Default 2% volatility
            
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
        Compares USD, USDC, USDT pairs only (EUR/GBP removed for simplicity and reliability)
        """
        exchange_marker = "🔵" if exchange_id == 'coinbase' else "🟢"
        
        pairs = await self._get_all_pairs_for_crypto(exchange_id, base_crypto)
        
        if len(pairs) < 2:
            logger.debug(f"{exchange_marker} [{exchange_id.upper()}] {base_crypto}: Only {len(pairs)} pair(s) found (need 2+ for arbitrage)")
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
                
                # Safety check: Skip futures markets (they have ':' in symbol)
                if ':' in pair1 or ':' in pair2:
                    continue
                
                try:
                    # Get prices - use exchange manager (ensures exchange separation)
                    ticker1 = await self.exchange_manager.fetch_ticker(exchange_id, pair1)
                    ticker2 = await self.exchange_manager.fetch_ticker(exchange_id, pair2)
                    
                    # 🔵 CRITICAL FIX: Use ASK for buy and BID for sell (not last price)
                    # ASK = what we pay to buy, BID = what we get when we sell
                    ask1 = ticker1.get('ask', 0) or ticker1.get('last', 0)
                    bid1 = ticker1.get('bid', 0) or ticker1.get('last', 0)
                    ask2 = ticker2.get('ask', 0) or ticker2.get('last', 0)
                    bid2 = ticker2.get('bid', 0) or ticker2.get('last', 0)
                    
                    # For arbitrage: we want to buy where it's cheaper and sell where it's more expensive
                    # Compare: buy at ASK of pair1 vs ASK of pair2, sell at BID of pair1 vs BID of pair2
                    # We need: min(ask1, ask2) < max(bid1, bid2) for profit
                    
                    if ask1 <= 0 or bid1 <= 0 or ask2 <= 0 or bid2 <= 0:
                        continue
                    
                    # Normalize prices to USD for comparison
                    usd_ask1 = await self._normalize_price_to_usd(exchange_id, ask1, quote1)
                    usd_bid1 = await self._normalize_price_to_usd(exchange_id, bid1, quote1)
                    usd_ask2 = await self._normalize_price_to_usd(exchange_id, ask2, quote2)
                    usd_bid2 = await self._normalize_price_to_usd(exchange_id, bid2, quote2)
                    
                    # Determine best buy/sell combination
                    # Option 1: Buy pair1, sell pair2
                    profit1 = usd_bid2 - usd_ask1
                    # Option 2: Buy pair2, sell pair1
                    profit2 = usd_bid1 - usd_ask2
                    
                    # Choose the better option (higher profit)
                    if profit1 > profit2 and profit1 > 0:
                        buy_pair, buy_price = pair1, ask1
                        sell_pair, sell_price = pair2, bid2
                        buy_quote, sell_quote = quote1, quote2
                    elif profit2 > 0:
                        buy_pair, buy_price = pair2, ask2
                        sell_pair, sell_price = pair1, bid1
                        buy_quote, sell_quote = quote2, quote1
                    else:
                        # No profitable opportunity
                        continue
                    
                    # Sanity check: prices shouldn't differ by more than 10x
                    if max(buy_price, sell_price) / min(buy_price, sell_price) > 10:
                        continue  # Likely conversion error
                    
                    # Calculate order book depth
                    depth_buy = await self._calculate_order_book_depth(exchange_id, buy_pair, 'buy', trade_size_usd)
                    depth_sell = await self._calculate_order_book_depth(exchange_id, sell_pair, 'sell', trade_size_usd)
                    
                    # Calculate volatility (use average of both pairs)
                    vol1 = await self._calculate_volatility(exchange_id, pair1)
                    vol2 = await self._calculate_volatility(exchange_id, pair2)
                    volatility = (vol1 + vol2) / 2
                    
                    # Normalize buy/sell prices to USD for calculation
                    usd_buy_price = await self._normalize_price_to_usd(exchange_id, buy_price, buy_quote)
                    usd_sell_price = await self._normalize_price_to_usd(exchange_id, sell_price, sell_quote)
                    
                    # Calculate spread width
                    spread_width = abs(usd_sell_price - usd_buy_price)
                    
                    # Calculate profitability
                    profit_data = calculator.calculate_net_profit(
                        buy_price=usd_buy_price,
                        sell_price=usd_sell_price,
                        trade_size_usd=trade_size_usd,
                        order_book_depth_buy=depth_buy,
                        order_book_depth_sell=depth_sell,
                        spread_width=spread_width,
                        volatility_24h=volatility,
                        execution_latency_ms=self.execution_latency_ms
                    )
                    
                    # No conversion costs needed - only USD/USDC/USDT pairs
                    # These are interchangeable at 1:1 rate
                    profit_data['expected_profit_usd'] = trade_size_usd * profit_data['net_profit']
                    
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
                        
                        # LOG PROFITABLE OPPORTUNITY FOUND
                        exchange_marker = "🔵" if exchange_id == 'coinbase' else "🟢"
                        logger.info(f"{exchange_marker} [{exchange_id.upper()}] ✅ PROFITABLE: {base_crypto} | "
                                   f"Buy: {buy_pair} @ ${usd_buy_price:.6f} (ASK) | "
                                   f"Sell: {sell_pair} @ ${usd_sell_price:.6f} (BID) | "
                                   f"Spread: {profit_data['raw_spread']*100:.3f}% | "
                                   f"Net Profit: {net_profit*100:.3f}% | "
                                   f"Expected: ${profit_data['expected_profit_usd']:.2f}")
                        
                        if score > best_score:
                            opportunity = TradeOpportunity(
                                exchange=exchange_id,
                                base_crypto=base_crypto,
                                buy_pair=buy_pair,
                                sell_pair=sell_pair,
                                buy_price=usd_buy_price,
                                sell_price=usd_sell_price,
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
                    else:
                        # LOG WHY NOT PROFITABLE (only for Coinbase, and only occasionally to reduce spam)
                        deficit = (threshold - net_profit) * 100
                        # For Coinbase, log first opportunity check per crypto, then every 10th check
                        if exchange_id == 'coinbase':
                            if not hasattr(self, '_coinbase_opportunity_logs'):
                                self._coinbase_opportunity_logs = {}
                            if base_crypto not in self._coinbase_opportunity_logs:
                                self._coinbase_opportunity_logs[base_crypto] = 0
                            self._coinbase_opportunity_logs[base_crypto] += 1
                            
                            # Log first check and every 10th check
                            if self._coinbase_opportunity_logs[base_crypto] <= 1 or self._coinbase_opportunity_logs[base_crypto] % 10 == 0:
                                logger.info(f"{exchange_marker} [{exchange_id.upper()}] ⚠️ {base_crypto}: Spread {profit_data['raw_spread']*100:.3f}% → Net {net_profit*100:.3f}% < Required {threshold*100:.3f}% (deficit: {deficit:.3f}%)")
                        else:
                            logger.debug(f"   {exchange_marker} [{exchange_id.upper()}] NOT PROFITABLE: {base_crypto} | "
                                   f"{buy_pair} vs {sell_pair} | "
                                   f"Spread: {profit_data['raw_spread']*100:.3f}% | "
                                   f"Net: {net_profit*100:.3f}% | "
                                   f"Required: {threshold*100:.3f}% | "
                                   f"Deficit: {deficit:.3f}%")
                
                except Exception as e:
                    logger.debug(f"Error evaluating {pair1} vs {pair2}: {e}")
                    continue
        
        return best_opportunity
    
    async def scan_exchange(self, exchange_id: str, max_cryptos: int = 100) -> List[TradeOpportunity]:
        """
        Scan an exchange for ALL profitable opportunities
        Returns ranked list of opportunities
        """
        logger.info("=" * 80)
        logger.info(f"🔍 SCANNING {exchange_id.upper()} FOR ARBITRAGE OPPORTUNITIES")
        logger.info("=" * 80)
        
        start_time = time.time()
        exchange = self.exchange_manager.get_exchange(exchange_id)
        
        # Get all unique base cryptos that have at least 2 USD/USDC/USDT pairs
        # This filters for cryptos that can actually be arbitraged
        base_cryptos = set()
        crypto_pair_count = {}
        
        for symbol, market_info in exchange.markets.items():
            if not market_info.get('active', True):
                continue
            
            # Skip futures/derivatives
            if market_info.get('future', False) or market_info.get('swap', False):
                continue
            if ':' in symbol:
                continue
            
            base = market_info.get('base', '').strip().upper()
            quote = market_info.get('quote', '').strip().upper()
            
            # Only count USD/USDC/USDT pairs
            if quote in ['USD', 'USDC', 'USDT']:
                if base not in crypto_pair_count:
                    crypto_pair_count[base] = 0
                crypto_pair_count[base] += 1
        
        # Only include cryptos with at least 2 pairs (needed for arbitrage)
        for crypto, pair_count in crypto_pair_count.items():
            if pair_count >= 2:
                base_cryptos.add(crypto)
        
        logger.info(f"   📊 Found {len(base_cryptos)} unique cryptos on {exchange_id.upper()} (with 2+ USD/USDC/USDT pairs)")
        logger.info(f"   🎯 Scanning for profitable intra-exchange arbitrage pairs...")
        logger.info("")
        
        opportunities = []
        scanned = 0
        profitable_found = 0
        
        # Scan each crypto
        for base_crypto in list(base_cryptos)[:max_cryptos]:
            scanned += 1
            if scanned % 50 == 0:
                logger.info(f"   📈 Progress: {scanned}/{min(len(base_cryptos), max_cryptos)} cryptos | "
                           f"✅ Profitable: {profitable_found} found so far")
            
            opportunity = await self._find_opportunity_for_crypto(
                exchange_id=exchange_id,
                base_crypto=base_crypto,
                trade_size_usd=self.max_position_size_usd
            )
            
            if opportunity:
                opportunities.append(opportunity)
                profitable_found += 1
                self.stats[exchange_id]['opportunities_found'] += 1
        
        # Sort by opportunity score (highest first)
        opportunities.sort(key=lambda x: x.opportunity_score, reverse=True)
        
        scan_time = time.time() - start_time
        logger.info("")
        logger.info(f"   ✅ [{exchange_id.upper()}] SCAN COMPLETE:")
        logger.info(f"      Time: {scan_time:.2f}s")
        logger.info(f"      Cryptos scanned: {scanned}")
        logger.info(f"      ✅ Profitable opportunities: {len(opportunities)}")
        
        if opportunities:
            logger.info(f"   🏆 TOP 10 OPPORTUNITIES ON {exchange_id.upper()} (by score):")
            for i, opp in enumerate(opportunities[:10], 1):
                logger.info(f"      {i}. {opp.base_crypto} | "
                           f"{opp.buy_pair} → {opp.sell_pair} | "
                           f"Net Profit: {opp.net_profit_percent:.3f}% | "
                           f"Score: {opp.opportunity_score:.2f} | "
                           f"${opp.expected_profit_usd:.2f}")
            logger.info(f"   📋 ALL {len(opportunities)} OPPORTUNITIES WILL BE EVALUATED FOR EXECUTION")
        else:
            logger.info(f"   ⚠️  No profitable opportunities found on {exchange_id.upper()}")
        
        logger.info("=" * 80)
        
        return opportunities
    
    async def scan_and_execute_immediately(self, exchange_id: str, max_cryptos: int = 200) -> Dict:
        """
        Scan and execute opportunities IMMEDIATELY when found (STREAMING EXECUTION)
        This ensures we don't wait for the entire scan to complete before executing
        Returns dict with execution statistics
        """
        logger.info("=" * 80)
        logger.info(f"🚀 SCANNING & EXECUTING {exchange_id.upper()} (IMMEDIATE MODE)")
        logger.info("=" * 80)
        
        start_time = time.time()
        exchange = self.exchange_manager.get_exchange(exchange_id)
        
        # Get all unique base cryptos that have at least 2 USD/USDC/USDT pairs
        # This filters for cryptos that can actually be arbitraged
        base_cryptos = set()
        crypto_pair_count = {}
        
        for symbol, market_info in exchange.markets.items():
            if not market_info.get('active', True):
                continue
            
            # Skip futures/derivatives
            if market_info.get('future', False) or market_info.get('swap', False):
                continue
            if ':' in symbol:
                continue
            
            base = market_info.get('base', '').strip().upper()
            quote = market_info.get('quote', '').strip().upper()
            
            # Only count USD/USDC/USDT pairs
            if base and quote in ['USD', 'USDC', 'USDT']:
                if base not in crypto_pair_count:
                    crypto_pair_count[base] = 0
                crypto_pair_count[base] += 1
        
        # Only include cryptos with at least 2 pairs (needed for arbitrage)
        for crypto, pair_count in crypto_pair_count.items():
            if pair_count >= 2:
                base_cryptos.add(crypto)
        
        exchange_marker = "🔵" if exchange_id == 'coinbase' else "🟢"
        logger.info(f"{exchange_marker} [{exchange_id.upper()}] 📊 Found {len(base_cryptos)} unique cryptos (with 2+ USD/USDC/USDT pairs)")
        logger.info(f"{exchange_marker} [{exchange_id.upper()}] ⚡ IMMEDIATE EXECUTION MODE: Trades execute as soon as found!")
        
        # 🔵 IMPROVEMENT: Skip during low liquidity hours (reduce scan size)
        current_hour = datetime.now().hour
        # US market hours: 9 AM - 4 PM EST (14:00 - 21:00 UTC)
        if 14 <= current_hour <= 21:
            max_cryptos = max_cryptos  # Full scan during peak hours
            logger.info(f"{exchange_marker} [{exchange_id.upper()}] ⏰ Peak hours detected - full scan: {max_cryptos} cryptos")
        else:
            max_cryptos = min(max_cryptos, 50)  # Reduced scan during off-peak
            logger.info(f"{exchange_marker} [{exchange_id.upper()}] ⏰ Off-peak hours - reduced scan to {max_cryptos} cryptos")
        
        logger.info("")
        
        scanned = 0
        opportunities_found = 0
        trades_executed = 0
        trades_skipped = 0
        
        # Track active trades to avoid conflicts
        active_pairs = set()
        active_base_cryptos = set()
        execution_tasks = []
        
        # Scan each crypto and execute immediately
        for base_crypto in list(base_cryptos)[:max_cryptos]:
            scanned += 1
            exchange_marker = "🔵" if exchange_id == 'coinbase' else "🟢"
            if scanned % 50 == 0:
                logger.info(f"{exchange_marker} [{exchange_id.upper()}] 📈 Progress: {scanned}/{min(len(base_cryptos), max_cryptos)} cryptos | "
                           f"✅ Found: {opportunities_found} | "
                           f"🚀 Executed: {trades_executed} | "
                           f"⏭️ Skipped: {trades_skipped}")
            
            # Check if we've reached max concurrent trades
            if len(execution_tasks) >= self.max_concurrent_trades_per_exchange:
                # Wait for at least one trade to complete before continuing
                if execution_tasks:
                    done, pending = await asyncio.wait(execution_tasks, return_when=asyncio.FIRST_COMPLETED)
                    execution_tasks = list(pending)
                    # Clean up completed tasks
                    for task in done:
                        try:
                            result = await task
                            if result and result.status == 'success':
                                trades_executed += 1
                            elif result:
                                trades_skipped += 1
                        except Exception as e:
                            logger.debug(f"Task completed with error: {e}")
                            trades_skipped += 1
            
            # Check for conflicts
            if base_crypto in active_base_cryptos:
                continue  # Skip if already trading this crypto
            
            opportunity = await self._find_opportunity_for_crypto(
                exchange_id=exchange_id,
                base_crypto=base_crypto,
                trade_size_usd=self.max_position_size_usd
            )
            
            if opportunity:
                opportunities_found += 1
                self.stats[exchange_id]['opportunities_found'] += 1
                
                # 🔵 IMPROVEMENT: Skip recently failed pairs (5 minute cooldown)
                exchange_marker = "🔵" if exchange_id == 'coinbase' else "🟢"
                pair_key = f"{opportunity.buy_pair}/{opportunity.sell_pair}"
                if pair_key in self.failed_pairs_cache:
                    time_since_fail = time.time() - self.failed_pairs_cache[pair_key]
                    if time_since_fail < 300:  # 5 minutes
                        logger.info(f"{exchange_marker} [{exchange_id.upper()}] ⏭️ Skipping {opportunity.base_crypto} ({pair_key}) - failed {time_since_fail:.0f}s ago (cooldown: 5min)")
                        trades_skipped += 1
                        continue
                
                # Check if profitable enough
                if opportunity.net_profit_percent < self.min_profit_threshold * 100:
                    trades_skipped += 1
                    exchange_marker = "🔵" if exchange_id == 'coinbase' else "🟢"
                    logger.info(f"{exchange_marker} [{exchange_id.upper()}] ⏭️ Skipped {opportunity.base_crypto}: profit {opportunity.net_profit_percent:.3f}% < threshold {self.min_profit_threshold*100:.2f}%")
                    continue
                
                # Check for pair conflicts
                if pair_key in active_pairs:
                    trades_skipped += 1
                    logger.info(f"{exchange_marker} [{exchange_id.upper()}] ⏭️ Skipped {opportunity.base_crypto}: pair conflict {pair_key} (already trading)")
                    continue
                
                # ALL CHECKS PASSED - EXECUTE IMMEDIATELY!
                active_pairs.add(pair_key)
                active_base_cryptos.add(base_crypto)
                
                logger.info("")
                logger.info(f"{exchange_marker} [{exchange_id.upper()}] 🚀🚀🚀 IMMEDIATE EXECUTION: {opportunity.base_crypto}")
                logger.info(f"{exchange_marker} [{exchange_id.upper()}]    Buy: {opportunity.buy_pair} @ ${opportunity.buy_price:.6f}")
                logger.info(f"{exchange_marker} [{exchange_id.upper()}]    Sell: {opportunity.sell_pair} @ ${opportunity.sell_price:.6f}")
                logger.info(f"{exchange_marker} [{exchange_id.upper()}]    Net Profit: {opportunity.net_profit_percent:.3f}% (${opportunity.expected_profit_usd:.2f})")
                logger.info(f"{exchange_marker} [{exchange_id.upper()}]    Volume depth: ${min(opportunity.order_book_depth_buy, opportunity.order_book_depth_sell):.2f}")
                logger.info("")
                
                # 🔵 IMPROVEMENT: Prioritize high volume opportunities
                # Note: We execute immediately, but we prioritize by checking volume depth
                # Higher volume = better liquidity = faster fills = less slippage
                
                # Execute immediately (non-blocking)
                execution_task = asyncio.create_task(self.execute_trade(opportunity))
                
                # Cleanup function to remove from active sets after execution
                async def cleanup_after_execution(task, pair_key, base_crypto):
                    try:
                        result = await task
                        # Remove from active sets after execution completes
                        active_pairs.discard(pair_key)
                        active_base_cryptos.discard(base_crypto)
                        return result
                    except Exception as e:
                        logger.debug(f"Execution error: {e}")
                        active_pairs.discard(pair_key)
                        active_base_cryptos.discard(base_crypto)
                        return None
                
                # Wrap task with cleanup
                wrapped_task = asyncio.create_task(cleanup_after_execution(execution_task, pair_key, base_crypto))
                execution_tasks.append(wrapped_task)
        
        # Wait for remaining executions to complete
        if execution_tasks:
            logger.info(f"   ⏳ Waiting for {len(execution_tasks)} remaining trades to complete...")
            results = await asyncio.gather(*execution_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    trades_skipped += 1
                elif result and result.status == 'success':
                    trades_executed += 1
                elif result:
                    trades_skipped += 1
        
        scan_time = time.time() - start_time
        exchange_marker = "🔵" if exchange_id == 'coinbase' else "🟢"
        logger.info("")
        logger.info(f"{exchange_marker} [{exchange_id.upper()}] ✅ SCAN & EXECUTE COMPLETE:")
        logger.info(f"{exchange_marker} [{exchange_id.upper()}]    Time: {scan_time:.2f}s")
        logger.info(f"{exchange_marker} [{exchange_id.upper()}]    Cryptos scanned: {scanned}")
        logger.info(f"{exchange_marker} [{exchange_id.upper()}]    ✅ Opportunities found: {opportunities_found}")
        logger.info(f"{exchange_marker} [{exchange_id.upper()}]    🚀 Trades executed: {trades_executed}")
        logger.info(f"{exchange_marker} [{exchange_id.upper()}]    ⏭️ Trades skipped: {trades_skipped}")
        if opportunities_found == 0:
            logger.info(f"{exchange_marker} [{exchange_id.upper()}]    💡 No opportunities found - spreads may be too tight or fees too high")
        logger.info("=" * 80)
        
        return {
            'scanned': scanned,
            'opportunities_found': opportunities_found,
            'trades_executed': trades_executed,
            'trades_skipped': trades_skipped,
            'scan_time': scan_time
        }
    
    async def _validate_opportunity_still_exists(
        self,
        opportunity: TradeOpportunity
    ) -> Optional[TradeOpportunity]:
        """
        Re-check spread right before execution
        Opportunities disappear fast - this prevents bad trades
        """
        exchange_id = opportunity.exchange
        exchange_marker = "🔵" if exchange_id == 'coinbase' else "🟢"
        
        try:
            logger.debug(f"{exchange_marker} [{exchange_id.upper()}]    🔍 Validating opportunity: {opportunity.base_crypto}")
            logger.debug(f"{exchange_marker} [{exchange_id.upper()}]       Buy pair: {opportunity.buy_pair}")
            logger.debug(f"{exchange_marker} [{exchange_id.upper()}]       Sell pair: {opportunity.sell_pair}")
            
            # Get fresh prices - use ASK for buy, BID for sell (same as opportunity finding)
            ticker1 = await self.exchange_manager.fetch_ticker(exchange_id, opportunity.buy_pair)
            ticker2 = await self.exchange_manager.fetch_ticker(exchange_id, opportunity.sell_pair)
            
            # 🔵 CRITICAL FIX: Use ASK for buy, BID for sell (not last price)
            ask1 = ticker1.get('ask', 0) or ticker1.get('last', 0)
            bid2 = ticker2.get('bid', 0) or ticker2.get('last', 0)
            
            logger.debug(f"{exchange_marker} [{exchange_id.upper()}]       Fresh prices: Buy ASK={ask1}, Sell BID={bid2}")
            
            if ask1 <= 0 or bid2 <= 0:
                logger.warning(f"{exchange_marker} [{exchange_id.upper()}]    ⚠️ Invalid prices: ask1={ask1}, bid2={bid2}")
                return None
            
            # Extract quote currencies
            buy_quote = opportunity.buy_pair.split('/')[1]
            sell_quote = opportunity.sell_pair.split('/')[1]
            
            # Normalize to USD
            usd_price1 = await self._normalize_price_to_usd(exchange_id, ask1, buy_quote)
            usd_price2 = await self._normalize_price_to_usd(exchange_id, bid2, sell_quote)
            
            logger.debug(f"{exchange_marker} [{exchange_id.upper()}]       USD prices: Buy=${usd_price1:.6f}, Sell=${usd_price2:.6f}")
            
            # Recalculate spread
            if usd_price1 < usd_price2:
                raw_spread = (usd_price2 - usd_price1) / usd_price1
            else:
                logger.warning(f"{exchange_marker} [{exchange_id.upper()}]    ⚠️ Opportunity reversed: buy price ${usd_price1:.6f} >= sell price ${usd_price2:.6f}")
                return None  # Opportunity reversed
            
            # Check if still profitable
            # 🔵 Use Coinbase calculator for Coinbase, 🟢 Gemini calculator for Gemini
            calculator = self.coinbase_calculator if exchange_id == 'coinbase' else self.gemini_calculator
            fees_total = calculator.maker_fee + calculator.maker_fee
            net_spread = raw_spread - fees_total - 0.002  # Account for slippage
            
            logger.debug(f"{exchange_marker} [{exchange_id.upper()}]       Spread: {raw_spread*100:.3f}% → Net: {net_spread*100:.3f}% (fees: {fees_total*100:.3f}%)")
            
            if net_spread < self.min_profit_threshold:
                logger.warning(f"{exchange_marker} [{exchange_id.upper()}]    ⚠️ Opportunity disappeared: spread now {net_spread*100:.3f}% < {self.min_profit_threshold*100:.3f}%")
                return None
            
            # Update opportunity with fresh prices
            opportunity.buy_price = usd_price1
            opportunity.sell_price = usd_price2
            opportunity.raw_spread_percent = raw_spread * 100
            opportunity.net_profit_percent = net_spread * 100
            
            logger.debug(f"{exchange_marker} [{exchange_id.upper()}]    ✅ Opportunity still valid: {net_spread*100:.3f}% profit")
            return opportunity
            
        except Exception as e:
            logger.warning(f"{exchange_marker} [{exchange_id.upper()}]    ⚠️ Could not validate opportunity: {type(e).__name__}: {e}")
            import traceback
            logger.debug(f"{exchange_marker} [{exchange_id.upper()}]    Traceback: {traceback.format_exc()}")
            return None  # If we can't validate, skip the trade
    
    async def _wait_for_order_fill_with_chase(
        self,
        exchange_id: str,
        order_id: str,
        symbol: str,
        side: str,
        original_price: float,
        max_wait: int
    ) -> Tuple[Optional[Dict], float]:
        """
        Wait for order fill, with price chasing if needed
        Returns: (order_status, actual_price)
        """
        waited = 0
        current_price = original_price
        price_chased = 0.0
        
        while waited < max_wait:
            await asyncio.sleep(2)
            waited += 2
            
            try:
                order_status = await self.exchange_manager.fetch_order(exchange_id, order_id, symbol)
                status = order_status.get('status', 'unknown')
                
                if status in ['closed', 'filled']:
                    filled_price = order_status.get('average') or order_status.get('price') or current_price
                    return order_status, filled_price
                
                if status == 'canceled':
                    return None, current_price
                
                # Check partial fill
                filled = order_status.get('filled', 0)
                if filled > 0:
                    logger.info(f"   ⏳ Partially filled: {filled:.6f} {symbol}")
                
                # Price chasing: if not filled after 2s, adjust price slightly (FASTER!)
                if waited >= self.price_chase_start_seconds and price_chased < self.max_price_chase_percent:
                    # Cancel old order
                    try:
                        await self.exchange_manager.cancel_order(exchange_id, order_id, symbol)
                        logger.info(f"   🔄 Canceling to chase price...")
                    except:
                        pass
                    
                    # Adjust price (more aggressive chasing)
                    chase_multiplier = max(1, (waited - self.price_chase_start_seconds) // self.price_chase_start_seconds)
                    if side == 'buy':
                        current_price = original_price * (1 + self.price_chase_increment * chase_multiplier)
                    else:
                        current_price = original_price * (1 - self.price_chase_increment * chase_multiplier)
                    
                    price_chased = abs(current_price - original_price) / original_price
                    
                    if price_chased < self.max_price_chase_percent:
                        # Place new order at adjusted price
                        try:
                            base_amount = order_status.get('amount', 0) - filled
                            if base_amount > 0:
                                # 🔵 CRITICAL FIX: Validate parameters before creating order
                                if base_amount is None or base_amount <= 0:
                                    logger.warning(f"   ⚠️ Invalid base_amount for price chase: {base_amount}")
                                    continue
                                if current_price is None or current_price <= 0:
                                    logger.warning(f"   ⚠️ Invalid current_price for price chase: {current_price}")
                                    continue
                                
                                exchange_marker = "🔵" if exchange_id == 'coinbase' else "🟢"
                                logger.info(f"{exchange_marker} [{exchange_id.upper()}]    🎯 Price chasing: ${current_price:.6f} (chased {price_chased*100:.2f}%)")
                                new_order = await self.exchange_manager.create_order(
                                    exchange_id=exchange_id,
                                    symbol=symbol,
                                    order_type='limit',
                                    side=side,
                                    amount=base_amount,
                                    price=current_price
                                )
                                order_id = new_order.get('id') if new_order else None
                                if order_id:
                                    logger.info(f"{exchange_marker} [{exchange_id.upper()}]    ✅ Price chase order placed: ID={order_id}")
                                else:
                                    logger.warning(f"{exchange_marker} [{exchange_id.upper()}]    ⚠️ Price chase order failed: no ID")
                        except Exception as e:
                            exchange_marker = "🔵" if exchange_id == 'coinbase' else "🟢"
                            logger.warning(f"{exchange_marker} [{exchange_id.upper()}]    ⚠️ Price chase failed: {type(e).__name__}: {e}")
                            # Continue waiting instead of returning early
                            pass
                    
            except Exception as e:
                logger.warning(f"   ⚠️ Error checking order: {e}")
        
        # Timeout
        logger.warning(f"   ⏱️ Order timeout after {max_wait}s")
        return None, current_price
    
    async def _convert_currency(
        self,
        exchange_id: str,
        from_currency: str,
        to_currency: str,
        amount: float
    ) -> bool:
        """
        Convert one currency to another on the exchange
        Only supports USD/USDC/USDT (interchangeable at 1:1)
        Returns True if conversion successful (or not needed)
        """
        # USD/USDC/USDT are interchangeable - no conversion needed
        if from_currency in ['USD', 'USDC', 'USDT'] and to_currency in ['USD', 'USDC', 'USDT']:
            return True
        
        if from_currency == to_currency:
            return True
        
        # For other currencies, conversion is not supported
        logger.warning(f"   ⚠️ Currency conversion not supported: {from_currency} → {to_currency}")
        logger.warning(f"   💡 Only USD/USDC/USDT pairs are supported for intra-exchange arbitrage")
        return False
    
    async def _ensure_currency_available(
        self,
        exchange_id: str,
        required_currency: str,
        required_amount: float
    ) -> bool:
        """
        Ensure we have the required currency, converting if necessary
        Only handles USD/USDC/USDT (interchangeable at 1:1)
        """
        balance = await self.exchange_manager.fetch_balance(exchange_id)
        free_balance = balance.get('free', {})
        
        # Check if we already have enough
        available = free_balance.get(required_currency, 0)
        if available >= required_amount * 1.1:  # 10% buffer
            return True
        
        # For USD/USDC/USDT, check if we have any of them (they're interchangeable)
        if required_currency in ['USD', 'USDC', 'USDT']:
            total_available = 0
            for currency in ['USD', 'USDC', 'USDT']:
                total_available += free_balance.get(currency, 0)
            
            if total_available >= required_amount * 1.1:
                logger.info(f"   ✅ Have ${total_available:.2f} in USD/USDC/USDT (need ${required_amount:.2f} {required_currency})")
                return True
        
        # Only USD/USDC/USDT are supported - no conversion needed as they're interchangeable
        
        logger.warning(f"   ⚠️ Insufficient {required_currency}: have {available:.2f}, need {required_amount:.2f}")
        return False
    
    async def _check_balance_sufficient(
        self,
        exchange_id: str,
        buy_pair: str,
        sell_pair: str,
        trade_size_usd: float
    ) -> Tuple[bool, float]:
        """
        Check if we have sufficient balance for both sides of the trade
        Accounts for:
        - Cash (quote currency) for buying
        - Existing positions (base crypto) for selling
        
        Returns: (success, actual_available_amount_usd)
        CRITICAL: Need quote currency for buy, base currency for sell
        """
        try:
            balance = await self.exchange_manager.fetch_balance(exchange_id)
            free_balance = balance.get('free', {})
            
            # Extract currencies
            buy_quote = buy_pair.split('/')[1]  # e.g., 'USDC' from 'BTC/USDC'
            sell_quote = sell_pair.split('/')[1]  # e.g., 'USD' from 'BTC/USD'
            base_crypto = buy_pair.split('/')[0]  # e.g., 'BTC'
            
            # Get current prices for calculations
            buy_ticker = await self.exchange_manager.fetch_ticker(exchange_id, buy_pair)
            sell_ticker = await self.exchange_manager.fetch_ticker(exchange_id, sell_pair)
            buy_price = buy_ticker.get('ask') or buy_ticker.get('last', 0)
            sell_price = sell_ticker.get('bid') or sell_ticker.get('last', 0)
            
            if buy_price <= 0 or sell_price <= 0:
                logger.warning(f"   ⚠️ Invalid prices for balance check")
                return False, 0
            
            # Check for convertible currencies (USD/USDC/USDT) - these are interchangeable
            total_convertible = free_balance.get('USD', 0) + free_balance.get('USDC', 0) + free_balance.get('USDT', 0)
            
            # OPTION 1: Check if we have the required quote currency directly
            # For USD/USDC/USDT, we can use any of them interchangeably
            buy_balance = free_balance.get(buy_quote, 0)
            
            # If we don't have enough of the exact quote currency, use USD/USDC/USDT pool (interchangeable)
            if buy_quote in ['USD', 'USDC', 'USDT']:
                # Use the convertible pool if we don't have enough of the specific currency
                if buy_balance < trade_size_usd:
                    # Use total convertible pool (USD/USDC/USDT are 1:1 interchangeable)
                    if total_convertible > buy_balance:
                        logger.info(f"   💱 Need {buy_quote} but have ${buy_balance:.2f} - using ${total_convertible:.2f} from USD/USDC/USDT pool")
                        buy_balance = total_convertible  # Use total convertible as they're 1:1
                    else:
                        logger.info(f"   💱 Using available {buy_quote}: ${buy_balance:.2f}")
                else:
                    logger.info(f"   💰 Have sufficient {buy_quote}: ${buy_balance:.2f}")
                
                # Calculate cash available in USD equivalent
                # USD/USDC/USDT are all 1:1 with USD
                cash_available_usd = buy_balance
            else:
                # For other currencies, not supported (only USD/USDC/USDT)
                cash_available_usd = buy_balance
                logger.warning(f"   ⚠️ Non-USD/USDC/USDT quote currency: {buy_quote} (not supported)")
            
            # OPTION 2: Check if we already have the base crypto (can sell immediately)
            base_crypto_balance = free_balance.get(base_crypto, 0)
            crypto_value_usd = base_crypto_balance * sell_price  # Value if we sell what we have
            
            # Calculate total available BEFORE logging (fixes scoping error)
            total_available_usd = cash_available_usd + crypto_value_usd
            
            # 🔵 COINBASE / 🟢 GEMINI: Add exchange marker for balance logging
            exchange_marker = "🔵" if exchange_id == 'coinbase' else "🟢"
            
            logger.info(f"{exchange_marker} [{exchange_id.upper()}]    💰 Balance check:")
            logger.info(f"{exchange_marker} [{exchange_id.upper()}]       Cash ({buy_quote}): {buy_balance:.2f} = ${cash_available_usd:.2f} USD equivalent")
            logger.info(f"{exchange_marker} [{exchange_id.upper()}]       Convertible (USD/USDC/USDT): ${total_convertible:.2f}")
            logger.info(f"{exchange_marker} [{exchange_id.upper()}]       Position ({base_crypto}): {base_crypto_balance:.8f} = ${crypto_value_usd:.2f} USD value")
            logger.info(f"{exchange_marker} [{exchange_id.upper()}]       Total available: ${total_available_usd:.2f}")
            
            # Determine actual position size based on available resources
            # Use 90% of available to leave buffer for fees/slippage
            actual_position_size = min(trade_size_usd, total_available_usd * 0.9)
            
            # Minimum position size check - allow smaller trades if balance is low
            # If we have at least $5, allow the trade (lowered threshold)
            min_required = max(self.min_position_size_usd * 0.2, 5.0)  # At least $5 or 20% of minimum
            if actual_position_size < min_required:
                logger.warning(f"{exchange_marker} [{exchange_id.upper()}]    ⚠️ Available ${actual_position_size:.2f} < minimum ${min_required:.2f}")
                logger.warning(f"{exchange_marker} [{exchange_id.upper()}]    📊 Breakdown: Cash=${cash_available_usd:.2f}, Positions=${crypto_value_usd:.2f}, Convertible=${total_convertible:.2f}")
                
                # If we have convertible currency but insufficient balance, log it
                if total_convertible >= min_required:
                    logger.warning(f"{exchange_marker} [{exchange_id.upper()}]    ⚠️ Have ${total_convertible:.2f} in USD/USDC/USDT but insufficient for trade")
                    logger.warning(f"{exchange_marker} [{exchange_id.upper()}]    💡 Ensure sufficient balance in {buy_quote} for trading")
                
                return False, 0
            
            if actual_position_size < trade_size_usd:
                logger.info(f"   💡 Position sizing: Using ${actual_position_size:.2f} (available) vs ${trade_size_usd:.2f} (desired)")
            
            return True, actual_position_size
            
        except Exception as e:
            logger.error(f"   ❌ Error checking balance: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            # Return False with 0 amount - don't proceed with trade if we can't verify balance
            return False, 0
    
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
        
        # 🔵 COINBASE / 🟢 GEMINI: Exchange marker for logging
        exchange_marker = "🔵" if exchange_id == 'coinbase' else "🟢"
        
        logger.info("")
        logger.info(f"{exchange_marker} [{exchange_id.upper()}] 💰 STARTING TRADE EXECUTION")
        logger.info(f"{exchange_marker} [{exchange_id.upper()}]    Crypto: {opportunity.base_crypto}")
        logger.info(f"{exchange_marker} [{exchange_id.upper()}]    Strategy: Buy {opportunity.buy_pair} → Sell {opportunity.sell_pair}")
        logger.info(f"{exchange_marker} [{exchange_id.upper()}]    Expected profit: {opportunity.net_profit_percent:.3f}% (${opportunity.expected_profit_usd:.2f})")
        logger.info(f"{exchange_marker} [{exchange_id.upper()}]    Raw spread: {opportunity.raw_spread_percent:.3f}%")
        logger.info(f"{exchange_marker} [{exchange_id.upper()}]    Fees: {opportunity.fees_buy:.3f}% + {opportunity.fees_sell:.3f}%")
        logger.info(f"{exchange_marker} [{exchange_id.upper()}]    Estimated slippage: {opportunity.estimated_slippage:.3f}%")
        
        # CIRCUIT BREAKER CHECK
        if self.circuit_breaker_enabled and self.session_loss <= self.circuit_breaker_loss_threshold:
            logger.warning(f"{exchange_marker} [{exchange_id.upper()}]    ❌ EXECUTION BLOCKED: Circuit breaker active")
            logger.warning(f"{exchange_marker} [{exchange_id.upper()}]       Session loss: ${self.session_loss:.2f}")
            logger.warning(f"{exchange_marker} [{exchange_id.upper()}]       Threshold: ${self.circuit_breaker_loss_threshold:.2f}")
            logger.warning(f"{exchange_marker} [{exchange_id.upper()}]       Reason: Too much loss this session - protecting capital")
            return TradeExecution(
                exchange=exchange_id,
                opportunity=opportunity,
                buy_order_id=None,
                sell_order_id=None,
                actual_buy_price=0,
                actual_sell_price=0,
                actual_profit_usd=0,
                execution_time_seconds=0,
                status='failed'
            )
        logger.info(f"{exchange_marker} [{exchange_id.upper()}]    ✅ Circuit breaker: PASSED (session loss: ${self.session_loss:.2f})")
        
        # STEP 1: Validate opportunity still exists (CRITICAL - opportunities disappear fast)
        logger.info(f"{exchange_marker} [{exchange_id.upper()}]    🔍 Validating opportunity still exists...")
        validated_opp = await self._validate_opportunity_still_exists(opportunity)
        if not validated_opp:
            logger.warning(f"{exchange_marker} [{exchange_id.upper()}]    ❌ EXECUTION BLOCKED: Opportunity disappeared")
            logger.warning(f"{exchange_marker} [{exchange_id.upper()}]       Reason: Spread changed or opportunity no longer profitable")
            logger.warning(f"{exchange_marker} [{exchange_id.upper()}]       This is normal - market moves fast, protecting against losses")
            return TradeExecution(
                exchange=exchange_id,
                opportunity=opportunity,
                buy_order_id=None,
                sell_order_id=None,
                actual_buy_price=0,
                actual_sell_price=0,
                actual_profit_usd=0,
                execution_time_seconds=0,
                status='failed'
            )
        opportunity = validated_opp
        logger.info(f"{exchange_marker} [{exchange_id.upper()}]    ✅ Opportunity validation: PASSED (spread still profitable)")
        
        # STEP 2: Check balance and get available amount (DYNAMIC POSITION SIZING)
        logger.info(f"{exchange_marker} [{exchange_id.upper()}]    💰 Checking balance sufficiency...")
        balance_ok, available_amount = await self._check_balance_sufficient(
            exchange_id, opportunity.buy_pair, opportunity.sell_pair, opportunity.trade_size_usd
        )
        
        if not balance_ok:
            logger.warning(f"{exchange_marker} [{exchange_id.upper()}]    ❌ EXECUTION BLOCKED: Insufficient balance")
            logger.warning(f"{exchange_marker} [{exchange_id.upper()}]       Reason: Need ${opportunity.trade_size_usd * 1.1:.2f} in quote currency for buy")
            logger.warning(f"{exchange_marker} [{exchange_id.upper()}]       This trade requires sufficient balance to execute both sides")
            return TradeExecution(
                exchange=exchange_id,
                opportunity=opportunity,
                buy_order_id=None,
                sell_order_id=None,
                actual_buy_price=0,
                actual_sell_price=0,
                actual_profit_usd=0,
                execution_time_seconds=0,
                status='failed'
            )
        
        logger.info(f"{exchange_marker} [{exchange_id.upper()}]    ✅ Balance check: PASSED (${available_amount:.2f} available)")
        
        logger.info(f"{exchange_marker} [{exchange_id.upper()}]    ✅ ALL PRE-FLIGHT CHECKS PASSED - PROCEEDING WITH TRADE")
        
        start_time = time.time()
        buy_order_id = None
        sell_order_id = None
        actual_buy_price = opportunity.buy_price
        actual_sell_price = opportunity.sell_price
        status = 'failed'
        execution_time = 0.0
        
        try:
            # Calculate trade size - DYNAMIC based on available balance
            # Use available amount, but respect min/max limits
            if self.dynamic_position_sizing:
                # Scale position size with opportunity score
                # Better opportunity = larger position (up to max)
                score_multiplier = min(2.0, opportunity.opportunity_score / 10.0)  # Max 2x
                desired_size = self.min_position_size_usd * (1 + score_multiplier)
                desired_size = min(self.max_position_size_usd, max(self.min_position_size_usd, desired_size))
                
                # 🔵 IMPROVEMENT: Dynamic position sizing based on spread quality
                spread_quality = opportunity.raw_spread_percent / (self.min_profit_threshold * 100)
                if spread_quality > 3.0:  # 3x minimum spread
                    position_multiplier = 1.0  # Full size
                elif spread_quality > 2.0:  # 2x minimum spread
                    position_multiplier = 0.8  # 80% size
                else:
                    position_multiplier = 0.6  # 60% size
                
                # Apply multiplier to desired size
                desired_size = desired_size * position_multiplier
                desired_size = min(self.max_position_size_usd, max(self.min_position_size_usd, desired_size))
                
                # Use available amount, but don't exceed desired size
                trade_size = min(available_amount, desired_size)
                
                logger.info(f"   📊 Spread quality: {spread_quality:.2f}x → Position multiplier: {position_multiplier:.1f}x → Trade size: ${trade_size:.2f}")
                
                # Ensure we meet minimum size - allow smaller trades if balance is low
                min_required = max(self.min_position_size_usd * 0.2, 5.0)  # At least $5 or 20% of minimum
                if trade_size < min_required:
                    logger.warning(f"{exchange_marker} [{exchange_id.upper()}]    ⚠️ Available amount ${trade_size:.2f} < minimum ${min_required:.2f}")
                    # Still proceed if we have at least $5
                    if trade_size >= 5.0:
                        logger.info(f"{exchange_marker} [{exchange_id.upper()}]    💡 Using smaller trade size: ${trade_size:.2f} (minimum $5.00)")
                    else:
                        logger.warning(f"{exchange_marker} [{exchange_id.upper()}]    ❌ Trade size too small (${trade_size:.2f} < $5.00), skipping")
                        return TradeExecution(
                            exchange=exchange_id,
                            opportunity=opportunity,
                            buy_order_id=None,
                            sell_order_id=None,
                            actual_buy_price=0,
                            actual_sell_price=0,
                            actual_profit_usd=0,
                            execution_time_seconds=0,
                            status='failed'
                        )
                
                logger.info(f"   📊 Dynamic sizing: Available ${available_amount:.2f}, Score {opportunity.opportunity_score:.2f} → ${trade_size:.2f} position")
            else:
                # Fixed sizing, but use available amount if less
                trade_size = min(available_amount, opportunity.trade_size_usd)
                if trade_size < opportunity.trade_size_usd:
                    logger.info(f"   💡 Adjusted trade size: ${trade_size:.2f} (available) vs ${opportunity.trade_size_usd:.2f} (desired)")
                else:
                    logger.info(f"   📊 Fixed sizing: ${trade_size:.2f} position")
            
            base_amount = trade_size / opportunity.buy_price
            logger.info(f"   💵 Trade size: ${trade_size:.2f} → {base_amount:.6f} {opportunity.base_crypto}")
            
            # Get calculator for fees
            # 🔵 Use Coinbase calculator for Coinbase, 🟢 Gemini calculator for Gemini
            calculator = self.coinbase_calculator if exchange_id == 'coinbase' else self.gemini_calculator
            
            # 🔵 IMPROVEMENT: Better order price adjustments based on spread width
            spread_width = opportunity.raw_spread_percent
            if spread_width > 2.0:  # Wide spread (>2%)
                price_buffer = 1.002  # 0.2% above market (more aggressive for wide spreads)
            else:
                price_buffer = 1.001  # 0.1% above market (standard)
            
            # Place limit buy order (maker fee) - use exchange manager
            buy_price_limit = opportunity.buy_price * price_buffer
            logger.info(f"{exchange_marker} [{exchange_id.upper()}]    📝 ATTEMPTING TO PLACE BUY ORDER...")
            logger.info(f"{exchange_marker} [{exchange_id.upper()}]       Pair: {opportunity.buy_pair}")
            logger.info(f"{exchange_marker} [{exchange_id.upper()}]       Amount: {base_amount:.6f} {opportunity.base_crypto}")
            logger.info(f"{exchange_marker} [{exchange_id.upper()}]       Price: ${buy_price_limit:.6f} (target: ${opportunity.buy_price:.6f})")
            logger.info(f"{exchange_marker} [{exchange_id.upper()}]       Fee type: Maker (lower fee)")
            logger.debug(f"{exchange_marker} [{exchange_id.upper()}]       Creating buy order - amount={base_amount:.6f}, price=${buy_price_limit:.6f}")
            
            try:
                buy_order = await self.exchange_manager.create_order(
                    exchange_id=exchange_id,  # CRITICAL: Pass exchange_id explicitly
                    symbol=opportunity.buy_pair,
                    order_type='limit',
                    side='buy',
                    amount=base_amount,
                    price=buy_price_limit
                )
                logger.debug(f"{exchange_marker} [{exchange_id.upper()}]       Buy order response = {buy_order}")
                
                buy_order_id = buy_order.get('id') if buy_order else None
                if buy_order_id:
                    logger.info(f"{exchange_marker} [{exchange_id.upper()}]    ✅✅✅ BUY ORDER PLACED SUCCESSFULLY: Order ID: {buy_order_id}")
                else:
                    logger.error(f"{exchange_marker} [{exchange_id.upper()}]    ❌❌❌ BUY ORDER FAILED: No order ID returned! Response: {buy_order}")
                    raise ValueError(f"Buy order creation returned no ID: {buy_order}")
            except Exception as e:
                logger.error(f"{exchange_marker} [{exchange_id.upper()}]    ❌❌❌ FAILED TO PLACE BUY ORDER: {type(e).__name__}: {e}")
                import traceback
                logger.error(f"{exchange_marker} [{exchange_id.upper()}]    Traceback: {traceback.format_exc()}")
                raise
            
            # Wait for fill with price chasing
            buy_order_status, actual_buy_price = await self._wait_for_order_fill_with_chase(
                exchange_id=exchange_id,
                order_id=buy_order_id,
                symbol=opportunity.buy_pair,
                side='buy',
                original_price=buy_price_limit,
                max_wait=self.max_order_wait_seconds
            )
            
            if not buy_order_status or buy_order_status.get('status') not in ['closed', 'filled']:
                # MARKET ORDER FALLBACK for time-sensitive opportunities
                if self.market_order_fallback_enabled and opportunity.raw_spread_percent >= self.market_order_threshold * 100:
                    logger.warning(f"   ⚠️ Limit order not filled - using market order fallback")
                    logger.info(f"   ⚡ REASON: Spread {opportunity.raw_spread_percent:.3f}% > threshold {self.market_order_threshold*100:.1f}%")
                    logger.info(f"   ⚡ ACTION: Switching to market order to capture opportunity")
                    logger.info(f"   ⚠️ Note: Market orders use taker fee (higher), but ensure fill")
                    try:
                        # Cancel limit order
                        await self.exchange_manager.cancel_order(exchange_id, buy_order_id, opportunity.buy_pair)
                    except:
                        pass
                    
                    # Place market order (taker fee, but fills immediately)
                    try:
                        market_order = await self.exchange_manager.create_order(
                            exchange_id=exchange_id,
                            symbol=opportunity.buy_pair,
                            order_type='market',
                            side='buy',
                            amount=base_amount
                        )
                        buy_order_id = market_order.get('id')
                        await asyncio.sleep(1)  # Wait for fill
                        buy_order_status = await self.exchange_manager.fetch_order(exchange_id, buy_order_id, opportunity.buy_pair)
                        if buy_order_status.get('status') in ['closed', 'filled']:
                            actual_buy_price = buy_order_status.get('average') or buy_order_status.get('price') or buy_order_status.get('filled', 0) / max(buy_order_status.get('amount', 1), 0.000001)
                            logger.info(f"   ✅ Market buy filled @ ${actual_buy_price:.6f}")
                            # Use taker fee for market orders
                            calculator = self.coinbase_calculator if exchange_id == 'coinbase' else self.gemini_calculator
                            # Note: We'll use taker fee in profit calculation
                        else:
                            logger.warning(f"   ⚠️ Market order also failed")
                    except Exception as e:
                        logger.warning(f"   ⚠️ Market order fallback failed: {e}")
                        try:
                            await self.exchange_manager.cancel_order(exchange_id, buy_order_id, opportunity.buy_pair)
                        except:
                            pass
                else:
                    logger.warning(f"   ⚠️ Buy order not filled - canceling")
                    try:
                        await self.exchange_manager.cancel_order(exchange_id, buy_order_id, opportunity.buy_pair)
                    except:
                        pass
                # Check if we got partial fill
                if buy_order_status:
                    filled = buy_order_status.get('filled', 0)
                    if filled > 0:
                        base_amount = filled  # Use partial fill
                        logger.info(f"   ⚠️ Using partial fill: {filled:.6f}")
                    else:
                        status = 'failed'
                        execution_time = time.time() - start_time
                        return TradeExecution(
                            exchange=exchange_id,
                            opportunity=opportunity,
                            buy_order_id=buy_order_id,
                            sell_order_id=None,
                            actual_buy_price=actual_buy_price,
                            actual_sell_price=0,
                            actual_profit_usd=0,
                            execution_time_seconds=execution_time,
                            status=status
                        )
            else:
                # Get actual filled amount
                filled = buy_order_status.get('filled', base_amount)
                if filled < base_amount * 0.99:
                    base_amount = filled  # Adjust for partial fill
                    logger.info(f"   ⚠️ Buy partial fill: {filled:.6f} (using this amount)")
                logger.info(f"{exchange_marker} [{exchange_id.upper()}]    ✅ Buy order filled @ ${actual_buy_price:.6f}")
            
            # ====================================================================
            # 🔵 COINBASE / 🟢 GEMINI: Wait for balance to update after buy
            # ====================================================================
            # CRITICAL: Exchange balance may not update immediately after order fill
            # We need to verify we actually have the crypto before selling
            logger.info(f"{exchange_marker} [{exchange_id.upper()}]    Verifying balance after buy...")
            max_balance_wait = 10  # Wait up to 10 seconds for balance to update
            balance_check_interval = 0.5  # Check every 0.5 seconds
            balance_verified = False
            actual_available_amount = 0
            
            for attempt in range(int(max_balance_wait / balance_check_interval)):
                await asyncio.sleep(balance_check_interval)
                try:
                    # 🔵 COINBASE / 🟢 GEMINI: Fetch fresh balance
                    balance = await self.exchange_manager.fetch_balance(exchange_id)
                    
                    # Check available amount of base crypto
                    base_crypto = opportunity.base_crypto
                    if base_crypto in balance:
                        available = balance[base_crypto].get('free', 0) or balance[base_crypto].get('available', 0) or 0
                        if isinstance(available, str):
                            available = float(available)
                        actual_available_amount = available
                        
                        # We need at least 95% of what we bought (account for fees/precision)
                        if actual_available_amount >= base_amount * 0.95:
                            balance_verified = True
                            logger.info(f"{exchange_marker} [{exchange_id.upper()}]    ✅ Balance verified: {actual_available_amount:.6f} {base_crypto} available")
                            break
                        else:
                            logger.debug(f"{exchange_marker} [{exchange_id.upper()}]    Balance not ready: {actual_available_amount:.6f} < {base_amount * 0.95:.6f} (attempt {attempt + 1})")
                    else:
                        logger.debug(f"{exchange_marker} [{exchange_id.upper()}]    {base_crypto} not in balance yet (attempt {attempt + 1})")
                except Exception as e:
                    logger.debug(f"{exchange_marker} [{exchange_id.upper()}]    Balance check error: {e}")
            
            if not balance_verified:
                logger.warning(f"{exchange_marker} [{exchange_id.upper()}]    ⚠️ Balance not updated after {max_balance_wait}s")
                logger.warning(f"{exchange_marker} [{exchange_id.upper()}]    Available: {actual_available_amount:.6f} {base_crypto}, Needed: {base_amount:.6f}")
                logger.warning(f"{exchange_marker} [{exchange_id.upper()}]    Proceeding with sell order anyway (may fail if balance truly insufficient)")
            else:
                # Use actual available amount (may be slightly less due to fees)
                if actual_available_amount < base_amount:
                    logger.info(f"{exchange_marker} [{exchange_id.upper()}]    Adjusting sell amount: {base_amount:.6f} → {actual_available_amount:.6f} (fees/precision)")
                    base_amount = actual_available_amount
            
            # Place limit sell order (maker fee) - use exchange manager
            sell_price_limit = opportunity.sell_price * 0.999  # Slightly below to ensure fill
            # 🔵 COINBASE / 🟢 GEMINI: Place sell order with comprehensive logging
            logger.info(f"{exchange_marker} [{exchange_id.upper()}]    📝 ATTEMPTING TO PLACE SELL ORDER...")
            logger.info(f"{exchange_marker} [{exchange_id.upper()}]       Pair: {opportunity.sell_pair}")
            logger.info(f"{exchange_marker} [{exchange_id.upper()}]       Amount: {base_amount:.6f} {opportunity.base_crypto}")
            logger.info(f"{exchange_marker} [{exchange_id.upper()}]       Price: ${sell_price_limit:.6f} (target: ${opportunity.sell_price:.6f})")
            logger.info(f"{exchange_marker} [{exchange_id.upper()}]       Fee type: Maker (lower fee)")
            logger.debug(f"{exchange_marker} [{exchange_id.upper()}]       Creating sell order - amount={base_amount:.6f}, price=${sell_price_limit:.6f}")
            
            try:
                sell_order = await self.exchange_manager.create_order(
                    exchange_id=exchange_id,  # CRITICAL: Pass exchange_id explicitly
                    symbol=opportunity.sell_pair,
                    order_type='limit',
                    side='sell',
                    amount=base_amount,
                    price=sell_price_limit
                )
                logger.debug(f"{exchange_marker} [{exchange_id.upper()}]       Sell order response = {sell_order}")
                
                sell_order_id = sell_order.get('id') if sell_order else None
                if sell_order_id:
                    logger.info(f"{exchange_marker} [{exchange_id.upper()}]    ✅✅✅ SELL ORDER PLACED SUCCESSFULLY: Order ID: {sell_order_id}")
                else:
                    logger.error(f"{exchange_marker} [{exchange_id.upper()}]    ❌❌❌ SELL ORDER FAILED: No order ID returned! Response: {sell_order}")
                    raise ValueError(f"Sell order creation returned no ID: {sell_order}")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"{exchange_marker} [{exchange_id.upper()}]    ❌❌❌ FAILED TO PLACE SELL ORDER: {type(e).__name__}: {error_msg}")
                import traceback
                logger.error(f"{exchange_marker} [{exchange_id.upper()}]    Traceback: {traceback.format_exc()}")
                
                # 🔵 COINBASE / 🟢 GEMINI: Check balance again for diagnostics
                if "insufficient" in error_msg.lower() or "fund" in error_msg.lower():
                    try:
                        balance = await self.exchange_manager.fetch_balance(exchange_id)
                        base_crypto = opportunity.base_crypto
                        if base_crypto in balance:
                            available = balance[base_crypto].get('free', 0) or balance[base_crypto].get('available', 0) or 0
                            if isinstance(available, str):
                                available = float(available)
                            logger.error(f"   {exchange_marker} [{exchange_id.upper()}] Current {base_crypto} balance: {available:.6f}")
                            logger.error(f"   {exchange_marker} [{exchange_id.upper()}] Needed: {base_amount:.6f}")
                            logger.error(f"   {exchange_marker} [{exchange_id.upper()}] Shortfall: {base_amount - available:.6f}")
                        else:
                            logger.error(f"   {exchange_marker} [{exchange_id.upper()}] {base_crypto} not found in balance!")
                    except Exception as balance_error:
                        logger.error(f"   {exchange_marker} [{exchange_id.upper()}] Could not check balance: {balance_error}")
                
                raise
            
            # Wait for fill with price chasing
            sell_order_status, actual_sell_price = await self._wait_for_order_fill_with_chase(
                exchange_id=exchange_id,
                order_id=sell_order_id,
                symbol=opportunity.sell_pair,
                side='sell',
                original_price=sell_price_limit,
                max_wait=self.max_order_wait_seconds
            )
            
            if not sell_order_status or sell_order_status.get('status') not in ['closed', 'filled']:
                logger.warning(f"   ⚠️ Sell order not filled - canceling")
                try:
                    await self.exchange_manager.cancel_order(exchange_id, sell_order_id, opportunity.sell_pair)
                except:
                    pass
                # We have crypto from buy, but couldn't sell - mark as partial
                status = 'partial'
            else:
                logger.info(f"{exchange_marker} [{exchange_id.upper()}]    ✅ Sell order filled @ ${actual_sell_price:.6f}")
            
            # Calculate actual profit
            if buy_order_status and buy_order_status.get('status') in ['closed', 'filled'] and \
               sell_order_status and sell_order_status.get('status') in ['closed', 'filled']:
                
                # Check for excessive slippage
                buy_slippage = abs(actual_buy_price - opportunity.buy_price) / opportunity.buy_price
                sell_slippage = abs(actual_sell_price - opportunity.sell_price) / opportunity.sell_price
                total_slippage = buy_slippage + sell_slippage
                
                if total_slippage > self.max_slippage_percent:
                    logger.warning(f"   ⚠️ Excessive slippage: {total_slippage*100:.2f}% > {self.max_slippage_percent*100:.2f}%")
                    status = 'partial'
                    actual_profit_usd = -opportunity.trade_size_usd * 0.01  # Estimate loss due to slippage
                else:
                    actual_profit_usd = (actual_sell_price - actual_buy_price) * base_amount - (
                        opportunity.trade_size_usd * (calculator.maker_fee + calculator.maker_fee)
                    )
                    status = 'success' if actual_profit_usd > 0 else 'partial'
            else:
                # Partial fill - calculate what we can
                if buy_order_status and buy_order_status.get('status') in ['closed', 'filled']:
                    # We have crypto but couldn't sell - estimate loss
                    actual_profit_usd = -opportunity.trade_size_usd * 0.01  # Estimate 1% loss
                    status = 'partial'
                else:
                    # Buy order didn't fill either
                    actual_profit_usd = 0.0
                    status = 'failed'
            
            # 🔵 IMPROVEMENT: Track failed pairs (add to cache for 5 minute cooldown)
            pair_key = f"{opportunity.buy_pair}/{opportunity.sell_pair}"
            if status in ['failed', 'partial']:
                self.failed_pairs_cache[pair_key] = time.time()
                logger.debug(f"   🔵 Added {pair_key} to failed pairs cache (cooldown: 5 minutes)")
            
            execution_time = time.time() - start_time
            self.execution_latency_ms = execution_time * 1000  # Update latency tracking
            
            # LOG FINAL RESULT WITH EXPLANATION
            logger.info("")
            logger.info(f"   📊 TRADE EXECUTION RESULT:")
            if status == 'success':
                logger.info(f"   ✅ STATUS: SUCCESS")
                logger.info(f"      ✅ REASON: Both orders filled successfully")
                logger.info(f"      ✅ Buy: ${actual_buy_price:.6f} (expected: ${opportunity.buy_price:.6f})")
                logger.info(f"      ✅ Sell: ${actual_sell_price:.6f} (expected: ${opportunity.sell_price:.6f})")
                logger.info(f"      ✅ Actual profit: ${actual_profit_usd:.2f} (expected: ${opportunity.expected_profit_usd:.2f})")
                logger.info(f"      ✅ Execution time: {execution_time:.2f}s")
            elif status == 'partial':
                logger.warning(f"   ⚠️ STATUS: PARTIAL")
                if buy_order_status and buy_order_status.get('status') in ['closed', 'filled']:
                    if not sell_order_status or sell_order_status.get('status') not in ['closed', 'filled']:
                        logger.warning(f"      ⚠️ REASON: Buy filled but sell did not fill")
                        logger.warning(f"      ⚠️ ACTION: Crypto acquired but couldn't sell - may need manual sell")
                    else:
                        logger.warning(f"      ⚠️ REASON: Excessive slippage detected")
                        logger.warning(f"      ⚠️ ACTION: Spread changed during execution")
                else:
                    logger.warning(f"      ⚠️ REASON: Partial fill or order timeout")
                logger.warning(f"      ⚠️ Actual profit: ${actual_profit_usd:.2f}")
            else:
                logger.error(f"   ❌ STATUS: FAILED")
                if not buy_order_status:
                    logger.error(f"      ❌ REASON: Buy order did not fill")
                    logger.error(f"      ❌ ACTION: No trade executed - opportunity may have disappeared")
                else:
                    logger.error(f"      ❌ REASON: Order execution failed")
                logger.error(f"      ❌ Actual profit: ${actual_profit_usd:.2f}")
            logger.info("")
            
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
        
        # Update session loss (for circuit breaker)
        self.session_loss += actual_profit_usd if actual_profit_usd < 0 else 0
        
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
            
            # Learn from failure: Only raise threshold if actual execution failures (not opportunity disappeared)
            # Don't count "opportunity disappeared" as a failure - that's normal!
            if status == 'failed' and 'disappeared' not in str(opportunity).lower():
                failure_count = sum(1 for h in self.trade_history.get(pair_key, []) if h < 0)
                if failure_count >= 5 and failure_count / max(len(self.trade_history[pair_key]), 1) > 0.5:
                    # Only raise threshold if >50% failure rate over last 10 trades
                    self.pair_thresholds[pair_key] = self.pair_thresholds[pair_key] * 1.2
                    logger.warning(f"   ⚠️ Raised threshold for {pair_key} to {self.pair_thresholds[pair_key]*100:.3f}% (failure rate: {failure_count/len(self.trade_history[pair_key])*100:.1f}%)")
            
            # Blacklist only if consistently failing (not just low opportunity frequency)
            if status == 'failed' and 'disappeared' not in str(opportunity).lower():
                failure_count = sum(1 for h in self.trade_history.get(pair_key, []) if h < 0)
                if failure_count >= 7 and failure_count / max(len(self.trade_history[pair_key]), 1) > 0.7:
                    # Only blacklist if >70% failure rate over 10+ trades
                    self.blacklisted_pairs.add(pair_key)
                    logger.warning(f"   ⚠️ Blacklisted {pair_key} due to consistent failures (failure rate: {failure_count/len(self.trade_history[pair_key])*100:.1f}%)")
        
        return execution
    
    async def run_trading_loop(self, scan_interval_seconds: int = 60):
        """
        Main trading loop - continuously scans and trades
        EXECUTES MULTIPLE OPPORTUNITIES CONCURRENTLY
        """
        logger.info("=" * 80)
        logger.info("🚀 STARTING TRADING LOOP")
        logger.info("=" * 80)
        logger.info(f"   Scan interval: {scan_interval_seconds}s")
        logger.info(f"   Min profit threshold: {self.min_profit_threshold * 100:.2f}%")
        logger.info(f"   Position size: ${self.min_position_size_usd:.2f}-${self.max_position_size_usd:.2f}")
        logger.info(f"   Max concurrent trades: {self.max_concurrent_trades_per_exchange} per exchange")
        logger.info(f"   Market order fallback: {'Enabled' if self.market_order_fallback_enabled else 'Disabled'}")
        
        while True:
            try:
                # IMMEDIATE EXECUTION MODE: Scan and execute simultaneously
                logger.info("")
                logger.info("🔍 STARTING NEW SCAN CYCLE (IMMEDIATE EXECUTION MODE)")
                logger.info("")
                logger.info("⚡ MODE: Trades execute IMMEDIATELY when found (no waiting for full scan)")
                logger.info(f"   Minimum profit threshold: {self.min_profit_threshold * 100:.2f}%")
                logger.info(f"   Max concurrent trades per exchange: {self.max_concurrent_trades_per_exchange}")
                logger.info("")
                
                # Run both exchanges concurrently with immediate execution
                coinbase_task = asyncio.create_task(
                    self.scan_and_execute_immediately('coinbase', max_cryptos=200)
                )
                gemini_task = asyncio.create_task(
                    self.scan_and_execute_immediately('gemini', max_cryptos=200)
                )
                
                # Wait for both to complete
                coinbase_results, gemini_results = await asyncio.gather(
                    coinbase_task, gemini_task, return_exceptions=True
                )
                
                # Handle results
                if isinstance(coinbase_results, Exception):
                    logger.error(f"❌ Coinbase scan/execute error: {coinbase_results}")
                    coinbase_results = {}
                if isinstance(gemini_results, Exception):
                    logger.error(f"❌ Gemini scan/execute error: {gemini_results}")
                    gemini_results = {}
                
                # SUMMARY
                logger.info("")
                logger.info("=" * 80)
                logger.info("📊 CYCLE SUMMARY")
                logger.info("=" * 80)
                logger.info(f"   ✅ COINBASE:")
                logger.info(f"      Opportunities found: {coinbase_results.get('opportunities_found', 0)}")
                logger.info(f"      Trades executed: {coinbase_results.get('trades_executed', 0)}")
                logger.info(f"      Trades skipped: {coinbase_results.get('trades_skipped', 0)}")
                logger.info(f"")
                logger.info(f"   ✅ GEMINI:")
                logger.info(f"      Opportunities found: {gemini_results.get('opportunities_found', 0)}")
                logger.info(f"      Trades executed: {gemini_results.get('trades_executed', 0)}")
                logger.info(f"      Trades skipped: {gemini_results.get('trades_skipped', 0)}")
                logger.info(f"")
                logger.info(f"   📈 TOTAL:")
                total_found = coinbase_results.get('opportunities_found', 0) + gemini_results.get('opportunities_found', 0)
                total_executed = coinbase_results.get('trades_executed', 0) + gemini_results.get('trades_executed', 0)
                logger.info(f"      Opportunities found: {total_found}")
                logger.info(f"      Trades executed: {total_executed}")
                logger.info("=" * 80)
                logger.info("")
                
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
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 TRADING STATISTICS SUMMARY")
        logger.info("=" * 80)
        
        total_opportunities = 0
        total_trades = 0
        total_profit = 0.0
        
        for exchange_id in ['coinbase', 'gemini']:
            stats = self.stats[exchange_id]
            total_opportunities += stats['opportunities_found']
            total_trades += stats['trades_executed']
            total_profit += stats['total_profit_usd']
            
            success_rate = (stats['successful_trades'] / max(stats['trades_executed'], 1)) * 100
            
            logger.info(f"\n   📈 {exchange_id.upper()}:")
            logger.info(f"      Opportunities found: {stats['opportunities_found']}")
            logger.info(f"      Trades executed: {stats['trades_executed']}")
            logger.info(f"      ✅ Successful: {stats['successful_trades']} ({success_rate:.1f}%)")
            logger.info(f"      ❌ Failed: {stats['failed_trades']}")
            logger.info(f"      💰 Total profit: ${stats['total_profit_usd']:.2f}")
        
        logger.info(f"\n   🌐 TOTAL:")
        logger.info(f"      Opportunities: {total_opportunities}")
        logger.info(f"      Trades: {total_trades}")
        logger.info(f"      💰 Profit: ${total_profit:.2f}")
        logger.info(f"      🚫 Blacklisted pairs: {len(self.blacklisted_pairs)}")
        logger.info("=" * 80)
        logger.info("")


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

