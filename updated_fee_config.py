#!/usr/bin/env python3
"""
Updated fee and slippage configuration for Binance and OKX
Based on current 2024 fee structures
"""

def get_exchange_fees():
    """Get current trading fees for each exchange"""
    
    return {
        'binance': {
            'spot_trading': {
                'maker': 0.001,      # 0.1% standard
                'taker': 0.001,      # 0.1% standard
                'maker_bnb': 0.00075, # 0.075% with BNB discount
                'taker_bnb': 0.00075, # 0.075% with BNB discount
                'vip_maker': 0.0000,  # 0% for VIP levels
                'vip_taker': 0.00017, # 0.017% for VIP levels
            },
            'withdrawal_fees': {
                'BTC': 0.0004,       # 0.0004 BTC
                'ETH': 0.005,        # 0.005 ETH
                'USDT': 1.0,         # 1 USDT (ERC-20)
                'USDC': 1.0,         # 1 USDC (ERC-20)
                'XRP': 0.25,         # 0.25 XRP
                'XLM': 0.02,         # 0.02 XLM
                'SOL': 0.01,         # 0.01 SOL
                'EOS': 0.1,          # 0.1 EOS
                'TRX': 1.0,          # 1 TRX
                'BNB': 0.0005,       # 0.0005 BNB
                'AVAX': 0.01,        # 0.01 AVAX
                'DOT': 0.1,          # 0.1 DOT
                'ADA': 1.0,          # 1 ADA
                'MATIC': 0.1,        # 0.1 MATIC
                'LTC': 0.001,        # 0.001 LTC
                'DOGE': 5.0,         # 5 DOGE
                'UNI': 0.5,          # 0.5 UNI
                'LINK': 0.5,         # 0.5 LINK
                'TON': 0.1,          # 0.1 TON
                'DAI': 1.0,          # 1 DAI
                'BUSD': 1.0,         # 1 BUSD
            }
        },
        'okx': {
            'spot_trading': {
                'maker': 0.0008,     # 0.08% standard
                'taker': 0.001,      # 0.1% standard
                'vip_maker': -0.00005, # -0.005% for VIP (negative fees)
                'vip_taker': 0.00015, # 0.015% for VIP
            },
            'withdrawal_fees': {
                'BTC': 0.0005,       # 0.0005 BTC
                'ETH': 0.005,        # 0.005 ETH
                'USDT': 1.0,         # 1 USDT (ERC-20)
                'USDC': 1.0,         # 1 USDC (ERC-20)
                'XRP': 0.15,         # 0.15 XRP
                'XLM': 0.02,         # 0.02 XLM
                'SOL': 0.01,         # 0.01 SOL
                'EOS': 0.1,          # 0.1 EOS
                'TRX': 1.0,          # 1 TRX
                'BNB': 0.0005,       # 0.0005 BNB
                'AVAX': 0.01,        # 0.01 AVAX
                'DOT': 0.1,          # 0.1 DOT
                'ADA': 1.0,          # 1 ADA
                'MATIC': 0.1,        # 0.1 MATIC
                'LTC': 0.001,        # 0.001 LTC
                'DOGE': 5.0,         # 5 DOGE
                'UNI': 0.5,          # 0.5 UNI
                'LINK': 0.5,         # 0.5 LINK
                'TON': 0.1,          # 0.1 TON
                'DAI': 1.0,          # 1 DAI
                'BUSD': 1.0,         # 1 BUSD
            }
        }
    }

