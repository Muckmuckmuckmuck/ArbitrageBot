#!/usr/bin/env python3
"""
Updated cryptocurrency configuration based on comprehensive evaluation
Focus on A+ and A grade cryptocurrencies with high arbitrage potential
"""

def create_updated_config():
    """Create updated configuration with best cryptocurrencies"""
    
    print('=' * 80)
    print('UPDATED CRYPTOCURRENCY CONFIGURATION')
    print('=' * 80)
    
    # Tier 1: Ultra-Fast, High-Spread Assets (A+ Grade)
    TIER1_ASSETS = [
        'TON/USDT',   # 1.5%-2.5% spread, 30s transfer, Medium-High liquidity
        'ALGO/USDT',  # 1.5%-2.0% spread, 4s transfer, Medium-High liquidity
        'VET/USDT',   # 1.7%-2.2% spread, 10s transfer, Medium liquidity
        'XLM/USDT',   # 1.5%-2.0% spread, 3s transfer, Medium-High liquidity
    ]
    
    # Tier 2: Fast, Good-Spread Assets (A Grade)
    TIER2_ASSETS = [
        'TRX/USDT',   # 1.5%-2.0% spread, 120s transfer, High liquidity
        'FTM/USDT',   # 1.5% spread, 60s transfer, Medium liquidity
        'MATIC/USDT', # 1.2%-1.8% spread, 90s transfer, High liquidity
        'SOL/USDT',   # 1.0%-1.5% spread, 10s transfer, High liquidity
    ]
    
    # Tier 3: Established Assets (B+ Grade)
    TIER3_ASSETS = [
        'BCH/USDT',   # 1.0%-1.3% spread, 300s transfer, Medium liquidity
        'XRP/USDT',   # 1.0%-1.2% spread, 5s transfer, High liquidity
        'DASH/USDT',  # 1.3%-1.7% spread, 150s transfer, Medium liquidity
        'LTC/USDT',   # 1.1%-1.4% spread, 150s transfer, High liquidity
    ]
    
    # Tier 4: Additional Profitable Assets
    TIER4_ASSETS = [
        'HBAR/USDT',  # 1.2% spread, 30s transfer, Medium liquidity
        'ICP/USDT',   # 1.0% spread, 90s transfer, Medium liquidity
        'LINK/USDT',  # 1.0%-1.3% spread, 10s transfer, High liquidity
        'ATOM/USDT',  # 1.0%-1.3% spread, 7s transfer, Medium-High liquidity
    ]
    
    # Combine all tiers
    CURRENCY_PAIRS = TIER1_ASSETS + TIER2_ASSETS + TIER3_ASSETS + TIER4_ASSETS
    
    print('UPDATED CURRENCY PAIRS:')
    print('-' * 50)
    print(f'Total pairs: {len(CURRENCY_PAIRS)}')
    print(f'Tier 1 (A+ Grade): {len(TIER1_ASSETS)} pairs')
    print(f'Tier 2 (A Grade): {len(TIER2_ASSETS)} pairs')
    print(f'Tier 3 (B+ Grade): {len(TIER3_ASSETS)} pairs')
    print(f'Tier 4 (Additional): {len(TIER4_ASSETS)} pairs')
    print()
    
    # Transfer speed configurations
    TRANSFER_SPEEDS = {
        # Tier 1: Ultra-fast (A+ Grade)
        'TON/USDT': {'speed': 30, 'strategy': 'transfer_first', 'min_spread': 0.015, 'max_spread': 0.025},
        'ALGO/USDT': {'speed': 4, 'strategy': 'transfer_first', 'min_spread': 0.015, 'max_spread': 0.02},
        'VET/USDT': {'speed': 10, 'strategy': 'transfer_first', 'min_spread': 0.017, 'max_spread': 0.022},
        'XLM/USDT': {'speed': 3, 'strategy': 'transfer_first', 'min_spread': 0.015, 'max_spread': 0.02},
        
        # Tier 2: Fast (A Grade)
        'TRX/USDT': {'speed': 120, 'strategy': 'transfer_first', 'min_spread': 0.015, 'max_spread': 0.02},
        'FTM/USDT': {'speed': 60, 'strategy': 'transfer_first', 'min_spread': 0.015, 'max_spread': 0.015},
        'MATIC/USDT': {'speed': 90, 'strategy': 'transfer_first', 'min_spread': 0.012, 'max_spread': 0.018},
        'SOL/USDT': {'speed': 10, 'strategy': 'transfer_first', 'min_spread': 0.01, 'max_spread': 0.015},
        
        # Tier 3: Established (B+ Grade)
        'BCH/USDT': {'speed': 300, 'strategy': 'simultaneous', 'min_spread': 0.01, 'max_spread': 0.013},
        'XRP/USDT': {'speed': 5, 'strategy': 'transfer_first', 'min_spread': 0.01, 'max_spread': 0.012},
        'DASH/USDT': {'speed': 150, 'strategy': 'transfer_first', 'min_spread': 0.013, 'max_spread': 0.017},
        'LTC/USDT': {'speed': 150, 'strategy': 'simultaneous', 'min_spread': 0.011, 'max_spread': 0.014},
        
        # Tier 4: Additional
        'HBAR/USDT': {'speed': 30, 'strategy': 'transfer_first', 'min_spread': 0.012, 'max_spread': 0.012},
        'ICP/USDT': {'speed': 90, 'strategy': 'transfer_first', 'min_spread': 0.01, 'max_spread': 0.01},
        'LINK/USDT': {'speed': 10, 'strategy': 'transfer_first', 'min_spread': 0.01, 'max_spread': 0.013},
        'ATOM/USDT': {'speed': 7, 'strategy': 'transfer_first', 'min_spread': 0.01, 'max_spread': 0.013},
    }
    
    # Position size limits based on asset characteristics
    POSITION_LIMITS = {
        # Tier 1: Ultra-fast, high-spread (larger positions)
        'TON/USDT': 15000, 'ALGO/USDT': 15000, 'VET/USDT': 12000, 'XLM/USDT': 15000,
        
        # Tier 2: Fast, good-spread (medium positions)
        'TRX/USDT': 10000, 'FTM/USDT': 8000, 'MATIC/USDT': 10000, 'SOL/USDT': 12000,
        
        # Tier 3: Established (medium positions)
        'BCH/USDT': 8000, 'XRP/USDT': 10000, 'DASH/USDT': 6000, 'LTC/USDT': 8000,
        
        # Tier 4: Additional (smaller positions)
        'HBAR/USDT': 6000, 'ICP/USDT': 5000, 'LINK/USDT': 8000, 'ATOM/USDT': 6000,
    }
    
    # Daily opportunities estimate
    DAILY_OPPORTUNITIES = {
        # Tier 1: High-frequency opportunities
        'TON/USDT': 25, 'ALGO/USDT': 25, 'VET/USDT': 25, 'XLM/USDT': 25,
        
        # Tier 2: Medium-frequency opportunities
        'TRX/USDT': 15, 'FTM/USDT': 15, 'MATIC/USDT': 15, 'SOL/USDT': 15,
        
        # Tier 3: Lower-frequency opportunities
        'BCH/USDT': 10, 'XRP/USDT': 12, 'DASH/USDT': 8, 'LTC/USDT': 10,
        
        # Tier 4: Additional opportunities
        'HBAR/USDT': 8, 'ICP/USDT': 6, 'LINK/USDT': 10, 'ATOM/USDT': 8,
    }
    
    print('TRANSFER SPEED CONFIGURATIONS:')
    print('-' * 50)
    for symbol, config in TRANSFER_SPEEDS.items():
        print(f'{symbol}: {config["speed"]}s, {config["min_spread"]*100:.1f}%-{config["max_spread"]*100:.1f}% spread')
    
    print('\nPOSITION LIMITS:')
    print('-' * 30)
    for symbol, limit in POSITION_LIMITS.items():
        print(f'{symbol}: ${limit:,} max position')
    
    print('\nDAILY OPPORTUNITIES:')
    print('-' * 30)
    total_opportunities = 0
    for symbol, opportunities in DAILY_OPPORTUNITIES.items():
        print(f'{symbol}: {opportunities} opportunities/day')
        total_opportunities += opportunities
    
    print(f'\nTotal daily opportunities: {total_opportunities}')
    
    # Profit projections
    print('\nPROFIT PROJECTIONS:')
    print('-' * 30)
    
    tier1_profit = 0
    tier2_profit = 0
    tier3_profit = 0
    tier4_profit = 0
    
    # Calculate estimated daily profit for each tier
    for symbol in TIER1_ASSETS:
        opportunities = DAILY_OPPORTUNITIES[symbol]
        position_size = POSITION_LIMITS[symbol]
        min_spread = TRANSFER_SPEEDS[symbol]['min_spread']
        
        # Conservative profit calculation
        gross_profit = position_size * min_spread
        costs = position_size * 0.00032 + 1.0 + position_size * 0.0003  # fees + withdrawal + slippage
        net_profit = gross_profit - costs
        
        if net_profit > 0:
            daily_profit = net_profit * opportunities
            tier1_profit += daily_profit
            print(f'{symbol}: ${daily_profit:.2f}/day')
    
    for symbol in TIER2_ASSETS:
        opportunities = DAILY_OPPORTUNITIES[symbol]
        position_size = POSITION_LIMITS[symbol]
        min_spread = TRANSFER_SPEEDS[symbol]['min_spread']
        
        gross_profit = position_size * min_spread
        costs = position_size * 0.00032 + 1.0 + position_size * 0.0003
        net_profit = gross_profit - costs
        
        if net_profit > 0:
            daily_profit = net_profit * opportunities
            tier2_profit += daily_profit
            print(f'{symbol}: ${daily_profit:.2f}/day')
    
    for symbol in TIER3_ASSETS:
        opportunities = DAILY_OPPORTUNITIES[symbol]
        position_size = POSITION_LIMITS[symbol]
        min_spread = TRANSFER_SPEEDS[symbol]['min_spread']
        
        gross_profit = position_size * min_spread
        costs = position_size * 0.00032 + 1.0 + position_size * 0.0003
        net_profit = gross_profit - costs
        
        if net_profit > 0:
            daily_profit = net_profit * opportunities
            tier3_profit += daily_profit
            print(f'{symbol}: ${daily_profit:.2f}/day')
    
    for symbol in TIER4_ASSETS:
        opportunities = DAILY_OPPORTUNITIES[symbol]
        position_size = POSITION_LIMITS[symbol]
        min_spread = TRANSFER_SPEEDS[symbol]['min_spread']
        
        gross_profit = position_size * min_spread
        costs = position_size * 0.00032 + 1.0 + position_size * 0.0003
        net_profit = gross_profit - costs
        
        if net_profit > 0:
            daily_profit = net_profit * opportunities
            tier4_profit += daily_profit
            print(f'{symbol}: ${daily_profit:.2f}/day')
    
    total_daily_profit = tier1_profit + tier2_profit + tier3_profit + tier4_profit
    
    print(f'\nTier 1 (A+ Grade) Daily Profit: ${tier1_profit:.2f}')
    print(f'Tier 2 (A Grade) Daily Profit: ${tier2_profit:.2f}')
    print(f'Tier 3 (B+ Grade) Daily Profit: ${tier3_profit:.2f}')
    print(f'Tier 4 (Additional) Daily Profit: ${tier4_profit:.2f}')
    print(f'Total Daily Profit: ${total_daily_profit:.2f}')
    print(f'Monthly Profit: ${total_daily_profit * 30:,.2f}')
    print(f'Annual Profit: ${total_daily_profit * 365:,.2f}')
    
    # Integration recommendations
    print('\nINTEGRATION RECOMMENDATIONS:')
    print('-' * 40)
    print('1. IMMEDIATE INTEGRATION (A+ Grade):')
    print('   - TON: Highest spread, good liquidity')
    print('   - ALGO: Ultra-fast transfers, decent spread')
    print('   - VET: High spread, low competition')
    print('   - XLM: Ultra-fast, reliable')
    
    print('\n2. SECONDARY INTEGRATION (A Grade):')
    print('   - TRX: High volume, good spread')
    print('   - FTM: Growing interest, consistent spread')
    print('   - MATIC: High liquidity, decent spread')
    print('   - SOL: Fast chain, frequent opportunities')
    
    print('\n3. TERTIARY INTEGRATION (B+ Grade):')
    print('   - XRP: Bridge currency, very fast')
    print('   - BCH: Lower fees, decent spread')
    print('   - DASH: Privacy coin, good volume')
    print('   - LTC: Widely supported, stable')
    
    print('\n4. ADDITIONAL ASSETS (Tier 4):')
    print('   - HBAR: Enterprise interest')
    print('   - ICP: High throughput')
    print('   - LINK: Oracle demand')
    print('   - ATOM: Interoperability')
    
    print('\nEXCLUDED ASSETS:')
    print('-' * 20)
    print('• NANO: Not available on OKX')
    print('• IOT: Limited OKX availability')
    print('• STRAT: Limited OKX availability')
    print('• KMD: Limited OKX availability')
    print('• FCT: Not available on either exchange')
    print('• SYS: Limited OKX availability')
    print('• LSK: Limited OKX availability')
    print('• ARDR: Limited OKX availability')
    print('• WAVES: Low grade (D)')
    print('• QTUM: Low grade (D)')
    
    return {
        'TIER1_ASSETS': TIER1_ASSETS,
        'TIER2_ASSETS': TIER2_ASSETS,
        'TIER3_ASSETS': TIER3_ASSETS,
        'TIER4_ASSETS': TIER4_ASSETS,
        'CURRENCY_PAIRS': CURRENCY_PAIRS,
        'TRANSFER_SPEEDS': TRANSFER_SPEEDS,
        'POSITION_LIMITS': POSITION_LIMITS,
        'DAILY_OPPORTUNITIES': DAILY_OPPORTUNITIES
    }

if __name__ == "__main__":
    config = create_updated_config()
