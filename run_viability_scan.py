#!/usr/bin/env python3
"""
Viability Scan Runner - Temporary replacement for main bot
This will scan all cryptos and exit (no trading)
"""

import sys
import logging
from crypto_viability_scanner import main

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    print("\n" + "="*100)
    print("🔍 CRYPTO VIABILITY SCAN MODE")
    print("="*100)
    print("This is a ONE-TIME scan to find the best cryptos.")
    print("The bot will NOT trade - only scan and log results.")
    print("="*100 + "\n")
    
    try:
        main()
        print("\n✅ Scan complete! Check logs above for results.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Scan failed: {str(e)}")
        sys.exit(1)

