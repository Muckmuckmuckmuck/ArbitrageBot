#!/usr/bin/env python3
"""
Comprehensive Code Audit for High-Frequency Arbitrage System
Critical review before real money deployment
"""

import os
import sys
import ast
import importlib.util
from typing import Dict, List, Any, Tuple
import logging

def audit_python_file(file_path: str) -> Dict[str, Any]:
    """Audit a Python file for potential issues"""
    issues = {
        'syntax_errors': [],
        'import_errors': [],
        'undefined_variables': [],
        'unused_imports': [],
        'potential_bugs': [],
        'security_issues': [],
        'performance_issues': [],
        'logic_errors': []
    }
    
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check syntax
        try:
            ast.parse(content)
        except SyntaxError as e:
            issues['syntax_errors'].append(f"Line {e.lineno}: {e.msg}")
        
        # Check for common issues
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Check for hardcoded values
            if 'api_key' in line.lower() and '=' in line and not 'os.getenv' in line:
                issues['security_issues'].append(f"Line {i}: Potential hardcoded API key")
            
            # Check for TODO/FIXME
            if 'TODO' in line or 'FIXME' in line or 'XXX' in line:
                issues['potential_bugs'].append(f"Line {i}: {line}")
            
            # Check for print statements (should use logging)
            if line.startswith('print('):
                issues['performance_issues'].append(f"Line {i}: Use logging instead of print")
            
            # Check for bare except
            if line.strip() == 'except:':
                issues['potential_bugs'].append(f"Line {i}: Bare except clause")
            
            # Check for potential division by zero
            if '/' in line and '0' in line and 'if' not in line:
                issues['logic_errors'].append(f"Line {i}: Potential division by zero")
            
            # Check for missing error handling
            if 'await' in line and 'try' not in lines[max(0, i-5):i]:
                issues['potential_bugs'].append(f"Line {i}: Async call without error handling")
        
        return issues
        
    except Exception as e:
        return {'error': f"Error auditing {file_path}: {str(e)}"}

def audit_configuration_consistency() -> Dict[str, Any]:
    """Audit configuration files for consistency"""
    issues = {
        'missing_configs': [],
        'inconsistent_values': [],
        'invalid_ranges': [],
        'missing_imports': []
    }
    
    try:
        # Check if all required files exist
        required_files = [
            'config.py',
            'high_frequency_config.py',
            'rate_limit_manager.py',
            'high_frequency_arbitrage_engine.py',
            'exchanges.py',
            'price_monitor.py',
            'arbitrage_engine.py'
        ]
        
        for file in required_files:
            if not os.path.exists(file):
                issues['missing_configs'].append(f"Missing file: {file}")
        
        # Check high_frequency_config.py
        if os.path.exists('high_frequency_config.py'):
            with open('high_frequency_config.py', 'r') as f:
                content = f.read()
            
            # Check for required configurations
            required_configs = [
                'CONTINUOUS_TRADING',
                'MAX_CONCURRENT_TRADES',
                'MAX_TOTAL_EXPOSURE',
                'RESERVE_PERCENT',
                'OPTIMIZED_SPREAD_REQUIREMENTS',
                'EXCHANGE_RATE_LIMITS',
                'EXCHANGE_FEES',
                'SLIPPAGE_ESTIMATES',
                'POSITION_PERCENTAGES',
                'RISK_MANAGEMENT'
            ]
            
            for config in required_configs:
                if config not in content:
                    issues['missing_configs'].append(f"Missing configuration: {config}")
            
            # Check for reasonable values
            if 'MAX_TOTAL_EXPOSURE' in content:
                if '0.80' not in content:
                    issues['inconsistent_values'].append("MAX_TOTAL_EXPOSURE should be 0.80 (80%)")
            
            if 'RESERVE_PERCENT' in content:
                if '0.15' not in content:
                    issues['inconsistent_values'].append("RESERVE_PERCENT should be 0.15 (15%)")
        
        return issues
        
    except Exception as e:
        return {'error': f"Error auditing configuration: {str(e)}"}

