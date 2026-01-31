#!/bin/bash

# ArmorIQ Validation Service Setup and Run Script

set -e

echo "🚀 ArmorIQ Validation Service Setup"
echo "===================================="

# Check Python version
echo "📋 Checking Python version..."
python3 --version || {
    echo "❌ Python 3 is required"
    exit 1
}

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating environment file..."
    cp .env.example .env
    echo "📝 Please edit .env file with your ArmorIQ API key"
    echo "   Required: ARMORIQ_API_KEY=ak_live_your_api_key_here"
fi

# Check if ArmorIQ API key is set
if grep -q "ak_live_your_api_key_here" .env 2>/dev/null; then
    echo "⚠️  Warning: Default API key detected in .env"
    echo "   Please update .env with your actual ArmorIQ API key"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🏃 To run the service:"
echo "   source venv/bin/activate"
echo "   uvicorn app.main:app --reload --port 8001"
echo ""
echo "🧪 To test the service:"
echo "   python test_client.py"
echo ""
echo "📚 API Documentation: http://localhost:8001/docs"
echo "🔍 Health Check: http://localhost:8001/health"
echo ""

# Ask if user wants to start the service
read -p "🚀 Start the validation service now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔥 Starting ArmorIQ Validation Service..."
    uvicorn app.main:app --reload --port 8001 --host 0.0.0.0
fi