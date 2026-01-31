"""
Test client for ArmorIQ Validation Service.
"""
import asyncio
import json
import httpx
from typing import Dict, Any


async def test_validation_service():
    """Test the validation service with various scenarios."""
    
    base_url = "http://localhost:8080"
    
    # Test scenarios
    scenarios = [
        {
            "name": "Financial Records Query",
            "request": {
                "content": "I'll search for financial records for the specified user.",
                "tool_calls": [
                    {
                        "name": "financial__search_records",
                        "args": {
                            "user_id": "john_doe",
                            "record_type": "transactions",
                            "date_range": "2024-01-01,2024-12-31"
                        }
                    },
                    {
                        "name": "financial__verify_access",
                        "args": {"user_id": "john_doe", "requester": "admin"}
                    }
                ],
                "llm_provider": "openai",
                "llm_model": "gpt-4o",
                "user_prompt": "Show me financial records for john_doe"
            }
        },
        {
            "name": "Browser Automation IAM Verification",
            "request": {
                "content": "I'll verify if this browser automation action is authorized within IAM rules.",
                "tool_calls": [
                    {
                        "name": "browser__verify_browser_action",
                        "args": {
                            "action_type": "click",
                            "target_element": "submit_button",
                            "selector": "#submit-form-btn",
                            "element_type": "button",
                            "url_context": "https://example.com/secure-form",
                            "user_context": "authenticated_user_session",
                            "user_id": "user_12345",
                            "session_id": "browser_session_abc123",
                            "permissions": ["form_submit", "data_entry"],
                            "llm_instruction": "Click the submit button to process the user form"
                        }
                    }
                ],
                "llm_provider": "openai",
                "llm_model": "gpt-4o",
                "user_prompt": "Verify browser action authorization for form submission"
            }
        },
        {
            "name": "Browser Automation",
            "request": {
                "content": "I'll use browser automation to extract data from the website.",
                "tool_calls": [
                    {
                        "name": "browser__navigate",
                        "args": {"url": "https://example.com", "wait_for": "load"}
                    },
                    {
                        "name": "browser__extract_data",
                        "args": {"selector": ".data-table", "format": "json"}
                    }
                ],
                "llm_provider": "anthropic",
                "llm_model": "claude-3-sonnet",
                "user_prompt": "Extract data from the website table"
            }
        },
        {
            "name": "DOM Operation Validation",
            "request": {
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
            }
        },
        {
            "name": "Automation Step Logging",
            "request": {
                "content": "I will log this browser automation step for audit trail and compliance tracking.",
                "tool_calls": [
                    {
                        "name": "automation__log_automation_step",
                        "args": {
                            "step_id": "step_001_login",
                            "user_interaction": "click_login_button",
                            "llm_response": "Successfully identified and clicked the login button",
                            "browser_action": "element_click"
                        }
                    }
                ],
                "llm_provider": "anthropic",
                "llm_model": "claude-3-sonnet",
                "user_prompt": "Log automation step for compliance audit",
                "user_id": "audit_bot_003"
            }
        },
        {
            "name": "Performance Analysis",
            "request": {
                "content": "I'll analyze browser automation performance metrics and success rates for optimization.",
                "tool_calls": [
                    {
                        "name": "analytics__analyze_automation_performance",
                        "args": {
                            "execution_times": [1250, 980, 1100, 890, 1300],
                            "success_rates": [0.95, 0.88, 0.92, 0.96, 0.89],
                            "metrics": ["avg_response_time", "success_percentage", "error_rate"]
                        }
                    }
                ],
                "llm_provider": "openai",
                "llm_model": "gpt-4o",
                "user_prompt": "Analyze automation performance for optimization insights",
                "user_id": "performance_analyst_004"
            }
        },
        {
            "name": "No Tools Needed",
            "request": {
                "content": "The weather is nice today. No tools are needed for this response.",
                "tool_calls": [],
                "llm_provider": "openai",
                "llm_model": "gpt-4o",
                "user_prompt": "What's the weather like?"
            }
        }
    ]
    
    async with httpx.AsyncClient() as client:
        print("🧪 Testing ArmorIQ Validation Service")
        print("=" * 50)
        
        # Health check
        try:
            health_response = await client.get(f"{base_url}/health")
            if health_response.status_code == 200:
                health_data = health_response.json()
                print(f"✅ Service Health: {health_data['status']}")
                print(f"🔗 ArmorIQ Connected: {health_data['armoriq_connected']}")
            else:
                print(f"❌ Health check failed: {health_response.status_code}")
                return
        except Exception as e:
            print(f"❌ Cannot connect to service: {e}")
            return
        
        print("\n🚀 Running Test Scenarios:")
        print("-" * 30)
        
        # Test each scenario
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n🧪 Test {i}: {scenario['name']}")
            
            try:
                response = await client.post(
                    f"{base_url}/validate",
                    json=scenario['request'],
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    print(f"   Status: {result['status'].upper()}")
                    print(f"   User: {result.get('user_id', 'N/A')}")
                    print(f"   Credibility: {result['credibility_score']:.1f}%")
                    print(f"   Assessment: {result.get('credibility_assessment', 'N/A')}")
                    print(f"   Tools Executed: {result['tools_executed']}")
                    print(f"   Plan Captured: {result['plan_captured']}")
                    print(f"   Processing Time: {result.get('processing_time_ms', 0):.0f}ms")
                    print(f"   Session ID: {result.get('session_id', 'N/A')}")
                    
                    metrics = result['metrics']
                    print(f"   Metrics:")
                    print(f"     • Plan Integrity: {metrics['plan_integrity']:.1f}%")
                    print(f"     • Execution Success: {metrics['execution_success']:.1f}%")
                    print(f"     • Response Consistency: {metrics['response_consistency']:.1f}%")
                    print(f"     • Security Compliance: {metrics['security_compliance']:.1f}%")
                    
                    if result.get('error_message'):
                        print(f"   Error: {result['error_message']}")
                    
                    # Show decision
                    if result['status'] == 'pass':
                        print("   🟢 DECISION: APPROVED FOR EXECUTION")
                    elif result['status'] == 'fail':
                        print("   🔴 DECISION: REJECTED (Low Credibility)")
                    else:
                        print("   🟡 DECISION: ERROR IN VALIDATION")
                        
                else:
                    print(f"   ❌ Request failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    
            except Exception as e:
                print(f"   ❌ Test failed: {e}")
        
        # Get service metrics
        print("\n📊 Service Metrics:")
        print("-" * 20)
        
        try:
            metrics_response = await client.get(f"{base_url}/metrics")
            if metrics_response.status_code == 200:
                metrics = metrics_response.json()
                print(f"Total Validations: {metrics['total_validations']}")
                print(f"Successful: {metrics['successful_validations']}")
                print(f"Failed: {metrics['failed_validations']}")
                print(f"Average Credibility: {metrics['average_credibility']:.1f}%")
                print(f"Average Processing Time: {metrics['average_processing_time_ms']:.0f}ms")
                print(f"Service Uptime: {metrics['uptime_seconds']:.0f}s")
        except Exception as e:
            print(f"Failed to get metrics: {e}")


def generate_curl_examples():
    """Generate curl command examples."""
    
    examples = [
        {
            "name": "Simple validation",
            "curl": '''curl -X POST "http://localhost:8001/validate" \\
  -H "Content-Type: application/json" \\
  -d '{
    "content": "I will search for user data",
    "tool_calls": [
      {
        "name": "database__query_users",
        "args": {"filter": "active=true"}
      }
    ],
    "llm_provider": "openai",
    "llm_model": "gpt-4o",
    "user_prompt": "Get all active users",
    "user_id": "client_user_123"
  }\'
'''
        },
        {
            "name": "Custom threshold",
            "curl": '''curl -X POST "http://localhost:8001/validate?credibility_threshold=80" \\
  -H "Content-Type: application/json" \\
  -d '{
    "content": "Processing financial data...",
    "tool_calls": [
      {
        "name": "financial__calculate_risk",
        "args": {"portfolio_id": "portfolio_123"}
      }
    ],
    "llm_provider": "anthropic",
    "llm_model": "claude-3-opus",
    "user_prompt": "Calculate risk for portfolio",
    "user_id": "financial_analyst_456"
  }\'
'''
        },
        {
            "name": "Browser IAM verification",
            "curl": '''curl -X POST "http://localhost:8001/validate" \\
  -H "Content-Type: application/json" \\
  -d '{
    "content": "Verifying browser automation authorization",
    "tool_calls": [
      {
        "name": "verify_browser_action",
        "args": {
          "action_type": "click",
          "target_element": "payment_button",
          "selector": "#pay-now-btn",
          "element_type": "button",
          "url_context": "https://secure-payments.example.com",
          "user_context": "premium_user_session",
          "user_id": "premium_user_789",
          "session_id": "secure_session_xyz456",
          "permissions": ["payment_processing", "secure_actions"],
          "llm_instruction": "Click payment button to process transaction"
        }
      }
    ],
    "llm_provider": "openai",
    "llm_model": "gpt-4o",
    "user_prompt": "Verify payment button click authorization",
    "user_id": "security_agent_001"
  }\'
'''
        }
    ]
    
    print("\n📋 Curl Command Examples:")
    print("=" * 30)
    
    for example in examples:
        print(f"\n{example['name']}:")
        print(example['curl'])


if __name__ == "__main__":
    print("🔧 ArmorIQ Validation Service Test Client")
    print("\n⚠️  Ensure the validation service is running:")
    print("   cd armoriq-validation-service")
    print("   uvicorn app.main:app --reload --port 8001")
    
    print("\n📚 API Documentation: http://localhost:8001/docs")
    
    generate_curl_examples()
    
    print("\n" + "=" * 50)
    
    # Run tests
    try:
        asyncio.run(test_validation_service())
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")