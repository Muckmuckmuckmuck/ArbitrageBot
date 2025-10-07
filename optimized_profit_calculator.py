#!/usr/bin/env python3
"""
Optimized profit calculator with VIP fees and larger trade sizes
Accounts for realistic arbitrage opportunities
"""

def calculate_optimized_profits():
    """Calculate profits with optimized fees and realistic scenarios"""
    
    print('=' * 80)
    print('OPTIMIZED PROFIT CALCULATOR - BINANCE & OKX')
    print('=' * 80)
    
    # Optimized fee structure (VIP levels)
    optimized_fees = {
        'binance': {
            'trading_fee': 0.00017,  # VIP taker fee
            'withdrawal_fees': {
                'BTC': 0.0004, 'ETH': 0.005, 'USDT': 1.0, 'XRP': 0.25,
                'SOL': 0.01, 'BNB': 0.0005, 'AVAX': 0.01, 'DOT': 0.1,
                'ADA': 1.0, 'MATIC': 0.1, 'LTC': 0.001, 'DOGE': 5.0,
                'UNI': 0.5, 'LINK': 0.5, 'TON': 0.1, 'DAI': 1.0, 'BUSD': 1.0
            }
        },
        'okx': {
            'trading_fee': 0.00015,  # VIP taker fee
            'withdrawal_fees': {
                'BTC': 0.0005, 'ETH': 0.005, 'USDT': 1.0, 'XRP': 0.15,
                'SOL': 0.01, 'BNB': 0.0005, 'AVAX': 0.01, 'DOT': 0.1,
                'ADA': 1.0, 'MATIC': 0.1, 'LTC': 0.001, 'DOGE': 5.0,
                'UNI': 0.5, 'LINK': 0.5, 'TON': 0.1, 'DAI': 1.0, 'BUSD': 1.0
            }
        }
    }
    
    # Realistic slippage (reduced for high-liquidity pairs)
    optimized_slippage = {
        'XRP/USDT': 0.0002,  # 0.02% (ultra-fast, high liquidity)
        'XLM/USDT': 0.0002,  # 0.02%
        'SOL/USDT': 0.0003,  # 0.03%
        'EOS/USDT': 0.0003,  # 0.03%
        'TRX/USDT': 0.0002,  # 0.02%
        'BNB/USDT': 0.0002,  # 0.02%
        'AVAX/USDT': 0.0003,  # 0.03%
        'DOT/USDT': 0.0003,  # 0.03%
        'ADA/USDT': 0.0003,  # 0.03%
        'MATIC/USDT': 0.0003, # 0.03%
        'BTC/USDT': 0.0001,  # 0.01% (highest liquidity)
        'ETH/USDT': 0.0001,  # 0.01%
        'LTC/USDT': 0.0002,  # 0.02%
        'DOGE/USDT': 0.0003, # 0.03%
        'UNI/USDT': 0.0004,  # 0.04%
        'LINK/USDT': 0.0004, # 0.04%
        'TON/USDT': 0.0003,  # 0.03%
        'USDT/USDC': 0.00005, # 0.005% (stablecoins)
        'USDC/USDT': 0.00005, # 0.005%
        'DAI/USDT': 0.0001,  # 0.01%
        'BUSD/USDT': 0.00005, # 0.005%
        'USDT/BUSD': 0.00005, # 0.005%
    }
    
    # Realistic spread scenarios
    scenarios = [
        # Tier 1: Ultra-fast assets (higher spreads, more opportunities)
        {
            'symbol': 'XRP/USDT',
            'spread_percent': 0.003,  # 0.3% spread
            'trade_amounts': [5000, 10000, 20000],
            'opportunities_per_day': 30
        },
        {
            'symbol': 'SOL/USDT',
            'spread_percent': 0.004,  # 0.4% spread
            'trade_amounts': [5000, 10000, 20000],
            'opportunities_per_day': 35
        },
        {
            'symbol': 'BNB/USDT',
            'spread_percent': 0.002,  # 0.2% spread
            'trade_amounts': [5000, 10000, 20000],
            'opportunities_per_day': 30
        },
        
        # Tier 2: High-liquidity assets (medium spreads)
        {
            'symbol': 'BTC/USDT',
            'spread_percent': 0.001,  # 0.1% spread
            'trade_amounts': [10000, 25000, 50000],
            'opportunities_per_day': 15
        },
        {
            'symbol': 'ETH/USDT',
            'spread_percent': 0.002,  # 0.2% spread
            'trade_amounts': [10000, 25000, 50000],
            'opportunities_per_day': 20
        },
        {
            'symbol': 'TON/USDT',
            'spread_percent': 0.017,  # 1.7% spread (TON's consistent spread)
            'trade_amounts': [2000, 5000, 10000],
            'opportunities_per_day': 15
        },
        
        # Tier 3: Stablecoins (low spreads, high volume)
        {
            'symbol': 'USDT/USDC',
            'spread_percent': 0.0005,  # 0.05% spread
            'trade_amounts': [20000, 50000, 100000],
            'opportunities_per_day': 10
        },
        {
            'symbol': 'DAI/USDT',
            'spread_percent': 0.001,  # 0.1% spread
            'trade_amounts': [10000, 25000, 50000],
            'opportunities_per_day': 8
        }
    ]
    
    print('OPTIMIZED PROFITABILITY ANALYSIS:')
    print('-' * 50)
    
    total_daily_profit = 0
    total_opportunities = 0
    
    for scenario in scenarios:
        symbol = scenario['symbol']
        spread_percent = scenario['spread_percent']
        opportunities_per_day = scenario['opportunities_per_day']
        
        print(f"\n{symbol} - {opportunities_per_day} opportunities/day:")
        print('-' * 40)
        
        symbol_daily_profit = 0
        
        for trade_amount in scenario['trade_amounts']:
            # Calculate costs
            trading_fees = trade_amount * (optimized_fees['binance']['trading_fee'] + 
                                        optimized_fees['okx']['trading_fee'])
            
            # Withdrawal fees (simplified - assume one withdrawal per trade)
            currency = symbol.split('/')[0]
            withdrawal_fee = max(
                optimized_fees['binance']['withdrawal_fees'].get(currency, 1.0),
                optimized_fees['okx']['withdrawal_fees'].get(currency, 1.0)
            )
            
            # Slippage cost
            slippage_percent = optimized_slippage.get(symbol, 0.0003)
            slippage_cost = trade_amount * slippage_percent
            
            # Calculate profit
            gross_profit = trade_amount * spread_percent
            total_costs = trading_fees + withdrawal_fee + slippage_cost
            net_profit = gross_profit - total_costs
            
            # Calculate profit percentage
            profit_percent = net_profit / trade_amount if trade_amount > 0 else 0
            
            print(f"  ${trade_amount:,}: {profit_percent*100:.3f}% profit (${net_profit:.2f})")
            
            if net_profit > 0:
                symbol_daily_profit += net_profit * opportunities_per_day
        
        if symbol_daily_profit > 0:
            print(f"  Daily profit: ${symbol_daily_profit:.2f}")
            total_daily_profit += symbol_daily_profit
            total_opportunities += opportunities_per_day
        else:
            print(f"  Daily profit: $0.00 (not profitable)")
    
    print('\n' + '=' * 80)
    print('TOTAL DAILY PROFIT SUMMARY:')
    print('=' * 80)
    
    print(f"Total daily opportunities: {total_opportunities}")
    print(f"Total daily profit: ${total_daily_profit:.2f}")
    
    if total_daily_profit > 0:
        # Calculate annual returns
        annual_profit = total_daily_profit * 365
        print(f"Annual profit: ${annual_profit:,.2f}")
        
        # Calculate return percentages for different starting balances
        starting_balances = [1000, 5000, 10000, 50000, 100000]
        
        print('\nANNUAL RETURN PERCENTAGES:')
        print('-' * 40)
        for balance in starting_balances:
            annual_return_percent = (annual_profit / balance) * 100
            print(f"Starting balance ${balance:,}: {annual_return_percent:.1f}% annual return")
    
    print('\nOPTIMIZATION STRATEGIES:')
    print('-' * 40)
    print('1. Focus on high-spread opportunities (>0.3%)')
    print('2. Use larger trade sizes to reduce fee impact')
    print('3. Target ultra-fast assets (XRP, SOL, BNB)')
    print('4. Leverage TON\'s consistent 1.7% spread')
    print('5. Use VIP fee structures on both exchanges')
    print('6. Minimize withdrawal frequency with larger positions')
    print('7. Focus on high-liquidity pairs to reduce slippage')
    
    print('\nRECOMMENDED TRADE SIZES:')
    print('-' * 40)
    print('• Ultra-fast assets: $5,000 - $20,000 per trade')
    print('• High-liquidity assets: $10,000 - $50,000 per trade')
    print('• Stablecoins: $20,000 - $100,000 per trade')
    print('• TON: $2,000 - $10,000 per trade (high spread)')

if __name__ == "__main__":
    calculate_optimized_profits()