def get_slippage_estimates():
    """Get slippage estimates based on asset liquidity"""
    
    return {
        # Ultra-fast assets (high liquidity, low slippage)
        'XRP/USDT': {'min_slippage': 0.0001, 'max_slippage': 0.0005, 'avg_slippage': 0.0003},
        'XLM/USDT': {'min_slippage': 0.0001, 'max_slippage': 0.0005, 'avg_slippage': 0.0003},
        'SOL/USDT': {'min_slippage': 0.0002, 'max_slippage': 0.0008, 'avg_slippage': 0.0005},
        'EOS/USDT': {'min_slippage': 0.0002, 'max_slippage': 0.0008, 'avg_slippage': 0.0005},
        'TRX/USDT': {'min_slippage': 0.0001, 'max_slippage': 0.0005, 'avg_slippage': 0.0003},
        'BNB/USDT': {'min_slippage': 0.0001, 'max_slippage': 0.0005, 'avg_slippage': 0.0003},
        'AVAX/USDT': {'min_slippage': 0.0002, 'max_slippage': 0.0008, 'avg_slippage': 0.0005},
        'DOT/USDT': {'min_slippage': 0.0002, 'max_slippage': 0.0008, 'avg_slippage': 0.0005},
        'ADA/USDT': {'min_slippage': 0.0002, 'max_slippage': 0.0008, 'avg_slippage': 0.0005},
        'MATIC/USDT': {'min_slippage': 0.0002, 'max_slippage': 0.0008, 'avg_slippage': 0.0005},
        
        # High-liquidity assets (medium slippage)
        'BTC/USDT': {'min_slippage': 0.0001, 'max_slippage': 0.0003, 'avg_slippage': 0.0002},
        'ETH/USDT': {'min_slippage': 0.0001, 'max_slippage': 0.0003, 'avg_slippage': 0.0002},
        'LTC/USDT': {'min_slippage': 0.0002, 'max_slippage': 0.0005, 'avg_slippage': 0.0003},
        'DOGE/USDT': {'min_slippage': 0.0002, 'max_slippage': 0.0008, 'avg_slippage': 0.0005},
        'UNI/USDT': {'min_slippage': 0.0003, 'max_slippage': 0.001, 'avg_slippage': 0.0006},
        'LINK/USDT': {'min_slippage': 0.0003, 'max_slippage': 0.001, 'avg_slippage': 0.0006},
        'TON/USDT': {'min_slippage': 0.0002, 'max_slippage': 0.0008, 'avg_slippage': 0.0005},
        
        # Stablecoins (lowest slippage)
        'USDT/USDC': {'min_slippage': 0.00005, 'max_slippage': 0.0002, 'avg_slippage': 0.0001},
        'USDC/USDT': {'min_slippage': 0.00005, 'max_slippage': 0.0002, 'avg_slippage': 0.0001},
        'DAI/USDT': {'min_slippage': 0.0001, 'max_slippage': 0.0003, 'avg_slippage': 0.0002},
        'BUSD/USDT': {'min_slippage': 0.00005, 'max_slippage': 0.0002, 'avg_slippage': 0.0001},
        'USDT/BUSD': {'min_slippage': 0.00005, 'max_slippage': 0.0002, 'avg_slippage': 0.0001},
    }

def calculate_net_profit(spread_percent, trade_amount, buy_exchange, sell_exchange, symbol):
    """Calculate net profit after fees and slippage"""
    
    fees = get_exchange_fees()
    slippage = get_slippage_estimates()
    
    # Get trading fees
    buy_fee = fees[buy_exchange]['spot_trading']['taker']
    sell_fee = fees[sell_exchange]['spot_trading']['taker']
    
    # Get withdrawal fees (in USD equivalent)
    currency = symbol.split('/')[0]
    withdrawal_fee_buy = fees[buy_exchange]['withdrawal_fees'].get(currency, 1.0)
    withdrawal_fee_sell = fees[sell_exchange]['withdrawal_fees'].get(currency, 1.0)
    
    # Get slippage
    symbol_slippage = slippage.get(symbol, {'avg_slippage': 0.0005})
    avg_slippage = symbol_slippage['avg_slippage']
    
    # Calculate costs
    trading_fees = trade_amount * (buy_fee + sell_fee)
    withdrawal_fees = withdrawal_fee_buy + withdrawal_fee_sell
    slippage_cost = trade_amount * avg_slippage
    
    # Calculate gross profit
    gross_profit = trade_amount * spread_percent
    
    # Calculate net profit
    total_costs = trading_fees + withdrawal_fees + slippage_cost
    net_profit = gross_profit - total_costs
    
    return {
        'gross_profit': gross_profit,
        'trading_fees': trading_fees,
        'withdrawal_fees': withdrawal_fees,
        'slippage_cost': slippage_cost,
        'total_costs': total_costs,
        'net_profit': net_profit,
        'net_profit_percent': net_profit / trade_amount if trade_amount > 0 else 0
    }

