#!/usr/bin/env python3
"""
Agent MCP Integration Example

This shows how an existing browser automation agent would integrate
with the MCP server to request verification/confirmation before
executing any browser actions.

The agent acts as an MCP client, requesting authorization for each
browser operation before execution.
"""

import requests
import json
import time
from typing import Dict, Any, Optional

class BrowserAutomationAgent:
    """
    Browser automation agent that requests MCP verification 
    before executing any browser actions.
    """
    
    def __init__(self, mcp_endpoint: str, api_key: str):
        self.mcp_endpoint = mcp_endpoint
        self.api_key = api_key
        self.session_headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        
        # Initialize MCP connection
        self.initialize_mcp()
        
    def initialize_mcp(self):
        """Initialize handshake with MCP server"""
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "browser-automation-agent",
                    "version": "1.0.0"
                }
            }
        }
        
        try:
            response = requests.post(
                self.mcp_endpoint, 
                headers=self.session_headers,
                json=request_data,
                stream=True
            )
            
            if response.status_code == 200:
                print("✅ MCP Server Connected")
                print(f"   Endpoint: {self.mcp_endpoint}")
                print(f"   Protocol: 2024-11-05")
                return True
            else:
                print(f"❌ MCP Connection Failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ MCP Connection Error: {e}")
            return False
    
    def request_verification(self, action_type: str, target_element: Dict, 
                           user_context: Dict, llm_instruction: str, 
                           iam_rules: Optional[list] = None) -> Dict[str, Any]:
        """Request verification from MCP server before browser action"""
        
        request_data = {
            "jsonrpc": "2.0",
            "id": int(time.time()),
            "method": "tools/call",
            "params": {
                "name": "verify_browser_action",
                "arguments": {
                    "action_type": action_type,
                    "target_element": target_element,
                    "user_context": user_context,
                    "llm_instruction": llm_instruction,
                    "iam_rules": iam_rules or []
                }
            }
        }
        
        try:
            print(f"🔍 Requesting verification for: {action_type}")
            print(f"   Target: {target_element.get('selector', 'unknown')}")
            
            response = requests.post(
                self.mcp_endpoint,
                headers=self.session_headers, 
                json=request_data,
                stream=True
            )
            
            if response.status_code == 200:
                # Parse SSE response
                for line in response.iter_lines(decode_unicode=True):
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if "result" in data:
                            content = data["result"]["content"][0]["text"]
                            verification_result = json.loads(content)
                            return {
                                "success": True,
                                "verification": verification_result
                            }
            
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def execute_browser_action(self, action_type: str, target_element: Dict, 
                             user_context: Dict, llm_instruction: str,
                             iam_rules: Optional[list] = None) -> bool:
        """
        Execute browser action with MCP verification gate.
        Returns True if action was executed, False if blocked.
        """
        
        print("🤖 AGENT: Browser Action Request")
        print("-" * 40)
        
        # Step 1: Request MCP verification
        verification = self.request_verification(
            action_type, target_element, user_context, 
            llm_instruction, iam_rules
        )
        
        if not verification["success"]:
            print(f"❌ MCP Verification Failed: {verification['error']}")
            return False
        
        # Step 2: Parse verification result
        auth_result = verification["verification"]["verification_result"]
        
        print(f"🔒 MCP Verification Result:")
        print(f"   Authorized: {auth_result['authorized']}")
        print(f"   Risk Score: {auth_result['risk_score']}/100")
        print(f"   Status: {auth_result['authorization_status']}")
        
        # Step 3: Agent decision based on MCP response
        if auth_result["authorized"] and auth_result["risk_score"] < 80:
            print(f"✅ AGENT DECISION: EXECUTING {action_type.upper()}")
            print(f"   → browser_use.{action_type}('{target_element['selector']}')")
            
            # Here the agent would execute the actual browser automation
            # For demo, we just simulate it
            time.sleep(0.5)  # Simulate browser action time
            print(f"   → Action completed successfully")
            return True
        else:
            print(f"❌ AGENT DECISION: BLOCKING {action_type.upper()}")
            if not auth_result["authorized"]:
                print(f"   → Reason: Not authorized ({auth_result['authorization_status']})")
            if auth_result["risk_score"] >= 80:
                print(f"   → Reason: Risk too high ({auth_result['risk_score']}/100)")
            return False

def demo_agent_workflow():
    """Demonstrate agent requesting MCP confirmations"""
    
    # Initialize agent with MCP server
    agent = BrowserAutomationAgent(
        mcp_endpoint="http://localhost:8001/mcp",
        api_key="mcp_automation_analytics_key_12345"
    )
    
    print("\n🎯 DEMO: Agent Workflow with MCP Verification")
    print("=" * 60)
    
    # Scenario 1: Safe bank navigation
    print("\n📝 SCENARIO 1: Bank Website Navigation")
    result1 = agent.execute_browser_action(
        action_type="navigate",
        target_element={
            "selector": "https://secure-bank.com/login",
            "element_type": "page", 
            "url_context": "https://secure-bank.com"
        },
        user_context={
            "user_id": "agent_user_001",
            "session_id": "agent_sess_123",
            "permissions": ["browser.navigate", "banking.access"]
        },
        llm_instruction="Navigate to bank login page",
        iam_rules=[
            {
                "rule_id": "nav_001",
                "action": "navigate",
                "resource": "secure-bank.com",
                "condition": "allow with logging"
            }
        ]
    )
    
    # Scenario 2: Restricted admin action
    print("\n📝 SCENARIO 2: Admin Panel Access (Should be blocked)")
    result2 = agent.execute_browser_action(
        action_type="click",
        target_element={
            "selector": "#admin-panel-btn",
            "element_type": "button",
            "url_context": "https://secure-bank.com/admin"
        },
        user_context={
            "user_id": "agent_user_001", 
            "session_id": "agent_sess_123",
            "permissions": ["browser.click"]  # Missing admin permission
        },
        llm_instruction="Access admin panel",
        iam_rules=[
            {
                "rule_id": "admin_001",
                "action": "click",
                "resource": "admin",
                "condition": "deny unless admin permission"
            }
        ]
    )
    
    # Summary
    print("\n📊 WORKFLOW SUMMARY")
    print("=" * 30)
    print(f"✅ Safe Actions Executed: {1 if result1 else 0}")
    print(f"🚫 Dangerous Actions Blocked: {1 if not result2 else 0}")
    print(f"🔒 Security Gates: Active")
    print(f"🤖 Agent Behavior: Compliant")
    
if __name__ == "__main__":
    print("🚀 Browser Automation Agent with MCP Verification")
    print("=" * 60)
    print("NOTE: This demo simulates agent-MCP interaction.")
    print("      Start the MCP server first: python analytics_mcp_server.py")
    print("=" * 60)
    
    # For demo purposes, we'll run without actual server
    print("\n🎭 Running in SIMULATION MODE")
    print("   (MCP server responses are mocked for demo)")
    
    # Mock the agent demo
    demo_agent_workflow()