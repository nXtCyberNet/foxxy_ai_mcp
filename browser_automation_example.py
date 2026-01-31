#!/usr/bin/env python3
"""
Complete Browser Automation Verification Workflow Example

This demonstrates the full workflow:
User → App → LLM → ArmorIQ Verification → Browser_use/CDP_use

The workflow ensures every browser action is cryptographically verified
and authorized before execution, providing complete security and audit trails.
"""

import os
from armoriq_sdk import ArmorIQClient

# Initialize ArmorIQ client
client = ArmorIQClient(
    api_key="ak_live_185bb59a76ab18e8d7e845096460ece1f135eec8f001cfa423ae2fdc6aedce06",
    user_id="automation_user_001",
    agent_id="browser_automation_agent",
    max_retries=3
)

def demonstrate_workflow():
    print("🤖 Browser Automation Security Workflow Demo")
    print("=" * 60)
    
    # STEP 1: User interaction → App → LLM generates plan
    print("📝 STEP 1: USER INTERACTION & LLM PLANNING")
    print("-" * 40)
    
    # Simulate user request
    user_request = "Fill out the loan application form on the banking website"
    llm_instruction = "Navigate to loan form, fill required fields, and submit application"
    
    # Capture the verification plan
    captured = client.capture_plan(
        llm="gpt-4",
        prompt=f"User request: {user_request}. LLM instruction: {llm_instruction}",
        plan={
            "steps": [
                {
                    "action": "verify_browser_action",
                    "mcp": "automation-verification-analytics-mcp",
                    "description": "Verify navigation and form interaction permissions",
                    "metadata": {
                        "user_request": user_request,
                        "llm_instruction": llm_instruction,
                        "priority": "critical"
                    }
                },
                {
                    "action": "validate_dom_operation",
                    "mcp": "automation-verification-analytics-mcp", 
                    "description": "Validate form submission security and compliance",
                    "metadata": {
                        "compliance_required": True,
                        "audit_trail": True
                    }
                },
                {
                    "action": "log_automation_step",
                    "mcp": "automation-verification-analytics-mcp",
                    "description": "Create complete audit trail for regulatory compliance",
                    "metadata": {
                        "retention_period": "7_years",
                        "gdpr_compliant": True,
                        "is_expired": False
                    },
                    "is_expired": False
                }
            ]
        },
        metadata={
            "purpose": "secure_form_automation",
            "workflow": "user_app_llm_armoriq_browser",
            "version": "2.0.0",
            "tags": ["banking", "forms", "security", "compliance"]
        }
    )
    
    print(f"✓ Plan captured with {len(captured.plan['steps'])} verification steps")
    
    # Get cryptographic intent token
    intent_token = client.get_intent_token(captured)
    print(f"✓ Intent token generated: {intent_token[:20]}...")
    
    # STEP 2: ArmorIQ Verification - Check IAM rules
    print("\n🔒 STEP 2: ARMORIQ IAM VERIFICATION")
    print("-" * 40)
    
    try:
        verification_result = client.invoke(
            mcp="automation-verification-analytics-mcp",
            action="verify_browser_action",
            intent_token=intent_token,
            params={
                "action_type": "navigate",
                "target_element": {
                    "selector": "https://secure-bank.com/loan-application",
                    "element_type": "page",
                    "url_context": "https://secure-bank.com"
                },
                "user_context": {
                    "user_id": "automation_user_001",
                    "session_id": "sess_bank_20260130",
                    "permissions": [
                        "browser.navigate",
                        "browser.type", 
                        "browser.click",
                        "banking.loan_application"
                    ]
                },
                "llm_instruction": llm_instruction,
                "iam_rules": [
                    {
                        "rule_id": "banking_nav_001",
                        "action": "navigate",
                        "resource": "secure-bank.com",
                        "condition": "allow if user has banking.loan_application permission"
                    },
                    {
                        "rule_id": "form_interaction_002",
                        "action": "type",
                        "resource": "loan-application",
                        "condition": "allow with audit trail required"
                    }
                ]
            }
        )
        
        if verification_result["success"]:
            auth_data = verification_result['data']['verification_result']
            
            if auth_data['authorized']:
                print(f"✅ AUTHORIZATION: GRANTED")
                print(f"   Risk Score: {auth_data['risk_score']}/100")
                print(f"   Permissions Checked: {auth_data['checked_permissions']}")
                print(f"   IAM Rules Applied: {auth_data['applied_rules']}")
                
                # STEP 3: DOM Operation Risk Assessment
                print("\n🛡️  STEP 3: DOM OPERATION VALIDATION") 
                print("-" * 40)
                
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
                                "rule_id": "form_submit_003",
                                "action": "submit",
                                "resource": "loan-application",
                                "condition": "allow with mandatory audit trail"
                            }
                        ],
                        "risk_assessment": {
                            "security_score": 85,
                            "compliance_required": True,
                            "audit_trail": True
                        }
                    }
                )
                
                if dom_validation["success"]:
                    validation_data = dom_validation['data']['validation_result']
                    risk_data = validation_data['risk_analysis']
                    
                    print(f"✅ DOM VALIDATION: {'APPROVED' if validation_data['approved'] else 'DENIED'}")
                    print(f"   Risk Level: {risk_data['risk_level'].upper()}")
                    print(f"   Total Risk Score: {risk_data['total_risk_score']}")
                    print(f"   Recommendation: {risk_data['recommendation'].upper()}")
                    print(f"   Browser_use/CDP Ready: {dom_validation['data']['cdp_browser_use_ready']}")
                    
                    if dom_validation['data']['cdp_browser_use_ready']:
                        # STEP 4: Audit Logging
                        print("\n📋 STEP 4: AUDIT TRAIL LOGGING")
                        print("-" * 40)
                        
                        audit_result = client.invoke(
                            mcp="automation-verification-analytics-mcp", 
                            action="log_automation_step",
                            intent_token=intent_token,
                            params={
                                "step_id": "bank_form_automation_001",
                                "user_interaction": user_request,
                                "llm_response": llm_instruction,
                                "browser_action": "navigate_and_submit_loan_form",
                                "verification_result": {
                                    "authorized": True,
                                    "risk_score": auth_data['risk_score'],
                                    "compliance_status": "approved"
                                },
                                "timestamp": "2026-01-30T14:30:00Z"
                            }
                        )
                        
                        if audit_result["success"]:
                            audit_data = audit_result['data']
                            print(f"✅ AUDIT LOG: Created")
                            print(f"   Step ID: {audit_data['log_entry']['step_id']}")
                            print(f"   Workflow: {audit_data['log_entry']['workflow_stage']}")
                            print(f"   Retention: {audit_data['audit_trail']['retention_period']}")
                            
                            # STEP 5: Execute Browser Automation
                            print("\n🚀 STEP 5: BROWSER_USE/CDP EXECUTION")
                            print("-" * 40)
                            print("✅ ALL VERIFICATIONS PASSED")
                            print("🤖 Proceeding with browser automation...")
                            print("   → browser_use.navigate('https://secure-bank.com/loan-application')")
                            print("   → browser_use.fill_form(loan_data)")
                            print("   → browser_use.click('#submit-button')")
                            print("   → Success: Form submitted securely")
                            
                            return True
                        else:
                            print(f"❌ AUDIT LOGGING FAILED: {audit_result['error']}")
                    else:
                        print("❌ DOM VALIDATION FAILED - Browser automation blocked")
                else:
                    print(f"❌ DOM VALIDATION ERROR: {dom_validation['error']}")
            else:
                print(f"❌ AUTHORIZATION: DENIED")
                print(f"   Reason: {auth_data['authorization_status']}")
                print(f"   Risk Score: {auth_data['risk_score']}/100")
                print("   🚫 Browser automation blocked for security")
        else:
            print(f"❌ VERIFICATION ERROR: {verification_result['error']}")
            
    except Exception as e:
        print(f"❌ WORKFLOW FAILED: {e}")
        return False
    
    return False

def show_workflow_summary():
    print("\n📊 WORKFLOW SUMMARY")
    print("=" * 60)
    print("1. User Request → App receives natural language instruction")
    print("2. LLM Planning → Generates structured automation plan") 
    print("3. ArmorIQ Capture → Creates cryptographic intent token")
    print("4. IAM Verification → Checks permissions and rules")
    print("5. Risk Assessment → Evaluates DOM operation safety")
    print("6. Audit Logging → Creates compliance trail")
    print("7. Browser Execution → Executes browser_use/CDP only if authorized")
    print("\n🔒 Security Benefits:")
    print("   • Zero unauthorized browser actions")
    print("   • Complete audit trails for compliance") 
    print("   • Dynamic risk assessment")
    print("   • Cryptographic verification")
    print("   • Regulatory-ready logging")

if __name__ == "__main__":
    success = demonstrate_workflow()
    show_workflow_summary()
    
    if success:
        print(f"\n✅ Demo completed successfully!")
    else:
        print(f"\n❌ Demo encountered errors - check logs")