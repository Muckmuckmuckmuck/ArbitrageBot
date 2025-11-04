#!/usr/bin/env python3
"""
Railway Log Viewer
==================

This script can fetch Railway logs if Railway CLI is installed and configured.
Alternatively, it can help you view logs from Railway's web interface.

Usage:
    python view_railway_logs.py
"""

import subprocess
import sys
import os

def check_railway_cli():
    """Check if Railway CLI is installed"""
    try:
        result = subprocess.run(['railway', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return True, result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return False, None

def view_railway_logs():
    """View Railway logs using CLI"""
    installed, version = check_railway_cli()
    
    if not installed:
        print("❌ Railway CLI is not installed")
        print("")
        print("To install Railway CLI:")
        print("  1. Run: bash setup_railway_cli.sh")
        print("  2. Or install manually: bash <(curl -fsSL cli.new)")
        print("")
        print("After installation:")
        print("  1. Run: railway login")
        print("  2. Run: railway link")
        print("  3. Run: railway logs")
        return False
    
    print(f"✅ Railway CLI found: {version}")
    print("")
    print("📋 Viewing Railway logs...")
    print("   (Press Ctrl+C to stop)")
    print("=" * 80)
    print("")
    
    try:
        # Stream logs
        process = subprocess.Popen(['railway', 'logs'], 
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  text=True,
                                  bufsize=1,
                                  universal_newlines=True)
        
        # Print logs line by line
        for line in process.stdout:
            print(line, end='')
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped viewing logs")
        process.terminate()
        return True
    except Exception as e:
        print(f"❌ Error viewing logs: {e}")
        print("")
        print("Make sure you're logged in and linked:")
        print("  railway login")
        print("  railway link")
        return False
    
    return True

if __name__ == "__main__":
    view_railway_logs()

