#!/bin/bash
# Setup environment variables for local transfer test
# 
# INSTRUCTIONS:
# 1. Go to Railway dashboard
# 2. Click on your bot deployment
# 3. Go to "Variables" tab
# 4. Copy the values for these 4 variables
# 5. Paste them below (replace the placeholders)
# 6. Run: source setup_env_for_test.sh
# 7. Run: python3 test_transfer_mechanism.py

echo "🔧 Setting up environment variables for transfer test..."

# TODO: Replace these with your actual values from Railway
export COINBASE_API_KEY="PASTE_YOUR_COINBASE_API_KEY_HERE"
export COINBASE_SECRET="PASTE_YOUR_COINBASE_SECRET_HERE"
export GEMINI_API_KEY="PASTE_YOUR_GEMINI_API_KEY_HERE"  
export GEMINI_SECRET="PASTE_YOUR_GEMINI_SECRET_HERE"

echo "✅ Environment variables set!"
echo ""
echo "Now run:"
echo "  python3 test_transfer_mechanism.py"
