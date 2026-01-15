#!/bin/bash

# ENTSO-E Function Test Script
# This script helps test the ENTSO-E Azure Function locally

set -e

echo "🔍 ENTSO-E Function Test Script"
echo "================================"
echo ""

# Check if we're in the right directory
if [ ! -f "function_app.py" ]; then
    echo "❌ Error: function_app.py not found. Run this script from the entsoe-function directory."
    exit 1
fi

# Check if local.settings.json exists
if [ ! -f "local.settings.json" ]; then
    echo "❌ Error: local.settings.json not found."
    exit 1
fi

# Check for required environment variables
echo "📋 Checking configuration..."
if grep -q "your-entsoe-api-key" local.settings.json; then
    echo "⚠️  Warning: ENTSOE_API_KEY not configured in local.settings.json"
    echo "   Please update local.settings.json with your actual ENTSO-E API key"
    exit 1
fi

if grep -q "your-elastic-cloud-id" local.settings.json; then
    echo "⚠️  Warning: ELASTICSEARCH_CLOUD_ID not configured in local.settings.json"
    echo "   Please update local.settings.json with your actual Elasticsearch Cloud ID"
    exit 1
fi

echo "✅ Configuration looks good"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

echo "🐍 Python version:"
python3 --version
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "✅ Dependencies installed"
echo ""

# Check if Azure Functions Core Tools is installed
if ! command -v func &> /dev/null; then
    echo "⚠️  Warning: Azure Functions Core Tools not installed"
    echo "   Install from: https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local"
    echo ""
    echo "   macOS: brew tap azure/functions && brew install azure-functions-core-tools@4"
    echo "   Linux: Follow instructions at the link above"
    echo ""
    exit 1
fi

echo "🔧 Azure Functions Core Tools version:"
func --version
echo ""

# Run a quick validation
echo "🧪 Running quick validation..."
python3 -c "
import sys
try:
    import azure.functions
    import requests
    from elasticsearch import Elasticsearch
    print('✅ All required Python packages are installed')
except ImportError as e:
    print(f'❌ Missing package: {e}')
    sys.exit(1)
"

echo ""
echo "🎯 Test Options:"
echo ""
echo "1. Start function locally:"
echo "   func start"
echo ""
echo "2. Test via HTTP (after starting function):"
echo "   curl http://localhost:7071/api/ingest"
echo ""
echo "3. Test specific countries:"
echo "   curl 'http://localhost:7071/api/ingest?countries=DE,FR,ES'"
echo ""
echo "4. Test with POST:"
echo "   curl -X POST http://localhost:7071/api/ingest -H 'Content-Type: application/json' -d '{\"countries\": [\"DE\"]}'"
echo ""
echo "📊 Monitor logs in Kibana:"
echo "   GET entsoe-energy/_search"
echo ""
echo "================================"
echo "Ready to test! Run 'func start' to begin."
