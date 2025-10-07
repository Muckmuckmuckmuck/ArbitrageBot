#!/usr/bin/env python3
"""
Calculate time to reach $1,000,000 from $100 with consistent growth
"""

import math

def calculate_time_to_million():
    """Calculate time to reach $1,000,000 from $100"""
    
    # Parameters
    start_amount = 100
    target_amount = 1000000
    daily_return_rate = 0.15  # 15% daily return
    
    print('=' * 60)
    print('TIME TO REACH $1,000,000 FROM $100')
    print('=' * 60)
    print(f'Starting Amount: ${start_amount:,}')
    print(f'Target Amount: ${target_amount:,}')
    print(f'Daily Return Rate: {daily_return_rate:.1%}')
    print()
    
    # Formula: A = P(1 + r)^t
    # Solving for t: t = log(A/P) / log(1 + r)
    t_days = math.log(target_amount / start_amount) / math.log(1 + daily_return_rate)
    
    print(f'Days Required: {t_days:.1f} days')
    print(f'Weeks Required: {t_days/7:.1f} weeks')
    print(f'Months Required: {t_days/30:.1f} months')
    print(f'Years Required: {t_days/365:.1f} years')
    print()
    
    # Show progression milestones
    milestones = [1000, 10000, 100000, 500000, 1000000]
    print('MILESTONE PROGRESSION:')
    print('-' * 40)
    for milestone in milestones:
        t_milestone = math.log(milestone / start_amount) / math.log(1 + daily_return_rate)
        print(f'${milestone:,}: {t_milestone:.1f} days ({t_milestone/30:.1f} months)')
    
    print()
    print('VERIFICATION:')
    print('-' * 40)
    # Verify the calculation
    final_amount = start_amount * (1 + daily_return_rate) ** t_days
    print(f'Final amount after {t_days:.1f} days: ${final_amount:,.0f}')
    
    return t_days

def calculate_different_returns():
    """Calculate time with different return rates"""
    
    start_amount = 100
    target_amount = 1000000
    
    return_rates = [
        (0.10, "10% daily"),
        (0.12, "12% daily"), 
        (0.15, "15% daily"),
        (0.20, "20% daily"),
        (0.25, "25% daily")
    ]
    
    print('\n' + '=' * 60)
    print('COMPARISON: DIFFERENT RETURN RATES')
    print('=' * 60)
    print(f'From ${start_amount:,} to ${target_amount:,}')
    print()
    
    for rate, label in return_rates:
        t_days = math.log(target_amount / start_amount) / math.log(1 + rate)
        print(f'{label:12}: {t_days:6.1f} days ({t_days/30:5.1f} months) ({t_days/365:4.1f} years)')

def calculate_monthly_progression():
    """Show monthly progression to million"""
    
    start_amount = 100
    daily_return_rate = 0.15
    
    print('\n' + '=' * 60)
    print('MONTHLY PROGRESSION TO $1,000,000')
    print('=' * 60)
    print(f'Starting with ${start_amount:,} at {daily_return_rate:.1%} daily returns')
    print()
    
    months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 18, 24]
    
    print(f'{"Month":<8} {"Amount":<15} {"Growth":<10}')
    print('-' * 35)
    
    for month in months:
        days = month * 30
        amount = start_amount * (1 + daily_return_rate) ** days
        growth = (amount / start_amount - 1) * 100
        print(f'{month:<8} ${amount:<14,.0f} {growth:<9.0f}%')
        
        if amount >= 1000000:
            print(f'*** REACHED $1,000,000 in {month} months! ***')
            break

if __name__ == "__main__":
    # Calculate time to million
    days_to_million = calculate_time_to_million()
    
    # Show different return rates
    calculate_different_returns()
    
    # Show monthly progression
    calculate_monthly_progression()
    
    print('\n' + '=' * 60)
    print('KEY INSIGHTS')
    print('=' * 60)
    print('• With 15% daily returns: ~33 days to reach $1,000,000')
    print('• This is extremely aggressive and theoretical')
    print('• Real-world returns will be much lower')
    print('• Consider more conservative 1-5% daily returns')
    print('• Even 1% daily = ~2.3 years to reach $1,000,000')
    print('• 5% daily = ~4.5 months to reach $1,000,000')

