#!/bin/bash
# Railway CLI Setup Script
# Run this script to install Railway CLI and set it up for log viewing

echo "🚂 Setting up Railway CLI..."
echo ""

# Check if Railway CLI is already installed
if command -v railway &> /dev/null; then
    echo "✅ Railway CLI is already installed!"
    railway --version
    echo ""
    echo "Next steps:"
    echo "1. Run: railway login"
    echo "2. Run: railway link (in project directory)"
    echo "3. Run: railway logs (to view logs)"
    exit 0
fi

# Try installation methods
echo "📦 Installing Railway CLI..."

# Method 1: Shell script installer (recommended)
echo "Trying shell script installer..."
if bash <(curl -fsSL cli.new) 2>&1; then
    echo "✅ Railway CLI installed successfully!"
    railway --version
    exit 0
fi

# Method 2: npm (if available)
if command -v npm &> /dev/null; then
    echo "Trying npm installation..."
    echo "Note: This may require sudo password"
    echo "Please run manually: sudo npm i -g @railway/cli"
    echo ""
fi

# Method 3: Homebrew (if available)
if command -v brew &> /dev/null; then
    echo "Trying Homebrew installation..."
    brew install railway
    exit 0
fi

echo ""
echo "❌ Could not install Railway CLI automatically."
echo ""
echo "Please install manually using one of these methods:"
echo ""
echo "1. Shell script (recommended):"
echo "   bash <(curl -fsSL cli.new)"
echo ""
echo "2. npm (requires Node.js):"
echo "   sudo npm i -g @railway/cli"
echo ""
echo "3. Homebrew (macOS):"
echo "   brew install railway"
echo ""
echo "After installation, run:"
echo "  railway login"
echo "  railway link"
echo "  railway logs"

