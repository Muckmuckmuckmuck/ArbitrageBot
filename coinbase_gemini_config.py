"""
Configuration for Coinbase + Gemini Arbitrage Bot
Updated: October 2025
Exchanges: Coinbase Advanced + Gemini
"""

import os
from dotenv import load_dotenv
from typing import Dict, List

load_dotenv()

# ============================================================================
# EXCHANGE CONFIGURATION
# ============================================================================

EXCHANGE_1_ID = 'coinbase'  # Coinbase Advanced
EXCHANGE_2_ID = 'gemini'    # Gemini

# ============================================================================
# API KEYS (Set in Railway Variables or .env file)
# ============================================================================

# Coinbase Advanced API Keys
# Note: Newer Coinbase API keys may not have a passphrase (CDP API)
# Older keys have passphrase. Bot supports both!
COINBASE_API_KEY = os.getenv('COINBASE_API_KEY', '')
COINBASE_SECRET_KEY = os.getenv('COINBASE_SECRET_KEY', '')
COINBASE_PASSPHRASE = os.getenv('COINBASE_PASSPHRASE', '')  # Optional for newer API keys
COINBASE_SANDBOX = os.getenv('COINBASE_SANDBOX', 'false').lower() == 'true'

# Gemini API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_SECRET_KEY = os.getenv('GEMINI_SECRET_KEY', '')
GEMINI_SANDBOX = os.getenv('GEMINI_SANDBOX', 'false').lower() == 'true'

# ============================================================================
# EXCHANGE-SPECIFIC FEES (October 2025)
# ============================================================================

EXCHANGE_FEES = {
    'coinbase': {
        # Coinbase Advanced Trade (formerly Coinbase Pro)
        'maker': 0.0040,   # 0.40% maker fee (volume < $10k/month)
        'taker': 0.0060,   # 0.60% taker fee (volume < $10k/month)
        
        # Note: Fees decrease with volume:
        # $10k-$50k: 0.25% maker, 0.40% taker
        # $50k-$100k: 0.15% maker, 0.25% taker
        # $100k+: Lower fees
        
        # Withdrawal fees (crypto transfers)
        'withdrawal': {
            'BTC': 0.0,      # FREE crypto withdrawals on Coinbase!
            'ETH': 0.0,
            'SOL': 0.0,
            'AVAX': 0.0,
            'DOGE': 0.0,
            'SHIB': 0.0,
            'XRP': 0.0,
            'DOT': 0.0,
            'LINK': 0.0,
            'UNI': 0.0,
            'ATOM': 0.0,
            'LTC': 0.0,
            'AAVE': 0.0,
            'COMP': 0.0,
            'default': 0.0,  # All crypto withdrawals are FREE!
        },
    },
    'gemini': {
        # Gemini API Trading Fees
        'maker': 0.0010,   # 0.10% maker fee (API orders)
        'taker': 0.0035,   # 0.35% taker fee (API orders)
        
        # Note: Web/mobile fees are higher:
        # Web: 0.25% maker, 0.35% taker
        # But API gets better rates!
        
        # Withdrawal fees (crypto transfers)
        # Gemini offers 10 FREE withdrawals per month, then charges network fees
        'withdrawal': {
            'BTC': 0.0,      # FREE (within 10/month limit)
            'ETH': 0.0,      # FREE (within 10/month limit)
            'SOL': 0.0,      # FREE (within 10/month limit)
            'AVAX': 0.0,     # FREE (within 10/month limit)
            'DOGE': 0.0,     # FREE (within 10/month limit)
            'SHIB': 0.0,     # FREE (within 10/month limit)
            'XRP': 0.0,      # FREE (within 10/month limit)
            'DOT': 0.0,      # FREE (within 10/month limit)
            'LINK': 0.0,     # FREE (within 10/month limit)
            'UNI': 0.0,      # FREE (within 10/month limit)
            'ATOM': 0.0,     # FREE (within 10/month limit)
            'LTC': 0.0,      # FREE (within 10/month limit)
            'AAVE': 0.0,     # FREE (within 10/month limit)
            'COMP': 0.0,     # FREE (within 10/month limit)
            'default': 0.0,  # FREE within monthly limit
        },
        'free_withdrawals_per_month': 10,
    },
}

# ============================================================================
# CRYPTOCURRENCY SELECTION (Available on BOTH Coinbase and Gemini)
# ============================================================================

