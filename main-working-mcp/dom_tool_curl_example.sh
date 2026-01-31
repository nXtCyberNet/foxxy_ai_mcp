#!/bin/bash

echo "🔧 DOM Validation Tool - curl Response Examples"
echo "==============================================="

echo ""
echo "1️⃣  STANDARD JSON REQUEST & RESPONSE"
echo "=====================================

# curl command:
curl -X POST \"http://localhost:8001/mcp\" \\
  -H \"Content-Type: application/json\" \\
  -d '{
    \"jsonrpc\": \"2.0\",
    \"method\": \"tools/call\",
    \"params\": {
      \"name\": \"validate_dom_operation\",
      \"arguments\": {
        \"operation\": \"write\",
        \"target_domain\": \"secure-payments.example.com\",
        \"data_sensitivity\": \"high\"
      }
    },
    \"id\": 1
  }'

# Expected JSON Response:
{
  \"jsonrpc\": \"2.0\",
  \"id\": 1,
  \"result\": {
    \"content\": [
      {
        \"type\": \"text\",
        \"text\": \"{
          \\\"validation_result\\\": {
            \\\"approved\\\": false,
            \\\"risk_analysis\\\": {
              \\\"total_risk_score\\\": 87.5,
              \\\"risk_level\\\": \\\"high\\\",
              \\\"operation_risk\\\": 30,
              \\\"domain_risk\\\": 20,
              \\\"sensitivity_multiplier\\\": 2.5,
              \\\"recommendation\\\": \\\"review\\\"
            },
            \\\"compliance_status\\\": \\\"requires_review\\\",
            \\\"cdp_browser_use_ready\\\": false
          },
          \\\"operation_details\\\": {
            \\\"operation\\\": \\\"write\\\",
            \\\"target_domain\\\": \\\"secure-payments.example.com\\\",
            \\\"data_sensitivity\\\": \\\"high\\\"
          },
          \\\"cdp_browser_use_ready\\\": false,
          \\\"timestamp\\\": \\\"2026-01-31T16:45:30.123456Z\\\"
        }\"
      }
    ]
  }
}"

echo ""
echo ""
echo "2️⃣  SSE STREAMING REQUEST & RESPONSE"
echo "===================================="

echo "
# SSE curl command (Accept header):
curl -X POST \"http://localhost:8001/mcp\" \\
  -H \"Content-Type: application/json\" \\
  -H \"Accept: text/event-stream\" \\
  -d '{
    \"jsonrpc\": \"2.0\",
    \"method\": \"tools/call\",
    \"params\": {
      \"name\": \"validate_dom_operation\",
      \"arguments\": {
        \"operation\": \"read\",
        \"target_domain\": \"public-site.com\",
        \"data_sensitivity\": \"public\"
      }
    },
    \"id\": 2
  }'

# Expected SSE Response:
data: {\"jsonrpc\":\"2.0\",\"id\":2,\"result\":{\"content\":[{\"type\":\"text\",\"text\":\"{\\\"validation_result\\\":{\\\"approved\\\":true,\\\"risk_analysis\\\":{\\\"total_risk_score\\\":10.0,\\\"risk_level\\\":\\\"low\\\"},\\\"compliance_status\\\":\\\"approved\\\",\\\"cdp_browser_use_ready\\\":true}}\"}]}}

data: {\"event\":\"completion\",\"timestamp\":\"2026-01-31T16:45:30.456Z\",\"status\":\"completed\"}
"

echo ""
echo ""
echo "3️⃣  SSE DEDICATED ENDPOINT"
echo "=========================="

echo "
# SSE dedicated endpoint:
curl -X POST \"http://localhost:8001/mcp/sse\" \\
  -H \"Content-Type: application/json\" \\
  -d '{
    \"jsonrpc\": \"2.0\",
    \"method\": \"tools/call\",
    \"params\": {
      \"name\": \"validate_dom_operation\",
      \"arguments\": {
        \"operation\": \"submit\",
        \"target_domain\": \"banking-app.secure.com\",
        \"data_sensitivity\": \"restricted\"
      }
    },
    \"id\": 3
  }'
"

echo ""
echo "4️⃣  RESPONSE FIELD MEANINGS"
echo "=========================="
echo "
✅ approved              - Can proceed with DOM operation
🔢 total_risk_score      - Combined risk assessment (0-100+)
📊 risk_level           - low/medium/high classification  
🌐 operation_risk       - Base risk for operation type
🏛️  domain_risk          - Additional risk from target domain
🔒 sensitivity_multiplier- Data sensitivity impact factor
📋 compliance_status     - approved/requires_review
🤖 cdp_browser_use_ready - Ready for Chrome DevTools Protocol
🕐 timestamp            - When validation was performed
"

echo ""
echo "5️⃣  INTEGRATION EXAMPLE"
echo "======================"
echo '
# Bash script integration:
RESPONSE=$(curl -s -X POST "http://localhost:8001/mcp" \
  -H "Content-Type: application/json" \
  -d '\''{
    "jsonrpc": "2.0",
    "method": "tools/call", 
    "params": {
      "name": "validate_dom_operation",
      "arguments": {
        "operation": "write",
        "target_domain": "'"$TARGET_DOMAIN"'",
        "data_sensitivity": "'"$DATA_LEVEL"'"
      }
    },
    "id": 1
  }'\'')

APPROVED=$(echo $RESPONSE | jq -r '.result.content[0].text | fromjson | .validation_result.approved')

if [ "$APPROVED" = "true" ]; then
  echo "✅ DOM operation approved"
  # Execute browser automation
else  
  echo "❌ DOM operation denied"
  exit 1
fi
'