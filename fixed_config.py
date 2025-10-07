#!/usr/bin/env python3
"""
Fixed Configuration - Complete configuration for the arbitrage bot
"""

import os
from typing import Dict, List

class FixedConfig:
    """Fixed configuration class with all required settings"""
    
    # API Keys
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', '')
    OKX_API_KEY = os.getenv('OKX_API_KEY', '')
    OKX_SECRET_KEY = os.getenv('OKX_SECRET_KEY', '')
    OKX_PASSPHRASE = os.getenv('OKX_PASSPHRASE', '')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///arbitrage_bot.db')
    
    # Trading Configuration
    MIN_SPREAD_PERCENT = 0.008  # 0.8%
    MAX_DAILY_TRADES = 200
    
    # Cryptocurrency Pairs
    CURRENCY_PAIRS = [
        'TON/USDT', 'ALGO/USDT', 'VET/USDT', 'XLM/USDT',
        'TRX/USDT', 'FTM/USDT', 'MATIC/USDT', 'SOL/USDT',
        'BCH/USDT', 'XRP/USDT', 'DASH/USDT', 'LTC/USDT',
        'HBAR/USDT', 'ICP/USDT', 'LINK/USDT', 'ATOM/USDT'
    ]
    
    # Percentage-based position sizing
    POSITION_PERCENTAGES = {
        # Tier 1: Ultra-Fast, High-Spread Assets (A+ Grade)
        'TON/USDT': 0.08,   # 8% of total account value
        'ALGO/USDT': 0.08,  # 8% of total account value
        'VET/USDT': 0.06,   # 6% of total account value
        'XLM/USDT': 0.08,   # 8% of total account value
        
        # Tier 2: Fast, Good-Spread Assets (A Grade)
        'TRX/USDT': 0.06,   # 6% of total account value
        'FTM/USDT': 0.05,   # 5% of total account value
        'MATIC/USDT': 0.06, # 6% of total account value
        'SOL/USDT': 0.07,   # 7% of total account value
        
        # Tier 3: Established Assets (B+ Grade)
        'BCH/USDT': 0.05,   # 5% of total account value
        'XRP/USDT': 0.06,   # 6% of total account value
        'DASH/USDT': 0.04,  # 4% of total account value
        'LTC/USDT': 0.05,   # 5% of total account value
        
        # Tier 4: Additional Profitable Assets
        'HBAR/USDT': 0.04,  # 4% of total account value
        'ICP/USDT': 0.03,   # 3% of total account value
        'LINK/USDT': 0.05,  # 5% of total account value
        'ATOM/USDT': 0.04,  # 4% of total account value
    }
    
    # Risk Management
    RISK_MANAGEMENT = {
        'min_account_balance_usd': 100,        # Minimum account balance
        'max_position_percent': 0.08,          # Maximum 8% of account per position
        'max_concurrent_trades': 8,            # Maximum 8 concurrent trades
        'max_total_exposure': 0.60,            # Maximum 60% of account in trades
        'reserve_percent': 0.20,               # Keep 20% in reserve
        'min_position_percent': 0.01,          # Minimum 1% of account per position
        'max_daily_trades': 200,               # Maximum 200 trades per day
        'stop_loss_percent': 0.005,             # 0.5% stop loss per trade
    }
    
    # Transfer Speeds and Requirements
    TRANSFER_SPEEDS = {
        'TON/USDT': {'speed': 30, 'min_spread': 0.015},
        'ALGO/USDT': {'speed': 4, 'min_spread': 0.015},
        'VET/USDT': {'speed': 10, 'min_spread': 0.017},
        'XLM/USDT': {'speed': 3, 'min_spread': 0.015},
        'TRX/USDT': {'speed': 120, 'min_spread': 0.015},
        'FTM/USDT': {'speed': 60, 'min_spread': 0.015},
        'MATIC/USDT': {'speed': 90, 'min_spread': 0.012},
        'SOL/USDT': {'speed': 10, 'min_spread': 0.01},
        'BCH/USDT': {'speed': 300, 'min_spread': 0.01},
        'XRP/USDT': {'speed': 5, 'min_spread': 0.01},
        'DASH/USDT': {'speed': 150, 'min_spread': 0.013},
        'LTC/USDT': {'speed': 150, 'min_spread': 0.011},
        'HBAR/USDT': {'speed': 30, 'min_spread': 0.012},
        'ICP/USDT': {'speed': 90, 'min_spread': 0.01},
        'LINK/USDT': {'speed': 10, 'min_spread': 0.01},
        'ATOM/USDT': {'speed': 7, 'min_spread': 0.01},
    }
    
    # Exchange Configuration
    EXCHANGES = {
        'binance': {
            'name': 'Binance',
            'api_key': BINANCE_API_KEY,
            'secret_key': BINANCE_SECRET_KEY,
            'base_url': 'https://api.binance.com',
            'rate_limits': {
                'requests_per_minute': 1200,
                'orders_per_minute': 1200,
                'weight_per_minute': 1200
            }
        },
        'okx': {
            'name': 'OKX',
            'api_key': OKX_API_KEY,
            'secret_key': OKX_SECRET_KEY,
            'passphrase': OKX_PASSPHRASE,
            'base_url': 'https://www.okx.com',
            'rate_limits': {
                'requests_per_minute': 3000,
                'orders_per_minute': 3000,
                'weight_per_minute': 3000
            }
        }
    }
    
    # Logging Configuration
    LOGGING = {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file': 'arbitrage_bot.log',
        'max_size': 10 * 1024 * 1024,  # 10MB
        'backup_count': 5
    }
    
    # Performance Configuration
    PERFORMANCE = {
        'max_concurrent_operations': 20,
        'operation_timeout': 30,  # seconds
        'balance_cache_ttl': 5,    # seconds
        'price_cache_ttl': 1,      # seconds
    }
    
    # Error Handling Configuration
    ERROR_HANDLING = {
        'max_retry_attempts': 3,
        'retry_delay': 1,  # seconds
        'circuit_breaker_threshold': 5,
        'circuit_breaker_duration': 300,  # seconds
    }
    
    # Monitoring Configuration
    MONITORING = {
        'dashboard_port': 5000,
        'metrics_interval': 60,  # seconds
        'alert_thresholds': {
            'error_rate': 0.1,  # 10%
            'performance_degradation': 0.2,  # 20%
            'balance_drop': 0.05,  # 5%
        }
    }
