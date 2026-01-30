#!/bin/bash
# Deployment script for foxxy-ai MCP server
# This configures the server to work with ArmorIQ at https://armo.eryzalabs.com/

echo "🚀 Starting foxxy-ai MCP Server for ArmorIQ"
echo "=" * 60

# Set environment variables for production deployment
export MCP_HOST="0.0.0.0"
export MCP_PORT="8001"
export MCP_API_KEY="mcp_automation_analytics_key_12345"

# Optional SSL configuration (recommended for production)
# export SSL_KEYFILE="/path/to/ssl/key.pem"
# export SSL_CERTFILE="/path/to/ssl/cert.pem"

echo "Server Configuration:"
echo "  Host: $MCP_HOST"
echo "  Port: $MCP_PORT"
echo "  API Key: ${MCP_API_KEY:0:10}..."
echo "  ArmorIQ Endpoint: https://armo.eryzalabs.com/"
echo "  Server Name: foxxy-ai"

# Install dependencies if needed
pip install fastapi uvicorn numpy

# Start the server
echo ""
echo "Starting uvicorn server..."
uvicorn analytics_mcp_server:app \
  --host $MCP_HOST \
  --port $MCP_PORT \
  --workers 2 \
  --log-level info \
  --access-log

# Alternative for development with auto-reload:
# uvicorn analytics_mcp_server:app --host $MCP_HOST --port $MCP_PORT --reload