def audit_imports_and_dependencies() -> Dict[str, Any]:
    """Audit imports and dependencies"""
    issues = {
        'missing_imports': [],
        'circular_imports': [],
        'unused_imports': [],
        'version_conflicts': []
    }
    
    try:
        # Check main files for import issues
        main_files = [
            'main.py',
            'high_frequency_arbitrage_engine.py',
            'rate_limit_manager.py',
            'exchanges.py',
            'arbitrage_engine.py'
        ]
        
        for file in main_files:
            if os.path.exists(file):
                with open(file, 'r') as f:
                    content = f.read()
                
                # Check for common import issues
                if 'from exchanges import' in content and 'exchanges.py' not in os.listdir('.'):
                    issues['missing_imports'].append(f"{file}: Missing exchanges.py")
                
                if 'from price_monitor import' in content and 'price_monitor.py' not in os.listdir('.'):
                    issues['missing_imports'].append(f"{file}: Missing price_monitor.py")
                
                if 'from config import' in content and 'config.py' not in os.listdir('.'):
                    issues['missing_imports'].append(f"{file}: Missing config.py")
        
        return issues
        
    except Exception as e:
        return {'error': f"Error auditing imports: {str(e)}"}

def audit_risk_management() -> Dict[str, Any]:
    """Audit risk management implementation"""
    issues = {
        'missing_risk_checks': [],
        'insufficient_limits': [],
        'missing_stop_loss': [],
        'insufficient_validation': []
    }
    
    try:
        # Check risk management in high_frequency_arbitrage_engine.py
        if os.path.exists('high_frequency_arbitrage_engine.py'):
            with open('high_frequency_arbitrage_engine.py', 'r') as f:
                content = f.read()
            
            # Check for essential risk management features
            risk_checks = [
                'check_rate_limit',
                'calculate_position_size',
                'get_total_balance',
                'RISK_MANAGEMENT',
                'max_position_percent',
                'stop_loss_percent'
            ]
            
            for check in risk_checks:
                if check not in content:
                    issues['missing_risk_checks'].append(f"Missing risk check: {check}")
            
            # Check for position size validation
            if 'position_size <= 0' not in content:
                issues['insufficient_validation'].append("Missing position size validation")
            
            # Check for balance validation
            if 'total_balance <= 0' not in content:
                issues['insufficient_validation'].append("Missing balance validation")
        
        return issues
        
    except Exception as e:
        return {'error': f"Error auditing risk management: {str(e)}"}

def audit_error_handling() -> Dict[str, Any]:
    """Audit error handling implementation"""
    issues = {
        'missing_try_catch': [],
        'bare_except': [],
        'unhandled_errors': [],
        'insufficient_logging': []
    }
    
    try:
        # Check error handling in key files
        key_files = [
            'high_frequency_arbitrage_engine.py',
            'rate_limit_manager.py',
            'exchanges.py'
        ]
        
        for file in key_files:
            if os.path.exists(file):
                with open(file, 'r') as f:
                    content = f.read()
                
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    # Check for bare except
                    if line.strip() == 'except:':
                        issues['bare_except'].append(f"{file}:{i}: Bare except clause")
                    
                    # Check for async calls without error handling
                    if 'await' in line and 'try' not in lines[max(0, i-5):i]:
                        issues['unhandled_errors'].append(f"{file}:{i}: Async call without error handling")
                    
                    # Check for missing error logging
                    if 'except' in line and 'logger.error' not in lines[i:i+3]:
                        issues['insufficient_logging'].append(f"{file}:{i}: Missing error logging")
        
        return issues
        
    except Exception as e:
        return {'error': f"Error auditing error handling: {str(e)}"}

def audit_security() -> Dict[str, Any]:
    """Audit security implementation"""
    issues = {
        'hardcoded_secrets': [],
        'insecure_practices': [],
        'missing_validation': [],
        'exposure_risks': []
    }
    
    try:
        # Check for hardcoded secrets
        files_to_check = [
            'config.py',
            'high_frequency_config.py',
            'main.py',
            'exchanges.py'
        ]
        
        for file in files_to_check:
            if os.path.exists(file):
                with open(file, 'r') as f:
                    content = f.read()
                
                # Check for hardcoded API keys
                if 'api_key' in content.lower() and 'os.getenv' not in content:
                    issues['hardcoded_secrets'].append(f"{file}: Potential hardcoded API key")
                
                # Check for hardcoded secrets
                if 'secret' in content.lower() and 'os.getenv' not in content:
                    issues['hardcoded_secrets'].append(f"{file}: Potential hardcoded secret")
                
                # Check for debug prints
                if 'print(' in content:
                    issues['insecure_practices'].append(f"{file}: Debug print statements")
        
        return issues
        
    except Exception as e:
        return {'error': f"Error auditing security: {str(e)}"}

