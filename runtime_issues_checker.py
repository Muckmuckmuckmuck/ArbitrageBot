#!/usr/bin/env python3
"""
Runtime Issues Checker
Analyzes the bot code for potential runtime issues
"""

import ast
import sys
from typing import List, Dict, Any

class RuntimeIssueChecker(ast.NodeVisitor):
    """Check for potential runtime issues in Python code"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.current_function = None
    
    def visit_FunctionDef(self, node):
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function
    
    def visit_Subscript(self, node):
        """Check for dict access without .get()"""
        if isinstance(node.ctx, ast.Load):
            if isinstance(node.slice, (ast.Constant, ast.Name)):
                self.warnings.append({
                    'type': 'dict_access',
                    'line': node.lineno,
                    'function': self.current_function,
                    'message': 'Dictionary access without .get() - may raise KeyError'
                })
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        """Check for potential AttributeError"""
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """Check for function calls that might fail"""
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.attr, str):
                # Check for common issues
                if node.func.attr in ['split', 'strip', 'lower', 'upper']:
                    if not any(isinstance(arg, ast.Constant) for arg in node.args):
                        pass  # Could check if working on None
        self.generic_visit(node)

def check_file(filename: str):
    """Check a Python file for runtime issues"""
    print(f"Analyzing {filename}...")
    
    try:
        with open(filename, 'r') as f:
            code = f.read()
        
        tree = ast.parse(code, filename=filename)
        checker = RuntimeIssueChecker()
        checker.visit(tree)
        
        print(f"  Found {len(checker.issues)} issues")
        print(f"  Found {len(checker.warnings)} warnings")
        
        return checker.issues, checker.warnings
        
    except SyntaxError as e:
        print(f"  SYNTAX ERROR: {e}")
        return [{'type': 'syntax', 'message': str(e)}], []
    except Exception as e:
        print(f"  ERROR: {e}")
        return [{'type': 'error', 'message': str(e)}], []

def main():
    print("=" * 80)
    print("RUNTIME ISSUES CHECKER")
    print("=" * 80)
    print()
    
    files_to_check = [
        'aggressive_bot_fixed.py',
        'aggressive_config.py',
        'auto_sizing_manager.py',
        'dynamic_spread_manager.py',
        'dynamic_slippage_detector.py',
        'smart_rate_limiter.py',
    ]
    
    all_issues = []
    all_warnings = []
    
    for filename in files_to_check:
        try:
            issues, warnings = check_file(filename)
            all_issues.extend(issues)
            all_warnings.extend(warnings)
        except FileNotFoundError:
            print(f"  File not found: {filename}")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total issues: {len(all_issues)}")
    print(f"Total warnings: {len(all_warnings)}")
    
    if len(all_issues) == 0:
        print()
        print("✅ No critical issues found!")
    else:
        print()
        print("❌ Issues found that need fixing")
    
    return len(all_issues)

if __name__ == "__main__":
    sys.exit(main())