# REFINED: Best 11 cryptos (removed BTC, ETH, LTC due to low spreads/slow transfers)
# Ranked by: Transfer speed + Spread potential + Frequency + Liquidity
CURRENCY_PAIRS = [
    'SHIB/USD',   # #1 - Best spread (1.2%), high frequency (38%)
    'AAVE/USD',   # #2 - Best spread (1.2%), good frequency (33%)
    'COMP/USD',   # #3 - Best spread (1.2%), good frequency (28%)
    'UNI/USD',    # #4 - Good spread (1.0%), good frequency (30%)
    'DOT/USD',    # #5 - Good spread (1.0%), high frequency (33%)
    'SOL/USD',    # #6 - Ultra fast (20s), good frequency (33%)
    'AVAX/USD',   # #7 - Very fast (90s), good spread (0.9%)
    'LINK/USD',   # #8 - Good spread (0.9%), good frequency (28%)
    'DOGE/USD',   # #9 - Fast transfer, decent spread (0.8%)
    'XRP/USD',    # #10 - Ultra fast (4s), decent frequency (28%)
    'ATOM/USD',   # #11 - Good spread (0.9%), decent frequency (28%)
]

# Removed (poor scores):
# - BTC/USD: Score 0.224 (30 min transfer, 0.3% spread, 18% frequency)
# - ETH/USD: Score 0.578 (0.4% spread too low, 23% frequency)
# - LTC/USD: Score 0.610 (6 min transfer, 0.7% spread, 23% frequency)

# ============================================================================
# CRYPTO-SPECIFIC PARAMETERS
# ============================================================================

# Minimum spread required for profitability (after fees + slippage)
# Formula: min_spread > (coinbase_taker + gemini_taker + slippage + buffer)
#         = 0.60% + 0.35% + 0.10% + 0.10% = 1.15%
# So minimum spread should be 1.2% for safety

CURRENCY_PAIR_SPREADS = {
    # REFINED LIST: Top 11 cryptos only (removed BTC, ETH, LTC)
    'SOL/USD': {
        'min_spread': 0.012,      # 1.2%
        'safe_spread': 0.015,     # 1.5%
        'max_spread': 0.030,      # 3.0%
        'slippage': 0.00100,      # 0.1%
        'transfer_time': 20,      # 20 seconds (Solana - very fast!)
        'frequency': 0.35,        # 35%
        'category': 'Layer 1',
        'liquidity_score': 0.9,
    },
    'AVAX/USD': {
        'min_spread': 0.012,      # 1.2%
        'safe_spread': 0.016,     # 1.6%
        'max_spread': 0.035,      # 3.5%
        'slippage': 0.00100,      # 0.1%
        'transfer_time': 60,      # 1 minute (Avalanche C-Chain)
        'frequency': 0.30,        # 30%
        'category': 'Layer 1',
        'liquidity_score': 0.8,
    },
    'DOGE/USD': {
        'min_spread': 0.012,      # 1.2%
        'safe_spread': 0.015,     # 1.5%
        'max_spread': 0.030,      # 3.0%
        'slippage': 0.00100,      # 0.1%
        'transfer_time': 180,     # 3 minutes (Dogecoin)
        'frequency': 0.30,        # 30%
        'category': 'Meme',
        'liquidity_score': 0.8,
    },
    'SHIB/USD': {
        'min_spread': 0.013,      # 1.3%
        'safe_spread': 0.018,     # 1.8%
        'max_spread': 0.035,      # 3.5%
        'slippage': 0.00150,      # 0.15% (higher slippage for meme coins)
        'transfer_time': 180,     # 3 minutes (Ethereum network)
        'frequency': 0.40,        # 40%
        'category': 'Meme',
        'liquidity_score': 0.7,
    },
    'XRP/USD': {
        'min_spread': 0.012,      # 1.2%
        'safe_spread': 0.014,     # 1.4%
        'max_spread': 0.028,      # 2.8%
        'slippage': 0.00100,      # 0.1%
        'transfer_time': 5,       # 5 seconds (XRP Ledger - very fast!)
        'frequency': 0.30,        # 30%
        'category': 'Payment',
        'liquidity_score': 0.9,
    },
    'DOT/USD': {
        'min_spread': 0.012,      # 1.2%
        'safe_spread': 0.017,     # 1.7%
        'max_spread': 0.035,      # 3.5%
        'slippage': 0.00100,      # 0.1%
        'transfer_time': 120,     # 2 minutes (Polkadot)
        'frequency': 0.25,        # 25%
        'category': 'Layer 0',
        'liquidity_score': 0.7,
    },
    'LINK/USD': {
        'min_spread': 0.012,      # 1.2%
        'safe_spread': 0.016,     # 1.6%
        'max_spread': 0.032,      # 3.2%
        'slippage': 0.00100,      # 0.1%
        'transfer_time': 180,     # 3 minutes (Ethereum)
        'frequency': 0.28,        # 28%
        'category': 'Oracle',
        'liquidity_score': 0.8,
    },
    'UNI/USD': {
        'min_spread': 0.012,      # 1.2%
        'safe_spread': 0.016,     # 1.6%
        'max_spread': 0.033,      # 3.3%
        'slippage': 0.00100,      # 0.1%
        'transfer_time': 180,     # 3 minutes (Ethereum)
        'frequency': 0.32,        # 32%
        'category': 'DeFi',
        'liquidity_score': 0.8,
    },
    'ATOM/USD': {
        'min_spread': 0.012,      # 1.2%
        'safe_spread': 0.016,     # 1.6%
        'max_spread': 0.033,      # 3.3%
        'slippage': 0.00100,      # 0.1%
        'transfer_time': 300,     # 5 minutes (Cosmos)
        'frequency': 0.28,        # 28%
        'category': 'Layer 1',
        'liquidity_score': 0.7,
    },
    'AAVE/USD': {
        'min_spread': 0.012,      # 1.2%
        'safe_spread': 0.018,     # 1.8%
        'max_spread': 0.036,      # 3.6%
        'slippage': 0.00120,      # 0.12%
        'transfer_time': 180,     # 3 minutes (Ethereum)
        'frequency': 0.30,        # 30%
        'category': 'DeFi',
        'liquidity_score': 0.7,
    },
    'COMP/USD': {
        'min_spread': 0.012,      # 1.2%
        'safe_spread': 0.018,     # 1.8%
        'max_spread': 0.036,      # 3.6%
        'slippage': 0.00120,      # 0.12%
        'transfer_time': 180,     # 3 minutes (Ethereum)
        'frequency': 0.28,        # 28%
        'category': 'DeFi',
        'liquidity_score': 0.7,
    },
}

