#!/usr/bin/env python3
"""
High-Frequency Arbitrage Configuration
Optimized for continuous trading with maximum profit
"""

import os
from dotenv import load_dotenv
from typing import Dict, List, Any
import logging

# Load environment variables
load_dotenv()

class HighFrequencyConfig:
    """Configuration for high-frequency arbitrage trading"""
    
    # API Configuration
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', '')
    BINANCE_TESTNET = os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
    
    OKX_API_KEY = os.getenv('OKX_API_KEY', '')
    OKX_SECRET_KEY = os.getenv('OKX_SECRET_KEY', '')
    OKX_PASSPHRASE = os.getenv('OKX_PASSPHRASE', '')
    OKX_SANDBOX = os.getenv('OKX_SANDBOX', 'true').lower() == 'true'
    
    # High-Frequency Trading Configuration
    CONTINUOUS_TRADING = True  # No trade limits
    MAX_CONCURRENT_TRADES = 20  # Increased for high frequency
    MAX_TOTAL_EXPOSURE = 0.80  # 80% of account in trades
    RESERVE_PERCENT = 0.15  # 15% reserve (reduced for more trading)
    
    # Optimized spread requirements per crypto (accounting for fees + slippage + buffer)
    OPTIMIZED_SPREAD_REQUIREMENTS = {
        # Tier 1: Ultra-Fast, High-Spread Assets
        'TON/USDT': {
            'min_spread': 0.008,  # 0.8% (fees: 0.032% + slippage: 0.03% + buffer: 0.738%)
            'target_spread': 0.015,  # 1.5% target
            'max_spread': 0.025,  # 2.5% max
            'transfer_time': 30,
            'strategy': 'transfer_first',
            'priority': 1
        },
        'ALGO/USDT': {
            'min_spread': 0.006,  # 0.6% (fees: 0.032% + slippage: 0.02% + buffer: 0.548%)
            'target_spread': 0.012,  # 1.2% target
            'max_spread': 0.020,  # 2.0% max
            'transfer_time': 4,
            'strategy': 'transfer_first',
            'priority': 1
        },
        'VET/USDT': {
            'min_spread': 0.007,  # 0.7% (fees: 0.032% + slippage: 0.03% + buffer: 0.638%)
            'target_spread': 0.014,  # 1.4% target
            'max_spread': 0.022,  # 2.2% max
            'transfer_time': 10,
            'strategy': 'transfer_first',
            'priority': 1
        },
        'XLM/USDT': {
            'min_spread': 0.006,  # 0.6% (fees: 0.032% + slippage: 0.02% + buffer: 0.548%)
            'target_spread': 0.012,  # 1.2% target
            'max_spread': 0.020,  # 2.0% max
            'transfer_time': 3,
            'strategy': 'transfer_first',
            'priority': 1
        },
        
        # Tier 2: Fast, Good-Spread Assets
        'TRX/USDT': {
            'min_spread': 0.006,  # 0.6% (fees: 0.032% + slippage: 0.02% + buffer: 0.548%)
            'target_spread': 0.012,  # 1.2% target
            'max_spread': 0.020,  # 2.0% max
            'transfer_time': 120,
            'strategy': 'transfer_first',
            'priority': 2
        },
        'FTM/USDT': {
            'min_spread': 0.007,  # 0.7% (fees: 0.032% + slippage: 0.03% + buffer: 0.638%)
            'target_spread': 0.014,  # 1.4% target
            'max_spread': 0.020,  # 2.0% max
            'transfer_time': 60,
            'strategy': 'transfer_first',
            'priority': 2
        },
        'MATIC/USDT': {
            'min_spread': 0.005,  # 0.5% (fees: 0.032% + slippage: 0.03% + buffer: 0.438%)
            'target_spread': 0.010,  # 1.0% target
            'max_spread': 0.018,  # 1.8% max
            'transfer_time': 90,
            'strategy': 'transfer_first',
            'priority': 2
        },
        'SOL/USDT': {
            'min_spread': 0.004,  # 0.4% (fees: 0.032% + slippage: 0.03% + buffer: 0.338%)
            'target_spread': 0.008,  # 0.8% target
            'max_spread': 0.015,  # 1.5% max
            'transfer_time': 10,
            'strategy': 'transfer_first',
            'priority': 2
        },
        
        # Tier 3: Established Assets
        'BCH/USDT': {
            'min_spread': 0.004,  # 0.4% (fees: 0.032% + slippage: 0.02% + buffer: 0.348%)
            'target_spread': 0.008,  # 0.8% target
            'max_spread': 0.013,  # 1.3% max
            'transfer_time': 300,
            'strategy': 'simultaneous',
            'priority': 3
        },
        'XRP/USDT': {
            'min_spread': 0.003,  # 0.3% (fees: 0.032% + slippage: 0.02% + buffer: 0.248%)
            'target_spread': 0.006,  # 0.6% target
            'max_spread': 0.012,  # 1.2% max
            'transfer_time': 5,
            'strategy': 'transfer_first',
            'priority': 3
        },
        'DASH/USDT': {
            'min_spread': 0.005,  # 0.5% (fees: 0.032% + slippage: 0.03% + buffer: 0.438%)
            'target_spread': 0.010,  # 1.0% target
            'max_spread': 0.017,  # 1.7% max
            'transfer_time': 150,
            'strategy': 'transfer_first',
            'priority': 3
        },
        'LTC/USDT': {
            'min_spread': 0.004,  # 0.4% (fees: 0.032% + slippage: 0.02% + buffer: 0.348%)
            'target_spread': 0.008,  # 0.8% target
            'max_spread': 0.014,  # 1.4% max
            'transfer_time': 150,
            'strategy': 'simultaneous',
            'priority': 3
        },
        
        # Tier 4: Additional Profitable Assets
        'HBAR/USDT': {
            'min_spread': 0.005,  # 0.5% (fees: 0.032% + slippage: 0.03% + buffer: 0.438%)
            'target_spread': 0.010,  # 1.0% target
            'max_spread': 0.015,  # 1.5% max
            'transfer_time': 30,
            'strategy': 'transfer_first',
            'priority': 4
        },
        'ICP/USDT': {
            'min_spread': 0.004,  # 0.4% (fees: 0.032% + slippage: 0.03% + buffer: 0.338%)
            'target_spread': 0.008,  # 0.8% target
            'max_spread': 0.012,  # 1.2% max
            'transfer_time': 90,
            'strategy': 'transfer_first',
            'priority': 4
        },
        'LINK/USDT': {
            'min_spread': 0.004,  # 0.4% (fees: 0.032% + slippage: 0.04% + buffer: 0.328%)
            'target_spread': 0.008,  # 0.8% target
            'max_spread': 0.013,  # 1.3% max
            'transfer_time': 10,
            'strategy': 'transfer_first',
            'priority': 4
        },
        'ATOM/USDT': {
            'min_spread': 0.004,  # 0.4% (fees: 0.032% + slippage: 0.03% + buffer: 0.338%)
            'target_spread': 0.008,  # 0.8% target
            'max_spread': 0.013,  # 1.3% max
            'transfer_time': 7,
            'strategy': 'transfer_first',
            'priority': 4
        }
    }
    
    # Exchange Rate Limits (requests per minute)
    EXCHANGE_RATE_LIMITS = {
        'binance': {
            'orders_per_minute': 1200,  # 1200 orders per minute
            'requests_per_minute': 1200,  # 1200 requests per minute
            'weight_per_minute': 1200,  # 1200 weight per minute
            'orders_per_second': 10,  # 10 orders per second
            'requests_per_second': 10,  # 10 requests per second
            'weight_per_second': 10,  # 10 weight per second
        },
        'okx': {
            'orders_per_minute': 3000,  # 3000 orders per minute
            'requests_per_minute': 3000,  # 3000 requests per minute
            'weight_per_minute': 3000,  # 3000 weight per minute
            'orders_per_second': 20,  # 20 orders per second
            'requests_per_second': 20,  # 20 requests per second
            'weight_per_second': 20,  # 20 weight per second
        }
    }
    
    # Fee Structure (VIP levels)
    EXCHANGE_FEES = {
        'binance': {
            'trading_fee': 0.00017,  # 0.017% VIP taker fee
            'maker_fee': 0.00000,  # 0.000% VIP maker fee
            'withdrawal_fees': {
                'TON': 0.1, 'ALGO': 0.1, 'VET': 0.5, 'XLM': 0.25,
                'TRX': 1.0, 'FTM': 0.1, 'MATIC': 0.1, 'SOL': 0.01,
                'BCH': 0.001, 'XRP': 0.25, 'DASH': 0.01, 'LTC': 0.001,
                'HBAR': 0.1, 'ICP': 0.1, 'LINK': 0.5, 'ATOM': 0.1,
                'USDT': 1.0, 'USDC': 1.0, 'DAI': 1.0, 'BUSD': 1.0,
            }
        },
        'okx': {
            'trading_fee': 0.00015,  # 0.015% VIP taker fee
            'maker_fee': 0.00000,  # 0.000% VIP maker fee
            'withdrawal_fees': {
                'TON': 0.1, 'ALGO': 0.1, 'VET': 0.5, 'XLM': 0.15,
                'TRX': 1.0, 'FTM': 0.1, 'MATIC': 0.1, 'SOL': 0.01,
                'BCH': 0.001, 'XRP': 0.15, 'DASH': 0.01, 'LTC': 0.001,
                'HBAR': 0.1, 'ICP': 0.1, 'LINK': 0.5, 'ATOM': 0.1,
                'USDT': 1.0, 'USDC': 1.0, 'DAI': 1.0, 'BUSD': 1.0,
            }
        }
    }
    
    # Slippage estimates (conservative)
    SLIPPAGE_ESTIMATES = {
        'TON/USDT': 0.0003, 'ALGO/USDT': 0.0002, 'VET/USDT': 0.0003, 'XLM/USDT': 0.0002,
        'TRX/USDT': 0.0002, 'FTM/USDT': 0.0003, 'MATIC/USDT': 0.0003, 'SOL/USDT': 0.0003,
        'BCH/USDT': 0.0002, 'XRP/USDT': 0.0002, 'DASH/USDT': 0.0003, 'LTC/USDT': 0.0002,
        'HBAR/USDT': 0.0003, 'ICP/USDT': 0.0003, 'LINK/USDT': 0.0004, 'ATOM/USDT': 0.0003,
    }
    
    # Position sizing (percentage-based)
    POSITION_PERCENTAGES = {
        'TON/USDT': 0.08, 'ALGO/USDT': 0.08, 'VET/USDT': 0.06, 'XLM/USDT': 0.08,
        'TRX/USDT': 0.06, 'FTM/USDT': 0.05, 'MATIC/USDT': 0.06, 'SOL/USDT': 0.07,
        'BCH/USDT': 0.05, 'XRP/USDT': 0.06, 'DASH/USDT': 0.04, 'LTC/USDT': 0.05,
        'HBAR/USDT': 0.04, 'ICP/USDT': 0.03, 'LINK/USDT': 0.05, 'ATOM/USDT': 0.04,
    }
    
    # Risk management (optimized for high frequency)
    RISK_MANAGEMENT = {
        'max_position_percent': 0.08,      # Maximum 8% of total account per position
        'max_concurrent_trades': 20,       # Maximum 20 concurrent trades
        'max_total_exposure': 0.80,       # Maximum 80% of account in trades
        'reserve_percent': 0.15,          # Keep 15% in reserve
        'min_position_percent': 0.01,      # Minimum 1% of account per position
        'stop_loss_percent': 0.003,       # 0.3% stop loss per trade
        'max_daily_loss_percent': 0.05,   # 5% maximum daily loss
        'emergency_stop_threshold': 0.10,  # 10% emergency stop
    }
    
    # Logging configuration
    LOGGING_CONFIG = {
        'log_level': 'DEBUG',
        'log_file': 'high_frequency_arbitrage.log',
        'trade_log_file': 'trade_executions.log',
        'performance_log_file': 'performance_metrics.log',
        'error_log_file': 'error_analysis.log',
        'profit_log_file': 'profit_analysis.log',
        'rate_limit_log_file': 'rate_limit_monitoring.log',
        'detailed_trade_logging': True,
        'performance_metrics_logging': True,
        'error_analysis_logging': True,
        'profit_optimization_logging': True,
    }
    
    # Performance optimization
    PERFORMANCE_CONFIG = {
        'price_update_interval': 0.5,  # 0.5 seconds
        'opportunity_scan_interval': 1.0,  # 1 second
        'trade_execution_timeout': 30,  # 30 seconds
        'transfer_timeout': 300,  # 5 minutes
        'max_retry_attempts': 3,
        'retry_delay': 1.0,  # 1 second
        'concurrent_opportunity_scanning': True,
        'parallel_trade_execution': True,
    }
    
    # Currency pairs for high-frequency trading
    CURRENCY_PAIRS = [
        'TON/USDT', 'ALGO/USDT', 'VET/USDT', 'XLM/USDT',
        'TRX/USDT', 'FTM/USDT', 'MATIC/USDT', 'SOL/USDT',
        'BCH/USDT', 'XRP/USDT', 'DASH/USDT', 'LTC/USDT',
        'HBAR/USDT', 'ICP/USDT', 'LINK/USDT', 'ATOM/USDT',
    ]
    
    # Exchange configurations
    EXCHANGE_CONFIGS = {
        'binance': {
            'apiKey': BINANCE_API_KEY,
            'secret': BINANCE_SECRET_KEY,
            'sandbox': BINANCE_TESTNET,
            'rateLimit': 1200,
            'enableRateLimit': True,
            'timeout': 30000,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True,
            }
        },
        'okx': {
            'apiKey': OKX_API_KEY,
            'secret': OKX_SECRET_KEY,
            'passphrase': OKX_PASSPHRASE,
            'sandbox': OKX_SANDBOX,
            'rateLimit': 3000,
            'enableRateLimit': True,
            'timeout': 30000,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True,
            }
        }
    }
    
    # Currency mappings
    CURRENCY_MAPPINGS = {
        'TON': {'binance': 'TON', 'okx': 'TON'},
        'ALGO': {'binance': 'ALGO', 'okx': 'ALGO'},
        'VET': {'binance': 'VET', 'okx': 'VET'},
        'XLM': {'binance': 'XLM', 'okx': 'XLM'},
        'TRX': {'binance': 'TRX', 'okx': 'TRX'},
        'FTM': {'binance': 'FTM', 'okx': 'FTM'},
        'MATIC': {'binance': 'MATIC', 'okx': 'MATIC'},
        'SOL': {'binance': 'SOL', 'okx': 'SOL'},
        'BCH': {'binance': 'BCH', 'okx': 'BCH'},
        'XRP': {'binance': 'XRP', 'okx': 'XRP'},
        'DASH': {'binance': 'DASH', 'okx': 'DASH'},
        'LTC': {'binance': 'LTC', 'okx': 'LTC'},
        'HBAR': {'binance': 'HBAR', 'okx': 'HBAR'},
        'ICP': {'binance': 'ICP', 'okx': 'ICP'},
        'LINK': {'binance': 'LINK', 'okx': 'LINK'},
        'ATOM': {'binance': 'ATOM', 'okx': 'ATOM'},
        'USDT': {'binance': 'USDT', 'okx': 'USDT'},
        'USDC': {'binance': 'USDC', 'okx': 'USDC'},
        'DAI': {'binance': 'DAI', 'okx': 'DAI'},
        'BUSD': {'binance': 'BUSD', 'okx': 'BUSD'},
    }

