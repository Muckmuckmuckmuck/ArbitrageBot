import os
from dotenv import load_dotenv
from typing import List, Dict, Any
import logging

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the arbitrage trading bot"""
    
    # API Configuration
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', '')
    BINANCE_TESTNET = os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
    
    OKX_API_KEY = os.getenv('OKX_API_KEY', '')
    OKX_SECRET_KEY = os.getenv('OKX_SECRET_KEY', '')
    OKX_PASSPHRASE = os.getenv('OKX_PASSPHRASE', '')
    OKX_SANDBOX = os.getenv('OKX_SANDBOX', 'true').lower() == 'true'
    
    # Trading Configuration
    MIN_SPREAD_PERCENT = float(os.getenv('MIN_SPREAD_PERCENT', '0.8'))
    MAX_TRADE_AMOUNT = float(os.getenv('MAX_TRADE_AMOUNT', '1000'))
    
    # High-Frequency Arbitrage Cryptocurrency Selection (Updated 2024)
    # Tier 1: Ultra-Fast, High-Spread Assets (A+ Grade) - Highest priority
    TIER1_ASSETS = [
        'TON/USDT',   # 30s, 1.5%-2.5% spread, Medium-High liquidity, 25/day
        'ALGO/USDT',  # 4s, 1.5%-2.0% spread, Medium-High liquidity, 25/day
        'VET/USDT',   # 10s, 1.7%-2.2% spread, Medium liquidity, 25/day
        'XLM/USDT',   # 3s, 1.5%-2.0% spread, Medium-High liquidity, 25/day
    ]
    
    # Tier 2: Fast, Good-Spread Assets (A Grade) - High priority
    TIER2_ASSETS = [
        'TRX/USDT',   # 120s, 1.5%-2.0% spread, High liquidity, 15/day
        'FTM/USDT',   # 60s, 1.5% spread, Medium liquidity, 15/day
        'MATIC/USDT', # 90s, 1.2%-1.8% spread, High liquidity, 15/day
        'SOL/USDT',   # 10s, 1.0%-1.5% spread, High liquidity, 15/day
    ]
    
    # Tier 3: Established Assets (B+ Grade) - Medium priority
    TIER3_ASSETS = [
        'BCH/USDT',   # 300s, 1.0%-1.3% spread, Medium liquidity, 10/day
        'XRP/USDT',   # 5s, 1.0%-1.2% spread, High liquidity, 12/day
        'DASH/USDT',  # 150s, 1.3%-1.7% spread, Medium liquidity, 8/day
        'LTC/USDT',   # 150s, 1.1%-1.4% spread, High liquidity, 10/day
    ]
    
    # Tier 4: Additional Profitable Assets - Lower priority
    TIER4_ASSETS = [
        'HBAR/USDT',  # 30s, 1.2% spread, Medium liquidity, 8/day
        'ICP/USDT',   # 90s, 1.0% spread, Medium liquidity, 6/day
        'LINK/USDT',  # 10s, 1.0%-1.3% spread, High liquidity, 10/day
        'ATOM/USDT',  # 7s, 1.0%-1.3% spread, Medium-High liquidity, 8/day
    ]
    
    # Combine all tiers for complete strategy
    CURRENCY_PAIRS = TIER1_ASSETS + TIER2_ASSETS + TIER3_ASSETS + TIER4_ASSETS
    
    # Risk Management (Updated for OKX and Binance)
    MAX_DAILY_TRADES = int(os.getenv('MAX_DAILY_TRADES', '200'))
    MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '15000'))
    STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', '0.5'))
    MIN_SPREAD_PERCENT = float(os.getenv('MIN_SPREAD_PERCENT', '1.0'))  # Updated for new strategy
    
    # Exchange-specific fees (VIP levels) - Updated 2024
    EXCHANGE_FEES = {
        'binance': {
            'trading_fee': 0.00017,  # VIP taker fee
            'withdrawal_fees': {
                # Tier 1: Ultra-Fast, High-Spread Assets
                'TON': 0.1, 'ALGO': 0.1, 'VET': 0.5, 'XLM': 0.25,
                
                # Tier 2: Fast, Good-Spread Assets
                'TRX': 1.0, 'FTM': 0.1, 'MATIC': 0.1, 'SOL': 0.01,
                
                # Tier 3: Established Assets
                'BCH': 0.001, 'XRP': 0.25, 'DASH': 0.01, 'LTC': 0.001,
                
                # Tier 4: Additional Profitable Assets
                'HBAR': 0.1, 'ICP': 0.1, 'LINK': 0.5, 'ATOM': 0.1,
                
                # Common base currencies
                'USDT': 1.0, 'USDC': 1.0, 'DAI': 1.0, 'BUSD': 1.0,
            }
        },
        'okx': {
            'trading_fee': 0.00015,  # VIP taker fee
            'withdrawal_fees': {
                # Tier 1: Ultra-Fast, High-Spread Assets
                'TON': 0.1, 'ALGO': 0.1, 'VET': 0.5, 'XLM': 0.15,
                
                # Tier 2: Fast, Good-Spread Assets
                'TRX': 1.0, 'FTM': 0.1, 'MATIC': 0.1, 'SOL': 0.01,
                
                # Tier 3: Established Assets
                'BCH': 0.001, 'XRP': 0.15, 'DASH': 0.01, 'LTC': 0.001,
                
                # Tier 4: Additional Profitable Assets
                'HBAR': 0.1, 'ICP': 0.1, 'LINK': 0.5, 'ATOM': 0.1,
                
                # Common base currencies
                'USDT': 1.0, 'USDC': 1.0, 'DAI': 1.0, 'BUSD': 1.0,
            }
        }
    }
    
    # Slippage estimates (conservative) - Updated 2024
    SLIPPAGE_ESTIMATES = {
        # Tier 1: Ultra-Fast, High-Spread Assets
        'TON/USDT': 0.0003, 'ALGO/USDT': 0.0002, 'VET/USDT': 0.0003, 'XLM/USDT': 0.0002,
        
        # Tier 2: Fast, Good-Spread Assets
        'TRX/USDT': 0.0002, 'FTM/USDT': 0.0003, 'MATIC/USDT': 0.0003, 'SOL/USDT': 0.0003,
        
        # Tier 3: Established Assets
        'BCH/USDT': 0.0002, 'XRP/USDT': 0.0002, 'DASH/USDT': 0.0003, 'LTC/USDT': 0.0002,
        
        # Tier 4: Additional Profitable Assets
        'HBAR/USDT': 0.0003, 'ICP/USDT': 0.0003, 'LINK/USDT': 0.0004, 'ATOM/USDT': 0.0003,
    }
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'arbitrage_bot.log')
    
    # Railway Configuration
    PORT = int(os.getenv('PORT', '8000'))
    RAILWAY_ENVIRONMENT = os.getenv('RAILWAY_ENVIRONMENT', 'production')
    
    # Exchange-specific configurations
    EXCHANGE_CONFIGS = {
        'binance': {
            'apiKey': BINANCE_API_KEY,
            'secret': BINANCE_SECRET_KEY,
            'sandbox': BINANCE_TESTNET,
            'rateLimit': 1200,
            'enableRateLimit': True,
        },
        'okx': {
            'apiKey': OKX_API_KEY,
            'secret': OKX_SECRET_KEY,
            'passphrase': OKX_PASSPHRASE,
            'sandbox': OKX_SANDBOX,
            'rateLimit': 3000,
            'enableRateLimit': True,
        }
    }
    
    # Currency mappings for different exchanges (Updated 2024)
    CURRENCY_MAPPINGS = {
        # Tier 1: Ultra-Fast, High-Spread Assets
        'TON': {'binance': 'TON', 'okx': 'TON'},
        'ALGO': {'binance': 'ALGO', 'okx': 'ALGO'},
        'VET': {'binance': 'VET', 'okx': 'VET'},
        'XLM': {'binance': 'XLM', 'okx': 'XLM'},
        
        # Tier 2: Fast, Good-Spread Assets
        'TRX': {'binance': 'TRX', 'okx': 'TRX'},
        'FTM': {'binance': 'FTM', 'okx': 'FTM'},
        'MATIC': {'binance': 'MATIC', 'okx': 'MATIC'},
        'SOL': {'binance': 'SOL', 'okx': 'SOL'},
        
        # Tier 3: Established Assets
        'BCH': {'binance': 'BCH', 'okx': 'BCH'},
        'XRP': {'binance': 'XRP', 'okx': 'XRP'},
        'DASH': {'binance': 'DASH', 'okx': 'DASH'},
        'LTC': {'binance': 'LTC', 'okx': 'LTC'},
        
        # Tier 4: Additional Profitable Assets
        'HBAR': {'binance': 'HBAR', 'okx': 'HBAR'},
        'ICP': {'binance': 'ICP', 'okx': 'ICP'},
        'LINK': {'binance': 'LINK', 'okx': 'LINK'},
        'ATOM': {'binance': 'ATOM', 'okx': 'ATOM'},
        
        # Common base currencies
        'USDT': {'binance': 'USDT', 'okx': 'USDT'},
        'USDC': {'binance': 'USDC', 'okx': 'USDC'},
        'DAI': {'binance': 'DAI', 'okx': 'DAI'},
        'BUSD': {'binance': 'BUSD', 'okx': 'BUSD'},
    }
    
    # Transfer speed configurations for each asset (Updated 2024)
    TRANSFER_SPEEDS = {
        # Tier 1: Ultra-Fast, High-Spread Assets (A+ Grade)
        'TON/USDT': {'speed': 30, 'strategy': 'transfer_first', 'min_spread': 0.015, 'max_spread': 0.025},
        'ALGO/USDT': {'speed': 4, 'strategy': 'transfer_first', 'min_spread': 0.015, 'max_spread': 0.02},
        'VET/USDT': {'speed': 10, 'strategy': 'transfer_first', 'min_spread': 0.017, 'max_spread': 0.022},
        'XLM/USDT': {'speed': 3, 'strategy': 'transfer_first', 'min_spread': 0.015, 'max_spread': 0.02},
        
        # Tier 2: Fast, Good-Spread Assets (A Grade)
        'TRX/USDT': {'speed': 120, 'strategy': 'transfer_first', 'min_spread': 0.015, 'max_spread': 0.02},
        'FTM/USDT': {'speed': 60, 'strategy': 'transfer_first', 'min_spread': 0.015, 'max_spread': 0.015},
        'MATIC/USDT': {'speed': 90, 'strategy': 'transfer_first', 'min_spread': 0.012, 'max_spread': 0.018},
        'SOL/USDT': {'speed': 10, 'strategy': 'transfer_first', 'min_spread': 0.01, 'max_spread': 0.015},
        
        # Tier 3: Established Assets (B+ Grade)
        'BCH/USDT': {'speed': 300, 'strategy': 'simultaneous', 'min_spread': 0.01, 'max_spread': 0.013},
        'XRP/USDT': {'speed': 5, 'strategy': 'transfer_first', 'min_spread': 0.01, 'max_spread': 0.012},
        'DASH/USDT': {'speed': 150, 'strategy': 'transfer_first', 'min_spread': 0.013, 'max_spread': 0.017},
        'LTC/USDT': {'speed': 150, 'strategy': 'simultaneous', 'min_spread': 0.011, 'max_spread': 0.014},
        
        # Tier 4: Additional Profitable Assets
        'HBAR/USDT': {'speed': 30, 'strategy': 'transfer_first', 'min_spread': 0.012, 'max_spread': 0.012},
        'ICP/USDT': {'speed': 90, 'strategy': 'transfer_first', 'min_spread': 0.01, 'max_spread': 0.01},
        'LINK/USDT': {'speed': 10, 'strategy': 'transfer_first', 'min_spread': 0.01, 'max_spread': 0.013},
        'ATOM/USDT': {'speed': 7, 'strategy': 'transfer_first', 'min_spread': 0.01, 'max_spread': 0.013},
    }
    
    # Percentage-based position sizing (Updated 2024)
    # Each tier gets a percentage of total account value
    POSITION_PERCENTAGES = {
        # Tier 1: Ultra-Fast, High-Spread Assets (A+ Grade) - Higher allocation
        'TON/USDT': 0.08,   # 8% of total account value
        'ALGO/USDT': 0.08,  # 8% of total account value
        'VET/USDT': 0.06,   # 6% of total account value
        'XLM/USDT': 0.08,   # 8% of total account value
        
        # Tier 2: Fast, Good-Spread Assets (A Grade) - Medium allocation
        'TRX/USDT': 0.06,   # 6% of total account value
        'FTM/USDT': 0.05,   # 5% of total account value
        'MATIC/USDT': 0.06, # 6% of total account value
        'SOL/USDT': 0.07,   # 7% of total account value
        
        # Tier 3: Established Assets (B+ Grade) - Medium allocation
        'BCH/USDT': 0.05,   # 5% of total account value
        'XRP/USDT': 0.06,   # 6% of total account value
        'DASH/USDT': 0.04,  # 4% of total account value
        'LTC/USDT': 0.05,   # 5% of total account value
        
        # Tier 4: Additional Profitable Assets - Lower allocation
        'HBAR/USDT': 0.04,  # 4% of total account value
        'ICP/USDT': 0.03,   # 3% of total account value
        'LINK/USDT': 0.05,  # 5% of total account value
        'ATOM/USDT': 0.04,  # 4% of total account value
    }
    
    # Risk management percentages
    RISK_MANAGEMENT = {
        'max_position_percent': 0.08,      # Maximum 8% of total account per position
        'max_concurrent_trades': 8,        # Maximum 8 concurrent trades
        'max_total_exposure': 0.60,        # Maximum 60% of account in trades
        'reserve_percent': 0.20,           # Keep 20% in reserve
        'min_position_percent': 0.01,       # Minimum 1% of account per position
        'max_daily_trades': 200,           # Maximum 200 trades per day
        'stop_loss_percent': 0.005,        # 0.5% stop loss per trade
    }

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Config.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)
