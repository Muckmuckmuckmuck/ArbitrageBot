import asyncio
import time
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from flask import Flask, jsonify, request
from exchanges import ExchangeManager
from arbitrage_engine import ArbitrageEngine
from transfer_manager import TransferManager
from risk_manager import RiskManager
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class SystemStatus:
    """Data class for system status"""
    timestamp: float
    arbitrage_engine_running: bool
    price_monitor_running: bool
    transfer_manager_running: bool
    risk_manager_running: bool
    total_connections: int
    active_trades: int
    pending_transfers: int
    system_health: str

class MonitoringSystem:
    """Comprehensive monitoring and dashboard system"""
    
    def __init__(self, exchange_manager: ExchangeManager, arbitrage_engine: ArbitrageEngine, 
                 transfer_manager: TransferManager, risk_manager: RiskManager):
        self.exchange_manager = exchange_manager
        self.arbitrage_engine = arbitrage_engine
        self.transfer_manager = transfer_manager
        self.risk_manager = risk_manager
        self.flask_app = Flask(__name__)
        self.setup_routes()
        self.monitoring_data = {}
        self.performance_metrics = {}
        
    def setup_routes(self):
        """Setup Flask routes for monitoring dashboard"""
        
        @self.flask_app.route('/')
        def dashboard():
            return jsonify({
                'message': 'Arbitrage Trading Bot Dashboard',
                'version': '1.0.0',
                'status': 'running',
                'endpoints': {
                    '/status': 'System status',
                    '/metrics': 'Performance metrics',
                    '/trades': 'Trade history',
                    '/balances': 'Account balances',
                    '/opportunities': 'Arbitrage opportunities',
                    '/transfers': 'Transfer status',
                    '/risk': 'Risk metrics',
                    '/alerts': 'System alerts'
                }
            })
        
        @self.flask_app.route('/status')
        def get_status():
            return jsonify(self.get_system_status())
        
        @self.flask_app.route('/metrics')
        def get_metrics():
            return jsonify(self.get_performance_metrics())
        
        @self.flask_app.route('/trades')
        def get_trades():
            return jsonify(self.get_trade_history())
        
        @self.flask_app.route('/balances')
        def get_balances():
            return jsonify(self.get_account_balances())
        
        @self.flask_app.route('/opportunities')
        def get_opportunities():
            return jsonify(self.get_arbitrage_opportunities())
        
        @self.flask_app.route('/transfers')
        def get_transfers():
            return jsonify(self.get_transfer_status())
        
        @self.flask_app.route('/risk')
        def get_risk():
            return jsonify(self.get_risk_metrics())
        
        @self.flask_app.route('/alerts')
        def get_alerts():
            return jsonify(self.get_system_alerts())
        
        @self.flask_app.route('/emergency_stop', methods=['POST'])
        def emergency_stop():
            data = request.get_json()
            reason = data.get('reason', 'Manual emergency stop')
            self.risk_manager.emergency_stop_trading(reason)
            return jsonify({'status': 'success', 'message': f'Emergency stop activated: {reason}'})
        
        @self.flask_app.route('/resume', methods=['POST'])
        def resume_trading():
            data = request.get_json()
            reason = data.get('reason', 'Manual resume')
            self.risk_manager.resume_trading(reason)
            return jsonify({'status': 'success', 'message': f'Trading resumed: {reason}'})
    
    def get_system_status(self) -> SystemStatus:
        """Get current system status"""
        try:
            # Check if components are running
            arbitrage_running = self.arbitrage_engine.running
            price_monitor_running = self.arbitrage_engine.price_monitor.running
            transfer_manager_running = len(self.transfer_manager.pending_transfers) >= 0  # Simple check
            risk_manager_running = not self.risk_manager.emergency_stop  # Active if not in emergency stop
            
            # Count connections and activities
            total_connections = 2  # Binance + Kraken
            active_trades = len(self.arbitrage_engine.active_trades)
            pending_transfers = len(self.transfer_manager.pending_transfers)
            
            # Determine system health
            if self.risk_manager.emergency_stop:
                health = "emergency_stop"
            elif not arbitrage_running:
                health = "stopped"
            elif pending_transfers > 5:
                health = "degraded"
            else:
                health = "healthy"
            
            return SystemStatus(
                timestamp=time.time(),
                arbitrage_engine_running=arbitrage_running,
                price_monitor_running=price_monitor_running,
                transfer_manager_running=transfer_manager_running,
                risk_manager_running=risk_manager_running,
                total_connections=total_connections,
                active_trades=active_trades,
                pending_transfers=pending_transfers,
                system_health=health
            )
            
        except Exception as e:
            logger.error(f"Error getting system status: {str(e)}")
            return SystemStatus(time.time(), False, False, False, False, 0, 0, 0, "error")
    
    def get_performance_metrics(self) -> Dict:
        """Get performance metrics"""
        try:
            # Get trade statistics
            trade_stats = self.arbitrage_engine.get_trade_statistics()
            
            # Get transfer statistics
            transfer_stats = self.transfer_manager.get_transfer_statistics()
            
            # Get risk metrics
            risk_summary = self.risk_manager.get_risk_summary()
            
            return {
                'trade_metrics': trade_stats,
                'transfer_metrics': transfer_stats,
                'risk_metrics': risk_summary.get('risk_metrics', {}),
                'system_metrics': {
                    'uptime': time.time() - (self.monitoring_data.get('start_time', time.time())),
                    'memory_usage': self._get_memory_usage(),
                    'cpu_usage': self._get_cpu_usage()
                },
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {str(e)}")
            return {'error': str(e)}
    
    def get_trade_history(self) -> Dict:
        """Get trade history"""
        try:
            completed_trades = []
            for trade in self.arbitrage_engine.completed_trades:
                completed_trades.append({
                    'symbol': trade.symbol,
                    'buy_exchange': trade.buy_exchange,
                    'sell_exchange': trade.sell_exchange,
                    'amount': trade.amount,
                    'buy_price': trade.buy_price,
                    'sell_price': trade.sell_price,
                    'profit': (trade.sell_price - trade.buy_price) * trade.amount,
                    'timestamp': trade.timestamp,
                    'status': trade.status
                })
            
            active_trades = []
            for trade_id, trade in self.arbitrage_engine.active_trades.items():
                active_trades.append({
                    'trade_id': trade_id,
                    'symbol': trade.symbol,
                    'buy_exchange': trade.buy_exchange,
                    'sell_exchange': trade.sell_exchange,
                    'amount': trade.amount,
                    'buy_price': trade.buy_price,
                    'sell_price': trade.sell_price,
                    'timestamp': trade.timestamp,
                    'status': trade.status
                })
            
            return {
                'completed_trades': completed_trades,
                'active_trades': active_trades,
                'total_trades': len(completed_trades) + len(active_trades),
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error getting trade history: {str(e)}")
            return {'error': str(e)}
    
    def get_account_balances(self) -> Dict:
        """Get account balances from all exchanges"""
        try:
            balances = {}
            
            for exchange_name in ['binance', 'kraken']:
                exchange = self.exchange_manager.get_exchange(exchange_name)
                balances[exchange_name] = {}
                
                for currency, balance_info in exchange.balances.items():
                    if isinstance(balance_info, dict):
                        balances[exchange_name][currency] = {
                            'free': balance_info.get('free', 0),
                            'used': balance_info.get('used', 0),
                            'total': balance_info.get('total', 0)
                        }
            
            return {
                'balances': balances,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error getting account balances: {str(e)}")
            return {'error': str(e)}
    
    def get_arbitrage_opportunities(self) -> Dict:
        """Get current arbitrage opportunities"""
        try:
            opportunities = {}
            
            for symbol in Config.CURRENCY_PAIRS:
                spreads = self.arbitrage_engine.price_monitor.get_price_spread(symbol)
                
                if spreads:
                    opportunities[symbol] = []
                    for spread_id, spread_data in spreads.items():
                        if spread_data['spread_percent'] >= Config.MIN_SPREAD_PERCENT:
                            opportunities[symbol].append({
                                'spread_percent': spread_data['spread_percent'],
                                'buy_exchange': spread_data['lower_price_exchange'],
                                'sell_exchange': spread_data['higher_price_exchange'],
                                'buy_price': spread_data['price1'] if spread_data['lower_price_exchange'] == spread_data['exchange1'] else spread_data['price2'],
                                'sell_price': spread_data['price2'] if spread_data['lower_price_exchange'] == spread_data['exchange1'] else spread_data['price1'],
                                'timestamp': time.time()
                            })
            
            return {
                'opportunities': opportunities,
                'min_spread_percent': Config.MIN_SPREAD_PERCENT,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error getting arbitrage opportunities: {str(e)}")
            return {'error': str(e)}
    
    def get_transfer_status(self) -> Dict:
        """Get transfer status"""
        try:
            pending_transfers = []
            for transfer_id, transfer in self.transfer_manager.pending_transfers.items():
                pending_transfers.append({
                    'transfer_id': transfer_id,
                    'currency': transfer.currency,
                    'amount': transfer.amount,
                    'from_exchange': transfer.from_exchange,
                    'to_exchange': transfer.to_exchange,
                    'status': transfer.status,
                    'tx_id': transfer.tx_id,
                    'timestamp': transfer.timestamp
                })
            
            completed_transfers = []
            for transfer in self.transfer_manager.completed_transfers:
                completed_transfers.append({
                    'currency': transfer.currency,
                    'amount': transfer.amount,
                    'from_exchange': transfer.from_exchange,
                    'to_exchange': transfer.to_exchange,
                    'status': transfer.status,
                    'tx_id': transfer.tx_id,
                    'timestamp': transfer.timestamp
                })
            
            return {
                'pending_transfers': pending_transfers,
                'completed_transfers': completed_transfers[-10:],  # Last 10 transfers
                'transfer_statistics': self.transfer_manager.get_transfer_statistics(),
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error getting transfer status: {str(e)}")
            return {'error': str(e)}
    
    def get_risk_metrics(self) -> Dict:
        """Get risk metrics"""
        try:
            return self.risk_manager.get_risk_summary()
            
        except Exception as e:
            logger.error(f"Error getting risk metrics: {str(e)}")
            return {'error': str(e)}
    
    def get_system_alerts(self) -> Dict:
        """Get system alerts"""
        try:
            alerts = []
            
            # Get risk alerts
            for alert in self.risk_manager.risk_alerts:
                alerts.append({
                    'type': alert.alert_type,
                    'severity': alert.severity,
                    'message': alert.message,
                    'timestamp': alert.timestamp,
                    'source': 'risk_manager'
                })
            
            # Add system alerts
            system_status = self.get_system_status()
            if system_status.system_health != 'healthy':
                alerts.append({
                    'type': 'system_health',
                    'severity': 'warning' if system_status.system_health == 'degraded' else 'critical',
                    'message': f"System health: {system_status.system_health}",
                    'timestamp': time.time(),
                    'source': 'system'
                })
            
            return {
                'alerts': alerts,
                'total_alerts': len(alerts),
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error getting system alerts: {str(e)}")
            return {'error': str(e)}
    
    def _get_memory_usage(self) -> float:
        """Get memory usage percentage"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Get CPU usage percentage"""
        try:
            import psutil
            return psutil.cpu_percent()
        except ImportError:
            return 0.0
    
    async def start_monitoring(self):
        """Start the monitoring system"""
        try:
            self.monitoring_data['start_time'] = time.time()
            
            # Start Flask app in a separate task
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.flask_app.run, '0.0.0.0', Config.PORT, False)
            
        except Exception as e:
            logger.error(f"Error starting monitoring system: {str(e)}")
    
    def run_flask_app(self):
        """Run Flask app (for Railway deployment)"""
        self.flask_app.run(host='0.0.0.0', port=Config.PORT, debug=False)

