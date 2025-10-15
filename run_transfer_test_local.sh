#!/bin/bash
# Quick script to run the transfer test locally
# 
# STEP 1: Go to your Railway dashboard
# STEP 2: Click on your bot project
# STEP 3: Go to "Variables" tab
# STEP 4: Copy and paste the values below (replace the PASTE_HERE placeholders)

echo "🔧 Transfer Test - Quick Setup"
echo "================================================"
echo ""
echo "⚠️  BEFORE RUNNING THIS SCRIPT:"
echo "   1. Open this file in a text editor"
echo "   2. Replace the PASTE_HERE placeholders with your actual API keys from Railway"
echo "   3. Save the file"
echo "   4. Run: bash run_transfer_test_local.sh"
echo ""
echo "================================================"
echo ""

# TODO: Replace these with your actual Railway values
export COINBASE_API_KEY="PASTE_YOUR_COINBASE_API_KEY_HERE"
export COINBASE_SECRET="PASTE_YOUR_COINBASE_SECRET_HERE"
export GEMINI_API_KEY="PASTE_YOUR_GEMINI_API_KEY_HERE"
export GEMINI_SECRET="PASTE_YOUR_GEMINI_SECRET_HERE"

# Check if variables are set
if [[ "$COINBASE_API_KEY" == "PASTE_YOUR_COINBASE_API_KEY_HERE" ]]; then
    echo "❌ ERROR: You need to edit this file and add your API keys first!"
    echo ""
    echo "Open run_transfer_test_local.sh and replace the PASTE_HERE placeholders."
    echo ""
    exit 1
fi

echo "✅ Environment variables loaded"
echo ""
echo "🚀 Running transfer test..."
echo ""

python3 test_transfer_mechanism.py

echo ""
echo "✅ Test complete!"

