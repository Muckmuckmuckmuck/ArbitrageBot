import asyncio
import sqlite3
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class TradeRecord:
    """Data class for trade records"""
    id: Optional[int] = None
    symbol: str = ""
    buy_exchange: str = ""
    sell_exchange: str = ""
    amount: float = 0.0
    buy_price: float = 0.0
    sell_price: float = 0.0
    profit: float = 0.0
    execution_time_ms: int = 0
    slippage: float = 0.0
    timestamp: float = 0.0
    status: str = ""
    strategy: str = ""
    risk_score: float = 0.0

@dataclass
class MarketDataRecord:
    """Data class for market data records"""
    id: Optional[int] = None
    symbol: str = ""
    exchange: str = ""
    price: float = 0.0
    volume: float = 0.0
    spread_percent: float = 0.0
    timestamp: float = 0.0
    order_book_depth: float = 0.0

@dataclass
class PerformanceRecord:
    """Data class for performance records"""
    id: Optional[int] = None
    symbol: str = ""
    date: str = ""
    total_trades: int = 0
    successful_trades: int = 0
    total_profit: float = 0.0
    avg_execution_time_ms: int = 0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0

class DatabaseManager:
    """Database manager for trade history and analytics"""
    
    def __init__(self, db_path: str = "trades.db"):
        self.db_path = db_path
        self.connection = None
        self.setup_database()
    
    def setup_database(self):
        """Set up database tables"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            
            # Create tables
            self._create_tables()
            logger.info(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error setting up database: {str(e)}")
            raise
    
    def _create_tables(self):
        """Create database tables"""
        try:
            cursor = self.connection.cursor()
            
            # Trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol VARCHAR(20) NOT NULL,
                    buy_exchange VARCHAR(20) NOT NULL,
                    sell_exchange VARCHAR(20) NOT NULL,
                    amount DECIMAL(20,8) NOT NULL,
                    buy_price DECIMAL(20,8) NOT NULL,
                    sell_price DECIMAL(20,8) NOT NULL,
                    profit DECIMAL(20,8) NOT NULL,
                    execution_time_ms INTEGER NOT NULL,
                    slippage DECIMAL(10,6) NOT NULL,
                    timestamp REAL NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    strategy VARCHAR(20) NOT NULL,
                    risk_score DECIMAL(10,6) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Market data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol VARCHAR(20) NOT NULL,
                    exchange VARCHAR(20) NOT NULL,
                    price DECIMAL(20,8) NOT NULL,
                    volume DECIMAL(20,8) NOT NULL,
                    spread_percent DECIMAL(10,6) NOT NULL,
                    timestamp REAL NOT NULL,
                    order_book_depth DECIMAL(20,8) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Performance metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol VARCHAR(20) NOT NULL,
                    date DATE NOT NULL,
                    total_trades INTEGER NOT NULL,
                    successful_trades INTEGER NOT NULL,
                    total_profit DECIMAL(20,8) NOT NULL,
                    avg_execution_time_ms INTEGER NOT NULL,
                    max_drawdown DECIMAL(10,6) NOT NULL,
                    sharpe_ratio DECIMAL(10,6) NOT NULL,
                    win_rate DECIMAL(10,6) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date)
                )
            """)
            
            # Risk metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS risk_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol VARCHAR(20) NOT NULL,
                    timestamp REAL NOT NULL,
                    exposure DECIMAL(20,8) NOT NULL,
                    volatility DECIMAL(10,6) NOT NULL,
                    correlation_risk DECIMAL(10,6) NOT NULL,
                    liquidity_risk DECIMAL(10,6) NOT NULL,
                    risk_score DECIMAL(10,6) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ML predictions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ml_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol VARCHAR(20) NOT NULL,
                    model_type VARCHAR(50) NOT NULL,
                    predicted_value DECIMAL(20,8) NOT NULL,
                    confidence DECIMAL(10,6) NOT NULL,
                    actual_value DECIMAL(20,8),
                    error DECIMAL(20,8),
                    timestamp REAL NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes separately to satisfy SQLite syntax
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_profit ON trades(profit);")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_data_symbol_exchange ON market_data(symbol, exchange);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp);")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_symbol_date ON performance_metrics(symbol, date);")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_risk_symbol_timestamp ON risk_metrics(symbol, timestamp);")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ml_symbol_model ON ml_predictions(symbol, model_type);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ml_timestamp ON ml_predictions(timestamp);")
            
            self.connection.commit()
            logger.info("Database tables created successfully")
            
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise
    
    def save_trade(self, trade: TradeRecord) -> int:
        """Save trade record to database"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                INSERT INTO trades (
                    symbol, buy_exchange, sell_exchange, amount, buy_price, sell_price,
                    profit, execution_time_ms, slippage, timestamp, status, strategy, risk_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.symbol, trade.buy_exchange, trade.sell_exchange, trade.amount,
                trade.buy_price, trade.sell_price, trade.profit, trade.execution_time_ms,
                trade.slippage, trade.timestamp, trade.status, trade.strategy, trade.risk_score
            ))
            
            trade_id = cursor.lastrowid
            self.connection.commit()
            
            logger.info(f"Saved trade {trade_id} for {trade.symbol}")
            return trade_id
            
        except Exception as e:
            logger.error(f"Error saving trade: {str(e)}")
            return -1
    
    def save_market_data(self, market_data: MarketDataRecord) -> int:
        """Save market data record to database"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                INSERT INTO market_data (
                    symbol, exchange, price, volume, spread_percent, timestamp, order_book_depth
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                market_data.symbol, market_data.exchange, market_data.price, market_data.volume,
                market_data.spread_percent, market_data.timestamp, market_data.order_book_depth
            ))
            
            record_id = cursor.lastrowid
            self.connection.commit()
            
            return record_id
            
        except Exception as e:
            logger.error(f"Error saving market data: {str(e)}")
            return -1
    
    def save_performance_metrics(self, performance: PerformanceRecord) -> int:
        """Save performance metrics to database"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO performance_metrics (
                    symbol, date, total_trades, successful_trades, total_profit,
                    avg_execution_time_ms, max_drawdown, sharpe_ratio, win_rate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                performance.symbol, performance.date, performance.total_trades,
                performance.successful_trades, performance.total_profit,
                performance.avg_execution_time_ms, performance.max_drawdown,
                performance.sharpe_ratio, performance.win_rate
            ))
            
            record_id = cursor.lastrowid
            self.connection.commit()
            
            return record_id
            
        except Exception as e:
            logger.error(f"Error saving performance metrics: {str(e)}")
            return -1
    
    def save_risk_metrics(self, symbol: str, risk_data: Dict) -> int:
        """Save risk metrics to database"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                INSERT INTO risk_metrics (
                    symbol, timestamp, exposure, volatility, correlation_risk,
                    liquidity_risk, risk_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, risk_data['timestamp'], risk_data['exposure'],
                risk_data['volatility'], risk_data['correlation_risk'],
                risk_data['liquidity_risk'], risk_data['risk_score']
            ))
            
            record_id = cursor.lastrowid
            self.connection.commit()
            
            return record_id
            
        except Exception as e:
            logger.error(f"Error saving risk metrics: {str(e)}")
            return -1
    
    def save_ml_prediction(self, symbol: str, model_type: str, predicted_value: float,
                          confidence: float, actual_value: float = None) -> int:
        """Save ML prediction to database"""
        try:
            cursor = self.connection.cursor()
            
            error = None
            if actual_value is not None:
                error = abs(predicted_value - actual_value)
            
            cursor.execute("""
                INSERT INTO ml_predictions (
                    symbol, model_type, predicted_value, confidence, actual_value, error, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, model_type, predicted_value, confidence, actual_value, error, time.time()
            ))
            
            record_id = cursor.lastrowid
            self.connection.commit()
            
            return record_id
            
        except Exception as e:
            logger.error(f"Error saving ML prediction: {str(e)}")
            return -1
    
    def get_trades(self, symbol: str = None, limit: int = 1000, 
                   start_time: float = None, end_time: float = None) -> List[Dict]:
        """Get trade records"""
        try:
            cursor = self.connection.cursor()
            
            query = "SELECT * FROM trades"
            params = []
            conditions = []
            
            if symbol:
                conditions.append("symbol = ?")
                params.append(symbol)
            
            if start_time:
                conditions.append("timestamp >= ?")
                params.append(start_time)
            
            if end_time:
                conditions.append("timestamp <= ?")
                params.append(end_time)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting trades: {str(e)}")
            return []
    
    def get_performance_summary(self, symbol: str = None, days: int = 30) -> Dict:
        """Get performance summary"""
        try:
            cursor = self.connection.cursor()
            
            # Calculate date range
            end_date = time.time()
            start_date = end_date - (days * 24 * 3600)
            
            query = """
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as successful_trades,
                    SUM(profit) as total_profit,
                    AVG(execution_time_ms) as avg_execution_time,
                    MIN(profit) as min_profit,
                    MAX(profit) as max_profit,
                    AVG(slippage) as avg_slippage
                FROM trades
                WHERE timestamp >= ? AND timestamp <= ?
            """
            params = [start_date, end_date]
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            
            if not row or row['total_trades'] == 0:
                return {}
            
            # Calculate additional metrics
            total_trades = row['total_trades']
            successful_trades = row['successful_trades']
            total_profit = row['total_profit']
            
            win_rate = (successful_trades / total_trades) * 100 if total_trades > 0 else 0
            avg_profit = total_profit / total_trades if total_trades > 0 else 0
            
            summary = {
                'total_trades': total_trades,
                'successful_trades': successful_trades,
                'total_profit': total_profit,
                'avg_profit': avg_profit,
                'win_rate': win_rate,
                'avg_execution_time': row['avg_execution_time'],
                'min_profit': row['min_profit'],
                'max_profit': row['max_profit'],
                'avg_slippage': row['avg_slippage'],
                'period_days': days,
                'symbol': symbol
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {str(e)}")
            return {}
    
    def get_symbol_performance(self, days: int = 30) -> Dict:
        """Get performance by symbol"""
        try:
            cursor = self.connection.cursor()
            
            end_date = time.time()
            start_date = end_date - (days * 24 * 3600)
            
            cursor.execute("""
                SELECT 
                    symbol,
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as successful_trades,
                    SUM(profit) as total_profit,
                    AVG(profit) as avg_profit,
                    AVG(execution_time_ms) as avg_execution_time,
                    AVG(slippage) as avg_slippage
                FROM trades
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY symbol
                ORDER BY total_profit DESC
            """, [start_date, end_date])
            
            rows = cursor.fetchall()
            
            performance_by_symbol = {}
            for row in rows:
                symbol = row['symbol']
                total_trades = row['total_trades']
                successful_trades = row['successful_trades']
                
                performance_by_symbol[symbol] = {
                    'total_trades': total_trades,
                    'successful_trades': successful_trades,
                    'total_profit': row['total_profit'],
                    'avg_profit': row['avg_profit'],
                    'win_rate': (successful_trades / total_trades) * 100 if total_trades > 0 else 0,
                    'avg_execution_time': row['avg_execution_time'],
                    'avg_slippage': row['avg_slippage']
                }
            
            return performance_by_symbol
            
        except Exception as e:
            logger.error(f"Error getting symbol performance: {str(e)}")
            return {}
    
    def get_market_data(self, symbol: str, exchange: str = None, 
                       limit: int = 1000, hours: int = 24) -> List[Dict]:
        """Get market data records"""
        try:
            cursor = self.connection.cursor()
            
            end_time = time.time()
            start_time = end_time - (hours * 3600)
            
            query = """
                SELECT * FROM market_data
                WHERE symbol = ? AND timestamp >= ? AND timestamp <= ?
            """
            params = [symbol, start_time, end_time]
            
            if exchange:
                query += " AND exchange = ?"
                params.append(exchange)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting market data: {str(e)}")
            return []
    
    def get_ml_predictions(self, symbol: str, model_type: str = None, 
                          limit: int = 100) -> List[Dict]:
        """Get ML predictions"""
        try:
            cursor = self.connection.cursor()
            
            query = "SELECT * FROM ml_predictions WHERE symbol = ?"
            params = [symbol]
            
            if model_type:
                query += " AND model_type = ?"
                params.append(model_type)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting ML predictions: {str(e)}")
            return []
    
    def cleanup_old_data(self, days: int = 90):
        """Clean up old data"""
        try:
            cursor = self.connection.cursor()
            cutoff_time = time.time() - (days * 24 * 3600)
            
            # Clean up old market data
            cursor.execute("DELETE FROM market_data WHERE timestamp < ?", [cutoff_time])
            market_data_deleted = cursor.rowcount
            
            # Clean up old risk metrics
            cursor.execute("DELETE FROM risk_metrics WHERE timestamp < ?", [cutoff_time])
            risk_metrics_deleted = cursor.rowcount
            
            # Clean up old ML predictions
            cursor.execute("DELETE FROM ml_predictions WHERE timestamp < ?", [cutoff_time])
            ml_predictions_deleted = cursor.rowcount
            
            self.connection.commit()
            
            logger.info(f"Cleaned up old data: {market_data_deleted} market data, "
                       f"{risk_metrics_deleted} risk metrics, {ml_predictions_deleted} ML predictions")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {str(e)}")
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        try:
            cursor = self.connection.cursor()
            
            # Get table counts
            cursor.execute("SELECT COUNT(*) FROM trades")
            trades_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM market_data")
            market_data_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM performance_metrics")
            performance_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM risk_metrics")
            risk_metrics_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ml_predictions")
            ml_predictions_count = cursor.fetchone()[0]
            
            # Get database size
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            db_size = cursor.fetchone()[0]
            
            stats = {
                'trades_count': trades_count,
                'market_data_count': market_data_count,
                'performance_count': performance_count,
                'risk_metrics_count': risk_metrics_count,
                'ml_predictions_count': ml_predictions_count,
                'database_size_bytes': db_size,
                'database_size_mb': db_size / (1024 * 1024)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database stats: {str(e)}")
            return {}
    
    def close(self):
        """Close database connection"""
        try:
            if self.connection:
                self.connection.close()
                logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database: {str(e)}")

