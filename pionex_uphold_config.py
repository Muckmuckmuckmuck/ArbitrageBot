import os
from dotenv import load_dotenv
from typing import List, Dict, Any
import logging

# Load environment variables
load_dotenv()

class PionexUpholdConfig:
    """Configuration class for the Pionex.US and Uphold arbitrage trading bot"""
    
    # API Configuration
    PIONEX_API_KEY = os.getenv('PIONEX_API_KEY', '')
    PIONEX_SECRET_KEY = os.getenv('PIONEX_SECRET_KEY', '')
    PIONEX_TESTNET = os.getenv('PIONEX_TESTNET', 'true').lower() == 'true'
    
    UPHOLD_API_KEY = os.getenv('UPHOLD_API_KEY', '')
    UPHOLD_SECRET_KEY = os.getenv('UPHOLD_SECRET_KEY', '')
    UPHOLD_SANDBOX = os.getenv('UPHOLD_SANDBOX', 'true').lower() == 'true'
    
    # Trading Configuration
    MIN_SPREAD_PERCENT = float(os.getenv('MIN_SPREAD_PERCENT', '0.5'))  # 0.5% minimum for Pionex
    MAX_TRADE_AMOUNT = float(os.getenv('MAX_TRADE_AMOUNT', '1000'))
    
    # Cryptocurrency Selection (Major Assets Only - High Liquidity)
    # Focus on assets with excellent liquidity and low execution risk
    TIER1_ASSETS = [
        'BTC/USDT',   # Bitcoin - Excellent liquidity, 99% success rate
        'ETH/USDT',   # Ethereum - Excellent liquidity, 99% success rate
    ]
    
    TIER2_ASSETS = [
        'SOL/USDT',   # Solana - High liquidity, 95% success rate
        'MATIC/USDT', # Polygon - High liquidity, 95% success rate
        'ADA/USDT',   # Cardano - High liquidity, 95% success rate
    ]
    
    TIER3_ASSETS = [
        'XRP/USDT',   # Ripple - High liquidity, 95% success rate
        'LTC/USDT',   # Litecoin - High liquidity, 95% success rate
        'BCH/USDT',   # Bitcoin Cash - Medium liquidity, 90% success rate
    ]
    
    TIER4_ASSETS = [
        'LINK/USDT',  # Chainlink - Medium-High liquidity, 90% success rate
        'ATOM/USDT',  # Cosmos - Medium-High liquidity, 90% success rate
        'ALGO/USDT',  # Algorand - Medium-High liquidity, 90% success rate
        'XLM/USDT',   # Stellar - Medium-High liquidity, 90% success rate
    ]
    
    # Combine all tiers for complete strategy
    CURRENCY_PAIRS = TIER1_ASSETS + TIER2_ASSETS + TIER3_ASSETS + TIER4_ASSETS
    
    # Risk Management (Updated for Pionex and Uphold)
    MAX_DAILY_TRADES = int(os.getenv('MAX_DAILY_TRADES', '100'))
    MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '10000'))
    STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', '0.5'))
    
    # Exchange-specific fees (Pionex and Uphold)
    EXCHANGE_FEES = {
        'pionex': {
            'trading_fee': 0.001,  # 0.1% flat fee
            'withdrawal_fees': {
                # Tier 1: Major Assets
                'BTC': 0.0001, 'ETH': 0.001,
                
                # Tier 2: Major Altcoins
                'SOL': 0.01, 'MATIC': 0.1, 'ADA': 0.5,
                
                # Tier 3: Established Assets
                'XRP': 0.25, 'LTC': 0.001, 'BCH': 0.001,
                
                # Tier 4: Mid-Tier Altcoins
                'LINK': 0.5, 'ATOM': 0.1, 'ALGO': 0.1, 'XLM': 0.25,
                
                # Stablecoins
                'USDT': 1.0, 'USDC': 1.0,
            }
        },
        'uphold': {
            'trading_fee': 0.01,  # 1% spread (average)
            'withdrawal_fees': {
                # Tier 1: Major Assets
                'BTC': 0.0001, 'ETH': 0.001,
                
                # Tier 2: Major Altcoins
                'SOL': 0.01, 'MATIC': 0.1, 'ADA': 0.5,
                
                # Tier 3: Established Assets
                'XRP': 0.25, 'LTC': 0.001, 'BCH': 0.001,
                
                # Tier 4: Mid-Tier Altcoins
                'LINK': 0.5, 'ATOM': 0.1, 'ALGO': 0.1, 'XLM': 0.25,
                
                # Stablecoins
                'USDT': 1.0, 'USDC': 1.0,
            },
            'ach_withdrawal_fee': 0.0175,  # 1.75% for ACH withdrawals
        }
    }
    
    # Slippage estimates (conservative)
    SLIPPAGE_ESTIMATES = {
        # Tier 1: Major Assets - Very low slippage
        'BTC/USDT': 0.0001, 'ETH/USDT': 0.0001,
        
        # Tier 2: Major Altcoins - Low slippage
        'SOL/USDT': 0.0002, 'MATIC/USDT': 0.0002, 'ADA/USDT': 0.0002,
        
        # Tier 3: Established Assets - Low slippage
        'XRP/USDT': 0.0002, 'LTC/USDT': 0.0002, 'BCH/USDT': 0.0002,
        
        # Tier 4: Mid-Tier Altcoins - Medium slippage
        'LINK/USDT': 0.0003, 'ATOM/USDT': 0.0003, 'ALGO/USDT': 0.0002, 'XLM/USDT': 0.0002,
    }
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'pionex_uphold_arbitrage.log')
    
    # Railway Configuration
    PORT = int(os.getenv('PORT', '8000'))
    RAILWAY_ENVIRONMENT = os.getenv('RAILWAY_ENVIRONMENT', 'production')
    
    # Exchange-specific configurations
    EXCHANGE_CONFIGS = {
        'pionex': {
            'apiKey': PIONEX_API_KEY,
            'secret': PIONEX_SECRET_KEY,
            'sandbox': PIONEX_TESTNET,
            'rateLimit': 600,  # 600 requests per minute
            'enableRateLimit': True,
        },
        'uphold': {
            'apiKey': UPHOLD_API_KEY,
            'secret': UPHOLD_SECRET_KEY,
            'sandbox': UPHOLD_SANDBOX,
            'rateLimit': 300,  # 300 requests per minute
            'enableRateLimit': True,
        }
    }
    
    # Currency mappings for different exchanges
    CURRENCY_MAPPINGS = {
        # Tier 1: Major Assets
        'BTC': {'pionex': 'BTC', 'uphold': 'BTC'},
        'ETH': {'pionex': 'ETH', 'uphold': 'ETH'},
        
        # Tier 2: Major Altcoins
        'SOL': {'pionex': 'SOL', 'uphold': 'SOL'},
        'MATIC': {'pionex': 'MATIC', 'uphold': 'MATIC'},
        'ADA': {'pionex': 'ADA', 'uphold': 'ADA'},
        
        # Tier 3: Established Assets
        'XRP': {'pionex': 'XRP', 'uphold': 'XRP'},
        'LTC': {'pionex': 'LTC', 'uphold': 'LTC'},
        'BCH': {'pionex': 'BCH', 'uphold': 'BCH'},
        
        # Tier 4: Mid-Tier Altcoins
        'LINK': {'pionex': 'LINK', 'uphold': 'LINK'},
        'ATOM': {'pionex': 'ATOM', 'uphold': 'ATOM'},
        'ALGO': {'pionex': 'ALGO', 'uphold': 'ALGO'},
        'XLM': {'pionex': 'XLM', 'uphold': 'XLM'},
        
        # Stablecoins
        'USDT': {'pionex': 'USDT', 'uphold': 'USDT'},
        'USDC': {'pionex': 'USDC', 'uphold': 'USDC'},
    }
    
    # Transfer speed configurations for each asset
    TRANSFER_SPEEDS = {
        # Tier 1: Major Assets - Fast transfers
        'BTC/USDT': {'speed': 600, 'strategy': 'simultaneous', 'min_spread': 0.005, 'max_spread': 0.01},
        'ETH/USDT': {'speed': 300, 'strategy': 'simultaneous', 'min_spread': 0.005, 'max_spread': 0.01},
        
        # Tier 2: Major Altcoins - Fast transfers
        'SOL/USDT': {'speed': 10, 'strategy': 'transfer_first', 'min_spread': 0.005, 'max_spread': 0.01},
        'MATIC/USDT': {'speed': 90, 'strategy': 'transfer_first', 'min_spread': 0.005, 'max_spread': 0.01},
        'ADA/USDT': {'speed': 300, 'strategy': 'simultaneous', 'min_spread': 0.005, 'max_spread': 0.01},
        
        # Tier 3: Established Assets - Medium transfers
        'XRP/USDT': {'speed': 5, 'strategy': 'transfer_first', 'min_spread': 0.005, 'max_spread': 0.01},
        'LTC/USDT': {'speed': 150, 'strategy': 'transfer_first', 'min_spread': 0.005, 'max_spread': 0.01},
        'BCH/USDT': {'speed': 300, 'strategy': 'simultaneous', 'min_spread': 0.005, 'max_spread': 0.01},
        
        # Tier 4: Mid-Tier Altcoins - Fast transfers
        'LINK/USDT': {'speed': 10, 'strategy': 'transfer_first', 'min_spread': 0.005, 'max_spread': 0.01},
        'ATOM/USDT': {'speed': 7, 'strategy': 'transfer_first', 'min_spread': 0.005, 'max_spread': 0.01},
        'ALGO/USDT': {'speed': 4, 'strategy': 'transfer_first', 'min_spread': 0.005, 'max_spread': 0.01},
        'XLM/USDT': {'speed': 3, 'strategy': 'transfer_first', 'min_spread': 0.005, 'max_spread': 0.01},
    }
    
    # Percentage-based position sizing
    # Each tier gets a percentage of total account value
    POSITION_PERCENTAGES = {
        # Tier 1: Major Assets - Higher allocation (Excellent liquidity)
        'BTC/USDT': 0.12,   # 12% of total account value
        'ETH/USDT': 0.12,   # 12% of total account value
        
        # Tier 2: Major Altcoins - Medium-High allocation (High liquidity)
        'SOL/USDT': 0.08,   # 8% of total account value
        'MATIC/USDT': 0.08, # 8% of total account value
        'ADA/USDT': 0.08,   # 8% of total account value
        
        # Tier 3: Established Assets - Medium allocation (High liquidity)
        'XRP/USDT': 0.07,   # 7% of total account value
        'LTC/USDT': 0.06,   # 6% of total account value
        'BCH/USDT': 0.05,   # 5% of total account value
        
        # Tier 4: Mid-Tier Altcoins - Lower allocation (Medium-High liquidity)
        'LINK/USDT': 0.05,  # 5% of total account value
        'ATOM/USDT': 0.04,  # 4% of total account value
        'ALGO/USDT': 0.04,  # 4% of total account value
        'XLM/USDT': 0.04,   # 4% of total account value
    }
    
    # Risk management percentages
    RISK_MANAGEMENT = {
        'max_position_percent': 0.12,      # Maximum 12% of total account per position
        'max_concurrent_trades': 6,        # Maximum 6 concurrent trades
        'max_total_exposure': 0.50,        # Maximum 50% of account in trades
        'reserve_percent': 0.30,           # Keep 30% in reserve
        'min_position_percent': 0.02,       # Minimum 2% of account per position
        'max_daily_trades': 100,           # Maximum 100 trades per day
        'stop_loss_percent': 0.005,        # 0.5% stop loss per trade
        'min_account_balance_usd': 100,    # Minimum $100 to operate
    }
    
    # Liquidity requirements (Only trade high-liquidity assets)
    LIQUIDITY_REQUIREMENTS = {
        'min_daily_volume_usd': 100000000,  # $100M minimum daily volume
        'min_order_book_depth_usd': 1000000, # $1M minimum order book depth
        'max_slippage_percent': 0.001,       # 0.1% maximum slippage
    }
    
    # Spread requirements (Adjusted for Pionex.US low fees)
    SPREAD_REQUIREMENTS = {
        'pionex_only': 0.002,  # 0.2% minimum spread (Pionex low fees)
        'uphold_only': 0.015,  # 1.5% minimum spread (Uphold higher fees)
        'cross_exchange': 0.005, # 0.5% minimum spread for cross-exchange arbitrage
    }

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, PionexUpholdConfig.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(PionexUpholdConfig.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