def audit_performance() -> Dict[str, Any]:
    """Audit performance implementation"""
    issues = {
        'inefficient_loops': [],
        'blocking_operations': [],
        'memory_leaks': [],
        'slow_operations': []
    }
    
    try:
        # Check performance in high_frequency_arbitrage_engine.py
        if os.path.exists('high_frequency_arbitrage_engine.py'):
            with open('high_frequency_arbitrage_engine.py', 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                # Check for blocking operations
                if 'time.sleep(' in line and 'await' not in line:
                    issues['blocking_operations'].append(f"Line {i}: Blocking sleep operation")
                
                # Check for inefficient loops
                if 'for ' in line and 'in range(' in line and 'async' not in line:
                    issues['inefficient_loops'].append(f"Line {i}: Potential inefficient loop")
                
                # Check for synchronous operations in async context
                if 'await' in lines[max(0, i-2):i] and 'time.sleep(' in line:
                    issues['blocking_operations'].append(f"Line {i}: Sync sleep in async context")
        
        return issues
        
    except Exception as e:
        return {'error': f"Error auditing performance: {str(e)}"}

def run_comprehensive_audit() -> Dict[str, Any]:
    """Run comprehensive audit of the entire system"""
    print('=' * 80)
    print('COMPREHENSIVE CODE AUDIT - HIGH-FREQUENCY ARBITRAGE SYSTEM')
    print('=' * 80)
    
    audit_results = {
        'overall_status': 'PASS',
        'critical_issues': 0,
        'warnings': 0,
        'recommendations': 0,
        'detailed_results': {}
    }
    
    print('🔍 AUDITING SYSTEM COMPONENTS...')
    print('-' * 50)
    
    # 1. Configuration Consistency
    print('1. Checking configuration consistency...')
    config_issues = audit_configuration_consistency()
    audit_results['detailed_results']['configuration'] = config_issues
    
    if config_issues.get('missing_configs') or config_issues.get('inconsistent_values'):
        audit_results['critical_issues'] += len(config_issues.get('missing_configs', []))
        audit_results['critical_issues'] += len(config_issues.get('inconsistent_values', []))
        print(f"   ❌ Found {len(config_issues.get('missing_configs', []))} missing configs")
        print(f"   ❌ Found {len(config_issues.get('inconsistent_values', []))} inconsistent values")
    else:
        print('   ✅ Configuration consistency: PASS')
    
    # 2. Imports and Dependencies
    print('2. Checking imports and dependencies...')
    import_issues = audit_imports_and_dependencies()
    audit_results['detailed_results']['imports'] = import_issues
    
    if import_issues.get('missing_imports') or import_issues.get('circular_imports'):
        audit_results['critical_issues'] += len(import_issues.get('missing_imports', []))
        audit_results['critical_issues'] += len(import_issues.get('circular_imports', []))
        print(f"   ❌ Found {len(import_issues.get('missing_imports', []))} missing imports")
        print(f"   ❌ Found {len(import_issues.get('circular_imports', []))} circular imports")
    else:
        print('   ✅ Imports and dependencies: PASS')
    
    # 3. Risk Management
    print('3. Checking risk management...')
    risk_issues = audit_risk_management()
    audit_results['detailed_results']['risk_management'] = risk_issues
    
    if risk_issues.get('missing_risk_checks') or risk_issues.get('insufficient_limits'):
        audit_results['critical_issues'] += len(risk_issues.get('missing_risk_checks', []))
        audit_results['critical_issues'] += len(risk_issues.get('insufficient_limits', []))
        print(f"   ❌ Found {len(risk_issues.get('missing_risk_checks', []))} missing risk checks")
        print(f"   ❌ Found {len(risk_issues.get('insufficient_limits', []))} insufficient limits")
    else:
        print('   ✅ Risk management: PASS')
    
    # 4. Error Handling
    print('4. Checking error handling...')
    error_issues = audit_error_handling()
    audit_results['detailed_results']['error_handling'] = error_issues
    
    if error_issues.get('bare_except') or error_issues.get('unhandled_errors'):
        audit_results['warnings'] += len(error_issues.get('bare_except', []))
        audit_results['warnings'] += len(error_issues.get('unhandled_errors', []))
        print(f"   ⚠️  Found {len(error_issues.get('bare_except', []))} bare except clauses")
        print(f"   ⚠️  Found {len(error_issues.get('unhandled_errors', []))} unhandled errors")
    else:
        print('   ✅ Error handling: PASS')
    
    # 5. Security
    print('5. Checking security...')
    security_issues = audit_security()
    audit_results['detailed_results']['security'] = security_issues
    
    if security_issues.get('hardcoded_secrets') or security_issues.get('insecure_practices'):
        audit_results['critical_issues'] += len(security_issues.get('hardcoded_secrets', []))
        audit_results['critical_issues'] += len(security_issues.get('insecure_practices', []))
        print(f"   ❌ Found {len(security_issues.get('hardcoded_secrets', []))} hardcoded secrets")
        print(f"   ❌ Found {len(security_issues.get('insecure_practices', []))} insecure practices")
    else:
        print('   ✅ Security: PASS')
    
    # 6. Performance
    print('6. Checking performance...')
    performance_issues = audit_performance()
    audit_results['detailed_results']['performance'] = performance_issues
    
    if performance_issues.get('blocking_operations') or performance_issues.get('inefficient_loops'):
        audit_results['warnings'] += len(performance_issues.get('blocking_operations', []))
        audit_results['warnings'] += len(performance_issues.get('inefficient_loops', []))
        print(f"   ⚠️  Found {len(performance_issues.get('blocking_operations', []))} blocking operations")
        print(f"   ⚠️  Found {len(performance_issues.get('inefficient_loops', []))} inefficient loops")
    else:
        print('   ✅ Performance: PASS')
    
    # 7. Individual File Audits
    print('7. Auditing individual files...')
    python_files = [f for f in os.listdir('.') if f.endswith('.py')]
    file_issues = {}
    
    for file in python_files:
        if file != 'comprehensive_code_audit.py':  # Skip this file
            issues = audit_python_file(file)
            if any(issues.values()):
                file_issues[file] = issues
                audit_results['warnings'] += sum(len(v) for v in issues.values() if isinstance(v, list))
    
    audit_results['detailed_results']['file_issues'] = file_issues
    
    if file_issues:
        print(f"   ⚠️  Found issues in {len(file_issues)} files")
    else:
        print('   ✅ Individual files: PASS')
    
    # Determine overall status
    if audit_results['critical_issues'] > 0:
        audit_results['overall_status'] = 'FAIL'
    elif audit_results['warnings'] > 0:
        audit_results['overall_status'] = 'WARN'
    else:
        audit_results['overall_status'] = 'PASS'
    
    # Print summary
    print('\n' + '=' * 80)
    print('AUDIT SUMMARY')
    print('=' * 80)
    print(f'Overall Status: {audit_results["overall_status"]}')
    print(f'Critical Issues: {audit_results["critical_issues"]}')
    print(f'Warnings: {audit_results["warnings"]}')
    print(f'Recommendations: {audit_results["recommendations"]}')
    
    if audit_results['critical_issues'] > 0:
        print('\n❌ CRITICAL ISSUES FOUND - DO NOT DEPLOY WITH REAL MONEY')
        print('Fix these issues before proceeding:')
        
        for category, issues in audit_results['detailed_results'].items():
            if isinstance(issues, dict):
                for issue_type, issue_list in issues.items():
                    if isinstance(issue_list, list) and issue_list:
                        print(f'\n{category.upper()} - {issue_type.upper()}:')
                        for issue in issue_list[:5]:  # Show first 5
                            print(f'   • {issue}')
    
    elif audit_results['warnings'] > 0:
        print('\n⚠️  WARNINGS FOUND - REVIEW BEFORE DEPLOYMENT')
        print('Consider fixing these warnings:')
        
        for category, issues in audit_results['detailed_results'].items():
            if isinstance(issues, dict):
                for issue_type, issue_list in issues.items():
                    if isinstance(issue_list, list) and issue_list:
                        print(f'\n{category.upper()} - {issue_type.upper()}:')
                        for issue in issue_list[:3]:  # Show first 3
                            print(f'   • {issue}')
    
    else:
        print('\n✅ AUDIT PASSED - SYSTEM READY FOR DEPLOYMENT')
        print('No critical issues found. System appears ready for real money trading.')
    
    return audit_results

if __name__ == "__main__":
    results = run_comprehensive_audit()
    
    # Save results to file
    with open('audit_results.json', 'w') as f:
        import json
        json.dump(results, f, indent=2)
    
    print(f'\n📄 Detailed results saved to: audit_results.json')
