#!/bin/bash
# Quick start script for testing the arbitrage bot

echo "========================================"
echo "ARBITRAGE BOT - QUICK START"
echo "========================================"
echo ""

# Step 1: Test imports
echo "Step 1/4: Testing imports..."
python test_imports.py
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Import test failed. Please install missing dependencies."
    exit 1
fi

echo ""
echo "Step 2/4: Testing configuration..."
python test_config.py
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Configuration test failed. Please check .env file."
    exit 1
fi

echo ""
echo "Step 3/4: All tests passed!"
echo ""
echo "Step 4/4: Ready to start bot?"
echo ""
echo "Options:"
echo "  1) Start bot now"
echo "  2) View testing guide"
echo "  3) Exit"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "Starting bot..."
        echo "Press Ctrl+C to stop"
        echo ""
        sleep 2
        python aggressive_bot_fixed.py
        ;;
    2)
        echo ""
        echo "Opening testing guide..."
        cat TESTING_GUIDE.md | less
        ;;
    3)
        echo ""
        echo "Exiting. Good luck!"
        exit 0
        ;;
    *)
        echo ""
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

