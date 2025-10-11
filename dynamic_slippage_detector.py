#!/usr/bin/env python3
"""
Dynamic Slippage Detector
Real-time slippage detection and prediction using order book analysis
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from collections import deque
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

class DynamicSlippageDetector:
    """Detects and predicts slippage in real-time"""
    
    def __init__(self, config):
        self.config = config
        self.base_slippage = config.SLIPPAGE_ESTIMATES.copy()
        self.current_slippage = config.SLIPPAGE_ESTIMATES.copy()
        
        # Track historical slippage
        self.slippage_history: Dict[str, deque] = {}
        for symbol in config.CURRENCY_PAIRS:
            self.slippage_history[symbol] = deque(maxlen=config.DYNAMIC_SLIPPAGE['historical_lookback'])
        
        logger.info("Dynamic Slippage Detector initialized")
    
    def analyze_order_book(self, symbol: str, order_book: Dict[str, Any], 
                          position_size: float, side: str) -> Dict[str, Any]:
        """Analyze order book to predict slippage"""
        
        if not self.config.DYNAMIC_SLIPPAGE['enabled']:
            return {
                'predicted_slippage': self.current_slippage.get(symbol, 0.001),
                'sufficient_liquidity': True,
                'analysis': 'Slippage detection disabled'
            }
        
        try:
            # Get relevant side of order book
            levels = order_book['asks'] if side == 'buy' else order_book['bids']
            
            if not levels or len(levels) == 0:
                logger.warning(f"{symbol}: Empty order book")
                return {
                    'predicted_slippage': 0.005,  # High slippage estimate
                    'sufficient_liquidity': False,
                    'analysis': 'Empty order book'
                }
            
            # Analyze depth
            depth_analysis = self._analyze_depth(levels, position_size)
            
            # Predict slippage
            predicted_slippage = self._predict_slippage(
                symbol, depth_analysis, position_size
            )
            
            # Check if liquidity is sufficient
            min_liquidity_ratio = self.config.DYNAMIC_SLIPPAGE['min_liquidity_ratio']
            sufficient_liquidity = depth_analysis['total_liquidity'] >= position_size * min_liquidity_ratio
            
            # Determine if acceptable
            max_acceptable = self.config.DYNAMIC_SLIPPAGE['max_acceptable_slippage']
            warning_threshold = self.config.DYNAMIC_SLIPPAGE['warning_slippage']
            
            if predicted_slippage > max_acceptable:
                status = 'REJECT'
                logger.warning(f"⛔ {symbol}: Predicted slippage {predicted_slippage*100:.2f}% > max {max_acceptable*100:.2f}%")
            elif predicted_slippage > warning_threshold:
                status = 'WARNING'
                logger.warning(f"⚠️  {symbol}: Predicted slippage {predicted_slippage*100:.2f}% > warning {warning_threshold*100:.2f}%")
            else:
                status = 'OK'
                logger.debug(f"✅ {symbol}: Predicted slippage {predicted_slippage*100:.2f}% acceptable")
            
            return {
                'predicted_slippage': predicted_slippage,
                'sufficient_liquidity': sufficient_liquidity,
                'status': status,
                'depth_analysis': depth_analysis,
                'analysis': f"Slippage: {predicted_slippage*100:.2f}%, Liquidity: ${depth_analysis['total_liquidity']:,.0f}"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing order book for {symbol}: {e}")
            return {
                'predicted_slippage': 0.005,
                'sufficient_liquidity': False,
                'analysis': f'Error: {str(e)}'
            }
    
    def _analyze_depth(self, levels: List[List[float]], position_size: float) -> Dict[str, Any]:
        """Analyze order book depth"""
        
        if not levels:
            return {
                'total_liquidity': 0,
                'avg_price': 0,
                'price_impact': 0,
                'levels_needed': 0
            }
        
        # Calculate how many levels needed to fill order
        cumulative_size = 0
        cumulative_cost = 0
        levels_needed = 0
        first_price = levels[0][0]
        
        for price, size in levels[:self.config.DYNAMIC_SLIPPAGE['order_book_depth_levels']]:
            if cumulative_size >= position_size:
                break
            
            remaining = position_size - cumulative_size
            fill_size = min(remaining, size)
            
            cumulative_size += fill_size
            cumulative_cost += fill_size * price
            levels_needed += 1
        
        if cumulative_size == 0:
            return {
                'total_liquidity': 0,
                'avg_price': 0,
                'price_impact': 0,
                'levels_needed': 0
            }
        
        avg_price = cumulative_cost / cumulative_size
        price_impact = abs(avg_price - first_price) / first_price
        
        # Total available liquidity in order book
        total_liquidity = sum(size * price for price, size in levels[:self.config.DYNAMIC_SLIPPAGE['order_book_depth_levels']])
        
        return {
            'total_liquidity': total_liquidity,
            'avg_price': avg_price,
            'price_impact': price_impact,
            'levels_needed': levels_needed,
            'first_price': first_price,
        }
    
    def _predict_slippage(self, symbol: str, depth_analysis: Dict[str, Any], 
                         position_size: float) -> float:
        """Predict slippage based on order book analysis and historical data"""
        
        # Base slippage from order book analysis
        order_book_slippage = depth_analysis['price_impact']
        
        # Get historical average slippage
        if symbol in self.slippage_history and len(self.slippage_history[symbol]) > 0:
            historical_slippages = list(self.slippage_history[symbol])
            historical_avg = np.mean(historical_slippages)
            historical_std = np.std(historical_slippages)
            
            # Use ML prediction if enabled
            if self.config.DYNAMIC_SLIPPAGE['use_ml_prediction']:
                # Simple weighted average (can be replaced with actual ML model)
                predicted_slippage = (
                    0.5 * order_book_slippage +  # 50% weight on order book
                    0.3 * historical_avg +        # 30% weight on historical avg
                    0.2 * historical_std          # 20% weight on volatility
                )
            else:
                # Simple average
                predicted_slippage = (order_book_slippage + historical_avg) / 2
        else:
            # No historical data, use order book only
            predicted_slippage = order_book_slippage
        
        # Add base slippage estimate
        base_slippage = self.base_slippage.get(symbol, 0.001)
        predicted_slippage = max(predicted_slippage, base_slippage)
        
        # Update current slippage estimate
        self.current_slippage[symbol] = predicted_slippage
        
        return predicted_slippage
    
    def record_actual_slippage(self, symbol: str, expected_price: float, 
                              actual_price: float, side: str):
        """Record actual slippage experienced"""
        
        # Calculate actual slippage
        if side == 'buy':
            slippage = (actual_price - expected_price) / expected_price
        else:  # sell
            slippage = (expected_price - actual_price) / expected_price
        
        slippage = abs(slippage)
        
        # Record in history
        if symbol not in self.slippage_history:
            self.slippage_history[symbol] = deque(maxlen=self.config.DYNAMIC_SLIPPAGE['historical_lookback'])
        
        self.slippage_history[symbol].append(slippage)
        
        logger.info(f"{symbol}: Actual slippage {slippage*100:.3f}% "
                   f"(Expected: ${expected_price:.6f}, Actual: ${actual_price:.6f})")
    
    def adjust_position_for_slippage(self, symbol: str, original_position: float, 
                                     predicted_slippage: float) -> float:
        """Adjust position size if slippage is high"""
        
        if not self.config.DYNAMIC_SLIPPAGE['adjust_position_size']:
            return original_position
        
        warning_threshold = self.config.DYNAMIC_SLIPPAGE['warning_slippage']
        
        if predicted_slippage > warning_threshold:
            # Reduce position size
            scale_factor = self.config.DYNAMIC_SLIPPAGE['slippage_scale_factor']
            adjusted_position = original_position * scale_factor
            
            logger.warning(f"⚠️  {symbol}: Reducing position size due to high slippage "
                          f"(${original_position:,.0f} → ${adjusted_position:,.0f})")
            
            return adjusted_position
        
        return original_position
    
    def get_slippage_statistics(self, symbol: str) -> Dict[str, Any]:
        """Get slippage statistics for a symbol"""
        
        if symbol not in self.slippage_history or len(self.slippage_history[symbol]) == 0:
            return {
                'trades_recorded': 0,
                'avg_slippage': 0,
                'min_slippage': 0,
                'max_slippage': 0,
                'std_slippage': 0,
                'current_estimate': self.current_slippage.get(symbol, 0.001)
            }
        
        slippages = list(self.slippage_history[symbol])
        
        return {
            'trades_recorded': len(slippages),
            'avg_slippage': np.mean(slippages),
            'min_slippage': np.min(slippages),
            'max_slippage': np.max(slippages),
            'std_slippage': np.std(slippages),
            'current_estimate': self.current_slippage.get(symbol, 0.001),
            'base_estimate': self.base_slippage.get(symbol, 0.001),
        }
    
    def get_all_slippage_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get slippage statistics for all symbols"""
        stats = {}
        for symbol in self.config.CURRENCY_PAIRS:
            stats[symbol] = self.get_slippage_statistics(symbol)
        return stats
