#!/usr/bin/env python3
"""
Detailed Spread Analysis - Shows ALL spreads (profitable or not)
Helps understand market conditions and why opportunities aren't profitable
"""

import asyncio
import logging
from typing import Dict, List
from dataclasses import dataclass
import json

from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager
from coinbase_gemini_config import EXCHANGE_FEES

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SpreadAnalysis:
    """Detailed spread analysis for a crypto"""
    exchange: str
    crypto: str
    pair1: str
    pair2: str
    price1: float
    price2: float
    raw_spread_percent: float
    maker_fee: float
    taker_fee: float
    total_fees_percent: float
    estimated_slippage_percent: float
    net_profit_percent: float
    is_profitable: bool
    volume_usd: float = 0.0

async def analyze_all_spreads():
    """Analyze all spreads to understand market conditions"""
    manager = CoinbaseGeminiExchangeManager()
    await manager.initialize()
    
    all_analyses = []
    
    for exchange_id in ['coinbase', 'gemini']:
        logger.info(f"\n{'='*80}")
        logger.info(f"Analyzing {exchange_id.upper()}...")
        logger.info(f"{'='*80}")
        
        exchange = manager.get_exchange(exchange_id)
        markets = exchange.markets
        
        # Get fees
        if exchange_id == 'coinbase':
            maker_fee = EXCHANGE_FEES['coinbase']['maker']
            taker_fee = EXCHANGE_FEES['coinbase']['taker']
        else:
            maker_fee = EXCHANGE_FEES['gemini']['maker']
            taker_fee = EXCHANGE_FEES['gemini']['taker']
        
        # Find cryptos with multiple quote pairs
        crypto_pairs = {}
        for symbol, market_info in markets.items():
            if not market_info.get('active', True):
                continue
            
            base = market_info.get('base', '')
            quote = market_info.get('quote', '')
            
            if quote in ['USD', 'USDC', 'USDT']:
                if base not in crypto_pairs:
                    crypto_pairs[base] = {'USD': False, 'USDC': False, 'USDT': False}
                
                if quote == 'USD':
                    crypto_pairs[base]['USD'] = True
                elif quote == 'USDC':
                    crypto_pairs[base]['USDC'] = True
                elif quote == 'USDT':
                    crypto_pairs[base]['USDT'] = True
        
        # Find valid pairs
        valid_combos = []
        for crypto, pairs in crypto_pairs.items():
            if pairs['USD'] and pairs['USDC']:
                valid_combos.append((crypto, 'USD', 'USDC'))
            elif pairs['USD'] and pairs['USDT']:
                valid_combos.append((crypto, 'USD', 'USDT'))
            elif pairs['USDC'] and pairs['USDT']:
                valid_combos.append((crypto, 'USDC', 'USDT'))
        
        logger.info(f"Found {len(valid_combos)} cryptos with multiple quote pairs")
        
        # Analyze each
        for crypto, quote1, quote2 in valid_combos[:100]:  # Limit to 100 for speed
            try:
                pair1 = f'{crypto}/{quote1}'
                pair2 = f'{crypto}/{quote2}'
                
                # Get tickers
                ticker1 = exchange.fetch_ticker(pair1)
                ticker2 = exchange.fetch_ticker(pair2)
                
                if hasattr(ticker1, '__await__'):
                    ticker1 = await ticker1
                if hasattr(ticker2, '__await__'):
                    ticker2 = await ticker2
                
                price1 = ticker1.get('last', ticker1.get('close', 0))
                price2 = ticker2.get('last', ticker2.get('close', 0))
                
                if price1 == 0 or price2 == 0:
                    continue
                
                # Calculate spread
                raw_spread = abs(price2 - price1) / min(price1, price2)
                total_fees = maker_fee + taker_fee
                estimated_slippage = 0.002  # Assume 0.2%
                net_profit = raw_spread - total_fees - estimated_slippage
                
                volume = ticker1.get('quoteVolume', 0) or ticker1.get('volume', {}).get('USD', 0) if isinstance(ticker1.get('volume'), dict) else 0
                
                analysis = SpreadAnalysis(
                    exchange=exchange_id,
                    crypto=crypto,
                    pair1=pair1,
                    pair2=pair2,
                    price1=price1,
                    price2=price2,
                    raw_spread_percent=raw_spread * 100,
                    maker_fee=maker_fee * 100,
                    taker_fee=taker_fee * 100,
                    total_fees_percent=total_fees * 100,
                    estimated_slippage_percent=estimated_slippage * 100,
                    net_profit_percent=net_profit * 100,
                    is_profitable=net_profit > 0,
                    volume_usd=volume
                )
                
                all_analyses.append(analysis)
                
                # Log profitable ones immediately
                if analysis.is_profitable:
                    logger.info(f"✅ {crypto:8s} | {quote1}/{quote2:4s} | "
                               f"Spread: {analysis.raw_spread_percent:6.3f}% | "
                               f"Fees: {analysis.total_fees_percent:5.3f}% | "
                               f"Profit: {analysis.net_profit_percent:6.3f}% | "
                               f"Vol: ${volume:,.0f}")
                
                await asyncio.sleep(0.05)  # Rate limiting
                
            except Exception as e:
                continue
        
        # Summary for this exchange
        profitable = [a for a in all_analyses if a.exchange == exchange_id and a.is_profitable]
        unprofitable = [a for a in all_analyses if a.exchange == exchange_id and not a.is_profitable]
        
        if profitable:
            logger.info(f"\n📊 {exchange_id.upper()} Summary:")
            logger.info(f"   Profitable: {len(profitable)}")
            logger.info(f"   Unprofitable: {len(unprofitable)}")
            avg_spread_profitable = sum(a.raw_spread_percent for a in profitable) / len(profitable)
            logger.info(f"   Avg spread (profitable): {avg_spread_profitable:.3f}%")
        
        if unprofitable:
            avg_spread_unprofitable = sum(a.raw_spread_percent for a in unprofitable) / len(unprofitable)
            avg_fees = sum(a.total_fees_percent for a in unprofitable) / len(unprofitable)
            logger.info(f"   Avg spread (unprofitable): {avg_spread_unprofitable:.3f}%")
            logger.info(f"   Avg fees: {avg_fees:.3f}%")
            logger.info(f"   Reason: Spreads ({avg_spread_unprofitable:.3f}%) < Fees ({avg_fees:.3f}%)")
    
    # Overall summary
    logger.info(f"\n{'='*80}")
    logger.info("OVERALL SUMMARY")
    logger.info(f"{'='*80}")
    profitable_all = [a for a in all_analyses if a.is_profitable]
    logger.info(f"Total profitable opportunities: {len(profitable_all)}")
    
    if profitable_all:
        logger.info("\n🏆 TOP 10 PROFITABLE OPPORTUNITIES:")
        profitable_all.sort(key=lambda x: x.net_profit_percent, reverse=True)
        for i, analysis in enumerate(profitable_all[:10], 1):
            logger.info(f"#{i:2d} | {analysis.exchange:8s} | {analysis.crypto:8s} | "
                       f"{analysis.pair1:12s} / {analysis.pair2:12s} | "
                       f"Profit: {analysis.net_profit_percent:6.3f}% | "
                       f"Spread: {analysis.raw_spread_percent:6.3f}% | "
                       f"Fees: {analysis.total_fees_percent:5.3f}%")
    
    # Save results
    results = {
        'total_analyzed': len(all_analyses),
        'profitable': len(profitable_all),
        'analyses': [
            {
                'exchange': a.exchange,
                'crypto': a.crypto,
                'pair1': a.pair1,
                'pair2': a.pair2,
                'price1': a.price1,
                'price2': a.price2,
                'raw_spread_percent': a.raw_spread_percent,
                'total_fees_percent': a.total_fees_percent,
                'estimated_slippage_percent': a.estimated_slippage_percent,
                'net_profit_percent': a.net_profit_percent,
                'is_profitable': a.is_profitable,
                'volume_usd': a.volume_usd
            }
            for a in all_analyses
        ]
    }
    
    with open('detailed_spread_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\n💾 Results saved to detailed_spread_analysis.json")

if __name__ == "__main__":
    asyncio.run(analyze_all_spreads())

