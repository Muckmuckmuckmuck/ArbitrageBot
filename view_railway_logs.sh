#!/bin/bash
# Quick Railway Logs Viewer
# This script checks if Railway CLI is installed and views logs

PROJECT_NAME="lively-playfulness"

echo "🚂 Railway Logs Viewer"
echo "===================="
echo ""

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI is not installed"
    echo ""
    echo "Install it with:"
    echo "  bash <(curl -fsSL cli.new)"
    echo ""
    echo "Then run this script again"
    exit 1
fi

echo "✅ Railway CLI found"
echo ""

# Check if logged in
if ! railway whoami &> /dev/null; then
    echo "⚠️  Not logged in to Railway"
    echo "   Run: railway login"
    exit 1
fi

echo "✅ Logged in to Railway"
echo ""

# Check if project is linked
if [ ! -f ".railway/project.json" ]; then
    echo "⚠️  Project not linked"
    echo "   Linking to project: $PROJECT_NAME"
    railway link "$PROJECT_NAME" 2>&1 || {
        echo "   Could not auto-link. Please run: railway link"
        echo "   Then select: $PROJECT_NAME"
        exit 1
    }
fi

echo "✅ Project linked"
echo ""
echo "📋 Viewing Railway logs..."
echo "   (Press Ctrl+C to stop)"
echo "=" * 80
echo ""

# View logs
railway logs "$@"

