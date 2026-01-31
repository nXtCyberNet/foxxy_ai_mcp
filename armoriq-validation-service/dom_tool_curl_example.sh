#!/bin/bash
"""
Curl Response Example for DOM Validation Tool
"""

echo "🔧 DOM Validation Tool - Curl Command & Response"
echo "=" * 80

echo "📝 CURL COMMAND:"
echo "================"

cat << 'EOF'
curl -X POST "http://localhost:8080/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "I need to validate if this DOM operation is safe and compliant before browser execution.",
    "tool_calls": [
      {
        "name": "browser__validate_dom_operation", 
        "args": {
          "operation": "modify_payment_form",
          "target_domain": "secure-payments.example.com", 
          "data_sensitivity": "high"
        }
      }
    ],
    "llm_provider": "openai",
    "llm_model": "gpt-4o", 
    "user_prompt": "Validate DOM operation safety for payment form modification",
    "user_id": "security_validator_002"
  }'
EOF

echo ""
echo "📋 EXPECTED JSON RESPONSE:"
echo "========================="

cat << 'EOF'
{
  "status": "pass",
  "credibility_score": 87.5,
  "metrics": {
    "plan_integrity": 90.0,
    "execution_success": 100.0,
    "response_consistency": 85.0,
    "security_compliance": 75.0,
    "overall_credibility": 87.5
  },
  "user_id": "security_validator_002",
  "execution_details": {
    "tools": [
      {
        "tool_name": "browser__validate_dom_operation",
        "status": "success",
        "response": {
          "status": "success",
          "data": "Mock result for validate_dom_operation",
          "mcp": "browser",
          "params": {
            "operation": "modify_payment_form",
            "target_domain": "secure-payments.example.com",
            "data_sensitivity": "high"
          }
        },
        "error": null,
        "execution_time_ms": 123.45
      }
    ],
    "plan_steps": [
      {
        "action": "validate_dom_operation",
        "mcp": "browser", 
        "description": "Validate execution of browser__validate_dom_operation",
        "params": {
          "operation": "modify_payment_form",
          "target_domain": "secure-payments.example.com",
          "data_sensitivity": "high"
        }
      }
    ]
  },
  "tools_executed": 1,
  "plan_captured": false,
  "token_generated": false,
  "plan_id": "mock_hash_-1234567890",
  "session_id": "session_abc12345",
  "processing_time_ms": 156.78,
  "credibility_assessment": "very_good"
}
EOF

echo ""
echo "🔍 ARMORIQ SDK RESPONSES (when configured):"
echo "==========================================="

cat << 'EOF'
✅ ARMORIQ SDK RESPONSE [CAPTURE_PLAN]
====================================
{
  "sdk": "ArmorIQ",
  "method": "capture_plan", 
  "success": true,
  "timestamp": "2026-01-31T15:30:45.123456Z",
  "request": {
    "llm": "openai/gpt-4o",
    "prompt": "Validate DOM operation safety for payment form modification",
    "plan_steps_count": 1,
    "plan_structure": {
      "goal": "Validate LLM output through secure execution",
      "reasoning": "ArmorIQ validation workflow",
      "user_id": "security_validator_002",
      "session_id": "session_abc12345",
      "steps": [
        {
          "action": "validate_dom_operation",
          "mcp": "browser",
          "description": "Validate execution of browser__validate_dom_operation",
          "params": {
            "operation": "modify_payment_form", 
            "target_domain": "secure-payments.example.com",
            "data_sensitivity": "high"
          }
        }
      ]
    }
  },
  "response": {
    "raw_data": "PlanCapture object",
    "type": "PlanCapture",
    "attributes": {
      "plan_hash": "sha256_dom_validation_abc123def456",
      "captured_at": "2026-01-31T15:30:45.123456Z",
      "plan": {
        "plan_id": "plan_dom_val_987654321",
        "user_id": "security_validator_002",
        "session_id": "session_abc12345", 
        "steps": 1,
        "cryptographic_signature": "sig_dom_xyz789abc123",
        "validation_status": "approved",
        "risk_assessment": "medium",
        "domain_analysis": {
          "target_domain": "secure-payments.example.com",
          "domain_reputation": "trusted",
          "security_rating": "high",
          "compliance_status": "pci_compliant"
        }
      }
    }
  }
}

✅ ARMORIQ SDK RESPONSE [INVOKE_TOOL]  
===================================
{
  "sdk": "ArmorIQ",
  "method": "invoke_tool",
  "success": true,
  "timestamp": "2026-01-31T15:30:46.456789Z",
  "request": {
    "mcp_name": "browser",
    "action": "validate_dom_operation",
    "token_id": "intent_token_dom_xyz123abc789",
    "params": {
      "operation": "modify_payment_form",
      "target_domain": "secure-payments.example.com", 
      "data_sensitivity": "high"
    },
    "user_email": "security_validator_002@validation.armoriq.ai"
  },
  "response": {
    "raw_data": "MCPInvocationResult object",
    "type": "MCPInvocationResult",
    "attributes": {
      "result": {
        "status": "success",
        "dom_validation_result": {
          "approved": true,
          "risk_analysis": {
            "operation_type": "form_modification",
            "security_score": 92,
            "compliance_score": 95,
            "threat_indicators": [],
            "risk_level": "low",
            "recommendation": "approved_with_monitoring"
          },
          "compliance_status": "PCI_DSS_COMPLIANT",
          "cdp_browser_use_ready": true,
          "security_recommendations": [
            "Monitor DOM changes in real-time",
            "Log all form modifications", 
            "Verify SSL certificate validity",
            "Validate payment form integrity"
          ],
          "domain_validation": {
            "domain": "secure-payments.example.com",
            "ssl_valid": true,
            "reputation_score": 98,
            "blacklist_check": "clean",
            "security_headers": "present"
          }
        },
        "execution_metadata": {
          "mcp_server": "browser-security-mcp",
          "tool_version": "2.1.0",
          "execution_id": "exec_dom_789abc123def",
          "validation_time": "0.234s"
        }
      },
      "execution_time": 0.234,
      "status": "completed"
    }
  }
}
EOF

echo ""
echo "🛡️ DOM VALIDATION SECURITY FEATURES:"
echo "===================================="
echo "✅ Real-time DOM operation safety analysis"
echo "✅ Payment form integrity verification" 
echo "✅ Domain reputation and SSL validation"
echo "✅ PCI DSS compliance checking"
echo "✅ Threat indicator detection"
echo "✅ Cryptographic operation signatures"
echo "✅ Comprehensive audit trail logging"