# ============================================================================
# POSITION SIZING (Percentage-based, scales with balance)
# ============================================================================

# REFINED: Position percentages based on score (Speed + Spread + Frequency + Liquidity)
# Removed BTC, ETH, LTC - keeping only top 11 performers
BASE_POSITION_PERCENTAGES = {
    # Top tier: Best spreads (1.0-1.2%) + good frequency (28-38%)
    'SHIB/USD': 0.10,    # 10.0% - Score: 0.811 (Best spread 1.2%, 38% frequency)
    'AAVE/USD': 0.10,    # 10.0% - Score: 0.801 (Best spread 1.2%, 33% frequency)
    'COMP/USD': 0.10,    # 10.0% - Score: 0.791 (Best spread 1.2%, 28% frequency)
    'UNI/USD': 0.09,     # 9.0%  - Score: 0.747 (Good spread 1.0%, 30% frequency)
    'DOT/USD': 0.09,     # 9.0%  - Score: 0.737 (Good spread 1.0%, 33% frequency)
    
    # Fast transfers + good frequency
    'SOL/USD': 0.09,     # 9.0%  - Score: 0.735 (Ultra fast 20s, 33% frequency)
    'AVAX/USD': 0.09,    # 9.0%  - Score: 0.731 (Very fast 90s, 0.9% spread)
    'LINK/USD': 0.09,    # 9.0%  - Score: 0.714 (Good spread 0.9%, 28% frequency)
    
    # Good all-around performers
    'DOGE/USD': 0.09,    # 9.0%  - Score: 0.684 (Fast transfer, 0.8% spread)
    'XRP/USD': 0.08,     # 8.0%  - Score: 0.670 (Ultra fast 4s, 28% frequency)
    'ATOM/USD': 0.08,    # 8.0%  - Score: 0.651 (Good spread 0.9%, 28% frequency)
}

# Total: 100% across 11 cryptos (removed BTC, ETH, LTC)

