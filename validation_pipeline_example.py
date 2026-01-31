"""
ArmorIQ Validation API Integration Example
Shows how to integrate the validation API into an LLM pipeline.
"""
import asyncio
import json
import httpx
from typing import Dict, List, Any, Optional


class ArmorIQValidator:
    """Client for ArmorIQ Validation API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", jwt_token: str = None):
        self.base_url = base_url.rstrip('/')
        self.jwt_token = jwt_token
        self.validation_url = f"{self.base_url}/api/v1/validation/process"
        self.health_url = f"{self.base_url}/api/v1/validation/health"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        return headers
    
    async def validate_llm_output(
        self,
        content: str,
        tool_calls: List[Dict],
        llm_provider: str,
        llm_model: str,
        user_prompt: str,
        credibility_threshold: float = 75.0
    ) -> Dict[str, Any]:
        """
        Validate LLM output through ArmorIQ workflow.
        
        Args:
            content: LLM text response
            tool_calls: List of tool calls from LLM
            llm_provider: LLM provider name (e.g., "openai")
            llm_model: Model name (e.g., "gpt-4o")
            user_prompt: Original user prompt
            credibility_threshold: Minimum credibility for pass
            
        Returns:
            Validation result with status and metrics
        """
        payload = {
            "content": content,
            "tool_calls": tool_calls,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "user_prompt": user_prompt
        }
        
        params = {"credibility_threshold": credibility_threshold}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.validation_url,
                json=payload,
                headers=self._get_headers(),
                params=params,
                timeout=60.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Validation API error: {response.status_code} - {response.text}")
    
    async def health_check(self) -> bool:
        """Check if validation API is healthy."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.health_url, timeout=10.0)
                return response.status_code == 200
        except:
            return False


class LLMPipeline:
    """Example LLM pipeline with ArmorIQ validation."""
    
    def __init__(self, validator: ArmorIQValidator, credibility_threshold: float = 80.0):
        self.validator = validator
        self.credibility_threshold = credibility_threshold
    
    def simulate_llm_response(self, user_prompt: str) -> Dict[str, Any]:
        """Simulate LLM generating response with tool calls."""
        
        # Simulate different types of LLM responses
        if "financial" in user_prompt.lower():
            return {
                "content": "I'll search the financial database for the requested records.",
                "tool_calls": [
                    {
                        "name": "mcp_financial__search_records",
                        "args": {
                            "query": "user:john",
                            "date_range": "2024-01-01,2024-12-31",
                            "record_type": "transactions"
                        },
                        "id": "call_fin_1"
                    },
                    {
                        "name": "mcp_financial__verify_permissions", 
                        "args": {"user_id": "john", "requester": "admin"},
                        "id": "call_fin_2"
                    }
                ],
                "llm_provider": "openai",
                "llm_model": "gpt-4o"
            }
        elif "browser" in user_prompt.lower():
            return {
                "content": "I'll use browser automation to navigate to the website.",
                "tool_calls": [
                    {
                        "name": "mcp_browser__navigate",
                        "args": {"url": "https://example.com", "wait_for": "load"},
                        "id": "call_browser_1"
                    },
                    {
                        "name": "mcp_browser__extract_data",
                        "args": {"selector": ".data-table", "format": "json"},
                        "id": "call_browser_2"
                    }
                ],
                "llm_provider": "anthropic", 
                "llm_model": "claude-3-sonnet"
            }
        else:
            return {
                "content": "I'll help you with that request.",
                "tool_calls": [],
                "llm_provider": "openai",
                "llm_model": "gpt-4o"
            }
    
    async def process_request(self, user_prompt: str) -> Dict[str, Any]:
        """
        Process user request with validation.
        
        Returns:
            Processing result with validation status
        """
        print(f"📝 Processing request: {user_prompt}")
        
        # Step 1: Generate LLM response (simulated)
        llm_response = self.simulate_llm_response(user_prompt)
        print(f"🤖 LLM generated {len(llm_response['tool_calls'])} tool calls")
        
        # Step 2: Validate through ArmorIQ if tool calls exist
        validation_result = None
        if llm_response['tool_calls']:
            print("🔍 Validating through ArmorIQ...")
            
            try:
                validation_result = await self.validator.validate_llm_output(
                    content=llm_response['content'],
                    tool_calls=llm_response['tool_calls'],
                    llm_provider=llm_response['llm_provider'],
                    llm_model=llm_response['llm_model'],
                    user_prompt=user_prompt,
                    credibility_threshold=self.credibility_threshold
                )
                
                credibility = validation_result['credibility_metrics']['overall_credibility']
                status = validation_result['status']
                
                print(f"🎯 Validation: {status.upper()} (credibility: {credibility:.1f}%)")
                
            except Exception as e:
                print(f"❌ Validation failed: {e}")
                validation_result = {"status": "error", "error": str(e)}
        else:
            print("ℹ️  No tool calls to validate")
        
        # Step 3: Make decision based on validation
        if validation_result:
            if validation_result['status'] == 'pass':
                decision = "APPROVED"
                print("✅ Request approved for execution")
            elif validation_result['status'] == 'fail':
                decision = "REJECTED"
                credibility = validation_result['credibility_metrics']['overall_credibility']
                print(f"❌ Request rejected (credibility: {credibility:.1f}% < {self.credibility_threshold}%)")
            else:
                decision = "ERROR"
                print(f"⚠️  Validation error: {validation_result.get('error', 'Unknown error')}")
        else:
            decision = "APPROVED"  # No tools to validate
            print("✅ Request approved (no tool execution)")
        
        return {
            "user_prompt": user_prompt,
            "llm_response": llm_response,
            "validation_result": validation_result,
            "decision": decision
        }


