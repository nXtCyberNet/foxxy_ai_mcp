"""
Test script for ArmorIQ Validation API
Demonstrates how to send LLM output for credibility assessment.
"""
import asyncio
import json
import httpx
from typing import Dict, Any


async def test_validation_api():
    """Test the validation API with sample LLM output."""
    
    # Sample LLM output with tool calls
    llm_output = {
        "content": "I'll search for financial records for the specified user.",
        "tool_calls": [
            {
                "name": "mcp_financial123__search_records",
                "args": {
                    "user_id": "john_doe",
                    "record_type": "transactions",
                    "date_range": "2024-01-01 to 2024-12-31"
                },
                "id": "call_1"
            },
            {
                "name": "mcp_financial123__verify_access",
                "args": {
                    "user_id": "john_doe",
                    "requested_by": "admin"
                },
                "id": "call_2"
            }
        ],
        "llm_provider": "openai",
        "llm_model": "gpt-4o",
        "user_prompt": "Show me financial records for user john_doe"
    }
    
    # API endpoint
    base_url = "http://localhost:8000"  # Adjust as needed
    validation_url = f"{base_url}/api/v1/validation/process"
    
    # You'll need a valid JWT token for authentication
    # This is just a placeholder - replace with actual token
    jwt_token = "your-jwt-token-here"
    
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            print("🚀 Sending LLM output for validation...")
            print(f"📋 Tool calls: {len(llm_output['tool_calls'])}")
            
            response = await client.post(
                validation_url,
                json=llm_output,
                headers=headers,
                timeout=60.0
            )
            
            if response.status_code == 200:
                result = response.json()
                
                print("\n✅ Validation completed successfully!")
                print(f"📊 Status: {result['status'].upper()}")
                print(f"🎯 Overall Credibility: {result['credibility_metrics']['overall_credibility']:.1f}%")
                
                print("\n📈 Detailed Metrics:")
                metrics = result['credibility_metrics']
                print(f"  • Plan Integrity: {metrics['plan_integrity_score']:.1f}%")
                print(f"  • Execution Success: {metrics['execution_success_rate']:.1f}%")
                print(f"  • Response Consistency: {metrics['response_consistency_score']:.1f}%")
                print(f"  • Security Compliance: {metrics['security_compliance_score']:.1f}%")
                
                if result.get('plan_id'):
                    print(f"\n📝 Plan ID: {result['plan_id']}")
                
                print("\n🔍 Execution Details:")
                details = result['execution_details']
                print(f"  • Tools executed: {details.get('tool_calls_count', 0)}")
                print(f"  • Plan captured: {details.get('plan_captured', False)}")
                print(f"  • Token generated: {details.get('token_generated', False)}")
                
                if details.get('execution_results'):
                    print("\n🛠️ Tool Results:")
                    for i, tool_result in enumerate(details['execution_results'], 1):
                        status = "✅" if tool_result['status'] == 'success' else "❌"
                        print(f"  {i}. {tool_result['tool_name']}: {status} {tool_result['status']}")
                        if tool_result.get('error'):
                            print(f"     Error: {tool_result['error']}")
                
                print(f"\n🏁 Final Decision: {'PASS' if result['status'] == 'pass' else 'FAIL'}")
                
            else:
                print(f"❌ API call failed: {response.status_code}")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_health_endpoint():
    """Test the health endpoint."""
    base_url = "http://localhost:8000"
    health_url = f"{base_url}/api/v1/validation/health"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(health_url)
            if response.status_code == 200:
                print("✅ Validation API is healthy")
                print(f"Response: {response.json()}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")


def create_sample_curl_command():
    """Generate a sample curl command for testing."""
    
    llm_output = {
        "content": "I'll search for financial records.",
        "tool_calls": [
            {
                "name": "mcp_financial123__search_records",
                "args": {"user_id": "john", "type": "transactions"},
                "id": "call_1"
            }
        ],
        "llm_provider": "openai",
        "llm_model": "gpt-4o",
        "user_prompt": "Show me financial records"
    }
    
    curl_command = f"""
curl -X POST "http://localhost:8000/api/v1/validation/process" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{json.dumps(llm_output, indent=2)}'
    """.strip()
    
    print("📋 Sample curl command:")
    print(curl_command)


if __name__ == "__main__":
    print("🧪 ArmorIQ Validation API Test")
    print("=" * 40)
    
    # Test health endpoint first
    asyncio.run(test_health_endpoint())
    
    print("\n" + "=" * 40)
    
    # Generate sample curl command
    create_sample_curl_command()
    
    print("\n" + "=" * 40)
    print("⚠️  Note: Update JWT token and ensure backend is running")
    print("   Backend: uvicorn app.main:app --reload")
    print("   URL: http://localhost:8000")
    
    # Uncomment to run full test (requires valid JWT token)
    # asyncio.run(test_validation_api())