# Position sizing limits
MAX_POSITION_PERCENT_PER_TRADE = 0.15  # 15% of total account value per trade
MAX_TOTAL_EXPOSURE_PERCENT = 0.95      # 95% max exposure
RESERVE_PERCENT = 0.05                  # 5% reserve
MAX_CONCURRENT_TRADES = 10              # Max 10 simultaneous trades
MAX_DAILY_TRADES = None                 # Unlimited (as long as rate limits allow)

# ============================================================================
# RISK MANAGEMENT
# ============================================================================

RISK_MANAGEMENT = {
    # Stop-loss and circuit breakers
    'max_daily_loss_percent': 0.05,        # Stop if lose 5% in a day
    'max_consecutive_losses': 5,           # Stop after 5 losses in a row
    'emergency_stop_loss_percent': 0.10,   # Emergency stop at 10% loss
    
    # Position sizing
    'min_trade_size_usd': 10.0,           # Minimum $10 per trade
    'max_trade_size_usd': None,           # No max (scales with balance)
    'min_account_balance_usd': 50.0,      # Minimum $50 to operate
    
    # Slippage protection
    'max_slippage_percent': 0.003,        # 0.3% max slippage
    'slippage_rejection_threshold': 0.003, # Reject if predicted slippage > 0.3%
    
    # Performance tracking
    'min_sharpe_ratio': 1.0,              # Minimum Sharpe ratio
    'max_drawdown_percent': 0.15,         # Max 15% drawdown
}

# ============================================================================
# RATE LIMITS (Specific to Coinbase + Gemini)
# ============================================================================

RATE_LIMITS = {
    'coinbase': {
        'requests_per_second': 29.4,      # ~29 req/sec
        'requests_per_minute': 1765,      # ~1,765 req/min
        'requests_per_hour': 100000,      # Very high limit
        'safety_margin': 0.80,            # Use 80% of limit
    },
    'gemini': {
        'requests_per_second': 10.0,      # 10 req/sec
        'requests_per_minute': 600,       # 600 req/min
        'requests_per_hour': 36000,       # High limit
        'safety_margin': 0.80,            # Use 80% of limit
    },
}

# ============================================================================
# TRADING PARAMETERS
# ============================================================================

# Check interval (how often to scan for opportunities)
CHECK_INTERVAL_SECONDS = 5  # Check every 5 seconds (within rate limits)

# Order execution timeouts
ORDER_TIMEOUT_SECONDS = 30          # 30 seconds for order to fill
TRANSFER_TIMEOUT_SECONDS = 600      # 10 minutes for transfer to complete

# Minimum profit threshold
MIN_PROFIT_USD = 0.02              # Minimum $0.02 profit per trade (covers slippage)

# Dynamic spread adjustment
DYNAMIC_SPREAD_ADJUSTMENT_PERCENT = 0.10  # Adjust spreads by 10%
MIN_DYNAMIC_SPREAD_FLOOR = 0.010          # 1.0% absolute minimum
MAX_DYNAMIC_SPREAD_CEILING = 0.050        # 5.0% absolute maximum

# ============================================================================
# SLIPPAGE ESTIMATES (Based on liquidity)
# ============================================================================

SLIPPAGE_ESTIMATES = {
    # REFINED LIST: Top 11 cryptos only
    'SHIB/USD': 0.00150,  # 0.15%
    'AAVE/USD': 0.00120,  # 0.12%
    'COMP/USD': 0.00120,  # 0.12%
    'UNI/USD': 0.00100,   # 0.10%
    'DOT/USD': 0.00100,   # 0.10%
    'SOL/USD': 0.00100,   # 0.10%
    'AVAX/USD': 0.00100,  # 0.10%
    'LINK/USD': 0.00100,  # 0.10%
    'DOGE/USD': 0.00100,  # 0.10%
    'XRP/USD': 0.00080,   # 0.08%
    'ATOM/USD': 0.00100,  # 0.10%
}

# ============================================================================
# TRANSFER OPTIMIZATION
# ============================================================================

# Always transfer FROM Coinbase (FREE withdrawals!)
PREFERRED_TRANSFER_SOURCE = 'coinbase'

# Transfer strategy
TRANSFER_STRATEGY = 'per_trade'  # Transfer after every trade (true arbitrage)
# Alternative: 'rebalancing' (trade directionally, rebalance periodically)

# Rebalancing thresholds (if using rebalancing strategy)
REBALANCE_THRESHOLD_PERCENT = 0.30  # Rebalance when 30% imbalanced
REBALANCE_INTERVAL_HOURS = 168      # Or every 7 days

