import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class PositionSizingData:
    """Data class for position sizing calculations"""
    symbol: str
    current_price: float
    spread_percent: float
    volatility: float
    volume_ratio: float
    success_rate: float
    avg_profit: float
    max_drawdown: float
    account_balance: float
    recommended_size: float
    kelly_fraction: float
    risk_score: float

class SmartPositionSizer:
    """Smart position sizing using Kelly criterion and risk management"""
    
    def __init__(self):
        self.trade_history = []
        self.performance_metrics = {}
        self.volatility_cache = {}
        self.volume_cache = {}
        
    def calculate_kelly_fraction(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Calculate Kelly criterion fraction for optimal position sizing
        
        Kelly % = (bp - q) / b
        where:
        b = odds received on the wager (decimal odds minus 1)
        p = probability of winning
        q = probability of losing (1 - p)
        """
        try:
            if avg_loss == 0:
                return 0.1  # Default conservative fraction
            
            # Calculate net profit per trade
            net_profit = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
            
            if net_profit <= 0:
                return 0.0  # No edge, don't trade
            
            # Kelly fraction calculation
            b = avg_win / avg_loss  # Odds ratio
            p = win_rate
            q = 1 - win_rate
            
            kelly_fraction = (b * p - q) / b
            
            # Cap at 25% to prevent over-leverage
            return min(max(kelly_fraction, 0.0), 0.25)
            
        except Exception as e:
            logger.error(f"Error calculating Kelly fraction: {str(e)}")
            return 0.1  # Default conservative fraction
    
    def calculate_position_size(self, symbol: str, spread_data: Dict, account_balance: float) -> PositionSizingData:
        """Calculate optimal position size for a given opportunity"""
        try:
            # Get asset-specific data
            asset_config = Config.TRANSFER_SPEEDS.get(symbol, {})
            base_position_limit = Config.POSITION_LIMITS.get(symbol, Config.MAX_POSITION_SIZE)
            
            # Get current price and spread
            current_price = spread_data.get('price1', 0)
            spread_percent = spread_data.get('spread_percent', 0)
            
            # Calculate volatility
            volatility = self._calculate_volatility(symbol)
            
            # Calculate volume ratio
            volume_ratio = self._calculate_volume_ratio(symbol)
            
            # Get historical performance
            success_rate, avg_profit, avg_loss = self._get_performance_metrics(symbol)
            
            # Calculate Kelly fraction
            kelly_fraction = self.calculate_kelly_fraction(success_rate, avg_profit, avg_loss)
            
            # Adjust Kelly fraction based on risk factors
            risk_adjusted_kelly = self._adjust_for_risk(kelly_fraction, volatility, volume_ratio, spread_percent)
            
            # Calculate position size
            position_value = account_balance * risk_adjusted_kelly
            
            # Apply position limits
            max_position = min(base_position_limit, position_value)
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(volatility, volume_ratio, spread_percent)
            
            return PositionSizingData(
                symbol=symbol,
                current_price=current_price,
                spread_percent=spread_percent,
                volatility=volatility,
                volume_ratio=volume_ratio,
                success_rate=success_rate,
                avg_profit=avg_profit,
                max_drawdown=0.0,  # Will be calculated separately
                account_balance=account_balance,
                recommended_size=max_position,
                kelly_fraction=risk_adjusted_kelly,
                risk_score=risk_score
            )
            
        except Exception as e:
            logger.error(f"Error calculating position size for {symbol}: {str(e)}")
            # Return conservative default
            return PositionSizingData(
                symbol=symbol,
                current_price=0,
                spread_percent=0,
                volatility=0,
                volume_ratio=0,
                success_rate=0.5,
                avg_profit=0,
                max_drawdown=0,
                account_balance=account_balance,
                recommended_size=account_balance * 0.05,  # 5% conservative
                kelly_fraction=0.05,
                risk_score=0.5
            )
    
    def _calculate_volatility(self, symbol: str) -> float:
        """Calculate recent volatility for the symbol"""
        try:
            # For now, use a simple volatility estimate
            # In production, this would use historical price data
            
            # Get symbol-specific volatility estimates
            volatility_estimates = {
                # Tier 1 - Low volatility
                'XRP/USDT': 0.02, 'XLM/USDT': 0.02, 'SOL/USDT': 0.03,
                'EOS/USDT': 0.03, 'TRX/USDT': 0.03, 'TON/USDT': 0.03,
                'BNB/USDT': 0.02, 'MATIC/USDT': 0.03, 'AVAX/USDT': 0.03,
                'DOT/USDT': 0.03, 'USDC/USDT': 0.001, 'USDT/USDC': 0.001,
                'DAI/USDT': 0.001, 'BUSD/USDT': 0.001, 'UNI/USDT': 0.03,
                'LINK/USDT': 0.03, 'ADA/USDT': 0.03,
                
                # Tier 2 - Medium volatility
                'XTZ/USDT': 0.04, 'MKR/USDT': 0.04, 'FIL/USDT': 0.04,
                'ATOM/USDT': 0.04, 'AAVE/USDT': 0.04, 'COMP/USDT': 0.04,
                'CRV/USDT': 0.04, 'SNX/USDT': 0.04, 'YFI/USDT': 0.04,
                '1INCH/USDT': 0.04,
                
                # Tier 3 - Higher volatility
                'LTC/USDT': 0.04, 'DOGE/USDT': 0.05, 'VET/USDT': 0.04,
                'BCH/USDT': 0.04, 'XMR/USDT': 0.04,
            }
            
            return volatility_estimates.get(symbol, 0.04)  # Default 4% volatility
            
        except Exception as e:
            logger.error(f"Error calculating volatility for {symbol}: {str(e)}")
            return 0.04  # Default volatility
    
    def _calculate_volume_ratio(self, symbol: str) -> float:
        """Calculate volume ratio for liquidity assessment"""
        try:
            # For now, use static volume estimates
            # In production, this would use real-time volume data
            
            volume_ratios = {
                # High volume assets
                'XRP/USDT': 1.0, 'XLM/USDT': 1.0, 'SOL/USDT': 1.0,
                'BNB/USDT': 1.0, 'LTC/USDT': 0.9, 'DOGE/USDT': 0.9,
                'USDC/USDT': 1.0, 'USDT/USDC': 1.0, 'DAI/USDT': 1.0,
                'BUSD/USDT': 1.0, 'UNI/USDT': 1.0, 'LINK/USDT': 1.0,
                'ADA/USDT': 1.0,
                
                # Medium volume assets
                'EOS/USDT': 0.8, 'TRX/USDT': 0.8, 'TON/USDT': 0.8,
                'MATIC/USDT': 0.8, 'AVAX/USDT': 0.8, 'DOT/USDT': 0.8,
                'XTZ/USDT': 0.7, 'MKR/USDT': 0.7, 'FIL/USDT': 0.7,
                'ATOM/USDT': 0.7, 'AAVE/USDT': 0.7, 'COMP/USDT': 0.7,
                'BCH/USDT': 0.7, 'XMR/USDT': 0.7,
                
                # Lower volume assets
                'CRV/USDT': 0.6, 'SNX/USDT': 0.6, 'YFI/USDT': 0.6,
                '1INCH/USDT': 0.6, 'VET/USDT': 0.6,
            }
            
            return volume_ratios.get(symbol, 0.6)  # Default medium volume
            
        except Exception as e:
            logger.error(f"Error calculating volume ratio for {symbol}: {str(e)}")
            return 0.6  # Default medium volume
    
    def _get_performance_metrics(self, symbol: str) -> Tuple[float, float, float]:
        """Get historical performance metrics for the symbol"""
        try:
            # For now, use estimated performance metrics
            # In production, this would use actual trade history
            
            performance_estimates = {
                # Tier 1 - High success rate
                'XRP/USDT': (0.85, 0.015, 0.005),  # 85% success, 1.5% avg win, 0.5% avg loss
                'XLM/USDT': (0.80, 0.012, 0.005),
                'SOL/USDT': (0.80, 0.013, 0.005),
                'EOS/USDT': (0.80, 0.010, 0.005),
                'TRX/USDT': (0.80, 0.010, 0.005),
                'TON/USDT': (0.75, 0.017, 0.005),  # Higher spread but more volatile
                'BNB/USDT': (0.80, 0.009, 0.005),
                'MATIC/USDT': (0.80, 0.009, 0.005),
                'AVAX/USDT': (0.80, 0.011, 0.005),
                'DOT/USDT': (0.80, 0.009, 0.005),
                'USDC/USDT': (0.95, 0.002, 0.001),  # Stablecoin - very high success
                'USDT/USDC': (0.95, 0.002, 0.001),
                'DAI/USDT': (0.90, 0.003, 0.001),
                'BUSD/USDT': (0.95, 0.002, 0.001),
                'UNI/USDT': (0.80, 0.011, 0.005),
                'LINK/USDT': (0.80, 0.011, 0.005),
                'ADA/USDT': (0.80, 0.009, 0.005),
                
                # Tier 2 - Medium success rate
                'XTZ/USDT': (0.75, 0.009, 0.005),
                'MKR/USDT': (0.75, 0.011, 0.005),
                'FIL/USDT': (0.75, 0.011, 0.005),
                'ATOM/USDT': (0.75, 0.011, 0.005),
                'AAVE/USDT': (0.75, 0.011, 0.005),
                'COMP/USDT': (0.75, 0.011, 0.005),
                'CRV/USDT': (0.70, 0.011, 0.005),
                'SNX/USDT': (0.70, 0.011, 0.005),
                'YFI/USDT': (0.70, 0.012, 0.005),
                '1INCH/USDT': (0.70, 0.011, 0.005),
                
                # Tier 3 - Lower success rate but still profitable
                'LTC/USDT': (0.75, 0.008, 0.005),
                'DOGE/USDT': (0.70, 0.010, 0.005),
                'VET/USDT': (0.70, 0.008, 0.005),
                'BCH/USDT': (0.70, 0.009, 0.005),
                'XMR/USDT': (0.70, 0.010, 0.005),
            }
            
            return performance_estimates.get(symbol, (0.70, 0.010, 0.005))  # Default metrics
            
        except Exception as e:
            logger.error(f"Error getting performance metrics for {symbol}: {str(e)}")
            return (0.70, 0.010, 0.005)  # Default metrics
    
    def _adjust_for_risk(self, kelly_fraction: float, volatility: float, volume_ratio: float, spread_percent: float) -> float:
        """Adjust Kelly fraction based on risk factors"""
        try:
            # Start with base Kelly fraction
            adjusted_fraction = kelly_fraction
            
            # Adjust for volatility (higher volatility = smaller position)
            volatility_multiplier = 1 - (volatility * 2)  # Reduce by 2x volatility
            adjusted_fraction *= max(volatility_multiplier, 0.1)  # Minimum 10%
            
            # Adjust for volume/liquidity (lower volume = smaller position)
            volume_multiplier = volume_ratio
            adjusted_fraction *= volume_multiplier
            
            # Adjust for spread size (larger spreads = larger position, but cap it)
            spread_multiplier = min(1 + (spread_percent * 10), 2.0)  # Max 2x
            adjusted_fraction *= spread_multiplier
            
            # Apply final caps
            adjusted_fraction = min(max(adjusted_fraction, 0.01), 0.25)  # Between 1% and 25%
            
            return adjusted_fraction
            
        except Exception as e:
            logger.error(f"Error adjusting for risk: {str(e)}")
            return 0.1  # Default conservative fraction
    
    def _calculate_risk_score(self, volatility: float, volume_ratio: float, spread_percent: float) -> float:
        """Calculate overall risk score (0-1, where 0 is low risk, 1 is high risk)"""
        try:
            # Higher volatility = higher risk
            volatility_score = min(volatility * 10, 1.0)  # Scale volatility to 0-1
            
            # Lower volume = higher risk
            volume_score = 1 - volume_ratio
            
            # Lower spread = higher risk (less profit margin)
            spread_score = max(0, 1 - (spread_percent * 50))  # Scale spread to 0-1
            
            # Weighted average
            risk_score = (volatility_score * 0.4 + volume_score * 0.3 + spread_score * 0.3)
            
            return min(max(risk_score, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {str(e)}")
            return 0.5  # Default medium risk
    
    def update_trade_history(self, trade_data: Dict):
        """Update trade history for performance tracking"""
        try:
            self.trade_history.append({
                'timestamp': trade_data.get('timestamp', 0),
                'symbol': trade_data.get('symbol', ''),
                'profit': trade_data.get('profit', 0),
                'amount': trade_data.get('amount', 0),
                'spread': trade_data.get('spread', 0),
                'success': trade_data.get('profit', 0) > 0
            })
            
            # Keep only recent trades (last 1000)
            if len(self.trade_history) > 1000:
                self.trade_history = self.trade_history[-1000:]
                
        except Exception as e:
            logger.error(f"Error updating trade history: {str(e)}")
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary for all symbols"""
        try:
            if not self.trade_history:
                return {}
            
            # Group by symbol
            symbol_performance = {}
            for trade in self.trade_history:
                symbol = trade['symbol']
                if symbol not in symbol_performance:
                    symbol_performance[symbol] = {
                        'total_trades': 0,
                        'successful_trades': 0,
                        'total_profit': 0,
                        'avg_profit': 0,
                        'success_rate': 0,
                        'total_volume': 0
                    }
                
                perf = symbol_performance[symbol]
                perf['total_trades'] += 1
                perf['total_profit'] += trade['profit']
                perf['total_volume'] += trade['amount']
                
                if trade['success']:
                    perf['successful_trades'] += 1
            
            # Calculate derived metrics
            for symbol, perf in symbol_performance.items():
                if perf['total_trades'] > 0:
                    perf['success_rate'] = perf['successful_trades'] / perf['total_trades']
                    perf['avg_profit'] = perf['total_profit'] / perf['total_trades']
            
            return symbol_performance
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {str(e)}")
            return {}