def setup_high_frequency_logging():
    """Setup comprehensive logging for high-frequency trading"""
    import logging
    from logging.handlers import RotatingFileHandler
    import os
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure main logger
    logger = logging.getLogger('high_frequency_arbitrage')
    logger.setLevel(getattr(logging, HighFrequencyConfig.LOGGING_CONFIG['log_level']))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Main log file
    main_handler = RotatingFileHandler(
        f"logs/{HighFrequencyConfig.LOGGING_CONFIG['log_file']}",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    main_handler.setLevel(logging.DEBUG)
    main_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main_handler.setFormatter(main_formatter)
    logger.addHandler(main_handler)
    
    # Trade execution logger
    trade_logger = logging.getLogger('trade_executions')
    trade_logger.setLevel(logging.INFO)
    trade_handler = RotatingFileHandler(
        f"logs/{HighFrequencyConfig.LOGGING_CONFIG['trade_log_file']}",
        maxBytes=50*1024*1024,  # 50MB
        backupCount=10
    )
    trade_formatter = logging.Formatter(
        '%(asctime)s - TRADE - %(message)s'
    )
    trade_handler.setFormatter(trade_formatter)
    trade_logger.addHandler(trade_handler)
    
    # Performance metrics logger
    perf_logger = logging.getLogger('performance_metrics')
    perf_logger.setLevel(logging.INFO)
    perf_handler = RotatingFileHandler(
        f"logs/{HighFrequencyConfig.LOGGING_CONFIG['performance_log_file']}",
        maxBytes=20*1024*1024,  # 20MB
        backupCount=5
    )
    perf_formatter = logging.Formatter(
        '%(asctime)s - PERFORMANCE - %(message)s'
    )
    perf_handler.setFormatter(perf_formatter)
    perf_logger.addHandler(perf_handler)
    
    # Error analysis logger
    error_logger = logging.getLogger('error_analysis')
    error_logger.setLevel(logging.ERROR)
    error_handler = RotatingFileHandler(
        f"logs/{HighFrequencyConfig.LOGGING_CONFIG['error_log_file']}",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    error_formatter = logging.Formatter(
        '%(asctime)s - ERROR - %(message)s'
    )
    error_handler.setFormatter(error_formatter)
    error_logger.addHandler(error_handler)
    
    # Profit analysis logger
    profit_logger = logging.getLogger('profit_analysis')
    profit_logger.setLevel(logging.INFO)
    profit_handler = RotatingFileHandler(
        f"logs/{HighFrequencyConfig.LOGGING_CONFIG['profit_log_file']}",
        maxBytes=20*1024*1024,  # 20MB
        backupCount=5
    )
    profit_formatter = logging.Formatter(
        '%(asctime)s - PROFIT - %(message)s'
    )
    profit_handler.setFormatter(profit_formatter)
    profit_logger.addHandler(profit_handler)
    
    # Rate limit monitoring logger
    rate_logger = logging.getLogger('rate_limit_monitoring')
    rate_logger.setLevel(logging.WARNING)
    rate_handler = RotatingFileHandler(
        f"logs/{HighFrequencyConfig.LOGGING_CONFIG['rate_limit_log_file']}",
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    rate_formatter = logging.Formatter(
        '%(asctime)s - RATE_LIMIT - %(message)s'
    )
    rate_handler.setFormatter(rate_formatter)
    rate_logger.addHandler(rate_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger

if __name__ == "__main__":
    # Test configuration
    config = HighFrequencyConfig()
    print("High-Frequency Arbitrage Configuration:")
    print(f"Currency Pairs: {len(config.CURRENCY_PAIRS)}")
    print(f"Continuous Trading: {config.CONTINUOUS_TRADING}")
    print(f"Max Concurrent Trades: {config.MAX_CONCURRENT_TRADES}")
    print(f"Max Total Exposure: {config.MAX_TOTAL_EXPOSURE*100}%")
    print(f"Reserve Percent: {config.RESERVE_PERCENT*100}%")
    
    # Test logging setup
    logger = setup_high_frequency_logging()
    logger.info("High-frequency arbitrage configuration loaded successfully")