# ============================================================================
# AUTO-SIZING CONFIGURATION
# ============================================================================

AUTO_SIZING = {
    'enabled': True,
    'lookback_trades': 20,  # Number of recent trades to analyze
    'scale_interval_trades': 10,  # Adjust after every 10 trades
    'min_win_rate': 0.60,  # 60% win rate to scale up
    'scale_up_factor': 1.10,  # Increase by 10%
    'scale_down_factor': 0.90,  # Decrease by 10%
    'min_position_percent': 0.05,  # 5% minimum
    'max_position_percent': 0.15,  # 15% maximum
}

# ============================================================================
# DYNAMIC SPREAD ADJUSTMENT
# ============================================================================

DYNAMIC_SPREADS = {
    'enabled': True,
    'adjustment_interval_minutes': 60,  # Adjust every hour
    'lookback_hours': 24,  # Look at last 24 hours
    
    # Spread adjustment rules
    'high_success_rate': 0.80,  # 80%+ success = lower spread requirement
    'low_success_rate': 0.60,   # <60% success = higher spread requirement
    'spread_adjustment_percent': 0.10,  # Adjust by 10%
    
    # Spread bounds
    'min_spread_floor': 0.003,  # Never go below 0.3%
    'max_spread_ceiling': 0.030,  # Never go above 3.0%
}

# ============================================================================
# DYNAMIC SLIPPAGE DETECTION
# ============================================================================

DYNAMIC_SLIPPAGE = {
    'enabled': True,
    'real_time_detection': True,
    
    # Order book analysis
    'order_book_depth_levels': 20,  # Analyze 20 levels
    'min_liquidity_ratio': 5.0,  # 5x position size in order book
    
    # Slippage prediction
    'use_ml_prediction': False,  # Simplified for now
    'historical_lookback': 100,  # Last 100 trades
    
    # Slippage thresholds
    'max_acceptable_slippage': 0.003,  # 0.3% max
    'warning_slippage': 0.002,  # 0.2% warning
    
    # Position adjustment
    'adjust_position_size': True,
    'slippage_scale_factor': 0.50,  # Reduce size by 50% if high slippage
}

# ============================================================================
# EXCHANGE RATE LIMITS (Per exchange)
# ============================================================================

EXCHANGE_RATE_LIMITS = {
    'coinbase': {
        'requests_per_second': 15,  # 15 req/sec (1800/min documented)
        'requests_per_minute': 900,  # Conservative: 900/min (50% of limit)
        'requests_per_hour': 54000,  # 54k req/hour
        'weight_per_request': 1,
        'max_weight_per_minute': 900,
    },
    'gemini': {
        'requests_per_second': 5,   # 5 req/sec (conservative)
        'requests_per_minute': 120,  # 120 req/min documented
        'requests_per_hour': 7200,   # 7.2k req/hour
        'weight_per_request': 1,
        'max_weight_per_minute': 120,
    }
}

# ============================================================================
# SMART RATE LIMITING
# ============================================================================

SMART_RATE_LIMITING = {
    'enabled': True,
    'safety_margin': 0.80,  # Use 80% of limit (20% buffer)
    'adaptive_throttling': True,  # Slow down if approaching limit
    'priority_queue': True,  # Prioritize important requests
    
    # Request batching
    'batch_requests': False,  # Disabled for simplicity
    'max_batch_size': 10,  # Max 10 requests per batch
    
    # Caching
    'cache_enabled': True,
    'cache_ttl_seconds': 2,  # Cache for 2 seconds
    
    # Monitoring
    'track_usage': True,
}

# ============================================================================
# DYNAMIC POSITION SIZING
# ============================================================================

DYNAMIC_POSITION_SIZING = {
    'enabled': True,
    'spread_multiplier': True,  # Increase size for bigger spreads
    'max_multiplier': 1.5,  # Max 1.5x position size
}

# ============================================================================
# LOGGING
# ============================================================================

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'coinbase_gemini_arbitrage.log')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# ============================================================================
# EXCHANGE-SPECIFIC SETTINGS
# ============================================================================

EXCHANGE_CONFIGS = {
    'coinbase': {
        'enableRateLimit': True,
        'rateLimit': 34,  # 34ms between requests
        'timeout': 30000,  # 30 second timeout
        'options': {
            'defaultType': 'spot',
            'fetchCurrencies': True,
        },
    },
    'gemini': {
        'enableRateLimit': True,
        'rateLimit': 100,  # 100ms between requests
        'timeout': 30000,  # 30 second timeout
        'options': {
            'defaultType': 'spot',
        },
        'sandbox': GEMINI_SANDBOX,  # Gemini has sandbox mode
    },
}

