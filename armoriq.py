import os
from armoriq_sdk import ArmorIQClient

# Custom configuration
client = ArmorIQClient(
    api_key="ak_live_185bb59a76ab18e8d7e845096460ece1f135eec8f001cfa423ae2fdc6aedce06",
    user_id="alaotach",
    agent_id=f"agent_aloo",
    max_retries=5
)

# Step 1: Capture the plan for browser automation verification
captured = client.capture_plan(
    llm="gpt-4",
    prompt="User wants to fill out a form on a secure website - verify the action is authorized before browser automation",
    plan={
        "steps": [
            {
                "action": "verify_browser_action",
                "mcp": "automation-verification-analytics-mcp",
                "description": "Verify browser action against IAM rules before execution",
                "metadata": {"priority": "critical", "security_gate": True}
            },
            {
                "action": "validate_dom_operation", 
                "mcp": "automation-verification-analytics-mcp",
                "description": "Validate DOM operation risk and compliance",
                "metadata": {"priority": "high", "compliance_required": True}
            },
            {
                "action": "log_automation_step",
                "mcp": "automation-verification-analytics-mcp", 
                "description": "Log the complete workflow for audit trail",
                "metadata": {"audit_trail": True}
            }
        ]
    },
    metadata={
        "purpose": "browser_automation_security",
        "workflow": "user_app_llm_armoriq_browser",
        "version": "2.0.0",
        "tags": ["security", "iam", "browser_automation", "compliance"]
    }
)
print(f"Plan captured: {captured}")

# Step 2: Get intent token
intent_token = client.get_intent_token(captured)
print(f"Intent token obtained: {intent_token}")

# Step 3: Invoke the action with cryptographic verification
try:
    result = client.invoke(
        mcp="automation-verification-analytics-mcp",
        action="verify_browser_action",
        intent_token=intent_token,
        params={
            "action_type": "click",
            "target_element": {
                "selector": "#submit-button",
                "element_type": "button", 
                "url_context": "https://secure-bank.com/transfer"
            },
            "user_context": {
                "user_id": "alaotach",
                "session_id": "sess_abc123",
                "permissions": ["browser.click", "banking.transfer"]
            },
            "llm_instruction": "Click the submit button to complete the bank transfer",
            "iam_rules": [
                {
                    "rule_id": "banking_001",
                    "action": "click",
                    "resource": "secure-bank.com",
                    "condition": "allow if user has banking.transfer permission"
                }
            ]
        }
    )
    
    if result["success"]:
        verification_result = result['data']
        print(f"Verification Result: {verification_result}")
        
        if verification_result.get("verification_result", {}).get("authorized"):
            print("✅ ACTION AUTHORIZED - Proceeding to browser_use/CDP")
            print(f"Risk Score: {verification_result['verification_result']['risk_score']}")
            print(f"Next Step: {verification_result['next_step']}")
        else:
            print("❌ ACTION DENIED - Browser automation blocked")
            print(f"Reason: {verification_result['verification_result']['authorization_status']}")
            
        print(f"Execution time: {result['execution_time_ms']}ms")
    else:
        print(f"Error: {result['error']}")
        
except Exception as e:
    print(f"Invocation failed: {e}")

# Step 4: If authorized, demonstrate DOM operation validation
if result.get("success") and result['data'].get("verification_result", {}).get("authorized"):
    print("\n" + "="*50)
    print("🔍 STEP 2: DOM OPERATION VALIDATION")
    print("="*50)
    
    try:
        dom_validation = client.invoke(
            mcp="automation-verification-analytics-mcp",
            action="validate_dom_operation", 
            intent_token=intent_token,
            params={
                "operation": "submit",
                "target_domain": "secure-bank.com",
                "data_sensitivity": "confidential",
                "iam_rules": [
                    {
                        "rule_id": "banking_002",
                        "action": "submit",
                        "resource": "secure-bank.com/transfer",
                        "condition": "allow with audit trail"
                    }
                ],
                "risk_assessment": {
                    "security_score": 75,
                    "compliance_required": True,
                    "audit_trail": True
                }
            }
        )
        
        if dom_validation["success"]:
            dom_result = dom_validation['data']
            print(f"DOM Validation: {dom_result['validation_result']['approved']}")
            print(f"Risk Level: {dom_result['validation_result']['risk_analysis']['risk_level']}")
            print(f"Recommendation: {dom_result['validation_result']['risk_analysis']['recommendation']}")
            print(f"CDP/Browser_use Ready: {dom_result['cdp_browser_use_ready']}")
            
        print(f"DOM Validation time: {dom_validation['execution_time_ms']}ms")
        
    except Exception as e:
        print(f"DOM validation failed: {e}")