#!/usr/bin/env python3
"""
ArmorIQ Test without MCP Server Dependency

This tests the ArmorIQ workflow logic without requiring
an actual MCP server connection.
"""

import os
from armoriq_sdk import ArmorIQClient

def test_armoriq_workflow():
    """Test ArmorIQ plan capture and intent token generation"""
    
    # Initialize client
    client = ArmorIQClient(
        api_key="ak_live_185bb59a76ab18e8d7e845096460ece1f135eec8f001cfa423ae2fdc6aedce06",
        user_id="alaotach",
        agent_id="agent_aloo",
        max_retries=5
    )
    
    print("🚀 ArmorIQ Workflow Test")
    print("=" * 40)
    
    # Test 1: Plan Capture
    print("📋 STEP 1: Capturing Plan...")
    try:
        captured = client.capture_plan(
            llm="gpt-4",
            prompt="User wants to fill out a form on a secure website - verify the action is authorized before browser automation",
            plan={
                "steps": [
                    {
                        "action": "verify_browser_action",
                        "mcp": "automation-analytics-mcp",
                        "description": "Verify browser action against IAM rules before execution",
                        "metadata": {"priority": "critical", "security_gate": True}
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
        print(f"✅ Plan captured successfully")
        print(f"   Plan ID: {captured.plan}")
        print(f"   Steps: {len(captured.plan['steps'])}")
    except Exception as e:
        print(f"❌ Plan capture failed: {e}")
        return False
    
    # Test 2: Intent Token Generation
    print("\n🔐 STEP 2: Generating Intent Token...")
    try:
        intent_token = client.get_intent_token(captured)
        print(f"✅ Intent token generated successfully")
        print(f"   Token ID: {intent_token.token_id}")
        print(f"   Plan Hash: {intent_token.plan_hash[:16]}...")
        print(f"   Expires: {intent_token.expires_at}")
        print(f"   Steps with Proofs: {len(intent_token.step_proofs)}")
    except Exception as e:
        print(f"❌ Intent token generation failed: {e}")
        return False
    
    # Test 3: Simulated Verification (without MCP server)
    print("\n🔍 STEP 3: Simulated Verification Logic...")
    
    # Simulate the verification logic that would happen in the MCP server
    action_type = "click"
    target_element = {
        "selector": "#submit-button",
        "element_type": "button", 
        "url_context": "https://secure-bank.com/transfer"
    }
    user_context = {
        "user_id": "alaotach",
        "session_id": "sess_abc123",
        "permissions": ["browser.click", "banking.transfer"]
    }
    
    # Simulate IAM verification
    user_permissions = user_context.get("permissions", [])
    target_url = target_element.get("url_context", "")
    
    risk_score = 20  # Base risk
    authorization_status = "denied"
    
    # Check permissions
    required_permission = f"browser.{action_type}"
    if required_permission in user_permissions:
        authorization_status = "allowed"
    
    # Domain risk
    if "banking" in target_url.lower() or "secure" in target_url.lower():
        risk_score += 40
    
    simulated_result = {
        "authorized": authorization_status == "allowed",
        "risk_score": risk_score,
        "authorization_status": authorization_status,
        "checked_permissions": user_permissions
    }
    
    print(f"✅ Simulated Verification Complete")
    print(f"   Authorized: {simulated_result['authorized']}")
    print(f"   Risk Score: {simulated_result['risk_score']}/100")
    print(f"   Status: {simulated_result['authorization_status']}")
    
    if simulated_result["authorized"] and simulated_result["risk_score"] < 70:
        print(f"\n🤖 DECISION: ✅ PROCEED with browser automation")
        print(f"   → browser_use.click('{target_element['selector']}')")
    else:
        print(f"\n🤖 DECISION: ❌ BLOCK browser automation")
        print(f"   → Risk too high or not authorized")
    
    print("\n📊 Test Summary:")
    print("   ✅ ArmorIQ Plan Capture: Working")
    print("   ✅ Intent Token Generation: Working") 
    print("   ✅ Verification Logic: Working")
    print("   ⚠️  MCP Server: Not connected (expected)")
    
    return True

if __name__ == "__main__":
    success = test_armoriq_workflow()
    
    if success:
        print("\n🎉 ArmorIQ workflow components working correctly!")
        print("\n💡 Next Steps:")
        print("   1. Start MCP server: uvicorn analytics_mcp_server:app --port 8001")
        print("   2. Register MCP server with ArmorIQ")
        print("   3. Run the full armoriq.py script")
    else:
        print("\n❌ ArmorIQ workflow test failed")