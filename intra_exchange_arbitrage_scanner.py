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
            'rank': self.rank
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
        
        bids = orderbook['bids']
        asks = orderbook['asks']
        
        if not bids or not asks:
            return 0.002
        
        # Calculate average price for trade size
        total_cost = 0.0
        remaining = trade_size_usd
        best_price = bids[0][0] if bids else 0.0
        
        # For buying (using asks)
        for ask in asks:
            price, volume = ask[0], ask[1]
            cost = min(remaining, volume * price)
            total_cost += cost
            remaining -= cost
            if remaining <= 0:
                break
        
        if total_cost == 0:
            return 0.002
        
        avg_price = total_cost / trade_size_usd
        slippage = (avg_price - best_price) / best_price if best_price > 0 else 0.002
        
        return max(0.0, min(0.01, slippage))  # Cap at 1%
    
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
        
        high = ticker.get('high', 0)
        low = ticker.get('low', 0)
        last = ticker.get('last', ticker.get('close', 0))
        
        if last == 0:
            return 0.0
        
        # Simple volatility estimate: (high - low) / last
        volatility = (high - low) / last if high > low else 0.0
        
        return min(0.10, volatility)  # Cap at 10%
    
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
        
        price1 = ticker1.get('last', ticker1.get('close', 0))
        price2 = ticker2.get('last', ticker2.get('close', 0))
        
        if price1 == 0 or price2 == 0:
            return None
        
        # Calculate raw spread
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
        
        # For display, use standard names
        usd_price = price1 if quote1 == 'USD' else price2
        usdc_price = price2 if quote2 in ['USDC', 'USDT'] else price1
        
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
        
        # For display
        usd_orderbook = orderbook1 if quote1 == 'USD' else orderbook2
        usdc_orderbook = orderbook2 if quote2 in ['USDC', 'USDT'] else orderbook1
        
        # Calculate net profit after fees and slippage
        # We pay taker fee on one side, maker fee on the other (best case)
        total_fees = maker_fee + taker_fee
        net_profit = raw_spread - total_fees - total_slippage
        
        # Store all opportunities (even unprofitable) for analysis
        # But only return profitable ones for trading
        is_profitable = net_profit > 0
        
        # Get additional data for ranking
        volume_usd = ticker1.get('quoteVolume', 0) or ticker1.get('volume', {}).get('USD', 0) if isinstance(ticker1.get('volume'), dict) else 0
        if volume_usd == 0:
            volume_usd = ticker2.get('quoteVolume', 0) or ticker2.get('volume', {}).get('USD', 0) if isinstance(ticker2.get('volume'), dict) else 0
        
        depth_usd = self.calculate_order_book_depth(orderbook1 if quote1 == 'USD' else orderbook2)
        depth_usdc = self.calculate_order_book_depth(orderbook2 if quote2 in ['USDC', 'USDT'] else orderbook1)
        volatility = self.calculate_volatility(ticker1)
        
        # Create opportunity
        opp = ArbitrageOpportunity(
            exchange=exchange_id,
            crypto=crypto,
            usd_pair=pair1 if quote1 == 'USD' else pair2,
            usdc_pair=pair2 if quote2 in ['USDC', 'USDT'] else pair1,
            usd_price=usd_price,
            usdc_price=usdc_price,
            raw_spread_percent=raw_spread * 100,
            maker_fee=maker_fee * 100,
            taker_fee=taker_fee * 100,
            estimated_slippage=total_slippage * 100,
            net_profit_percent=net_profit * 100,
            volume_usd=volume_usd,
            order_book_depth_usd=depth_usd,
            order_book_depth_usdc=depth_usdc,
            volatility_24h=volatility * 100
        )
        
        # Calculate arb score
        opp.arb_score = self.calculate_arb_score(opp)
        
        # Only return profitable opportunities
        if not is_profitable:
            return None
        
        return opp
    
    async def scan_exchange(self, exchange_id: str, max_cryptos: int = 1000) -> List[ArbitrageOpportunity]:
        """Scan an exchange for arbitrage opportunities"""
        logger.info(f"🔍 Scanning {exchange_id} for arbitrage opportunities...")
        
        markets = await self.get_all_markets(exchange_id)
        opportunities = []
        
        # Find all cryptos that have both USD and USDC pairs
        crypto_pairs = {}
        
        for symbol, market_info in markets.items():
            if not market_info.get('active', True):
                continue
            
            base = market_info.get('base', '')
            quote = market_info.get('quote', '')
            
            # Check for USD, USDC, USDT, or other USD-pegged stablecoins
            if quote in ['USD', 'USDC', 'USDT']:
                if base not in crypto_pairs:
                    crypto_pairs[base] = {'USD': False, 'USDC': False, 'USDT': False}
                
                if quote == 'USD':
                    crypto_pairs[base]['USD'] = True
                elif quote == 'USDC':
                    crypto_pairs[base]['USDC'] = True
                elif quote == 'USDT':
                    crypto_pairs[base]['USDT'] = True
        
        # Filter to cryptos with multiple USD-pegged pairs
        # Priority: USD/USDC, then USD/USDT, then USDC/USDT
        valid_cryptos = []
        for crypto, pairs in crypto_pairs.items():
            if pairs['USD'] and pairs['USDC']:
                valid_cryptos.append((crypto, 'USD', 'USDC'))
            elif pairs['USD'] and pairs['USDT']:
                valid_cryptos.append((crypto, 'USD', 'USDT'))
            elif pairs['USDC'] and pairs['USDT']:
                valid_cryptos.append((crypto, 'USDC', 'USDT'))
        
        # Log what quote currencies are available
        usd_count = sum(1 for _, pairs in crypto_pairs.items() if pairs['USD'])
        usdc_count = sum(1 for _, pairs in crypto_pairs.items() if pairs['USDC'])
        usdt_count = sum(1 for _, pairs in crypto_pairs.items() if pairs['USDT'])
        logger.info(f"   Available pairs: {usd_count} USD, {usdc_count} USDC, {usdt_count} USDT")
        
        # Extract just the crypto names for scanning
        valid_crypto_names = [crypto for crypto, _, _ in valid_cryptos]
        
        logger.info(f"   Found {len(valid_cryptos)} cryptos with multiple quote pairs ({quote1}/{quote2} combinations)")
        
        # Limit to max_cryptos
        valid_cryptos = valid_cryptos[:max_cryptos]
        
        # Scan each crypto
        scanned = 0
        profitable_count = 0
        total_spreads = []
        
        for crypto_info in valid_cryptos:
            crypto, quote1, quote2 = crypto_info
            try:
                opp = await self.scan_crypto(exchange_id, crypto, quote1, quote2)
                scanned += 1
                self.scan_stats['total_pairs_scanned'] += 1
                
                if opp:
                    opportunities.append(opp)
                    profitable_count += 1
                    total_spreads.append(opp.raw_spread_percent)
                    logger.info(f"   ✅ {crypto} ({quote1}/{quote2}): {opp.net_profit_percent:.3f}% profit (spread: {opp.raw_spread_percent:.3f}%, fees: {opp.maker_fee + opp.taker_fee:.3f}%, slippage: {opp.estimated_slippage:.3f}%)")
                else:
                    # Log unprofitable but show spread for analysis
                    try:
                        # Quick price check to show spread
                        ticker1 = await self.get_ticker(exchange_id, f'{crypto}/{quote1}')
                        ticker2 = await self.get_ticker(exchange_id, f'{crypto}/{quote2}')
                        if ticker1 and ticker2:
                            price1 = ticker1.get('last', ticker1.get('close', 0))
                            price2 = ticker2.get('last', ticker2.get('close', 0))
                            if price1 > 0 and price2 > 0:
                                spread = abs(price2 - price1) / min(price1, price2) * 100
                                total_spreads.append(spread)
                                if scanned % 50 == 0:  # Log every 50th to avoid spam
                                    logger.debug(f"   ⚠️  {crypto} ({quote1}/{quote2}): {spread:.3f}% spread (not profitable)")
                    except:
                        pass
                
                # Rate limiting
                if scanned % 10 == 0:
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.debug(f"   ⚠️  Error scanning {crypto}: {e}")
                continue
        
        logger.info(f"   Found {len(opportunities)} profitable opportunities on {exchange_id}")
        
        if total_spreads:
            avg_spread = sum(total_spreads) / len(total_spreads)
            max_spread = max(total_spreads)
            min_spread = min(total_spreads)
            logger.info(f"   Spread stats: avg={avg_spread:.3f}%, max={max_spread:.3f}%, min={min_spread:.3f}%")
        
        return opportunities
    
    async def scan_all_exchanges(self) -> List[ArbitrageOpportunity]:
        """Scan both exchanges for arbitrage opportunities"""
        start_time = time.time()
        
        logger.info("=" * 80)
        logger.info("🚀 INTRA-EXCHANGE ARBITRAGE SCANNER")
        logger.info("=" * 80)
        logger.info(f"Scanning Coinbase and Gemini for USD/USDC arbitrage opportunities...")
        logger.info("")
        
        # Scan both exchanges in parallel
        coinbase_task = self.scan_exchange('coinbase', max_cryptos=1000)
        gemini_task = self.scan_exchange('gemini', max_cryptos=1000)
        
        coinbase_opps, gemini_opps = await asyncio.gather(
            coinbase_task,
            gemini_task,
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(coinbase_opps, Exception):
            logger.error(f"❌ Error scanning Coinbase: {coinbase_opps}")
            coinbase_opps = []
        if isinstance(gemini_opps, Exception):
            logger.error(f"❌ Error scanning Gemini: {gemini_opps}")
            gemini_opps = []
        
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
        logger.info("📊 SCAN RESULTS")
        logger.info("=" * 80)
        logger.info(f"Total pairs scanned: {self.scan_stats['total_pairs_scanned']}")
        logger.info(f"Opportunities found: {self.scan_stats['opportunities_found']}")
        logger.info(f"  - Coinbase: {self.scan_stats['coinbase_opportunities']}")
        logger.info(f"  - Gemini: {self.scan_stats['gemini_opportunities']}")
        logger.info(f"Scan duration: {self.scan_stats['scan_duration_seconds']:.2f} seconds")
        logger.info("")
        
        if not self.opportunities:
            logger.warning("⚠️  No profitable opportunities found")
            return
        
        logger.info("=" * 80)
        logger.info("🏆 TOP 50 ARBITRAGE OPPORTUNITIES (Ranked by Profitability)")
        logger.info("=" * 80)
        logger.info("")
        
        # Print top 50
        for opp in self.opportunities[:50]:
            logger.info(f"#{opp.rank:3d} | {opp.exchange.upper():8s} | {opp.crypto:8s} | "
                       f"Profit: {opp.net_profit_percent:6.3f}% | "
                       f"Spread: {opp.raw_spread_percent:6.3f}% | "
                       f"Fees: {opp.maker_fee + opp.taker_fee:5.3f}% | "
                       f"Slippage: {opp.estimated_slippage:5.3f}% | "
                       f"Score: {opp.arb_score:8.2f}")
            logger.info(f"     {opp.usd_pair} = ${opp.usd_price:.6f} | "
                       f"{opp.usdc_pair} = ${opp.usdc_price:.6f}")
            logger.info(f"     Volume: ${opp.volume_usd:,.0f} | "
                       f"Depth USD: ${opp.order_book_depth_usd:,.0f} | "
                       f"Depth USDC: ${opp.order_book_depth_usdc:,.0f} | "
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