# ============================================================================
# WHITELIST ADDRESSES (To be filled after setup)
# ============================================================================

# After one-time whitelisting, store addresses here
# These will be the approved addresses for transfers
WHITELISTED_ADDRESSES = {
    'coinbase_to_gemini': {
        # Gemini deposit addresses (get from Gemini)
        # 'SOL': 'gemini_sol_address_here',
        # 'DOGE': 'gemini_doge_address_here',
        # ... etc
    },
    'gemini_to_coinbase': {
        # Coinbase deposit addresses (get from Coinbase)
        # 'SOL': 'coinbase_sol_address_here',
        # 'DOGE': 'coinbase_doge_address_here',
        # ... etc
    },
}

# Note: Addresses will be fetched dynamically via API if not pre-configured
# But whitelisting them in advance speeds up transfers

# ============================================================================
# VALIDATION
# ============================================================================

def validate_config():
    """Validate configuration"""
    errors = []
    
    # Check API keys
    if not COINBASE_API_KEY or not COINBASE_SECRET_KEY:
        errors.append("Coinbase API keys not set")
    if not GEMINI_API_KEY or not GEMINI_SECRET_KEY:
        errors.append("Gemini API keys not set")
    
    # Check position percentages sum to ~1.0
    total_position = sum(BASE_POSITION_PERCENTAGES.values())
    if not (0.95 <= total_position <= 1.05):
        errors.append(f"Position percentages sum to {total_position:.2f}, should be ~1.0")
    
    # Check all currency pairs have spread config
    for pair in CURRENCY_PAIRS:
        if pair not in CURRENCY_PAIR_SPREADS:
            errors.append(f"Missing spread config for {pair}")
    
    # Check min spreads are profitable
    for pair, spread_config in CURRENCY_PAIR_SPREADS.items():
        min_spread = spread_config['min_spread']
        total_fees = EXCHANGE_FEES['coinbase']['taker'] + EXCHANGE_FEES['gemini']['taker']
        slippage = spread_config['slippage']
        min_required = total_fees + slippage + 0.001  # +0.1% buffer
        
        if min_spread < min_required:
            errors.append(f"{pair}: min_spread {min_spread:.3f} < required {min_required:.3f}")
    
    return errors

# ============================================================================
# CONFIG CLASS
# ============================================================================

