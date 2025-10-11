import os
from dotenv import load_dotenv
from typing import List, Dict, Any
import logging

# Load environment variables
load_dotenv()

class PionexCoinbaseConfig:
    """Configuration class for the Pionex.US and Coinbase Pro arbitrage trading bot"""
    
    # API Configuration
    PIONEX_API_KEY = os.getenv('PIONEX_API_KEY', '')
    PIONEX_SECRET_KEY = os.getenv('PIONEX_SECRET_KEY', '')
    PIONEX_TESTNET = os.getenv('PIONEX_TESTNET', 'true').lower() == 'true'
    
    COINBASE_API_KEY = os.getenv('COINBASE_API_KEY', '')
    COINBASE_SECRET_KEY = os.getenv('COINBASE_SECRET_KEY', '')
    COINBASE_PASSPHRASE = os.getenv('COINBASE_PASSPHRASE', '')
    COINBASE_SANDBOX = os.getenv('COINBASE_SANDBOX', 'true').lower() == 'true'
    
    # Trading Configuration
    MIN_SPREAD_PERCENT = float(os.getenv('MIN_SPREAD_PERCENT', '0.6'))  # 0.6% minimum
    MAX_TRADE_AMOUNT = float(os.getenv('MAX_TRADE_AMOUNT', '1000'))
    
    # Cryptocurrency Selection (BEST COMPATIBLE CRYPTOS)
    # Based on comprehensive scan of 33 cryptos - Top 10 by profitability score
    
    # TIER 1: Top Performers (Score > 0.65) - 50% allocation
    TIER1_ASSETS = [
        'TON/USDT',   # Score: 0.713 - Layer 1 - 1.7% spread, 60% freq
        'SHIB/USDT',  # Score: 0.710 - Meme - 1.2% spread, 50% freq
        'SOL/USDT',   # Score: 0.667 - Layer 1 - 0.8% spread, 45% freq
    ]
    
    # TIER 2: Strong Performers (Score 0.60-0.65) - 35% allocation
    TIER2_ASSETS = [
        'AVAX/USDT',  # Score: 0.654 - Layer 1 - 0.9% spread, 40% freq
        'ARB/USDT',   # Score: 0.640 - Layer 2 - 1.0% spread, 35% freq
        'PEPE/USDT',  # Score: 0.633 - Meme - 1.5% spread, 55% freq
        'DOGE/USDT',  # Score: 0.630 - Meme - 0.8% spread, 35% freq
        'ATOM/USDT',  # Score: 0.627 - Layer 1 - 0.9% spread, 35% freq
    ]
    
    # TIER 3: Good Performers (Score < 0.60) - 15% allocation
    TIER3_ASSETS = [
        'XLM/USDT',   # Score: 0.621 - Payment - 0.8% spread, 30% freq
        'UNI/USDT',   # Score: 0.615 - DeFi - 0.9% spread, 40% freq
    ]
    
    # Combine all tiers for complete strategy (diversified portfolio)
    CURRENCY_PAIRS = TIER1_ASSETS + TIER2_ASSETS + TIER3_ASSETS
    
    # Risk Management (Updated for Pionex and Coinbase)
    MAX_DAILY_TRADES = int(os.getenv('MAX_DAILY_TRADES', '100'))
    MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '10000'))
    STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', '0.5'))
    
    # Exchange-specific fees (Pionex and Coinbase Pro)
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
        'coinbasepro': {
            'trading_fee': 0.005,  # 0.5% fee
            'withdrawal_fees': {
                # Tier 1: Major Assets
                'BTC': 0.0, 'ETH': 0.0,  # Free withdrawals
                
                # Tier 2: Major Altcoins
                'SOL': 0.0, 'MATIC': 0.0, 'ADA': 0.0,
                
                # Tier 3: Established Assets
                'XRP': 0.0, 'LTC': 0.0, 'BCH': 0.0,
                
                # Tier 4: Mid-Tier Altcoins
                'LINK': 0.0, 'ATOM': 0.0, 'ALGO': 0.0, 'XLM': 0.0,
                
                # Stablecoins
                'USDT': 0.0, 'USDC': 0.0,  # Free withdrawals
            }
        }
    }
    
    # Slippage estimates (adjusted for lower liquidity on Pionex/Coinbase)
    # Note: 2-4x higher than Binance/OKX due to lower volumes
    SLIPPAGE_ESTIMATES = {
        # Tier 1: Major Assets - Low slippage (still good liquidity)
        'BTC/USDT': 0.0005, 'ETH/USDT': 0.0005,
        
        # Tier 2: Major Altcoins - Medium-low slippage
        'SOL/USDT': 0.001, 'MATIC/USDT': 0.001, 'ADA/USDT': 0.001,
        
        # Tier 3: Established Assets - Medium slippage
        'XRP/USDT': 0.001, 'LTC/USDT': 0.001, 'BCH/USDT': 0.0012,
        
        # Tier 4: Mid-Tier Altcoins - Medium-high slippage
        'LINK/USDT': 0.0015, 'ATOM/USDT': 0.0015, 'ALGO/USDT': 0.001, 'XLM/USDT': 0.001,
    }
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'pionex_coinbase_arbitrage.log')
    
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
        'coinbasepro': {
            'apiKey': COINBASE_API_KEY,
            'secret': COINBASE_SECRET_KEY,
            'password': COINBASE_PASSPHRASE,
            'sandbox': COINBASE_SANDBOX,
            'rateLimit': 600,  # 600 requests per minute
            'enableRateLimit': True,
        }
    }
    
    # Currency mappings for different exchanges
    CURRENCY_MAPPINGS = {
        # Tier 1: Major Assets
        'BTC': {'pionex': 'BTC', 'coinbasepro': 'BTC'},
        'ETH': {'pionex': 'ETH', 'coinbasepro': 'ETH'},
        
        # Tier 2: Major Altcoins
        'SOL': {'pionex': 'SOL', 'coinbasepro': 'SOL'},
        'MATIC': {'pionex': 'MATIC', 'coinbasepro': 'MATIC'},
        'ADA': {'pionex': 'ADA', 'coinbasepro': 'ADA'},
        
        # Tier 3: Established Assets
        'XRP': {'pionex': 'XRP', 'coinbasepro': 'XRP'},
        'LTC': {'pionex': 'LTC', 'coinbasepro': 'LTC'},
        'BCH': {'pionex': 'BCH', 'coinbasepro': 'BCH'},
        
        # Tier 4: Mid-Tier Altcoins
        'LINK': {'pionex': 'LINK', 'coinbasepro': 'LINK'},
        'ATOM': {'pionex': 'ATOM', 'coinbasepro': 'ATOM'},
        'ALGO': {'pionex': 'ALGO', 'coinbasepro': 'ALGO'},
        'XLM': {'pionex': 'XLM', 'coinbasepro': 'XLM'},
        
        # Stablecoins
        'USDT': {'pionex': 'USDT', 'coinbasepro': 'USDT'},
        'USDC': {'pionex': 'USDC', 'coinbasepro': 'USDC'},
    }
    
    # Transfer speed configurations for each asset
    TRANSFER_SPEEDS = {
        # Tier 1: Major Assets - Fast transfers
        'BTC/USDT': {'speed': 600, 'strategy': 'simultaneous', 'min_spread': 0.006, 'max_spread': 0.01},
        'ETH/USDT': {'speed': 300, 'strategy': 'simultaneous', 'min_spread': 0.006, 'max_spread': 0.01},
        
        # Tier 2: Major Altcoins - Fast transfers
        'SOL/USDT': {'speed': 10, 'strategy': 'transfer_first', 'min_spread': 0.006, 'max_spread': 0.01},
        'MATIC/USDT': {'speed': 90, 'strategy': 'transfer_first', 'min_spread': 0.006, 'max_spread': 0.01},
        'ADA/USDT': {'speed': 300, 'strategy': 'simultaneous', 'min_spread': 0.006, 'max_spread': 0.01},
        
        # Tier 3: Established Assets - Medium transfers
        'XRP/USDT': {'speed': 5, 'strategy': 'transfer_first', 'min_spread': 0.006, 'max_spread': 0.01},
        'LTC/USDT': {'speed': 150, 'strategy': 'transfer_first', 'min_spread': 0.006, 'max_spread': 0.01},
        'BCH/USDT': {'speed': 300, 'strategy': 'simultaneous', 'min_spread': 0.006, 'max_spread': 0.01},
        
        # Tier 4: Mid-Tier Altcoins - Fast transfers
        'LINK/USDT': {'speed': 10, 'strategy': 'transfer_first', 'min_spread': 0.006, 'max_spread': 0.01},
        'ATOM/USDT': {'speed': 7, 'strategy': 'transfer_first', 'min_spread': 0.006, 'max_spread': 0.01},
        'ALGO/USDT': {'speed': 4, 'strategy': 'transfer_first', 'min_spread': 0.006, 'max_spread': 0.01},
        'XLM/USDT': {'speed': 3, 'strategy': 'transfer_first', 'min_spread': 0.006, 'max_spread': 0.01},
    }
    
    # Percentage-based position sizing (DIVERSIFIED STRATEGY)
    # Based on profitability score and category diversification
    POSITION_PERCENTAGES = {
        # Tier 1: Top Performers (50% total allocation)
        'TON/USDT': 0.18,    # 18% - Highest score (0.713)
        'SHIB/USDT': 0.17,   # 17% - Second highest (0.710)
        'SOL/USDT': 0.15,    # 15% - Third highest (0.667)
        
        # Tier 2: Strong Performers (35% total allocation)
        'AVAX/USDT': 0.08,   # 8% - Layer 1 (0.654)
        'ARB/USDT': 0.07,    # 7% - Layer 2 (0.640)
        'PEPE/USDT': 0.07,   # 7% - Meme (0.633)
        'DOGE/USDT': 0.06,   # 6% - Meme (0.630)
        'ATOM/USDT': 0.07,   # 7% - Layer 1 (0.627)
        
        # Tier 3: Good Performers (15% total allocation)
        'XLM/USDT': 0.08,    # 8% - Fast transfer (0.621)
        'UNI/USDT': 0.07,    # 7% - DeFi (0.615)
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
    
    # Crypto-specific spread requirements (TOP 10 BEST CRYPTOS)
    CURRENCY_PAIR_SPREADS = {
        'TON/USDT': {
            'min_spread': 0.00800,  # 0.80%
            'safe_spread': 0.01700,  # 1.70%
            'max_spread': 0.03000,  # 3.00%
            'slippage': 0.00100,
            'transfer_time': 60,
            'frequency': 0.60,
            'category': 'Layer 1',
            'score': 0.713,
        },
        'SHIB/USDT': {
            'min_spread': 0.00600,  # 0.60%
            'safe_spread': 0.01200,  # 1.20%
            'max_spread': 0.02200,  # 2.20%
            'slippage': 0.00100,
            'transfer_time': 30,
            'frequency': 0.50,
            'category': 'Meme',
            'score': 0.710,
        },
        'SOL/USDT': {
            'min_spread': 0.00400,  # 0.40%
            'safe_spread': 0.00800,  # 0.80%
            'max_spread': 0.01500,  # 1.50%
            'slippage': 0.00100,
            'transfer_time': 10,
            'frequency': 0.45,
            'category': 'Layer 1',
            'score': 0.667,
        },
        'AVAX/USDT': {
            'min_spread': 0.00500,  # 0.50%
            'safe_spread': 0.00900,  # 0.90%
            'max_spread': 0.01700,  # 1.70%
            'slippage': 0.00100,
            'transfer_time': 30,
            'frequency': 0.40,
            'category': 'Layer 1',
            'score': 0.654,
        },
        'ARB/USDT': {
            'min_spread': 0.00500,  # 0.50%
            'safe_spread': 0.01000,  # 1.00%
            'max_spread': 0.01900,  # 1.90%
            'slippage': 0.00100,
            'transfer_time': 60,
            'frequency': 0.35,
            'category': 'Layer 2',
            'score': 0.640,
        },
        'PEPE/USDT': {
            'min_spread': 0.00700,  # 0.70%
            'safe_spread': 0.01500,  # 1.50%
            'max_spread': 0.02800,  # 2.80%
            'slippage': 0.00100,
            'transfer_time': 30,
            'frequency': 0.55,
            'category': 'Meme',
            'score': 0.633,
        },
        'DOGE/USDT': {
            'min_spread': 0.00400,  # 0.40%
            'safe_spread': 0.00800,  # 0.80%
            'max_spread': 0.01600,  # 1.60%
            'slippage': 0.00100,
            'transfer_time': 60,
            'frequency': 0.35,
            'category': 'Meme',
            'score': 0.630,
        },
        'ATOM/USDT': {
            'min_spread': 0.00500,  # 0.50%
            'safe_spread': 0.00900,  # 0.90%
            'max_spread': 0.01700,  # 1.70%
            'slippage': 0.00100,
            'transfer_time': 60,
            'frequency': 0.35,
            'category': 'Layer 1',
            'score': 0.627,
        },
        'XLM/USDT': {
            'min_spread': 0.00400,  # 0.40%
            'safe_spread': 0.00800,  # 0.80%
            'max_spread': 0.01500,  # 1.50%
            'slippage': 0.00100,
            'transfer_time': 3,
            'frequency': 0.30,
            'category': 'Payment',
            'score': 0.621,
        },
        'UNI/USDT': {
            'min_spread': 0.00500,  # 0.50%
            'safe_spread': 0.00900,  # 0.90%
            'max_spread': 0.01800,  # 1.80%
            'slippage': 0.00100,
            'transfer_time': 120,
            'frequency': 0.40,
            'category': 'DeFi',
            'score': 0.615,
        },
    }
    
    # Spread requirements (Adjusted for combined fees: 0.1% + 0.5% = 0.6%)
    SPREAD_REQUIREMENTS = {
        'pionex_only': 0.002,  # 0.2% minimum spread (Pionex low fees)
        'coinbase_only': 0.006,  # 0.6% minimum spread (Coinbase higher fees)
        'cross_exchange': 0.007, # 0.7% minimum spread for cross-exchange arbitrage (0.6% fees + 0.1% profit)
    }

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, PionexCoinbaseConfig.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(PionexCoinbaseConfig.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

