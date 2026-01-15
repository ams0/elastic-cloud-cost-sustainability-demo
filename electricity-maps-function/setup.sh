#!/bin/bash
set -e

echo "🔧 Setting up Electricity Maps Azure Function..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

# Check if Azure Functions Core Tools is installed
if ! command -v func &> /dev/null; then
    echo "⚠️  Azure Functions Core Tools not found."
    echo "📦 Install it from: https://docs.microsoft.com/azure/azure-functions/functions-run-local"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check if local.settings.json has been configured
if grep -q "your-electricity-maps-api-key-here" local.settings.json 2>/dev/null; then
    echo ""
    echo "⚠️  WARNING: Please configure your API keys in local.settings.json"
    echo ""
    echo "You need to set:"
    echo "  - ELECTRICITY_MAPS_API_KEY"
    echo "  - ELASTICSEARCH_CLOUD_ID"
    echo "  - ELASTICSEARCH_API_KEY"
    echo ""
fi

echo "✅ Setup complete!"
echo ""
echo "To run the function locally:"
echo "  1. Configure local.settings.json with your API keys"
echo "  2. Run: func start"
echo ""
echo "To test the function:"
echo "  curl http://localhost:7071/api/ingest"
echo ""
