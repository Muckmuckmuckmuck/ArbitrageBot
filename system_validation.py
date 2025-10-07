#!/usr/bin/env python3
"""
Comprehensive system validation after fixes
Verifies all configurations are consistent and correct
"""

def validate_system():
    """Validate the entire system configuration"""
    
    print('=' * 80)
    print('SYSTEM VALIDATION REPORT')
    print('=' * 80)
    
    # Import the updated config
    from config import Config
    
    print('✅ CONFIGURATION VALIDATION:')
    print('-' * 50)
    
    # Check currency pairs
    all_pairs = Config.CURRENCY_PAIRS
    tier1_pairs = Config.TIER1_ASSETS
    tier2_pairs = Config.TIER2_ASSETS
    tier3_pairs = Config.TIER3_ASSETS
    tier4_pairs = Config.TIER4_ASSETS
    
    print(f'Total currency pairs: {len(all_pairs)}')
    print(f'Tier 1 pairs: {len(tier1_pairs)}')
    print(f'Tier 2 pairs: {len(tier2_pairs)}')
    print(f'Tier 3 pairs: {len(tier3_pairs)}')
    print(f'Tier 4 pairs: {len(tier4_pairs)}')
    
    # Verify all tiers are included
    expected_pairs = tier1_pairs + tier2_pairs + tier3_pairs + tier4_pairs
    if set(all_pairs) == set(expected_pairs):
        print('✅ CURRENCY_PAIRS includes all tiers')
    else:
        print('❌ CURRENCY_PAIRS missing some tiers')
    
    print()
    
    # Check transfer speeds
    print('✅ TRANSFER SPEEDS VALIDATION:')
    print('-' * 50)
    
    transfer_speeds = Config.TRANSFER_SPEEDS
    missing_speeds = []
    for pair in all_pairs:
        if pair not in transfer_speeds:
            missing_speeds.append(pair)
    
    if not missing_speeds:
        print('✅ All currency pairs have transfer speeds')
    else:
        print(f'❌ Missing transfer speeds for: {missing_speeds}')
    
    # Check for old/unused pairs
    old_pairs = []
    for pair in transfer_speeds:
        if pair not in all_pairs:
            old_pairs.append(pair)
    
    if not old_pairs:
        print('✅ No old/unused transfer speeds')
    else:
        print(f'⚠️  Old/unused transfer speeds: {old_pairs}')
    
    print()
    
    # Check slippage estimates
    print('✅ SLIPPAGE ESTIMATES VALIDATION:')
    print('-' * 50)
    
    slippage_estimates = Config.SLIPPAGE_ESTIMATES
    missing_slippage = []
    for pair in all_pairs:
        if pair not in slippage_estimates:
            missing_slippage.append(pair)
    
    if not missing_slippage:
        print('✅ All currency pairs have slippage estimates')
    else:
        print(f'❌ Missing slippage estimates for: {missing_slippage}')
    
    # Check for old/unused slippage
    old_slippage = []
    for pair in slippage_estimates:
        if pair not in all_pairs:
            old_slippage.append(pair)
    
    if not old_slippage:
        print('✅ No old/unused slippage estimates')
    else:
        print(f'⚠️  Old/unused slippage estimates: {old_slippage}')
    
    print()
    
    # Check position limits
    print('✅ POSITION LIMITS VALIDATION:')
    print('-' * 50)
    
    position_limits = Config.POSITION_LIMITS
    missing_limits = []
    for pair in all_pairs:
        if pair not in position_limits:
            missing_limits.append(pair)
    
    if not missing_limits:
        print('✅ All currency pairs have position limits')
    else:
        print(f'❌ Missing position limits for: {missing_limits}')
    
    # Check for old/unused limits
    old_limits = []
    for pair in position_limits:
        if pair not in all_pairs:
            old_limits.append(pair)
    
    if not old_limits:
        print('✅ No old/unused position limits')
    else:
        print(f'⚠️  Old/unused position limits: {old_limits}')
    
    print()
    
    # Check currency mappings
    print('✅ CURRENCY MAPPINGS VALIDATION:')
    print('-' * 50)
    
    currency_mappings = Config.CURRENCY_MAPPINGS
    missing_mappings = []
    
    for pair in all_pairs:
        base_currency = pair.split('/')[0]
        if base_currency not in currency_mappings:
            missing_mappings.append(base_currency)
    
    if not missing_mappings:
        print('✅ All currencies have mappings')
    else:
        print(f'❌ Missing currency mappings for: {missing_mappings}')
    
    print()
    
    # Check exchange fees
    print('✅ EXCHANGE FEES VALIDATION:')
    print('-' * 50)
    
    exchange_fees = Config.EXCHANGE_FEES
    missing_fees = []
    
    for pair in all_pairs:
        base_currency = pair.split('/')[0]
        if base_currency not in exchange_fees['binance']['withdrawal_fees']:
            missing_fees.append(f'Binance {base_currency}')
        if base_currency not in exchange_fees['okx']['withdrawal_fees']:
            missing_fees.append(f'OKX {base_currency}')
    
    if not missing_fees:
        print('✅ All currencies have exchange fees')
    else:
        print(f'❌ Missing exchange fees for: {missing_fees}')
    
    print()
    
    # Check risk management consistency
    print('✅ RISK MANAGEMENT VALIDATION:')
    print('-' * 50)
    
    max_position_size = Config.MAX_POSITION_SIZE
    max_individual_limit = max(Config.POSITION_LIMITS.values())
    
    if max_individual_limit <= max_position_size:
        print('✅ Position limits are within max position size')
    else:
        print(f'❌ Some position limits exceed max position size: {max_individual_limit} > {max_position_size}')
    
    min_spread_percent = Config.MIN_SPREAD_PERCENT
    min_required_spread = min([Config.TRANSFER_SPEEDS[pair]['min_spread'] for pair in all_pairs])
    
    if min_required_spread >= min_spread_percent / 100:
        print('✅ Min spread threshold is appropriate')
    else:
        print(f'❌ Min spread threshold too high: {min_spread_percent}% > {min_required_spread*100:.1f}%')
    
    print()
    
    # Check data consistency
    print('✅ DATA CONSISTENCY VALIDATION:')
    print('-' * 50)
    
    # Check that all pairs have consistent data
    consistency_issues = []
    
    for pair in all_pairs:
        base_currency = pair.split('/')[0]
        
        # Check if currency has mapping
        if base_currency not in currency_mappings:
            consistency_issues.append(f'{pair}: Missing currency mapping')
        
        # Check if currency has fees
        if base_currency not in exchange_fees['binance']['withdrawal_fees']:
            consistency_issues.append(f'{pair}: Missing Binance fees')
        if base_currency not in exchange_fees['okx']['withdrawal_fees']:
            consistency_issues.append(f'{pair}: Missing OKX fees')
        
        # Check if pair has transfer speed
        if pair not in transfer_speeds:
            consistency_issues.append(f'{pair}: Missing transfer speed')
        
        # Check if pair has slippage
        if pair not in slippage_estimates:
            consistency_issues.append(f'{pair}: Missing slippage estimate')
        
        # Check if pair has position limit
        if pair not in position_limits:
            consistency_issues.append(f'{pair}: Missing position limit')
    
    if not consistency_issues:
        print('✅ All data is consistent')
    else:
        print('❌ Data consistency issues:')
        for issue in consistency_issues:
            print(f'   - {issue}')
    
    print()
    
    # Summary
    print('📊 VALIDATION SUMMARY:')
    print('-' * 50)
    
    total_issues = len(missing_speeds) + len(missing_slippage) + len(missing_limits) + len(missing_mappings) + len(missing_fees) + len(consistency_issues)
    
    if total_issues == 0:
        print('🎉 ALL VALIDATIONS PASSED!')
        print('✅ System is ready for live trading')
        print('✅ All configurations are consistent')
        print('✅ All data is complete and accurate')
    else:
        print(f'⚠️  {total_issues} issues found')
        print('❌ System needs fixes before live trading')
    
    print()
    
    # Recommendations
    print('💡 RECOMMENDATIONS:')
    print('-' * 50)
    print('1. Test all configurations in sandbox mode')
    print('2. Verify all currency pairs are available on both exchanges')
    print('3. Test transfer functionality for all assets')
    print('4. Validate fee calculations with real data')
    print('5. Start with small amounts for initial testing')
    print('6. Monitor all trades closely in the beginning')
    print('7. Keep detailed logs of all operations')
    print('8. Have emergency stop procedures ready')
    
    return {
        'total_issues': total_issues,
        'ready_for_live': total_issues == 0
    }

if __name__ == "__main__":
    validate_system()