async def demo_validation_pipeline():
    """Demonstrate the complete validation pipeline."""
    
    print("🚀 ArmorIQ Validation Pipeline Demo")
    print("=" * 50)
    
    # Initialize validator (replace with actual JWT token)
    validator = ArmorIQValidator(
        base_url="http://localhost:8000",
        jwt_token="your-jwt-token-here"  # Replace with actual token
    )
    
    # Check API health
    print("🏥 Checking API health...")
    is_healthy = await validator.health_check()
    if not is_healthy:
        print("❌ Validation API is not available")
        return
    print("✅ Validation API is healthy")
    
    # Initialize pipeline
    pipeline = LLMPipeline(validator, credibility_threshold=75.0)
    
    # Test scenarios
    test_prompts = [
        "Show me financial records for user john from last year",
        "Use browser automation to scrape data from website",
        "What's the weather like today?",  # No tools needed
    ]
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n🧪 Test {i}: {prompt}")
        print("-" * 30)
        
        try:
            result = await pipeline.process_request(prompt)
            
            print(f"\n📊 Summary:")
            print(f"   Decision: {result['decision']}")
            
            if result['validation_result'] and 'credibility_metrics' in result['validation_result']:
                metrics = result['validation_result']['credibility_metrics']
                print(f"   Credibility: {metrics['overall_credibility']:.1f}%")
                print(f"   Plan Integrity: {metrics['plan_integrity_score']:.1f}%")
                print(f"   Execution Success: {metrics['execution_success_rate']:.1f}%")
                print(f"   Response Consistency: {metrics['response_consistency_score']:.1f}%")
                print(f"   Security Compliance: {metrics['security_compliance_score']:.1f}%")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
        
        print()


def print_setup_instructions():
    """Print setup instructions."""
    
    print("""
🛠️  Setup Instructions:

1. Start the backend server:
   cd armoriq-agent/backend
   uvicorn app.main:app --reload

2. Get a JWT token:
   - Register/login through /api/v1/auth/register or /api/v1/auth/login
   - Use the returned access_token

3. Update the JWT token in the code:
   validator = ArmorIQValidator(jwt_token="your-actual-token")

4. Ensure MCPs are configured:
   - Add MCP servers through /api/v1/mcp/add
   - Verify they're connected through /api/v1/mcp/status

5. Configure ArmorIQ:
   - Set ARMORIQ_API_KEY in environment variables
   - Ensure ArmorIQ proxy/backend URLs are correct

📚 API Documentation: http://localhost:8000/docs
    """)


if __name__ == "__main__":
    print_setup_instructions()
    
    # Uncomment to run demo (requires proper setup)
    # asyncio.run(demo_validation_pipeline())