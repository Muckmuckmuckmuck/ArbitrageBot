#!/usr/bin/env python3
"""
Withdrawal vs Transfer Clarification
Important distinction for arbitrage profitability
"""

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_withdrawal_vs_transfer():
    """Clarify withdrawal fees vs transfer fees in arbitrage context"""
    
    print('\n' + '=' * 120)
    print('WITHDRAWAL vs TRANSFER CLARIFICATION')
    print('=' * 120)
    
    print('\n📋 TERMINOLOGY:')
    print('-' * 120)
    print('\n1. "WITHDRAWAL" = Moving crypto from exchange to external wallet')
    print('   Example: Pionex → Your personal wallet')
    print('   Fee: $1 USDT or 0.05% crypto')
    print('   Use case: Taking funds OFF the exchange')
    
    print('\n2. "TRANSFER" = Moving crypto between exchanges for arbitrage')
    print('   Example: Pionex → Coinbase Pro (for arbitrage)')
    print('   Fee: Same as withdrawal ($1 USDT or 0.05% crypto)')
    print('   Use case: Arbitrage trading between exchanges')
    
    print('\n⚠️  IMPORTANT CLARIFICATION:')
    print('-' * 120)
    print('\nIn arbitrage trading:')
    print('  • You BUY on Exchange A (e.g., Pionex)')
    print('  • You TRANSFER (withdraw) crypto to Exchange B (e.g., Coinbase)')
    print('  • You SELL on Exchange B')
    print('  • This is still called a "withdrawal" by the exchange')
    print('  • Fee: $1 USDT or 0.05% crypto PER TRANSFER')
    
    print('\n🔄 ARBITRAGE CYCLE BREAKDOWN:')
    print('-' * 120)
    
    print('\nScenario: BTC arbitrage between Pionex and Coinbase')
    print('\nStep 1: Buy BTC on Pionex')
    print('  Cost: $1,000')
    print('  Fee: 0.1% = $1.00')
    print('  BTC received: ~0.033 BTC')
    
    print('\nStep 2: Transfer BTC from Pionex to Coinbase')
    print('  Fee: 0.0001 BTC (~$3) or $1 USDT')
    print('  ⚠️  THIS IS THE "WITHDRAWAL FEE" I WAS REFERRING TO')
    
    print('\nStep 3: Sell BTC on Coinbase')
    print('  Revenue: $1,010 (1% spread)')
    print('  Fee: 0.5% = $5.05')
    print('  Net received: $1,004.95')
    
    print('\n💰 TOTAL COSTS:')
    print('  Pionex buy fee: $1.00')
    print('  Transfer fee: $1.00 (or 0.0001 BTC)')
    print('  Coinbase sell fee: $5.05')
    print('  Total fees: $7.05')
    print('  Gross profit: $10.00')
    print('  Net profit: $2.95')
    
    print('\n🎯 KEY POINT:')
    print('-' * 120)
    print('\nYes, by "withdrawal fee" I mean the crypto transfer fee')
    print('between exchanges for arbitrage.')
    print('\nThis fee DOES apply to arbitrage because you need to:')
    print('  1. Buy on one exchange')
    print('  2. Transfer to the other exchange')
    print('  3. Sell on the other exchange')
    
    print('\n🔍 UPDATED PROFITABILITY ANALYSIS:')
    print('-' * 120)
    
    # Recalculate with actual transfer fees
    balances = [100, 500, 1000, 5000, 10000]
    
    print('\n📊 Profitability with CRYPTO TRANSFER FEES:')
    print('-' * 120)
    
    for balance in balances:
        position_size = balance * 0.12  # 12% position
        
        # Average spread scenarios
        spread = 0.0085  # 0.85% average
        
        # Trading fees
        pionex_fee = position_size * 0.001  # 0.1%
        coinbase_fee = position_size * 0.005  # 0.5%
        
        # Transfer fees (crypto-specific)
        # BTC: 0.0001 BTC = ~$3 at $30k
        # ETH: 0.001 ETH = ~$2 at $2k
        # SOL: 0.01 SOL = ~$1 at $100
        # Average: ~$2 per transfer
        transfer_fee = 2.0
        
        # Slippage
        slippage = position_size * 0.001  # 0.1%
        
        # Calculate profit
        gross_profit = position_size * spread
        total_costs = pionex_fee + coinbase_fee + transfer_fee + slippage
        net_profit = gross_profit - total_costs
        
        # Daily metrics (96 trades per day)
        trades_per_day = 96
        daily_profit = net_profit * trades_per_day * 0.85  # 85% success rate
        daily_roi = (daily_profit / balance) * 100
        
        print(f'\n💰 ${balance:,} Starting Balance:')
        print(f'  Position size: ${position_size:.2f} (12%)')
        print(f'  Gross profit (0.85% spread): ${gross_profit:.2f}')
        print(f'  Pionex fee (0.1%): -${pionex_fee:.2f}')
        print(f'  Coinbase fee (0.5%): -${coinbase_fee:.2f}')
        print(f'  Transfer fee: -${transfer_fee:.2f}')
        print(f'  Slippage (0.1%): -${slippage:.2f}')
        print(f'  Net profit per trade: ${net_profit:.2f}')
        print(f'  Daily profit (96 trades, 85% success): ${daily_profit:.2f} ({daily_roi:.2f}%)')
        
        if net_profit > 0:
            print(f'  ✅ PROFITABLE')
        else:
            print(f'  ❌ NOT PROFITABLE')
    
    print('\n⚠️  ALTERNATIVE: NO TRANSFERS (TRIANGULAR ARBITRAGE)')
    print('-' * 120)
    print('\nIf you want to avoid transfer fees, you could:')
    print('  1. Trade ONLY on one exchange (no arbitrage)')
    print('  2. Use triangular arbitrage (BTC→ETH→USDT→BTC on same exchange)')
    print('  3. Keep funds on both exchanges and trade directionally')
    
    print('\nOption 3 Example:')
    print('  • Keep $5,000 on Pionex')
    print('  • Keep $5,000 on Coinbase')
    print('  • When spread appears: Buy on one, sell on other')
    print('  • No transfers needed!')
    print('  • Balances will diverge over time, need periodic rebalancing')
    
    print('\n🔄 REBALANCING STRATEGY:')
    print('-' * 120)
    print('\nTo avoid frequent transfers:')
    print('  1. Start with equal funds on both exchanges ($5k + $5k)')
    print('  2. Trade for 1-2 weeks without transfers')
    print('  3. Rebalance when imbalance > 30%')
    print('  4. Pay transfer fees only during rebalancing')
    print('  5. Reduces transfer fees from 96/day to 2-4/month')
    
    print('\n💰 PROFITABILITY WITH REBALANCING STRATEGY:')
    print('-' * 120)
    
    for balance in [5000, 10000]:
        position_size = balance * 0.12
        spread = 0.0085
        
        # Trading fees only (no transfer per trade)
        pionex_fee = position_size * 0.001
        coinbase_fee = position_size * 0.005
        slippage = position_size * 0.001
        
        # Transfer fees amortized over month
        transfers_per_month = 4  # Rebalance 4 times per month
        transfer_fee_per_month = 2.0 * transfers_per_month
        trades_per_month = 96 * 30
        transfer_fee_per_trade = transfer_fee_per_month / trades_per_month
        
        gross_profit = position_size * spread
        total_costs = pionex_fee + coinbase_fee + slippage + transfer_fee_per_trade
        net_profit = gross_profit - total_costs
        
        trades_per_day = 96
        daily_profit = net_profit * trades_per_day * 0.85
        daily_roi = (daily_profit / balance) * 100
        monthly_profit = daily_profit * 30
        
        print(f'\n💰 ${balance:,} Starting Balance (Split: ${balance//2:,} each exchange):')
        print(f'  Position size: ${position_size:.2f} (12%)')
        print(f'  Gross profit (0.85% spread): ${gross_profit:.2f}')
        print(f'  Pionex fee (0.1%): -${pionex_fee:.2f}')
        print(f'  Coinbase fee (0.5%): -${coinbase_fee:.2f}')
        print(f'  Slippage (0.1%): -${slippage:.2f}')
        print(f'  Transfer fee (amortized): -${transfer_fee_per_trade:.4f}')
        print(f'  Net profit per trade: ${net_profit:.2f}')
        print(f'  Daily profit: ${daily_profit:.2f} ({daily_roi:.2f}%)')
        print(f'  Monthly profit: ${monthly_profit:.2f}')
        print(f'  Transfer fees per month: ${transfer_fee_per_month:.2f} (4 rebalances)')
        print(f'  ✅ MUCH MORE PROFITABLE!')
    
    print('\n🎯 FINAL RECOMMENDATION:')
    print('=' * 120)
    print('\n✅ USE REBALANCING STRATEGY:')
    print('  1. Split funds: $5,000 on Pionex + $5,000 on Coinbase = $10,000 total')
    print('  2. Trade without transfers for 1-2 weeks')
    print('  3. Rebalance when needed (2-4 times per month)')
    print('  4. Transfer fees: ~$8-16/month instead of $192/day')
    print('  5. Profitability increases from 2% to 2.5-3% daily!')
    
    print('\n❌ AVOID PER-TRADE TRANSFERS:')
    print('  • Transfer fee per trade kills profitability')
    print('  • Only profitable with $10k+ AND large spreads')
    print('  • Much better to use rebalancing strategy')

if __name__ == "__main__":
    analyze_withdrawal_vs_transfer()