class Config:
    """Configuration class for easy access"""
    
    # Exchanges
    EXCHANGE_1_ID = EXCHANGE_1_ID
    EXCHANGE_2_ID = EXCHANGE_2_ID
    
    # API Keys
    COINBASE_API_KEY = COINBASE_API_KEY
    COINBASE_SECRET_KEY = COINBASE_SECRET_KEY
    COINBASE_PASSPHRASE = COINBASE_PASSPHRASE
    COINBASE_SANDBOX = COINBASE_SANDBOX
    
    GEMINI_API_KEY = GEMINI_API_KEY
    GEMINI_SECRET_KEY = GEMINI_SECRET_KEY
    GEMINI_SANDBOX = GEMINI_SANDBOX
    
    # Trading
    CURRENCY_PAIRS = CURRENCY_PAIRS
    CURRENCY_PAIR_SPREADS = CURRENCY_PAIR_SPREADS
    BASE_POSITION_PERCENTAGES = BASE_POSITION_PERCENTAGES
    POSITION_PERCENTAGES = BASE_POSITION_PERCENTAGES  # Alias for compatibility
    
    # Fees
    EXCHANGE_FEES = EXCHANGE_FEES
    
    # Risk Management
    RISK_MANAGEMENT = RISK_MANAGEMENT
    MAX_POSITION_PERCENT_PER_TRADE = MAX_POSITION_PERCENT_PER_TRADE
    MAX_TOTAL_EXPOSURE_PERCENT = MAX_TOTAL_EXPOSURE_PERCENT
    RESERVE_PERCENT = RESERVE_PERCENT
    MAX_CONCURRENT_TRADES = MAX_CONCURRENT_TRADES
    MAX_DAILY_TRADES = MAX_DAILY_TRADES
    
    # Rate Limits
    RATE_LIMITS = RATE_LIMITS
    
    # Trading Parameters
    CHECK_INTERVAL_SECONDS = CHECK_INTERVAL_SECONDS
    ORDER_TIMEOUT_SECONDS = ORDER_TIMEOUT_SECONDS
    TRANSFER_TIMEOUT_SECONDS = TRANSFER_TIMEOUT_SECONDS
    MIN_PROFIT_USD = MIN_PROFIT_USD
    
    # Dynamic adjustments
    DYNAMIC_SPREAD_ADJUSTMENT_PERCENT = DYNAMIC_SPREAD_ADJUSTMENT_PERCENT
    MIN_DYNAMIC_SPREAD_FLOOR = MIN_DYNAMIC_SPREAD_FLOOR
    MAX_DYNAMIC_SPREAD_CEILING = MAX_DYNAMIC_SPREAD_CEILING
    
    # Slippage
    SLIPPAGE_ESTIMATES = SLIPPAGE_ESTIMATES
    
    # Transfer
    PREFERRED_TRANSFER_SOURCE = PREFERRED_TRANSFER_SOURCE
    TRANSFER_STRATEGY = TRANSFER_STRATEGY
    REBALANCE_THRESHOLD_PERCENT = REBALANCE_THRESHOLD_PERCENT
    REBALANCE_INTERVAL_HOURS = REBALANCE_INTERVAL_HOURS
    
    # Auto-sizing
    AUTO_SIZING = AUTO_SIZING
    
    # Dynamic adjustments
    DYNAMIC_SPREADS = DYNAMIC_SPREADS
    DYNAMIC_SLIPPAGE = DYNAMIC_SLIPPAGE
    EXCHANGE_RATE_LIMITS = EXCHANGE_RATE_LIMITS
    SMART_RATE_LIMITING = SMART_RATE_LIMITING
    DYNAMIC_POSITION_SIZING = DYNAMIC_POSITION_SIZING
    
    # Whitelist
    WHITELISTED_ADDRESSES = WHITELISTED_ADDRESSES
    
    # Exchange configs
    EXCHANGE_CONFIGS = EXCHANGE_CONFIGS
    
    # Logging
    LOG_LEVEL = LOG_LEVEL
    LOG_FILE = LOG_FILE
    LOG_FORMAT = LOG_FORMAT

# Validate on import
if __name__ != "__main__":
    validation_errors = validate_config()
    if validation_errors and COINBASE_API_KEY:  # Only show errors if trying to use
        print("⚠️  Configuration warnings:")
        for error in validation_errors:
            print(f"   - {error}")

if __name__ == "__main__":
    print("=" * 80)
    print("COINBASE + GEMINI CONFIGURATION")
    print("=" * 80)
    print()
    
    print(f"Exchanges: {EXCHANGE_1_ID.upper()} + {EXCHANGE_2_ID.upper()}")
    print(f"Currency pairs: {len(CURRENCY_PAIRS)}")
    print(f"API keys configured: {bool(COINBASE_API_KEY and GEMINI_API_KEY)}")
    print()
    
    print("Fee Summary:")
    print(f"  Coinbase maker: {EXCHANGE_FEES['coinbase']['maker']*100:.2f}%")
    print(f"  Coinbase taker: {EXCHANGE_FEES['coinbase']['taker']*100:.2f}%")
    print(f"  Gemini maker: {EXCHANGE_FEES['gemini']['maker']*100:.2f}%")
    print(f"  Gemini taker: {EXCHANGE_FEES['gemini']['taker']*100:.2f}%")
    print(f"  Total per trade: {(EXCHANGE_FEES['coinbase']['taker'] + EXCHANGE_FEES['gemini']['taker'])*100:.2f}%")
    print()
    
    print("Withdrawal Fees:")
    print(f"  Coinbase: FREE (all cryptos)")
    print(f"  Gemini: FREE (10 per month, then network fees)")
    print()
    
    print("Rate Limits:")
    print(f"  Coinbase: {RATE_LIMITS['coinbase']['requests_per_second']:.1f} req/sec")
    print(f"  Gemini: {RATE_LIMITS['gemini']['requests_per_second']:.1f} req/sec")
    print()
    
    print("Validation:")
    errors = validate_config()
    if errors:
        print("  ⚠️  Issues found:")
        for error in errors:
            print(f"     - {error}")
    else:
        print("  ✅ Configuration valid!")
    print()

