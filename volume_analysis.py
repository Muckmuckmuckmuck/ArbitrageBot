import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class VolumeAnalysis:
    """Data class for volume analysis results"""
    symbol: str
    current_volume: float
    avg_volume_24h: float
    volume_ratio: float
    volume_trend: str  # 'increasing', 'decreasing', 'stable'
    liquidity_score: float
    market_depth: float
    order_book_imbalance: float
    volume_profile: Dict[str, float]

class VolumeAnalyzer:
    """Volume analysis for arbitrage opportunities"""
    
    def __init__(self):
        self.volume_history = {}
        self.liquidity_cache = {}
        self.order_book_cache = {}
        
    async def analyze_volume(self, symbol: str, exchange_manager) -> VolumeAnalysis:
        """Analyze volume metrics for a symbol"""
        try:
            # Get current volume data
            current_volume = await self._get_current_volume(symbol, exchange_manager)
            
            # Get historical volume data
            avg_volume_24h = await self._get_avg_volume_24h(symbol, exchange_manager)
            
            # Calculate volume ratio
            volume_ratio = current_volume / avg_volume_24h if avg_volume_24h > 0 else 1.0
            
            # Determine volume trend
            volume_trend = self._determine_volume_trend(symbol, volume_ratio)
            
            # Calculate liquidity score
            liquidity_score = self._calculate_liquidity_score(volume_ratio, current_volume)
            
            # Analyze market depth
            market_depth = await self._analyze_market_depth(symbol, exchange_manager)
            
            # Analyze order book imbalance
            order_book_imbalance = await self._analyze_order_book_imbalance(symbol, exchange_manager)
            
            # Create volume profile
            volume_profile = self._create_volume_profile(symbol, current_volume, avg_volume_24h)
            
            return VolumeAnalysis(
                symbol=symbol,
                current_volume=current_volume,
                avg_volume_24h=avg_volume_24h,
                volume_ratio=volume_ratio,
                volume_trend=volume_trend,
                liquidity_score=liquidity_score,
                market_depth=market_depth,
                order_book_imbalance=order_book_imbalance,
                volume_profile=volume_profile
            )
            
        except Exception as e:
            logger.error(f"Error analyzing volume for {symbol}: {str(e)}")
            return self._get_default_volume_analysis(symbol)
    
    async def _get_current_volume(self, symbol: str, exchange_manager) -> float:
        """Get current trading volume for the symbol"""
        try:
            # Get volume from both exchanges
            binance = exchange_manager.get_exchange('binance')
            kraken = exchange_manager.get_exchange('kraken')
            
            binance_ticker = await binance.get_ticker(symbol)
            kraken_ticker = await kraken.get_ticker(symbol)
            
            # Combine volumes from both exchanges
            total_volume = 0
            if binance_ticker and 'baseVolume' in binance_ticker:
                total_volume += binance_ticker['baseVolume']
            if kraken_ticker and 'baseVolume' in kraken_ticker:
                total_volume += kraken_ticker['baseVolume']
            
            return total_volume
            
        except Exception as e:
            logger.error(f"Error getting current volume for {symbol}: {str(e)}")
            return 1000000  # Default volume
    
    async def _get_avg_volume_24h(self, symbol: str, exchange_manager) -> float:
        """Get average 24-hour volume for the symbol"""
        try:
            # For now, use static estimates based on symbol
            # In production, this would use historical data
            
            volume_estimates = {
                # High volume assets
                'XRP/USDT': 50000000, 'XLM/USDT': 40000000, 'SOL/USDT': 30000000,
                'BNB/USDT': 60000000, 'LTC/USDT': 25000000, 'DOGE/USDT': 20000000,
                'USDC/USDT': 100000000, 'USDT/USDC': 100000000, 'DAI/USDT': 80000000,
                'BUSD/USDT': 50000000, 'UNI/USDT': 25000000, 'LINK/USDT': 30000000,
                'ADA/USDT': 35000000,
                
                # Medium volume assets
                'EOS/USDT': 15000000, 'TRX/USDT': 18000000, 'TON/USDT': 12000000,
                'MATIC/USDT': 16000000, 'AVAX/USDT': 14000000, 'DOT/USDT': 13000000,
                'XTZ/USDT': 7000000, 'MKR/USDT': 8000000, 'FIL/USDT': 9000000,
                'ATOM/USDT': 8000000, 'AAVE/USDT': 6000000, 'COMP/USDT': 5000000,
                'BCH/USDT': 10000000, 'XMR/USDT': 8000000,
                
                # Lower volume assets
                'CRV/USDT': 4000000, 'SNX/USDT': 3000000, 'YFI/USDT': 2000000,
                '1INCH/USDT': 3000000, 'VET/USDT': 4000000,
            }
            
            return volume_estimates.get(symbol, 5000000)  # Default 5M volume
            
        except Exception as e:
            logger.error(f"Error getting avg volume 24h for {symbol}: {str(e)}")
            return 5000000  # Default volume
    
    def _determine_volume_trend(self, symbol: str, volume_ratio: float) -> str:
        """Determine volume trend based on current vs average volume"""
        try:
            if volume_ratio > 1.5:
                return 'increasing'
            elif volume_ratio < 0.7:
                return 'decreasing'
            else:
                return 'stable'
                
        except Exception as e:
            logger.error(f"Error determining volume trend for {symbol}: {str(e)}")
            return 'stable'
    
    def _calculate_liquidity_score(self, volume_ratio: float, current_volume: float) -> float:
        """Calculate liquidity score (0-1, where 1 is high liquidity)"""
        try:
            # Base score from volume ratio
            ratio_score = min(volume_ratio, 2.0) / 2.0  # Cap at 2x and normalize
            
            # Volume magnitude score
            if current_volume > 10000000:  # 10M+
                magnitude_score = 1.0
            elif current_volume > 5000000:  # 5M+
                magnitude_score = 0.8
            elif current_volume > 1000000:  # 1M+
                magnitude_score = 0.6
            else:
                magnitude_score = 0.4
            
            # Combined score
            liquidity_score = (ratio_score * 0.6 + magnitude_score * 0.4)
            
            return min(max(liquidity_score, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating liquidity score: {str(e)}")
            return 0.5  # Default medium liquidity
    
    async def _analyze_market_depth(self, symbol: str, exchange_manager) -> float:
        """Analyze market depth for the symbol"""
        try:
            # Get order book from both exchanges
            binance = exchange_manager.get_exchange('binance')
            kraken = exchange_manager.get_exchange('kraken')
            
            binance_orderbook = await binance.get_orderbook(symbol, 10)
            kraken_orderbook = await kraken.get_orderbook(symbol, 10)
            
            # Calculate total depth
            total_depth = 0
            
            # Binance depth
            if binance_orderbook and 'asks' in binance_orderbook:
                for ask in binance_orderbook['asks'][:5]:  # Top 5 levels
                    total_depth += ask[0] * ask[1]  # price * quantity
            
            # Kraken depth
            if kraken_orderbook and 'asks' in kraken_orderbook:
                for ask in kraken_orderbook['asks'][:5]:  # Top 5 levels
                    total_depth += ask[0] * ask[1]  # price * quantity
            
            # Normalize depth score
            if total_depth > 1000000:  # 1M+
                depth_score = 1.0
            elif total_depth > 500000:  # 500K+
                depth_score = 0.8
            elif total_depth > 100000:  # 100K+
                depth_score = 0.6
            else:
                depth_score = 0.4
            
            return depth_score
            
        except Exception as e:
            logger.error(f"Error analyzing market depth for {symbol}: {str(e)}")
            return 0.6  # Default medium depth
    
    async def _analyze_order_book_imbalance(self, symbol: str, exchange_manager) -> float:
        """Analyze order book imbalance"""
        try:
            # Get order book from both exchanges
            binance = exchange_manager.get_exchange('binance')
            kraken = exchange_manager.get_exchange('kraken')
            
            binance_orderbook = await binance.get_orderbook(symbol, 10)
            kraken_orderbook = await kraken.get_orderbook(symbol, 10)
            
            total_imbalance = 0
            exchange_count = 0
            
            # Analyze Binance order book
            if binance_orderbook and 'bids' in binance_orderbook and 'asks' in binance_orderbook:
                bid_volume = sum([bid[1] for bid in binance_orderbook['bids'][:5]])
                ask_volume = sum([ask[1] for ask in binance_orderbook['asks'][:5]])
                
                if bid_volume + ask_volume > 0:
                    imbalance = abs(bid_volume - ask_volume) / (bid_volume + ask_volume)
                    total_imbalance += imbalance
                    exchange_count += 1
            
            # Analyze Kraken order book
            if kraken_orderbook and 'bids' in kraken_orderbook and 'asks' in kraken_orderbook:
                bid_volume = sum([bid[1] for bid in kraken_orderbook['bids'][:5]])
                ask_volume = sum([ask[1] for ask in kraken_orderbook['asks'][:5]])
                
                if bid_volume + ask_volume > 0:
                    imbalance = abs(bid_volume - ask_volume) / (bid_volume + ask_volume)
                    total_imbalance += imbalance
                    exchange_count += 1
            
            # Calculate average imbalance
            if exchange_count > 0:
                avg_imbalance = total_imbalance / exchange_count
            else:
                avg_imbalance = 0.1  # Default low imbalance
            
            return min(max(avg_imbalance, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Error analyzing order book imbalance for {symbol}: {str(e)}")
            return 0.1  # Default low imbalance
    
    def _create_volume_profile(self, symbol: str, current_volume: float, avg_volume_24h: float) -> Dict[str, float]:
        """Create volume profile for the symbol"""
        try:
            return {
                'current_volume': current_volume,
                'avg_volume_24h': avg_volume_24h,
                'volume_ratio': current_volume / avg_volume_24h if avg_volume_24h > 0 else 1.0,
                'volume_percentile': min(current_volume / 10000000 * 100, 100),  # Scale to 0-100%
                'liquidity_tier': self._get_liquidity_tier(current_volume)
            }
            
        except Exception as e:
            logger.error(f"Error creating volume profile for {symbol}: {str(e)}")
            return {
                'current_volume': 1000000,
                'avg_volume_24h': 1000000,
                'volume_ratio': 1.0,
                'volume_percentile': 50,
                'liquidity_tier': 'medium'
            }
    
    def _get_liquidity_tier(self, volume: float) -> str:
        """Get liquidity tier based on volume"""
        try:
            if volume > 20000000:  # 20M+
                return 'high'
            elif volume > 5000000:  # 5M+
                return 'medium'
            else:
                return 'low'
                
        except Exception as e:
            logger.error(f"Error getting liquidity tier: {str(e)}")
            return 'medium'
    
    def _get_default_volume_analysis(self, symbol: str) -> VolumeAnalysis:
        """Get default volume analysis when real data is unavailable"""
        return VolumeAnalysis(
            symbol=symbol,
            current_volume=1000000,
            avg_volume_24h=1000000,
            volume_ratio=1.0,
            volume_trend='stable',
            liquidity_score=0.6,
            market_depth=0.6,
            order_book_imbalance=0.1,
            volume_profile={
                'current_volume': 1000000,
                'avg_volume_24h': 1000000,
                'volume_ratio': 1.0,
                'volume_percentile': 50,
                'liquidity_tier': 'medium'
            }
        )
    
    def update_volume_history(self, symbol: str, volume_data: VolumeAnalysis):
        """Update volume history for trend analysis"""
        try:
            if symbol not in self.volume_history:
                self.volume_history[symbol] = []
            
            self.volume_history[symbol].append({
                'timestamp': volume_data.current_volume,  # Using current volume as timestamp placeholder
                'volume': volume_data.current_volume,
                'ratio': volume_data.volume_ratio,
                'trend': volume_data.volume_trend
            })
            
            # Keep only recent history (last 100 entries)
            if len(self.volume_history[symbol]) > 100:
                self.volume_history[symbol] = self.volume_history[symbol][-100:]
                
        except Exception as e:
            logger.error(f"Error updating volume history for {symbol}: {str(e)}")
    
    def get_volume_summary(self) -> Dict:
        """Get volume analysis summary for all symbols"""
        try:
            summary = {}
            
            for symbol, history in self.volume_history.items():
                if history:
                    recent_volumes = [h['volume'] for h in history[-10:]]  # Last 10 entries
                    recent_ratios = [h['ratio'] for h in history[-10:]]
                    
                    summary[symbol] = {
                        'avg_recent_volume': np.mean(recent_volumes) if recent_volumes else 0,
                        'avg_recent_ratio': np.mean(recent_ratios) if recent_ratios else 1.0,
                        'volume_stability': 1 - np.std(recent_ratios) if len(recent_ratios) > 1 else 0.5,
                        'trend_consistency': len(set([h['trend'] for h in history[-5:]])) == 1 if len(history) >= 5 else False
                    }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting volume summary: {str(e)}")
            return {}
