import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from exchanges import ExchangeManager
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class RiskMetrics:
    """Data class for risk metrics"""
    total_exposure: float
    daily_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    avg_trade_size: float
    timestamp: float

@dataclass
class RiskAlert:
    """Data class for risk alerts"""
    alert_type: str
    severity: str
    message: str
    timestamp: float
    data: Optional[Dict] = None

class RiskManager:
    """Comprehensive risk management system"""
    
    def __init__(self, exchange_manager: ExchangeManager):
        self.exchange_manager = exchange_manager
        self.risk_metrics = RiskMetrics(0, 0, 0, 0, 0, 0, time.time())
        self.risk_alerts: List[RiskAlert] = []
        self.daily_pnl_history = []
        self.trade_history = []
        self.max_daily_loss = Config.MAX_POSITION_SIZE * 0.1  # 10% of max position
        self.max_position_size = Config.MAX_POSITION_SIZE
        self.max_daily_trades = Config.MAX_DAILY_TRADES
        self.stop_loss_percent = Config.STOP_LOSS_PERCENT
        self.emergency_stop = False
        self.last_balance_check = time.time()
        
    async def check_risk_limits(self, symbol: str, amount: float, price: float) -> Tuple[bool, str]:
        """Check if trade meets risk management criteria"""
        try:
            # Check emergency stop
            if self.emergency_stop:
                return False, "Emergency stop activated"
            
            # Check daily trade limit
            if len(self.trade_history) >= self.max_daily_trades:
                return False, "Daily trade limit exceeded"
            
            # Check position size
            trade_value = amount * price
            if trade_value > self.max_position_size:
                return False, f"Trade size {trade_value} exceeds maximum position size {self.max_position_size}"
            
            # Check daily loss limit
            if self.risk_metrics.daily_pnl < -self.max_daily_loss:
                return False, f"Daily loss limit exceeded: {self.risk_metrics.daily_pnl}"
            
            # Check account balance
            if not await self._check_sufficient_balance(symbol, amount, price):
                return False, "Insufficient account balance"
            
            # Check market conditions
            if not await self._check_market_conditions(symbol):
                return False, "Unfavorable market conditions"
            
            # Check correlation risk
            if not await self._check_correlation_risk(symbol, amount):
                return False, "High correlation risk detected"
            
            return True, "Risk checks passed"
            
        except Exception as e:
            logger.error(f"Error in risk check: {str(e)}")
            return False, f"Risk check error: {str(e)}"
    
    async def _check_sufficient_balance(self, symbol: str, amount: float, price: float) -> bool:
        """Check if there's sufficient balance for the trade"""
        try:
            base_currency = symbol.split('/')[0]
            quote_currency = symbol.split('/')[1]
            
            # Check balance on both exchanges
            for exchange_name in ['binance', 'kraken']:
                exchange = self.exchange_manager.get_exchange(exchange_name)
                balance = exchange.balances.get(quote_currency, {}).get('free', 0)
                
                required_amount = amount * price
                if balance < required_amount * 1.1:  # 10% buffer
                    logger.warning(f"Insufficient {quote_currency} balance on {exchange_name}: {balance} < {required_amount * 1.1}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking balance: {str(e)}")
            return False
    
    async def _check_market_conditions(self, symbol: str) -> bool:
        """Check if market conditions are favorable for trading"""
        try:
            # Get current prices from both exchanges
            binance = self.exchange_manager.get_exchange('binance')
            kraken = self.exchange_manager.get_exchange('kraken')
            
            try:
                binance_ticker = await binance.get_ticker(symbol)
                kraken_ticker = await kraken.get_ticker(symbol)
                
                # Check for extreme price movements
                binance_price = binance_ticker['last']
                kraken_price = kraken_ticker['last']
                
                price_diff = abs(binance_price - kraken_price) / min(binance_price, kraken_price)
                
                # If price difference is too high, market might be volatile
                if price_diff > 0.05:  # 5% difference
                    logger.warning(f"High price volatility detected for {symbol}: {price_diff:.2%}")
                    return False
                
                # Check volume
                binance_volume = binance_ticker.get('baseVolume', 0)
                kraken_volume = kraken_ticker.get('baseVolume', 0)
                
                if binance_volume < 1000 or kraken_volume < 1000:  # Minimum volume threshold
                    logger.warning(f"Low volume detected for {symbol}")
                    return False
                
                return True
                
            except Exception as e:
                logger.error(f"Error checking market conditions: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Error in market condition check: {str(e)}")
            return False
    
    async def _check_correlation_risk(self, symbol: str, amount: float) -> bool:
        """Check for correlation risk with existing positions"""
        try:
            # Simple correlation check - avoid trading same symbol multiple times in short period
            recent_trades = [t for t in self.trade_history if time.time() - t['timestamp'] < 300]  # 5 minutes
            
            same_symbol_trades = [t for t in recent_trades if t['symbol'] == symbol]
            
            if len(same_symbol_trades) >= 3:  # Max 3 trades per symbol in 5 minutes
                logger.warning(f"High correlation risk for {symbol}: {len(same_symbol_trades)} recent trades")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking correlation risk: {str(e)}")
            return False
    
    def update_trade_history(self, trade_data: Dict):
        """Update trade history for risk analysis"""
        try:
            trade_data['timestamp'] = time.time()
            self.trade_history.append(trade_data)
            
            # Keep only recent trades (last 24 hours)
            cutoff_time = time.time() - 86400
            self.trade_history = [t for t in self.trade_history if t['timestamp'] > cutoff_time]
            
            # Update daily P&L
            if trade_data['status'] == 'completed':
                pnl = (trade_data['sell_price'] - trade_data['buy_price']) * trade_data['amount']
                self.risk_metrics.daily_pnl += pnl
                self.daily_pnl_history.append({
                    'timestamp': time.time(),
                    'pnl': pnl,
                    'cumulative_pnl': self.risk_metrics.daily_pnl
                })
            
            # Check for risk alerts
            self._check_risk_alerts()
            
        except Exception as e:
            logger.error(f"Error updating trade history: {str(e)}")
    
    def _check_risk_alerts(self):
        """Check for risk conditions and generate alerts"""
        try:
            current_time = time.time()
            
            # Check daily loss limit
            if self.risk_metrics.daily_pnl < -self.max_daily_loss:
                alert = RiskAlert(
                    alert_type="daily_loss_limit",
                    severity="critical",
                    message=f"Daily loss limit exceeded: {self.risk_metrics.daily_pnl:.2f}",
                    timestamp=current_time,
                    data={"daily_pnl": self.risk_metrics.daily_pnl, "limit": -self.max_daily_loss}
                )
                self.risk_alerts.append(alert)
                self.emergency_stop = True
                logger.critical(f"EMERGENCY STOP: {alert.message}")
            
            # Check drawdown
            if len(self.daily_pnl_history) > 0:
                peak_pnl = max([h['cumulative_pnl'] for h in self.daily_pnl_history])
                current_drawdown = (peak_pnl - self.risk_metrics.daily_pnl) / peak_pnl if peak_pnl > 0 else 0
                
                if current_drawdown > 0.15:  # 15% drawdown
                    alert = RiskAlert(
                        alert_type="high_drawdown",
                        severity="warning",
                        message=f"High drawdown detected: {current_drawdown:.2%}",
                        timestamp=current_time,
                        data={"drawdown": current_drawdown, "peak_pnl": peak_pnl}
                    )
                    self.risk_alerts.append(alert)
                    logger.warning(alert.message)
            
            # Check trade frequency
            recent_trades = [t for t in self.trade_history if current_time - t['timestamp'] < 3600]  # 1 hour
            
            if len(recent_trades) > 20:  # More than 20 trades per hour
                alert = RiskAlert(
                    alert_type="high_trade_frequency",
                    severity="warning",
                    message=f"High trade frequency: {len(recent_trades)} trades in last hour",
                    timestamp=current_time,
                    data={"trade_count": len(recent_trades), "timeframe": "1 hour"}
                )
                self.risk_alerts.append(alert)
                logger.warning(alert.message)
            
            # Keep only recent alerts (last 24 hours)
            cutoff_time = current_time - 86400
            self.risk_alerts = [a for a in self.risk_alerts if a.timestamp > cutoff_time]
            
        except Exception as e:
            logger.error(f"Error checking risk alerts: {str(e)}")
    
    def calculate_risk_metrics(self) -> RiskMetrics:
        """Calculate current risk metrics"""
        try:
            # Calculate total exposure
            total_exposure = 0
            for exchange_name in ['binance', 'kraken']:
                exchange = self.exchange_manager.get_exchange(exchange_name)
                for currency, balance in exchange.balances.items():
                    if isinstance(balance, dict) and 'free' in balance:
                        total_exposure += balance['free'] * 1  # Simplified calculation
            
            # Calculate win rate
            completed_trades = [t for t in self.trade_history if t['status'] == 'completed']
            winning_trades = [t for t in completed_trades if (t['sell_price'] - t['buy_price']) > 0]
            win_rate = len(winning_trades) / len(completed_trades) if completed_trades else 0
            
            # Calculate average trade size
            avg_trade_size = sum([t['amount'] * t['buy_price'] for t in completed_trades]) / len(completed_trades) if completed_trades else 0
            
            # Calculate Sharpe ratio (simplified)
            if len(self.daily_pnl_history) > 1:
                returns = [h['pnl'] for h in self.daily_pnl_history]
                avg_return = sum(returns) / len(returns)
                variance = sum([(r - avg_return) ** 2 for r in returns]) / len(returns)
                sharpe_ratio = avg_return / (variance ** 0.5) if variance > 0 else 0
            else:
                sharpe_ratio = 0
            
            # Calculate max drawdown
            if len(self.daily_pnl_history) > 0:
                cumulative_pnl = [h['cumulative_pnl'] for h in self.daily_pnl_history]
                peak = cumulative_pnl[0]
                max_drawdown = 0
                for pnl in cumulative_pnl:
                    if pnl > peak:
                        peak = pnl
                    drawdown = (peak - pnl) / peak if peak > 0 else 0
                    max_drawdown = max(max_drawdown, drawdown)
            else:
                max_drawdown = 0
            
            self.risk_metrics = RiskMetrics(
                total_exposure=total_exposure,
                daily_pnl=self.risk_metrics.daily_pnl,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                win_rate=win_rate,
                avg_trade_size=avg_trade_size,
                timestamp=time.time()
            )
            
            return self.risk_metrics
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {str(e)}")
            return self.risk_metrics
    
    def get_risk_summary(self) -> Dict:
        """Get comprehensive risk summary"""
        try:
            metrics = self.calculate_risk_metrics()
            
            # Get recent alerts
            recent_alerts = [a for a in self.risk_alerts if time.time() - a.timestamp < 3600]  # Last hour
            
            return {
                'risk_metrics': {
                    'total_exposure': metrics.total_exposure,
                    'daily_pnl': metrics.daily_pnl,
                    'max_drawdown': metrics.max_drawdown,
                    'sharpe_ratio': metrics.sharpe_ratio,
                    'win_rate': metrics.win_rate,
                    'avg_trade_size': metrics.avg_trade_size
                },
                'risk_limits': {
                    'max_daily_loss': self.max_daily_loss,
                    'max_position_size': self.max_position_size,
                    'max_daily_trades': self.max_daily_trades,
                    'stop_loss_percent': self.stop_loss_percent
                },
                'current_status': {
                    'emergency_stop': self.emergency_stop,
                    'daily_trade_count': len(self.trade_history),
                    'recent_alerts': len(recent_alerts)
                },
                'alerts': [{
                    'type': a.alert_type,
                    'severity': a.severity,
                    'message': a.message,
                    'timestamp': a.timestamp
                } for a in recent_alerts]
            }
            
        except Exception as e:
            logger.error(f"Error getting risk summary: {str(e)}")
            return {}
    
    def reset_daily_metrics(self):
        """Reset daily metrics (call at start of new day)"""
        try:
            self.risk_metrics.daily_pnl = 0
            self.daily_pnl_history = []
            self.trade_history = []
            self.risk_alerts = []
            self.emergency_stop = False
            logger.info("Daily risk metrics reset")
            
        except Exception as e:
            logger.error(f"Error resetting daily metrics: {str(e)}")
    
    def emergency_stop_trading(self, reason: str):
        """Emergency stop trading"""
        try:
            self.emergency_stop = True
            alert = RiskAlert(
                alert_type="emergency_stop",
                severity="critical",
                message=f"Emergency stop activated: {reason}",
                timestamp=time.time()
            )
            self.risk_alerts.append(alert)
            logger.critical(f"EMERGENCY STOP ACTIVATED: {reason}")
            
        except Exception as e:
            logger.error(f"Error in emergency stop: {str(e)}")
    
    def resume_trading(self, reason: str):
        """Resume trading after emergency stop"""
        try:
            self.emergency_stop = False
            alert = RiskAlert(
                alert_type="trading_resumed",
                severity="info",
                message=f"Trading resumed: {reason}",
                timestamp=time.time()
            )
            self.risk_alerts.append(alert)
            logger.info(f"TRADING RESUMED: {reason}")
            
        except Exception as e:
            logger.error(f"Error resuming trading: {str(e)}")

