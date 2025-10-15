#!/bin/bash
# Quick script to run the transfer test on Railway

echo "🚀 Running transfer test on Railway..."
echo ""
echo "This will:"
echo "  1. Buy \$1 XRP on Coinbase"
echo "  2. Transfer to Gemini"
echo "  3. Sell on Gemini"
echo ""
echo "This tests if transfers work while keeping your main bot running."
echo ""

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found."
    echo ""
    echo "Install it with:"
    echo "  npm i -g @railway/cli"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo "Starting test..."
echo "==============================================================================="

railway run python3 simple_transfer_test.py

echo "==============================================================================="
echo ""
echo "Test complete! Check the output above."
echo ""