def analyze_profitability():
    """Analyze profitability for different scenarios"""
    
    print('=' * 80)
    print('UPDATED FEE AND SLIPPAGE ANALYSIS FOR BINANCE & OKX')
    print('=' * 80)
    
    # Example scenarios
    scenarios = [
        {
            'symbol': 'XRP/USDT',
            'spread_percent': 0.001,  # 0.1% spread
            'trade_amount': 1000,
            'buy_exchange': 'binance',
            'sell_exchange': 'okx'
        },
        {
            'symbol': 'SOL/USDT',
            'spread_percent': 0.002,  # 0.2% spread
            'trade_amount': 2000,
            'buy_exchange': 'okx',
            'sell_exchange': 'binance'
        },
        {
            'symbol': 'BTC/USDT',
            'spread_percent': 0.0005,  # 0.05% spread
            'trade_amount': 5000,
            'buy_exchange': 'binance',
            'sell_exchange': 'okx'
        },
        {
            'symbol': 'USDT/USDC',
            'spread_percent': 0.0003,  # 0.03% spread
            'trade_amount': 10000,
            'buy_exchange': 'binance',
            'sell_exchange': 'okx'
        }
    ]
    
    print('PROFITABILITY ANALYSIS:')
    print('-' * 50)
    
    for scenario in scenarios:
        result = calculate_net_profit(
            scenario['spread_percent'],
            scenario['trade_amount'],
            scenario['buy_exchange'],
            scenario['sell_exchange'],
            scenario['symbol']
        )
        
        print(f"\n{scenario['symbol']} - ${scenario['trade_amount']:,} trade:")
        print(f"  Spread: {scenario['spread_percent']:.3f} ({scenario['spread_percent']*100:.2f}%)")
        print(f"  Gross Profit: ${result['gross_profit']:.2f}")
        print(f"  Trading Fees: ${result['trading_fees']:.2f}")
        print(f"  Withdrawal Fees: ${result['withdrawal_fees']:.2f}")
        print(f"  Slippage Cost: ${result['slippage_cost']:.2f}")
        print(f"  Total Costs: ${result['total_costs']:.2f}")
        print(f"  Net Profit: ${result['net_profit']:.2f}")
        print(f"  Net Profit %: {result['net_profit_percent']:.4f} ({result['net_profit_percent']*100:.3f}%)")
        
        if result['net_profit'] > 0:
            print(f"  ✅ PROFITABLE")
        else:
            print(f"  ❌ NOT PROFITABLE")
    
    print('\n' + '=' * 80)
    print('FEE COMPARISON: BINANCE vs OKX')
    print('=' * 80)
    
    fees = get_exchange_fees()
    
    print('SPOT TRADING FEES:')
    print('-' * 30)
    print('Binance:')
    print(f"  Standard: {fees['binance']['spot_trading']['maker']*100:.2f}% maker, {fees['binance']['spot_trading']['taker']*100:.2f}% taker")
    print(f"  With BNB: {fees['binance']['spot_trading']['maker_bnb']*100:.3f}% maker, {fees['binance']['spot_trading']['taker_bnb']*100:.3f}% taker")
    print(f"  VIP: {fees['binance']['spot_trading']['vip_maker']*100:.3f}% maker, {fees['binance']['spot_trading']['vip_taker']*100:.3f}% taker")
    
    print('\nOKX:')
    print(f"  Standard: {fees['okx']['spot_trading']['maker']*100:.2f}% maker, {fees['okx']['spot_trading']['taker']*100:.2f}% taker")
    print(f"  VIP: {fees['okx']['spot_trading']['vip_maker']*100:.3f}% maker, {fees['okx']['spot_trading']['vip_taker']*100:.3f}% taker")
    
    print('\nWITHDRAWAL FEES (Key Assets):')
    print('-' * 30)
    key_assets = ['BTC', 'ETH', 'USDT', 'XRP', 'SOL', 'BNB']
    for asset in key_assets:
        binance_fee = fees['binance']['withdrawal_fees'].get(asset, 'N/A')
        okx_fee = fees['okx']['withdrawal_fees'].get(asset, 'N/A')
        print(f"{asset}: Binance {binance_fee}, OKX {okx_fee}")
    
    print('\nSLIPPAGE ESTIMATES:')
    print('-' * 30)
    slippage = get_slippage_estimates()
    for symbol, data in list(slippage.items())[:5]:  # Show first 5
        print(f"{symbol}: {data['avg_slippage']*100:.3f}% average slippage")
    
    print('\nOPTIMIZATION RECOMMENDATIONS:')
    print('-' * 30)
    print('1. Use BNB for fee payments on Binance (25% discount)')
    print('2. Hold OKB tokens on OKX for fee discounts')
    print('3. Aim for VIP levels on both exchanges')
    print('4. Focus on high-liquidity pairs to minimize slippage')
    print('5. Use limit orders to reduce slippage impact')
    print('6. Consider withdrawal fees when choosing transfer direction')

if __name__ == "__main__":
    analyze_profitability()
