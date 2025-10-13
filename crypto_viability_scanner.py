#!/usr/bin/env python3
"""
CRYPTO VIABILITY SCANNER
Scans 1000+ cryptos to find the BEST ones for arbitrage
Logs all spreads, volumes, and potential profits
"""

import ccxt
import time
import logging
import asyncio
from datetime import datetime
from coinbase_gemini_config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CryptoViabilityScanner:
    def __init__(self):
        logger.info("="*100)
        logger.info("🔍 CRYPTO VIABILITY SCANNER - SCANNING 1000+ CRYPTOS")
        logger.info("="*100)
        logger.info("💡 Using MAKER FEES (limit orders): Coinbase 0.40% + Gemini 0.10% = 0.50% total")
        logger.info("="*100)
        
        # Initialize PRIMARY exchanges (Coinbase + Gemini - our actual trading pair)
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
        
        # Initialize ADDITIONAL exchanges (for comparison only - no API keys needed)
        logger.info("Initializing additional exchanges for broader crypto coverage...")
        self.additional_exchanges = {}
        
        try:
            self.additional_exchanges['kraken'] = ccxt.kraken({'enableRateLimit': True})
            logger.info("  ✅ Kraken initialized")
        except:
            logger.warning("  ⚠️  Kraken failed to initialize")
        
        try:
            self.additional_exchanges['binanceus'] = ccxt.binanceus({'enableRateLimit': True})
            logger.info("  ✅ Binance.US initialized")
        except:
            logger.warning("  ⚠️  Binance.US failed to initialize")
        
        try:
            self.additional_exchanges['okx'] = ccxt.okx({'enableRateLimit': True})
            logger.info("  ✅ OKX initialized")
        except:
            logger.warning("  ⚠️  OKX failed to initialize")
        
        try:
            self.additional_exchanges['kucoin'] = ccxt.kucoin({'enableRateLimit': True})
            logger.info("  ✅ KuCoin initialized")
        except:
            logger.warning("  ⚠️  KuCoin failed to initialize")
        
        # Load markets
        logger.info("\nLoading markets from all exchanges...")
        self.coinbase.load_markets()
        self.gemini.load_markets()
        
        for name, exchange in self.additional_exchanges.items():
            try:
                exchange.load_markets()
                logger.info(f"  ✅ {name.upper()} markets loaded: {len(exchange.markets)} pairs")
            except Exception as e:
                logger.warning(f"  ⚠️  {name.upper()} markets failed: {str(e)[:50]}")
        
        # Get common pairs
        self.common_pairs = self._get_common_pairs()
        logger.info(f"\n✅ Found {len(self.common_pairs)} total pairs to scan")
        logger.info("="*100)
        
    def _get_common_pairs(self):
        """Get ALL unique crypto pairs from ALL exchanges"""
        logger.info("\n" + "="*100)
        logger.info("📊 AGGREGATING CRYPTOS FROM ALL EXCHANGES")
        logger.info("="*100)
        
        # Collect ALL unique pairs from ALL exchanges
        all_pairs = set()
        
        # Add Coinbase pairs
        cb_pairs = [s for s in self.coinbase.markets.keys() if '/' in s]
        all_pairs.update(cb_pairs)
        logger.info(f"Coinbase: {len(cb_pairs)} pairs")
        
        # Add Gemini pairs
        gem_pairs = [s for s in self.gemini.markets.keys() if '/' in s]
        all_pairs.update(gem_pairs)
        logger.info(f"Gemini: {len(gem_pairs)} pairs")
        
        # Add pairs from additional exchanges
        for name, exchange in self.additional_exchanges.items():
            try:
                ex_pairs = [s for s in exchange.markets.keys() if '/' in s]
                all_pairs.update(ex_pairs)
                logger.info(f"{name.upper()}: {len(ex_pairs)} pairs")
            except Exception as e:
                logger.warning(f"{name.upper()}: Failed to get pairs - {str(e)[:50]}")
        
        # Filter to only USD, USDT, USDC quotes (for easier comparison)
        quote_currencies = ['USD', 'USDT', 'USDC']
        filtered_pairs = [
            p for p in all_pairs 
            if any(p.endswith(f'/{q}') for q in quote_currencies)
        ]
        
        # Sort by quote currency and then alphabetically
        filtered_pairs = sorted(filtered_pairs, key=lambda x: (x.split('/')[-1], x))
        
        logger.info(f"="*100)
        logger.info(f"📊 TOTAL UNIQUE PAIRS (USD/USDT/USDC): {len(filtered_pairs)}")
        logger.info(f"="*100)
        
        # Show breakdown by quote
        for quote in quote_currencies:
            count = len([p for p in filtered_pairs if p.endswith(f'/{quote}')])
            logger.info(f"  {quote}: {count} pairs")
        
        logger.info(f"="*100)
        
        return filtered_pairs
    
    def calculate_potential_profit(self, symbol, spread_pct, price):
        """Calculate potential profit for a $100 position"""
        position_size_usd = 100.0  # $100 position
        
        # MAKER FEES (using limit orders, not market orders!)
        coinbase_maker = 0.0040  # 0.40% maker fee
        gemini_maker = 0.0010    # 0.10% maker fee
        total_fees = coinbase_maker + gemini_maker  # 0.50% total
        
        # Net spread after fees
        net_spread = spread_pct - total_fees
        
        # Profit
        gross_profit = position_size_usd * spread_pct
        fees_paid = position_size_usd * total_fees
        net_profit = position_size_usd * net_spread
        
        return {
            'gross_profit': gross_profit,
            'fees_paid': fees_paid,
            'net_profit': net_profit,
            'net_spread': net_spread,
        }
    
    def scan_crypto(self, symbol):
        """Scan a single crypto for arbitrage opportunity"""
        try:
            # Try to fetch from Coinbase first
            cb_ticker = None
            try:
                if symbol in self.coinbase.markets:
                    cb_ticker = self.coinbase.fetch_ticker(symbol)
                    time.sleep(0.12)
            except:
                pass
            
            # Try to fetch from Gemini
            gem_ticker = None
            try:
                if symbol in self.gemini.markets:
                    gem_ticker = self.gemini.fetch_ticker(symbol)
                    time.sleep(0.12)
            except:
                pass
            
            # If not on Coinbase/Gemini, try other exchanges
            if not cb_ticker:
                for name, exchange in self.additional_exchanges.items():
                    try:
                        if symbol in exchange.markets:
                            cb_ticker = exchange.fetch_ticker(symbol)
                            time.sleep(0.12)
                            break
                    except:
                        continue
            
            if not gem_ticker and not cb_ticker:
                return None
            
            # If only one exchange has it, use it for both (to show it exists)
            if not gem_ticker and cb_ticker:
                gem_ticker = cb_ticker
            elif not cb_ticker and gem_ticker:
                cb_ticker = gem_ticker
            
            # Get prices
            cb_ask = cb_ticker.get('ask')
            cb_bid = cb_ticker.get('bid')
            gem_ask = gem_ticker.get('ask')
            gem_bid = gem_ticker.get('bid')
            
            if not all([cb_ask, cb_bid, gem_ask, gem_bid]):
                return None
            
            # Calculate spreads both directions
            spread_cb_to_gem = ((gem_bid - cb_ask) / cb_ask) * 100
            spread_gem_to_cb = ((cb_bid - gem_ask) / gem_ask) * 100
            
            best_spread_pct = max(spread_cb_to_gem, spread_gem_to_cb) / 100
            direction = 'CB→GEM' if spread_cb_to_gem > spread_gem_to_cb else 'GEM→CB'
            
            # Get volume
            cb_vol = cb_ticker.get('quoteVolume') or cb_ticker.get('baseVolume') or 0
            gem_vol = gem_ticker.get('quoteVolume') or gem_ticker.get('baseVolume') or 0
            total_volume = cb_vol + gem_vol
            
            # Get average price
            avg_price = (cb_ask + cb_bid + gem_ask + gem_bid) / 4
            
            # Calculate potential profit
            profit_data = self.calculate_potential_profit(symbol, best_spread_pct, avg_price)
            
            return {
                'symbol': symbol,
                'spread_pct': best_spread_pct * 100,  # Convert back to percentage
                'direction': direction,
                'volume_24h': total_volume,
                'price': avg_price,
                'cb_ask': cb_ask,
                'cb_bid': cb_bid,
                'gem_ask': gem_ask,
                'gem_bid': gem_bid,
                'gross_profit': profit_data['gross_profit'],
                'fees_paid': profit_data['fees_paid'],
                'net_profit': profit_data['net_profit'],
                'net_spread_pct': profit_data['net_spread'] * 100,
            }
            
        except Exception as e:
            logger.debug(f"Error scanning {symbol}: {str(e)[:60]}")
            return None
    
    def run_scan(self):
        """Run the full scan"""
        logger.info("\n" + "="*100)
        logger.info(f"🚀 STARTING SCAN OF {len(self.common_pairs)} CRYPTOS")
        logger.info("="*100 + "\n")
        
        results = []
        errors = 0
        
        for i, symbol in enumerate(self.common_pairs, 1):
            result = self.scan_crypto(symbol)
            
            if result:
                results.append(result)
                
                # Log every crypto with its data
                logger.info(
                    f"[{i:3d}/{len(self.common_pairs)}] {result['symbol']:<15} | "
                    f"Spread: {result['spread_pct']:>7.3f}% | "
                    f"Net: {result['net_spread_pct']:>7.3f}% | "
                    f"Profit: ${result['net_profit']:>7.2f} | "
                    f"Vol: ${result['volume_24h']:>12,.0f} | "
                    f"{result['direction']}"
                )
            else:
                errors += 1
            
            # Progress update every 10
            if i % 10 == 0:
                logger.info(f"  📊 Progress: {i}/{len(self.common_pairs)} ({i/len(self.common_pairs)*100:.1f}%)")
        
        logger.info("\n" + "="*100)
        logger.info(f"✅ SCAN COMPLETE: {len(results)} cryptos analyzed, {errors} errors")
        logger.info("="*100 + "\n")
        
        # Sort by net profit
        results.sort(key=lambda x: x['net_profit'], reverse=True)
        
        # Log top 50 by net profit
        logger.info("="*100)
        logger.info("🏆 TOP 50 CRYPTOS BY NET PROFIT (After Fees)")
        logger.info("="*100)
        logger.info(f"{'Rank':<6} {'Symbol':<15} {'Spread':<10} {'Net Spread':<12} {'Net Profit':<12} {'Volume':<15} {'Direction':<10}")
        logger.info("-"*100)
        
        for i, r in enumerate(results[:50], 1):
            marker = '🔥' if r['net_profit'] > 0.50 else '✅' if r['net_profit'] > 0.20 else '⚠️' if r['net_profit'] > 0 else '❌'
            logger.info(
                f"{marker} {i:<4} {r['symbol']:<15} {r['spread_pct']:>6.3f}%    "
                f"{r['net_spread_pct']:>7.3f}%      ${r['net_profit']:>7.2f}      "
                f"${r['volume_24h']:>12,.0f}  {r['direction']:<10}"
            )
        
        logger.info("="*100 + "\n")
        
        # Categorize by profitability
        excellent = [r for r in results if r['net_profit'] > 0.50]
        good = [r for r in results if 0.20 < r['net_profit'] <= 0.50]
        marginal = [r for r in results if 0.05 < r['net_profit'] <= 0.20]
        breakeven = [r for r in results if 0 < r['net_profit'] <= 0.05]
        unprofitable = [r for r in results if r['net_profit'] <= 0]
        
        logger.info("="*100)
        logger.info("📊 PROFITABILITY BREAKDOWN")
        logger.info("="*100)
        logger.info(f"🔥 EXCELLENT (Net Profit > $0.50):    {len(excellent):>4} cryptos")
        logger.info(f"✅ GOOD (Net Profit $0.20-$0.50):     {len(good):>4} cryptos")
        logger.info(f"⚠️  MARGINAL (Net Profit $0.05-$0.20): {len(marginal):>4} cryptos")
        logger.info(f"💤 BREAKEVEN (Net Profit $0.00-$0.05): {len(breakeven):>4} cryptos")
        logger.info(f"❌ UNPROFITABLE (Net Profit < $0):     {len(unprofitable):>4} cryptos")
        logger.info("="*100 + "\n")
        
        # Log excellent opportunities
        if excellent:
            logger.info("="*100)
            logger.info("🔥 EXCELLENT OPPORTUNITIES (Net Profit > $0.50)")
            logger.info("="*100)
            for r in excellent:
                logger.info(
                    f"  🔥 {r['symbol']:<15} Net Profit: ${r['net_profit']:>6.2f} | "
                    f"Spread: {r['spread_pct']:>6.3f}% | Net: {r['net_spread_pct']:>6.3f}% | "
                    f"Vol: ${r['volume_24h']:>12,.0f}"
                )
            logger.info("="*100 + "\n")
        
        # Log good opportunities
        if good:
            logger.info("="*100)
            logger.info("✅ GOOD OPPORTUNITIES (Net Profit $0.20-$0.50)")
            logger.info("="*100)
            for r in good:
                logger.info(
                    f"  ✅ {r['symbol']:<15} Net Profit: ${r['net_profit']:>6.2f} | "
                    f"Spread: {r['spread_pct']:>6.3f}% | Net: {r['net_spread_pct']:>6.3f}% | "
                    f"Vol: ${r['volume_24h']:>12,.0f}"
                )
            logger.info("="*100 + "\n")
        
        # Log marginal opportunities
        if marginal:
            logger.info("="*100)
            logger.info("⚠️  MARGINAL OPPORTUNITIES (Net Profit $0.05-$0.20)")
            logger.info("="*100)
            for r in marginal[:20]:  # Top 20 only
                logger.info(
                    f"  ⚠️  {r['symbol']:<15} Net Profit: ${r['net_profit']:>6.2f} | "
                    f"Spread: {r['spread_pct']:>6.3f}% | Net: {r['net_spread_pct']:>6.3f}% | "
                    f"Vol: ${r['volume_24h']:>12,.0f}"
                )
            logger.info("="*100 + "\n")
        
        # Final recommendations
        recommended = excellent + good
        if recommended:
            logger.info("="*100)
            logger.info("🎯 RECOMMENDED CRYPTOS FOR BOT")
            logger.info("="*100)
            logger.info("\nCURRENCY_PAIRS = [")
            for r in recommended:
                logger.info(
                    f"    '{r['symbol']}',  # Net: ${r['net_profit']:.2f}, "
                    f"Spread: {r['spread_pct']:.3f}%, Vol: ${r['volume_24h']:,.0f}"
                )
            logger.info("]\n")
            logger.info("="*100 + "\n")
        else:
            logger.info("="*100)
            logger.info("❌ NO HIGHLY PROFITABLE CRYPTOS FOUND")
            logger.info("="*100)
            logger.info("Current market conditions may not be favorable for arbitrage.")
            logger.info("Consider lowering profit thresholds or waiting for more volatility.")
            logger.info("="*100 + "\n")
        
        logger.info("="*100)
        logger.info("🏁 SCAN COMPLETE")
        logger.info("="*100)
        logger.info(f"Total cryptos scanned: {len(results)}")
        logger.info(f"Profitable opportunities: {len(excellent) + len(good) + len(marginal)}")
        logger.info(f"Scan completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*100 + "\n")

def main():
    """Main entry point"""
    try:
        scanner = CryptoViabilityScanner()
        scanner.run_scan()
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Scan interrupted by user")
    except Exception as e:
        logger.error(f"\n\n❌ Scanner crashed: {str(e)}")
        raise

if __name__ == "__main__":
    main()

