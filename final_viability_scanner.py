#!/usr/bin/env python3
"""
FINAL VIABILITY SCANNER - ALL 146 COINBASE + GEMINI PAIRS
Scans every single pair available on both exchanges
Filters by spread, volume, transfer time, and profitability
"""

import ccxt
import time
import logging
from datetime import datetime
from coinbase_gemini_config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FinalViabilityScanner:
    def __init__(self):
        logger.info("="*100)
        logger.info("🔍 FINAL VIABILITY SCANNER - ALL 146 COINBASE + GEMINI PAIRS")
        logger.info("="*100)
        logger.info("💡 Using MAKER FEES: Coinbase 0.40% + Gemini 0.10% = 0.50% total")
        logger.info("💡 Scanning ONLY pairs available on BOTH exchanges")
        logger.info("="*100)
        
        # Initialize exchanges
        self.coinbase = ccxt.coinbase({
            'apiKey': Config.COINBASE_API_KEY,
            'secret': Config.COINBASE_SECRET_KEY,
            'enableRateLimit': True,
        })
        
        self.gemini = ccxt.gemini({
            'apiKey': Config.GEMINI_API_KEY,
            'secret': Config.GEMINI_SECRET_KEY,
            'enableRateLimit': True,
        })
        
        logger.info("\nLoading markets...")
        self.coinbase.load_markets()
        self.gemini.load_markets()
        
        # Get ALL common pairs
        self.common_pairs = self._get_all_common_pairs()
        logger.info(f"✅ Found {len(self.common_pairs)} common pairs to scan")
        logger.info("="*100 + "\n")
    
    def _get_all_common_pairs(self):
        """Get ALL common pairs between Coinbase and Gemini"""
        logger.info("\n📊 Finding common pairs across all quote currencies...")
        
        quotes = ['USD', 'USDT', 'USDC', 'BTC', 'ETH', 'EUR', 'GBP']
        all_common = []
        
        for quote in quotes:
            cb_pairs = [s for s in self.coinbase.markets.keys() if s.endswith(f'/{quote}')]
            gem_pairs = [s for s in self.gemini.markets.keys() if s.endswith(f'/{quote}')]
            common = sorted(set(cb_pairs) & set(gem_pairs))
            
            if common:
                all_common.extend(common)
                logger.info(f"  {quote}: {len(common)} common pairs")
        
        # Remove duplicates and sort
        all_common = sorted(set(all_common))
        return all_common
    
    def categorize_crypto(self, symbol):
        """Categorize crypto and estimate transfer time"""
        base = symbol.split('/')[0]
        
        # Fast transfer (< 1 min)
        fast = ['XRP', 'XLM', 'ALGO', 'NANO', 'HBAR', 'SOL', 'AVAX', 'NEAR', 'FTM', 'ONE', 'MATIC', 'POL', 'ATOM']
        # Medium (1-5 min)
        medium = ['LTC', 'BCH', 'DOGE', 'ADA', 'DOT', 'TRX', 'EOS', 'XTZ', 'DASH', 'ZEC']
        # Slow (> 5 min)
        slow = ['BTC', 'ETH']
        # Stablecoins
        stables = ['USDT', 'USDC', 'DAI', 'BUSD', 'TUSD', 'USDP', 'GUSD', 'USDD']
        # Fiat
        fiat = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD']
        
        if any(f in base for f in fiat):
            return 'fiat', 0, False
        elif any(s in base for s in stables):
            return 'stablecoin', 0, False
        elif any(f in base for f in fast):
            return 'fast', 30, True
        elif any(m in base for m in medium):
            return 'medium', 180, True
        elif any(s in base for s in slow):
            return 'slow', 600, True
        else:
            return 'unknown', 120, True  # Default 2 min
    
    def scan_pair(self, symbol):
        """Scan a single pair for arbitrage opportunity"""
        try:
            # Fetch from Coinbase
            cb_ticker = self.coinbase.fetch_ticker(symbol)
            time.sleep(0.12)
            
            # Fetch from Gemini
            gem_ticker = self.gemini.fetch_ticker(symbol)
            time.sleep(0.12)
            
            # Get prices
            cb_ask = cb_ticker.get('ask')
            cb_bid = cb_ticker.get('bid')
            gem_ask = gem_ticker.get('ask')
            gem_bid = gem_ticker.get('bid')
            
            if not all([cb_ask, cb_bid, gem_ask, gem_bid]):
                return None
            
            # Calculate spreads (both directions)
            spread_cb_to_gem = ((gem_bid - cb_ask) / cb_ask) * 100
            spread_gem_to_cb = ((cb_bid - gem_ask) / gem_ask) * 100
            
            # Take absolute value (we can trade either direction!)
            abs_spread_cb_gem = abs(spread_cb_to_gem)
            abs_spread_gem_cb = abs(spread_gem_to_cb)
            
            best_spread = max(abs_spread_cb_gem, abs_spread_gem_cb)
            direction = 'CB→GEM' if abs_spread_cb_gem > abs_spread_gem_cb else 'GEM→CB'
            
            # Calculate net profit after 0.50% maker fees
            net_spread = best_spread - 0.50
            net_profit = net_spread  # Per $100
            
            # Get volume
            cb_vol = cb_ticker.get('quoteVolume') or cb_ticker.get('baseVolume') or 0
            gem_vol = gem_ticker.get('quoteVolume') or gem_ticker.get('baseVolume') or 0
            total_volume = cb_vol + gem_vol
            
            # Get price
            avg_price = (cb_ask + cb_bid + gem_ask + gem_bid) / 4
            
            # Categorize
            category, transfer_time, is_crypto = self.categorize_crypto(symbol)
            
            return {
                'symbol': symbol,
                'gross_spread': best_spread,
                'net_spread': net_spread,
                'net_profit': net_profit,
                'volume': total_volume,
                'direction': direction,
                'price': avg_price,
                'category': category,
                'transfer_time': transfer_time,
                'is_crypto': is_crypto,
                'cb_ask': cb_ask,
                'cb_bid': cb_bid,
                'gem_ask': gem_ask,
                'gem_bid': gem_bid,
            }
            
        except Exception as e:
            logger.debug(f"Error scanning {symbol}: {str(e)[:60]}")
            return None
    
    def run_scan(self):
        """Run the full scan"""
        logger.info("="*100)
        logger.info(f"🚀 STARTING SCAN OF ALL {len(self.common_pairs)} PAIRS")
        logger.info("="*100)
        logger.info(f"⏱️  Estimated time: ~{len(self.common_pairs) * 0.25 / 60:.1f} minutes\n")
        
        results = []
        errors = 0
        
        for i, symbol in enumerate(self.common_pairs, 1):
            result = self.scan_pair(symbol)
            
            if result:
                results.append(result)
                logger.info(
                    f"[{i:3d}/{len(self.common_pairs)}] {result['symbol']:<20} | "
                    f"Spread: {result['gross_spread']:>7.3f}% | "
                    f"Net: {result['net_spread']:>7.3f}% | "
                    f"Profit: ${result['net_profit']:>7.2f} | "
                    f"Vol: ${result['volume']:>12,.0f} | "
                    f"{result['direction']}"
                )
            else:
                errors += 1
            
            if i % 10 == 0:
                logger.info(f"  📊 Progress: {i}/{len(self.common_pairs)} ({i/len(self.common_pairs)*100:.1f}%)")
        
        logger.info("\n" + "="*100)
        logger.info(f"✅ SCAN COMPLETE: {len(results)} pairs analyzed, {errors} errors")
        logger.info("="*100 + "\n")
        
        # Sort by net profit
        results.sort(key=lambda x: x['net_profit'], reverse=True)
        
        # Show top 50
        logger.info("="*100)
        logger.info("🏆 TOP 50 PAIRS BY NET PROFIT (After 0.50% Maker Fees)")
        logger.info("="*100)
        logger.info(f"{'Rank':<6} {'Symbol':<20} {'Gross Spread':<14} {'Net Profit':<12} {'Volume':<15} {'Transfer':<12}")
        logger.info("-"*100)
        
        for i, r in enumerate(results[:50], 1):
            marker = '🔥' if r['net_profit'] > 0.50 else '✅' if r['net_profit'] > 0.20 else '⚠️' if r['net_profit'] > 0 else '❌'
            transfer = f"{r['transfer_time']}s" if r['is_crypto'] else r['category']
            logger.info(
                f"{marker} {i:<4} {r['symbol']:<20} {r['gross_spread']:>7.3f}%       "
                f"${r['net_profit']:>7.2f}      ${r['volume']:>12,.0f}  {transfer:<10}"
            )
        
        logger.info("="*100 + "\n")
        
        # Filter profitable cryptos only (exclude fiat/stablecoins)
        crypto_only = [r for r in results if r['is_crypto']]
        profitable = [r for r in crypto_only if r['net_profit'] > 0]
        
        logger.info("="*100)
        logger.info("📊 PROFITABILITY BREAKDOWN (Crypto Only)")
        logger.info("="*100)
        logger.info(f"Total crypto pairs: {len(crypto_only)}")
        logger.info(f"Profitable (net > $0): {len(profitable)}")
        logger.info(f"  🔥 Excellent (> $0.50): {len([r for r in profitable if r['net_profit'] > 0.50])}")
        logger.info(f"  ✅ Good ($0.20-$0.50): {len([r for r in profitable if 0.20 < r['net_profit'] <= 0.50])}")
        logger.info(f"  ⚠️  Marginal ($0.05-$0.20): {len([r for r in profitable if 0.05 < r['net_profit'] <= 0.20])}")
        logger.info(f"  💤 Breakeven ($0-$0.05): {len([r for r in profitable if 0 < r['net_profit'] <= 0.05])}")
        logger.info("="*100 + "\n")
        
        # Show profitable opportunities
        if profitable:
            logger.info("="*100)
            logger.info(f"💰 ALL PROFITABLE CRYPTOS ({len(profitable)} found)")
            logger.info("="*100)
            for r in profitable:
                logger.info(
                    f"  {'🔥' if r['net_profit'] > 0.50 else '✅' if r['net_profit'] > 0.20 else '⚠️'} "
                    f"{r['symbol']:<20} Net: ${r['net_profit']:>6.2f} | "
                    f"Spread: {r['gross_spread']:>6.3f}% | "
                    f"Vol: ${r['volume']:>12,.0f} | "
                    f"Transfer: {r['transfer_time']}s"
                )
            logger.info("="*100 + "\n")
        
        # Quality filters
        excellent = [r for r in profitable if r['net_profit'] > 0.50 and r['volume'] > 5000]
        good = [r for r in profitable if 0.20 < r['net_profit'] <= 0.50 and r['volume'] > 1000]
        marginal = [r for r in profitable if 0.05 < r['net_profit'] <= 0.20 and r['volume'] > 500]
        
        # Final recommendations
        recommended = excellent + good + marginal[:10]  # Top 10 marginal
        
        if recommended:
            logger.info("="*100)
            logger.info("🚀 FINAL RECOMMENDATIONS FOR BOT")
            logger.info("="*100)
            logger.info(f"\nTop {len(recommended)} cryptos for arbitrage:\n")
            logger.info("CURRENCY_PAIRS = [")
            for r in recommended:
                logger.info(
                    f"    '{r['symbol']}',  # Net: ${r['net_profit']:.2f}, "
                    f"Spread: {r['gross_spread']:.3f}%, Vol: ${r['volume']:,.0f}, "
                    f"Transfer: {r['transfer_time']}s"
                )
            logger.info("]\n")
            logger.info("="*100)
        else:
            logger.info("="*100)
            logger.info("❌ NO PROFITABLE CRYPTOS FOUND")
            logger.info("="*100)
            logger.info("Current market conditions show no profitable opportunities.")
            logger.info("All spreads are below 0.50% (maker fee threshold).")
            logger.info("="*100)
        
        logger.info("\n" + "="*100)
        logger.info("🏁 SCAN COMPLETE")
        logger.info("="*100)
        logger.info(f"Total pairs scanned: {len(results)}")
        logger.info(f"Profitable opportunities: {len(profitable)}")
        logger.info(f"Recommended for bot: {len(recommended)}")
        logger.info(f"Scan completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*100 + "\n")

def main():
    try:
        scanner = FinalViabilityScanner()
        scanner.run_scan()
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Scan interrupted by user")
    except Exception as e:
        logger.error(f"\n\n❌ Scanner crashed: {str(e)}")
        raise

if __name__ == "__main__":
    main()

