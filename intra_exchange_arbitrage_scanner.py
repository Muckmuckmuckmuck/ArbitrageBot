#!/usr/bin/env python3
"""
Intra-Exchange Arbitrage Scanner
Scans 1,000+ cryptos on Coinbase and Gemini for USD/USDC arbitrage opportunities
Ranks by profitability after fees and slippage
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager
from coinbase_gemini_config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ArbitrageOpportunity:
    """Represents an intra-exchange arbitrage opportunity"""
    exchange: str
    crypto: str
    usd_pair: str
    usdc_pair: str
    usd_price: float
    usdc_price: float
    raw_spread_percent: float
    maker_fee: float
    taker_fee: float
    estimated_slippage: float
    net_profit_percent: float
    volume_usd: float = 0.0
    order_book_depth_usd: float = 0.0
    order_book_depth_usdc: float = 0.0
    volatility_24h: float = 0.0
    arb_score: float = 0.0
    rank: int = 0
    best_case_profit_percent: float = 0.0  # Profit with maker fees on both sides
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'exchange': self.exchange,
            'crypto': self.crypto,
            'usd_pair': self.usd_pair,
            'usdc_pair': self.usdc_pair,
            'usd_price': self.usd_price,
            'usdc_price': self.usdc_price,
            'raw_spread_percent': self.raw_spread_percent,
            'maker_fee': self.maker_fee,
            'taker_fee': self.taker_fee,
            'estimated_slippage': self.estimated_slippage,
            'net_profit_percent': self.net_profit_percent,
            'volume_usd': self.volume_usd,
            'order_book_depth_usd': self.order_book_depth_usd,
            'order_book_depth_usdc': self.order_book_depth_usdc,
            'volatility_24h': self.volatility_24h,
            'arb_score': self.arb_score,
            'rank': self.rank,
            'best_case_profit_percent': self.best_case_profit_percent
        }


class IntraExchangeArbitrageScanner:
    """Scans for intra-exchange arbitrage opportunities"""
    
    def __init__(self):
        self.exchange_manager = CoinbaseGeminiExchangeManager()
        self.opportunities: List[ArbitrageOpportunity] = []
        self.scan_stats = {
            'total_pairs_scanned': 0,
            'opportunities_found': 0,
            'coinbase_opportunities': 0,
            'gemini_opportunities': 0,
            'scan_duration_seconds': 0.0
        }
        
    async def initialize(self):
        """Initialize exchanges"""
        await self.exchange_manager.initialize()
        logger.info("✅ Exchanges initialized")
    
    async def get_all_markets(self, exchange_id: str) -> Dict:
        """Get all available markets for an exchange"""
        exchange = self.exchange_manager.get_exchange(exchange_id)
        return exchange.markets
    
    async def get_ticker(self, exchange_id: str, symbol: str) -> Optional[Dict]:
        """Get ticker data for a symbol"""
        try:
            exchange = self.exchange_manager.get_exchange(exchange_id)
            ticker = exchange.fetch_ticker(symbol)
            
            # Handle async/sync response
            if hasattr(ticker, '__await__'):
                ticker = await ticker
            
            return ticker
        except Exception as e:
            # Don't log every error to avoid spam
            return None
    
    async def get_order_book(self, exchange_id: str, symbol: str, limit: int = 20) -> Optional[Dict]:
        """Get order book for a symbol"""
        try:
            exchange = self.exchange_manager.get_exchange(exchange_id)
            orderbook = exchange.fetch_order_book(symbol, limit)
            
            # Handle async/sync response
            if hasattr(orderbook, '__await__'):
                orderbook = await orderbook
            
            return orderbook
        except Exception as e:
            return None
    
    def calculate_slippage(self, orderbook: Optional[Dict], trade_size_usd: float = 100.0) -> float:
        """Estimate slippage for a trade size"""
        if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
            return 0.002  # Default 0.2% slippage if no data
        
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        if not bids or not asks:
            return 0.002
        
        try:
            # Calculate average price for trade size
            total_cost = 0.0
            remaining = trade_size_usd
            best_price = float(bids[0][0]) if bids and len(bids) > 0 and bids[0] and len(bids[0]) > 0 else 0.0
            
            if best_price == 0:
                return 0.002
            
            # For buying (using asks)
            for ask in asks:
                if not ask or len(ask) < 2:
                    continue
                try:
                    price = float(ask[0])
                    volume = float(ask[1])
                    cost = min(remaining, volume * price)
                    total_cost += cost
                    remaining -= cost
                    if remaining <= 0:
                        break
                except (ValueError, TypeError, IndexError):
                    continue
            
            if total_cost == 0:
                return 0.002
            
            avg_price = total_cost / trade_size_usd
            slippage = (avg_price - best_price) / best_price if best_price > 0 else 0.002
            
            return max(0.0, min(0.01, slippage))  # Cap at 1%
        except Exception:
            return 0.002  # Default on any error
    
    def calculate_order_book_depth(self, orderbook: Optional[Dict], side: str = 'both') -> float:
        """Calculate order book depth in USD"""
        if not orderbook:
            return 0.0
        
        depth = 0.0
        
        if side in ['both', 'bids']:
            for bid in orderbook.get('bids', [])[:10]:  # Top 10 levels
                depth += bid[0] * bid[1]  # price * volume
        
        if side in ['both', 'asks']:
            for ask in orderbook.get('asks', [])[:10]:  # Top 10 levels
                depth += ask[0] * ask[1]  # price * volume
        
        return depth / 2 if side == 'both' else depth
    
    def calculate_volatility(self, ticker: Optional[Dict]) -> float:
        """Calculate 24h volatility from ticker"""
        if not ticker:
            return 0.0
        
        high = ticker.get('high') or ticker.get('high24h') or 0
        low = ticker.get('low') or ticker.get('low24h') or 0
        last = ticker.get('last') or ticker.get('close') or ticker.get('bid') or 0
        
        # Handle None values
        if high is None:
            high = 0
        if low is None:
            low = 0
        if last is None:
            last = 0
        
        # Convert to float
        try:
            high = float(high)
            low = float(low)
            last = float(last)
        except (ValueError, TypeError):
            return 0.0
        
        if last == 0:
            return 0.0
        
        # Simple volatility estimate: (high - low) / last
        if high > low and high > 0 and low > 0:
            volatility = (high - low) / last
        else:
            volatility = 0.0
        
        return min(0.10, max(0.0, volatility))  # Cap at 10%, floor at 0%
    
    def calculate_arb_score(self, opp: ArbitrageOpportunity) -> float:
        """Calculate arbitrage score for ranking
        
        Formula: (Volatility × QuotePairCount) / (AvgSpread × FeeRate)
        Higher score = better opportunity
        """
        if opp.net_profit_percent <= 0:
            return 0.0
        
        # QuotePairCount = 2 (USD + USDC)
        quote_pair_count = 2.0
        
        # Average spread (use raw spread)
        avg_spread = max(0.001, abs(opp.raw_spread_percent))
        
        # Fee rate (use maker fee, assume we can get maker on one side)
        fee_rate = max(0.0001, opp.maker_fee)
        
        # Volatility (use 24h volatility or estimate from spread)
        volatility = opp.volatility_24h if opp.volatility_24h > 0 else abs(opp.raw_spread_percent) * 2
        
        # Depth asymmetry (prefer imbalanced books)
        if opp.order_book_depth_usd > 0 and opp.order_book_depth_usdc > 0:
            depth_ratio = min(opp.order_book_depth_usd, opp.order_book_depth_usdc) / max(opp.order_book_depth_usd, opp.order_book_depth_usdc)
            depth_factor = 1.0 + (1.0 - depth_ratio)  # Boost for asymmetry
        else:
            depth_factor = 1.0
        
        # Volume factor (more volume = more opportunities)
        volume_factor = min(2.0, 1.0 + (opp.volume_usd / 1000000.0))  # Boost for high volume
        
        # Calculate score
        base_score = (volatility * quote_pair_count) / (avg_spread * fee_rate)
        arb_score = base_score * depth_factor * volume_factor * opp.net_profit_percent * 100
        
        return arb_score
    
    async def scan_crypto(self, exchange_id: str, crypto: str, quote1: str = 'USD', quote2: str = 'USDC') -> Optional[ArbitrageOpportunity]:
        """Scan a single crypto for arbitrage opportunities"""
        pair1 = f'{crypto}/{quote1}'
        pair2 = f'{crypto}/{quote2}'
        
        # For logging, use standard names
        usd_pair = pair1 if quote1 == 'USD' else pair2
        usdc_pair = pair2 if quote2 in ['USDC', 'USDT'] else pair1
        
        # Check if both pairs exist
        markets = await self.get_all_markets(exchange_id)
        
        if pair1 not in markets or pair2 not in markets:
            return None
        
        # Get fees for this exchange
        from coinbase_gemini_config import EXCHANGE_FEES
        if exchange_id == 'coinbase':
            maker_fee = EXCHANGE_FEES['coinbase']['maker']
            taker_fee = EXCHANGE_FEES['coinbase']['taker']
        else:  # gemini
            maker_fee = EXCHANGE_FEES['gemini']['maker']
            taker_fee = EXCHANGE_FEES['gemini']['taker']
        
        # Get tickers
        ticker1 = await self.get_ticker(exchange_id, pair1)
        ticker2 = await self.get_ticker(exchange_id, pair2)
        
        if not ticker1 or not ticker2:
            return None
        
        price1 = ticker1.get('last') or ticker1.get('close') or ticker1.get('bid') or 0
        price2 = ticker2.get('last') or ticker2.get('close') or ticker2.get('bid') or 0
        
        # Handle None values explicitly
        if price1 is None:
            price1 = 0
        if price2 is None:
            price2 = 0
        
        # Convert to float and validate
        try:
            price1 = float(price1)
            price2 = float(price2)
        except (ValueError, TypeError):
            return None
        
        if price1 == 0 or price2 == 0:
            return None
        
        # Final safety check - ensure no None values
        if price1 is None or price2 is None:
            return None
        
        # Calculate raw spread
        try:
            if price2 > price1:
            # Buy pair1, sell pair2
            raw_spread = (price2 - price1) / price1
            direction = f'{quote1}→{quote2}'
            buy_pair = pair1
            sell_pair = pair2
        else:
            # Buy pair2, sell pair1
            raw_spread = (price1 - price2) / price2
            direction = f'{quote2}→{quote1}'
            buy_pair = pair2
            sell_pair = pair1
        except (TypeError, ValueError, ZeroDivisionError) as e:
            # If any error in comparison/calculation, skip this pair
            return None
        
        # For display, use the actual prices
        display_price1 = price1
        display_price2 = price2
        
        # Get order books for slippage calculation
        orderbook1 = await self.get_order_book(exchange_id, pair1)
        orderbook2 = await self.get_order_book(exchange_id, pair2)
        
        # Use buy and sell orderbooks
        buy_orderbook = orderbook1 if buy_pair == pair1 else orderbook2
        sell_orderbook = orderbook2 if sell_pair == pair2 else orderbook1
        
        # Calculate slippage (assume $100 trade size)
        trade_size_usd = 100.0
        buy_slippage = self.calculate_slippage(buy_orderbook, trade_size_usd)
        sell_slippage = self.calculate_slippage(sell_orderbook, trade_size_usd)
        total_slippage = buy_slippage + sell_slippage
        
        # For display (keep orderbooks for depth calculation)
        display_orderbook1 = orderbook1
        display_orderbook2 = orderbook2
        
        # Calculate net profit with different fee scenarios
        # Best case: Maker on both sides (market making)
        best_case_fees = maker_fee * 2
        best_case_profit = raw_spread - best_case_fees - total_slippage
        
        # Realistic case: Maker on one side, taker on other
        realistic_fees = maker_fee + taker_fee
        realistic_profit = raw_spread - realistic_fees - total_slippage
        
        # Worst case: Taker on both sides
        worst_case_fees = taker_fee * 2
        worst_case_profit = raw_spread - worst_case_fees - total_slippage
        
        # Use realistic case for primary calculation
        net_profit = realistic_profit
        total_fees = realistic_fees
        
        # Store all opportunities (even unprofitable) for analysis
        # But only return profitable ones for trading
        is_profitable = realistic_profit > 0
        
        # Get additional data for ranking
        # Try to get volume in any currency
        volume_usd = ticker1.get('quoteVolume', 0) or ticker1.get('volume', 0)
        if isinstance(ticker1.get('volume'), dict):
            # Try USD first, then any key
            volume_usd = ticker1.get('volume', {}).get('USD', 0) or ticker1.get('volume', {}).get(quote1, 0) or (list(ticker1.get('volume', {}).values())[0] if ticker1.get('volume', {}) else 0)
        
        if volume_usd == 0:
            volume_usd = ticker2.get('quoteVolume', 0) or ticker2.get('volume', 0)
            if isinstance(ticker2.get('volume'), dict):
                volume_usd = ticker2.get('volume', {}).get('USD', 0) or ticker2.get('volume', {}).get(quote2, 0) or (list(ticker2.get('volume', {}).values())[0] if ticker2.get('volume', {}) else 0)
        
        depth1 = self.calculate_order_book_depth(orderbook1)
        depth2 = self.calculate_order_book_depth(orderbook2)
        
        # Calculate volatility safely
        try:
            volatility = self.calculate_volatility(ticker1)
        except Exception:
            volatility = 0.0
        
        # Create opportunity
        # For display, use the actual pair names
        opp = ArbitrageOpportunity(
            exchange=exchange_id,
            crypto=crypto,
            usd_pair=pair1,  # Actual pair name
            usdc_pair=pair2,  # Actual pair name
            usd_price=display_price1,  # Price in quote1
            usdc_price=display_price2,  # Price in quote2
            raw_spread_percent=raw_spread * 100,
            maker_fee=maker_fee * 100,
            taker_fee=taker_fee * 100,
            estimated_slippage=total_slippage * 100,
            net_profit_percent=realistic_profit * 100,  # Use realistic profit
            volume_usd=volume_usd,
            order_book_depth_usd=depth1,  # Depth in quote1 currency
            order_book_depth_usdc=depth2,  # Depth in quote2 currency
            volatility_24h=volatility * 100
        )
        
        # Calculate arb score using best case (maker fees)
        # This helps identify opportunities that would work with market making
        opp.arb_score = self.calculate_arb_score(opp)
        
        # Store best case profit for analysis (market making strategy)
        opp.best_case_profit_percent = best_case_profit * 100
        
        # Only return profitable opportunities (realistic case)
        # But we log all for analysis
        if not is_profitable:
            # Check if it would be profitable with maker fees (market making strategy)
            if best_case_profit > 0:
                logger.debug(f"   💡 {crypto} ({quote1}/{quote2}): {raw_spread*100:.3f}% spread - "
                           f"NOT profitable with taker fees ({(realistic_fees*100):.3f}%), "
                           f"BUT profitable with maker fees ({(best_case_fees*100):.3f}%) = {best_case_profit*100:.3f}% profit")
            return None
        
        return opp
    
    async def scan_exchange(self, exchange_id: str, max_cryptos: int = 1000) -> List[ArbitrageOpportunity]:
        """Scan an exchange for arbitrage opportunities"""
        logger.info(f"🔍 Scanning {exchange_id} for arbitrage opportunities...")
        
        markets = await self.get_all_markets(exchange_id)
        opportunities = []
        
        # Find ALL possible arbitrage pairs for each crypto
        # A crypto can have multiple quote currencies (USD, USDC, BTC, ETH, SOL, etc.)
        # We want to find arbitrage opportunities between ANY two quote pairs for the same base crypto
        crypto_quotes = {}  # {base_crypto: [list of quote currencies]}
        
        for symbol, market_info in markets.items():
            if not market_info.get('active', True):
                continue
            
            base = market_info.get('base', '').strip()
            quote = market_info.get('quote', '').strip()
            
            # Skip invalid pairs
            if not base or not quote:
                continue
            
            # Track all quote currencies for each base crypto
            if base not in crypto_quotes:
                crypto_quotes[base] = []
            
            if quote not in crypto_quotes[base]:
                crypto_quotes[base].append(quote)
        
        # Find all cryptos with at least 2 different quote pairs (arbitrage opportunity)
        valid_cryptos = []
        for crypto, quotes in crypto_quotes.items():
            if len(quotes) >= 2:
                # Generate all possible pairs of quote currencies
                # e.g., if quotes = ['USD', 'USDC', 'BTC'], we get:
                # (USD, USDC), (USD, BTC), (USDC, BTC)
                for i in range(len(quotes)):
                    for j in range(i + 1, len(quotes)):
                        quote1 = quotes[i]
                        quote2 = quotes[j]
                        valid_cryptos.append((crypto, quote1, quote2))
        
        # Log statistics
        quote_currency_count = {}
        for quotes in crypto_quotes.values():
            for q in quotes:
                quote_currency_count[q] = quote_currency_count.get(q, 0) + 1
        
        top_quotes = sorted(quote_currency_count.items(), key=lambda x: x[1], reverse=True)[:10]
        logger.info(f"   Top quote currencies: {', '.join(f'{q}({c})' for q, c in top_quotes)}")
        logger.info(f"   Found {len(crypto_quotes)} unique cryptos")
        logger.info(f"   Found {len(valid_cryptos)} possible arbitrage pairs (crypto with 2+ quote currencies)")
        
        # Limit to max_cryptos
        valid_cryptos = valid_cryptos[:max_cryptos]
        
        # Scan each crypto
        scanned = 0
        profitable_count = 0
        unprofitable_count = 0
        profitable_list = []
        unprofitable_list = []
        total_spreads = []
        profitable_spreads = []
        unprofitable_spreads = []
        
        logger.info(f"   📊 Scanning {len(valid_cryptos)} arbitrage pair combinations...")
        logger.info(f"   (Examples: BTC/USD vs BTC/USDC, ETH/BTC vs ETH/USD, SOL/USDC vs SOL/ETH, etc.)")
        logger.info("")
        
        for crypto_info in valid_cryptos:
            crypto, quote1, quote2 = crypto_info
            scanned += 1
            self.scan_stats['total_pairs_scanned'] += 1
            
            # Log progress every 10 cryptos
            if scanned % 10 == 0:
                logger.info(f"   🔄 Progress: {scanned}/{len(valid_cryptos)} | "
                           f"✅ Profitable: {profitable_count} | "
                           f"❌ Not Profitable: {unprofitable_count}")
            
            try:
                # Log what we're scanning (every 25th to avoid spam, but show first 10)
                if scanned % 25 == 0 or scanned <= 10:
                    logger.info(f"   🔍 Scanning [{scanned:3d}/{len(valid_cryptos)}] {crypto:8s} ({quote1:6s}/{quote2:6s})...")
                
                opp = await self.scan_crypto(exchange_id, crypto, quote1, quote2)
                
                if opp:
                    opportunities.append(opp)
                    profitable_count += 1
                    profitable_list.append(crypto)
                    total_spreads.append(opp.raw_spread_percent)
                    profitable_spreads.append(opp.raw_spread_percent)
                    logger.info(f"   ✅ [{scanned:3d}/{len(valid_cryptos)}] {crypto:8s} ({quote1:6s}/{quote2:6s}): "
                               f"PROFITABLE | Spread: {opp.raw_spread_percent:6.3f}% | "
                               f"Net Profit: {opp.net_profit_percent:6.3f}% | "
                               f"Fees: {opp.maker_fee + opp.taker_fee:5.3f}% | "
                               f"Slippage: {opp.estimated_slippage:5.3f}%")
                else:
                    unprofitable_count += 1
                    unprofitable_list.append(crypto)
                    
                    # Get spread data for unprofitable ones
                    try:
                        ticker1 = await self.get_ticker(exchange_id, f'{crypto}/{quote1}')
                        ticker2 = await self.get_ticker(exchange_id, f'{crypto}/{quote2}')
                        if ticker1 and ticker2:
                            price1 = ticker1.get('last') or ticker1.get('close') or ticker1.get('bid') or 0
                            price2 = ticker2.get('last') or ticker2.get('close') or ticker2.get('bid') or 0
                            
                            # Handle None values
                            if price1 is None:
                                price1 = 0
                            if price2 is None:
                                price2 = 0
                            
                            try:
                                price1 = float(price1)
                                price2 = float(price2)
                            except (ValueError, TypeError):
                                continue
                            
                            if price1 > 0 and price2 > 0:
                                spread = abs(price2 - price1) / min(price1, price2) * 100
                                total_spreads.append(spread)
                                unprofitable_spreads.append(spread)
                                
                                # Calculate why it's not profitable
                                if exchange_id == 'coinbase':
                                    total_fees_pct = (EXCHANGE_FEES['coinbase']['maker'] + EXCHANGE_FEES['coinbase']['taker']) * 100
                                else:
                                    total_fees_pct = (EXCHANGE_FEES['gemini']['maker'] + EXCHANGE_FEES['gemini']['taker']) * 100
                                
                                required_spread = total_fees_pct + 0.2  # 0.2% slippage
                                deficit = required_spread - spread
                                
                                # Log every 25th unprofitable to avoid spam, but show first 10
                                if scanned % 25 == 0 or scanned <= 10:
                                    logger.info(f"   ❌ [{scanned:3d}/{len(valid_cryptos)}] {crypto:8s} ({quote1:6s}/{quote2:6s}): "
                                               f"NOT PROFITABLE | Spread: {spread:6.3f}% | "
                                               f"Required: {required_spread:5.3f}% | "
                                               f"Deficit: {deficit:5.3f}%")
                    except Exception as ticker_error:
                        # Log ticker errors occasionally
                        if scanned % 50 == 0:
                            logger.debug(f"   ⚠️  Could not get tickers for {crypto}: {ticker_error}")
                
                # Rate limiting - smaller delay
                if scanned % 5 == 0:
                    await asyncio.sleep(0.05)
                    
            except Exception as e:
                logger.warning(f"   ⚠️  [{scanned:3d}/{len(valid_cryptos)}] Error scanning {crypto}: {str(e)[:100]}")
                unprofitable_count += 1
                unprofitable_list.append(crypto)
                continue
        
        # Detailed summary
        logger.info("")
        logger.info(f"   {'='*70}")
        logger.info(f"   📊 {exchange_id.upper()} SCAN SUMMARY")
        logger.info(f"   {'='*70}")
        logger.info(f"   Total cryptos scanned: {scanned}")
        logger.info(f"   ✅ Profitable: {profitable_count} ({profitable_count/scanned*100:.1f}%)")
        logger.info(f"   ❌ Not Profitable: {unprofitable_count} ({unprofitable_count/scanned*100:.1f}%)")
        logger.info("")
        
        if profitable_list:
            logger.info(f"   🏆 PROFITABLE CRYPTOS ({len(profitable_list)}):")
            # Show in columns for better readability
            for i in range(0, len(profitable_list), 5):
                chunk = profitable_list[i:i+5]
                logger.info(f"      {', '.join(f'{c:8s}' for c in chunk)}")
            logger.info("")
        
        if unprofitable_list and len(unprofitable_list) <= 50:  # Only show if reasonable size
            logger.info(f"   ⚠️  NOT PROFITABLE CRYPTOS (showing first 50):")
            for i in range(0, min(50, len(unprofitable_list)), 5):
                chunk = unprofitable_list[i:i+5]
                logger.info(f"      {', '.join(f'{c:8s}' for c in chunk)}")
            logger.info("")
        
        if total_spreads:
            avg_spread = sum(total_spreads) / len(total_spreads)
            max_spread = max(total_spreads)
            min_spread = min(total_spreads)
            required_spread = (maker_fee + taker_fee) * 100 + 0.2  # fees + slippage
            
            logger.info(f"   📈 SPREAD STATISTICS:")
            logger.info(f"      Average spread: {avg_spread:.3f}%")
            logger.info(f"      Maximum spread: {max_spread:.3f}%")
            logger.info(f"      Minimum spread: {min_spread:.3f}%")
            logger.info(f"      Required for profit: >{required_spread:.3f}% (fees + slippage)")
            logger.info("")
            
            if profitable_spreads:
                avg_profitable = sum(profitable_spreads) / len(profitable_spreads)
                logger.info(f"   ✅ PROFITABLE SPREADS:")
                logger.info(f"      Average: {avg_profitable:.3f}%")
                logger.info(f"      Count: {len(profitable_spreads)}")
            logger.info("")
            
            if unprofitable_spreads:
                avg_unprofitable = sum(unprofitable_spreads) / len(unprofitable_spreads)
                logger.info(f"   ❌ UNPROFITABLE SPREADS:")
                logger.info(f"      Average: {avg_unprofitable:.3f}%")
                logger.info(f"      Count: {len(unprofitable_spreads)}")
                logger.info(f"      Average deficit: {required_spread - avg_unprofitable:.3f}%")
            logger.info("")
        
        logger.info(f"   {'='*70}")
        logger.info("")
        
        return opportunities
    
    async def scan_all_exchanges(self) -> List[ArbitrageOpportunity]:
        """Scan both exchanges for arbitrage opportunities"""
        start_time = time.time()
        
        logger.info("=" * 80)
        logger.info("🚀 INTRA-EXCHANGE ARBITRAGE SCANNER")
        logger.info("=" * 80)
        logger.info(f"Scanning ALL possible arbitrage pairs on Coinbase and Gemini...")
        logger.info(f"Including: USD/USDC/USDT, BTC/ETH, SOL/AVAX, and ANY crypto-to-crypto pairs!")
        logger.info("")
        
        # Scan both exchanges sequentially (parallel causes too many API calls)
        # Start with Coinbase
        logger.info("Starting Coinbase scan...")
        coinbase_opps = await self.scan_exchange('coinbase', max_cryptos=1000)
        
        logger.info("")
        logger.info("Starting Gemini scan...")
        gemini_opps = await self.scan_exchange('gemini', max_cryptos=1000)
        
        # Note: We already handle exceptions in scan_exchange, so these should be lists
        
        all_opportunities = coinbase_opps + gemini_opps
        
        # Rank by arb score
        all_opportunities.sort(key=lambda x: x.arb_score, reverse=True)
        
        # Assign ranks
        for i, opp in enumerate(all_opportunities, 1):
            opp.rank = i
        
        self.scan_stats['opportunities_found'] = len(all_opportunities)
        self.scan_stats['coinbase_opportunities'] = len(coinbase_opps)
        self.scan_stats['gemini_opportunities'] = len(gemini_opps)
        self.scan_stats['scan_duration_seconds'] = time.time() - start_time
        
        self.opportunities = all_opportunities
        
        return all_opportunities
    
    def print_results(self):
        """Print scan results"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 FINAL SCAN RESULTS")
        logger.info("=" * 80)
        logger.info(f"Total pairs scanned: {self.scan_stats['total_pairs_scanned']}")
        logger.info(f"Total profitable opportunities: {self.scan_stats['opportunities_found']}")
        logger.info("")
        logger.info(f"📈 BY EXCHANGE:")
        logger.info(f"  ✅ Coinbase: {self.scan_stats['coinbase_opportunities']} profitable")
        logger.info(f"  ✅ Gemini: {self.scan_stats['gemini_opportunities']} profitable")
        logger.info("")
        logger.info(f"⏱️  Scan duration: {self.scan_stats['scan_duration_seconds']:.2f} seconds")
        logger.info("")
        
        # Calculate percentages
        total_scanned = self.scan_stats['total_pairs_scanned']
        if total_scanned > 0:
            profit_rate = (self.scan_stats['opportunities_found'] / total_scanned) * 100
            logger.info(f"📊 PROFITABILITY RATE: {profit_rate:.1f}% ({self.scan_stats['opportunities_found']}/{total_scanned})")
            logger.info("")
        
        if not self.opportunities:
            logger.warning("⚠️  No profitable opportunities found")
            logger.warning("")
            logger.warning("💡 RECOMMENDATIONS:")
            logger.warning("   1. Consider market making strategy (maker fees on both sides)")
            logger.warning("   2. Look for higher volatility periods")
            logger.warning("   3. Check if spreads widen during news events")
            logger.warning("   4. Consider smaller position sizes to reduce slippage")
            logger.warning("")
            return
        
        logger.info("=" * 80)
        logger.info(f"🏆 TOP {min(50, len(self.opportunities))} ARBITRAGE OPPORTUNITIES")
        logger.info("   (Ranked by Profitability Score)")
        logger.info("=" * 80)
        logger.info("")
        
        # Group by exchange
        coinbase_opps = [o for o in self.opportunities if o.exchange == 'coinbase']
        gemini_opps = [o for o in self.opportunities if o.exchange == 'gemini']
        
        if coinbase_opps:
            logger.info(f"📊 COINBASE ({len(coinbase_opps)} opportunities):")
            logger.info("")
            for opp in coinbase_opps[:25]:  # Top 25 per exchange
                logger.info(f"#{opp.rank:3d} | {opp.crypto:8s} | "
                           f"Profit: {opp.net_profit_percent:6.3f}% | "
                           f"Spread: {opp.raw_spread_percent:6.3f}% | "
                           f"Fees: {opp.maker_fee + opp.taker_fee:5.3f}% | "
                           f"Slippage: {opp.estimated_slippage:5.3f}% | "
                           f"Score: {opp.arb_score:8.2f}")
                logger.info(f"     {opp.usd_pair} = ${opp.usd_price:.6f} | "
                           f"{opp.usdc_pair} = ${opp.usdc_price:.6f}")
                logger.info(f"     Volume: ${opp.volume_usd:,.0f} | "
                           f"Depth: ${opp.order_book_depth_usd:,.0f} / ${opp.order_book_depth_usdc:,.0f} | "
                           f"Volatility: {opp.volatility_24h:.2f}%")
                logger.info("")
        
        if gemini_opps:
            logger.info(f"📊 GEMINI ({len(gemini_opps)} opportunities):")
            logger.info("")
            for opp in gemini_opps[:25]:  # Top 25 per exchange
                logger.info(f"#{opp.rank:3d} | {opp.crypto:8s} | "
                           f"Profit: {opp.net_profit_percent:6.3f}% | "
                           f"Spread: {opp.raw_spread_percent:6.3f}% | "
                           f"Fees: {opp.maker_fee + opp.taker_fee:5.3f}% | "
                           f"Slippage: {opp.estimated_slippage:5.3f}% | "
                           f"Score: {opp.arb_score:8.2f}")
                logger.info(f"     {opp.usd_pair} = ${opp.usd_price:.6f} | "
                           f"{opp.usdc_pair} = ${opp.usdc_price:.6f}")
                logger.info(f"     Volume: ${opp.volume_usd:,.0f} | "
                           f"Depth: ${opp.order_book_depth_usd:,.0f} / ${opp.order_book_depth_usdc:,.0f} | "
                           f"Volatility: {opp.volatility_24h:.2f}%")
                logger.info("")
    
    def save_results(self, filename: str = 'arbitrage_opportunities.json'):
        """Save results to JSON file"""
        results = {
            'scan_timestamp': datetime.now().isoformat(),
            'scan_stats': self.scan_stats,
            'opportunities': [opp.to_dict() for opp in self.opportunities]
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"💾 Results saved to {filename}")


async def main():
    """Main function"""
    scanner = IntraExchangeArbitrageScanner()
    
    try:
        await scanner.initialize()
        opportunities = await scanner.scan_all_exchanges()
        scanner.print_results()
        scanner.save_results()
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ SCAN COMPLETE")
        logger.info("=" * 80)
        
        if opportunities:
            logger.info(f"💡 Found {len(opportunities)} profitable opportunities!")
            logger.info(f"🎯 Top opportunity: {opportunities[0].crypto} on {opportunities[0].exchange} "
                       f"({opportunities[0].net_profit_percent:.3f}% profit)")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())

