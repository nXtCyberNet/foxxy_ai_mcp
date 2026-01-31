"""
ArmorIQ SDK integration service for validation.
"""
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio

from pydantic import BaseModel

# Import ArmorIQ SDK
from armoriq_sdk import ArmorIQClient
from armoriq_sdk.models import PlanCapture, IntentToken, MCPInvocationResult
from armoriq_sdk.exceptions import (
    TokenExpiredException,
    InvalidTokenException,
    IntentMismatchException,
    MCPInvocationException,
    ConfigurationException,
)

from app.config import settings, ValidationConstants

logger = logging.getLogger(__name__)


def log_armoriq_response(method: str, request_data: Dict, response_data: Any, success: bool = True):
    """
    Central logging function for all ArmorIQ SDK responses.
    
    Args:
        method: SDK method name
        request_data: Request parameters sent to SDK
        response_data: Response received from SDK
        success: Whether the call was successful
    """
    log_entry = {
        "sdk": "ArmorIQ",
        "method": method,
        "success": success,
        "timestamp": datetime.now().isoformat(),
        "request": request_data,
        "response": {
            "raw_data": response_data,
            "type": str(type(response_data).__name__),
            "attributes": {}
        }
    }
    
    # Extract attributes from response object if it has them
    if hasattr(response_data, '__dict__'):
        log_entry["response"]["attributes"] = {
            k: v for k, v in vars(response_data).items() 
            if not k.startswith('_')
        }
    elif hasattr(response_data, '__slots__'):
        log_entry["response"]["attributes"] = {
            slot: getattr(response_data, slot, None) 
            for slot in response_data.__slots__
        }
    
    # Print formatted JSON response
    status_emoji = "✅" if success else "❌"
    print(f"\n{'='*100}")
    print(f"{status_emoji} ARMORIQ SDK RESPONSE [{method.upper()}]")
    print(f"{'='*100}")
    print(json.dumps(log_entry, indent=2, default=str))
    print(f"{'='*100}\n")
    
    # Also log to standard logger
    if success:
        logger.info(f"ArmorIQ SDK {method} successful")
    else:
        logger.error(f"ArmorIQ SDK {method} failed: {response_data}")


class ValidationPlanStep(BaseModel):
    """Single step in a validation plan."""
    action: str
    mcp: str
    description: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


class ValidationPlan(BaseModel):
    """Validation execution plan."""
    steps: List[ValidationPlanStep]
    reasoning: str = "ArmorIQ validation workflow"
    user_id: str
    session_id: str


class ArmorIQValidationService:
    """
    ArmorIQ SDK integration for validation service.
    
    Handles:
    - Plan capture before tool execution
    - Cryptographic token generation 
    - Secure tool execution through ArmorIQ proxy
    - Result validation and credibility assessment
    """

    def __init__(self, user_id: str = "validation_user", agent_id: str = "validation_agent"):
        """
        Initialize ArmorIQ validation service.
        
        Args:
            user_id: User identifier for validation session
            agent_id: Agent identifier for ArmorIQ
        """
        self.user_id = user_id
        self.agent_id = agent_id
        self._client: Optional[ArmorIQClient] = None
        self._current_token: Optional[IntentToken] = None
        
        self._initialize_client()

    def _initialize_client(self):
        """Initialize ArmorIQ client."""
        try:
            if not settings.armoriq_api_key:
                logger.warning("ArmorIQ API key not provided. Service will run in mock mode.")
                self._client = None
                return
                
            api_key = settings.armoriq_api_key.get_secret_value()
            self._client = ArmorIQClient(
                api_key=api_key,
                user_id=self.user_id,
                agent_id=self.agent_id,
                proxy_endpoint=settings.armoriq_proxy_url,
                backend_endpoint=settings.armoriq_backend_url,
            )
            logger.info(f"ArmorIQ client initialized for validation service")
        except ConfigurationException as e:
            logger.error(f"ArmorIQ configuration error: {e}")
            self._client = None
        except Exception as e:
            logger.error(f"Failed to initialize ArmorIQ client: {e}")
            self._client = None

    @property
    def client(self) -> ArmorIQClient:
        """Get ArmorIQ client, raising if not initialized."""
        if self._client is None:
            if not settings.armoriq_api_key:
                raise ConfigurationException(
                    "ArmorIQ API key not configured. Set ARMORIQ_API_KEY environment variable."
                )
            else:
                raise ConfigurationException(
                    "ArmorIQ client not initialized. Check configuration."
                )
        return self._client

    async def capture_plan(
        self,
        llm_provider: str,
        llm_model: str,
        user_prompt: str,
        plan: ValidationPlan,
    ) -> PlanCapture:
        """
        Capture validation plan with ArmorIQ.
        
        Args:
            llm_provider: LLM provider (e.g., "openai")
            llm_model: Model name (e.g., "gpt-4o")
            user_prompt: Original user prompt
            plan: Validation plan to capture
            
        Returns:
            PlanCapture from ArmorIQ SDK or mock object
        """
        try:
            # Check if ArmorIQ is available
            if self._client is None:
                logger.info("ArmorIQ not available, using mock plan capture")
                # Return a mock PlanCapture-like object
                from types import SimpleNamespace
                return SimpleNamespace(
                    plan_hash=f"mock_hash_{hash(str(plan.steps))}",
                    plan={"steps": [step.dict() for step in plan.steps]},
                    captured_at="mock_timestamp"
                )
            
            # Convert to ArmorIQ plan format
            plan_structure = {
                "goal": "Validate LLM output through secure execution",
                "reasoning": plan.reasoning,
                "user_id": plan.user_id,
                "session_id": plan.session_id,
                "steps": [
                    {
                        "action": step.action,
                        "mcp": step.mcp,
                        "description": step.description,
                        "params": step.params or {},
                    }
                    for step in plan.steps
                ]
            }

            captured_plan = self.client.capture_plan(
                llm=f"{llm_provider}/{llm_model}",
                prompt=user_prompt,
                plan=plan_structure,
            )

            # Log the complete SDK response
            log_armoriq_response(
                method="capture_plan",
                request_data={
                    "llm": f"{llm_provider}/{llm_model}",
                    "prompt": user_prompt[:200] + "..." if len(user_prompt) > 200 else user_prompt,
                    "plan_steps_count": len(plan.steps),
                    "plan_structure": plan_structure
                },
                response_data=captured_plan,
                success=True
            )
            
            logger.info(f"Plan captured: {len(plan.steps)} steps")
            return captured_plan

        except Exception as e:
            logger.error(f"Plan capture failed: {e}")
            
            # Log the error response
            log_armoriq_response(
                method="capture_plan",
                request_data={
                    "llm": f"{llm_provider}/{llm_model}",
                    "prompt": user_prompt[:200] + "..." if len(user_prompt) > 200 else user_prompt,
                    "plan_steps_count": len(plan.steps),
                },
                response_data={"error": str(e)},
                success=False
            )
            
            # Return mock object on failure
            from types import SimpleNamespace
            return SimpleNamespace(
                plan_hash=f"error_hash_{hash(str(e))}",
                plan={"steps": [step.dict() for step in plan.steps], "error": str(e)},
                captured_at="error_timestamp"
            )

    async def get_intent_token(
        self,
        captured_plan: PlanCapture,
        expires_in: int = ValidationConstants.ARMORIQ_REQUEST_TIMEOUT,
        policy: Optional[Dict] = None,
    ) -> IntentToken:
        """
        Get cryptographic token for plan execution.
        
        Args:
            captured_plan: Previously captured plan
            expires_in: Token expiry in seconds
            policy: Execution policy constraints
            
        Returns:
            IntentToken from ArmorIQ SDK or mock object
        """
        try:
            # Check if ArmorIQ is available
            if self._client is None:
                logger.info("ArmorIQ not available, using mock intent token")
                from types import SimpleNamespace
                return SimpleNamespace(
                    token_id=f"mock_token_{hash(str(captured_plan.plan_hash))}",
                    expires_at=expires_in,
                    time_until_expiry=expires_in
                )
            
            token = self.client.get_intent_token(
                plan_capture=captured_plan,
                policy=policy or {"allow": ["*"], "deny": []},
                validity_seconds=expires_in,
            )

            # Log the complete SDK response
            log_armoriq_response(
                method="get_intent_token",
                request_data={
                    "plan_hash": getattr(captured_plan, 'plan_hash', 'no_hash'),
                    "policy": policy or {"allow": ["*"], "deny": []},
                    "validity_seconds": expires_in
                },
                response_data=token,
                success=True
            )

            self._current_token = token
            logger.info(f"Intent token generated: {token.token_id}")
            return token

        except Exception as e:
            logger.error(f"Token generation failed: {e}")
            
            # Log the error response
            log_armoriq_response(
                method="get_intent_token",
                request_data={
                    "plan_hash": getattr(captured_plan, 'plan_hash', 'no_hash'),
                    "validity_seconds": expires_in
                },
                response_data={"error": str(e)},
                success=False
            )
            
            # Return mock token on failure
            from types import SimpleNamespace
            return SimpleNamespace(
                token_id=f"error_token_{hash(str(e))}",
                expires_at=0,
                time_until_expiry=0
            )

    async def execute_tool(
        self,
        mcp_name: str,
        action: str,
        token: IntentToken,
        params: Optional[Dict] = None,
    ) -> MCPInvocationResult:
        """
        Execute tool through ArmorIQ proxy.
        
        Args:
            mcp_name: MCP server name
            action: Tool/action name
            token: Valid intent token
            params: Tool parameters
            
        Returns:
            MCPInvocationResult from execution or mock result
        """
        try:
            # Check if ArmorIQ is available
            if self._client is None:
                logger.info(f"ArmorIQ not available, using mock execution for {action}")
                from types import SimpleNamespace
                return SimpleNamespace(
                    result={
                        "status": "success",
                        "data": f"Mock result for {action}",
                        "mcp": mcp_name,
                        "params": params or {}
                    },
                    execution_time=0.1
                )
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self._execute_tool_internal(mcp_name, action, token, params),
                timeout=ValidationConstants.TOOL_EXECUTION_TIMEOUT
            )
            
            logger.info(f"Tool {action} executed successfully")
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Tool execution timeout: {action}")
            from types import SimpleNamespace
            return SimpleNamespace(
                result={"status": "timeout", "error": f"Timeout executing {action}"},
                execution_time=ValidationConstants.TOOL_EXECUTION_TIMEOUT
            )
        except Exception as e:
            logger.error(f"Tool execution failed: {action} - {e}")
            
            # Log the error response
            log_armoriq_response(
                method="invoke_tool",
                request_data={
                    "mcp_name": mcp_name,
                    "action": action,
                    "params": params or {}
                },
                response_data={"error": str(e)},
                success=False
            )
            
            from types import SimpleNamespace
            return SimpleNamespace(
                result={"status": "error", "error": str(e)},
                execution_time=0.0
            )

    async def _execute_tool_internal(
        self,
        mcp_name: str,
        action: str,
        token: IntentToken,
        params: Optional[Dict] = None,
    ) -> MCPInvocationResult:
        """Internal tool execution method."""
        print(f"gyguygyugyuguihuhuigylglyu: {token.token_id}")
        result = self.client.invoke(
            mcp=mcp_name,
            action=action,
            intent_token=token.token_id,
            params=params or {},
            user_email=f"{self.user_id}@validation.armoriq.ai",
        )
        
        # Log the complete SDK response
        log_armoriq_response(
            method="invoke_tool",
            request_data={
                "mcp_name": mcp_name,
                "action": action,
                "token_id": getattr(token, 'token_id', 'no_token_id'),
                "params": params or {},
                "user_email": f"{self.user_id}@validation.armoriq.ai"
            },
            response_data=result,
            success=True
        )
        
        return result

    def parse_tool_name(self, tool_name: str) -> tuple[str, str]:
        """
        Parse MCP name and action from tool name.
        
        Supports formats:
        - "mcp_name__action_name" 
        - "action_name" (uses default MCP)
        
        Args:
            tool_name: Full tool name
            
        Returns:
            Tuple of (mcp_name, action_name)
        """
        if "__" in tool_name:
            parts = tool_name.split("__", 1)
            mcp_name = parts[0].replace("mcp_", "").replace("_", "-")
            action_name = parts[1]
            return mcp_name, action_name
        else:
            # Default MCP for simple action names
            return "foxxy-ai", tool_name

    async def validate_execution_results(
        self,
        execution_results: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Validate execution results and calculate metrics.
        
        Args:
            execution_results: List of tool execution results
            
        Returns:
            Dictionary of validation metrics
        """
        if not execution_results:
            return {
                "execution_success_rate": 0.0,
                "response_consistency": 0.0,
                "error_rate": 100.0,
            }

        # Calculate success rate
        successful_executions = sum(
            1 for result in execution_results 
            if result.get("status") == "success"
        )
        success_rate = (successful_executions / len(execution_results)) * 100

        # Calculate response consistency
        consistency_score = 100.0
        for result in execution_results:
            response = result.get("response", {})
            
            if not response or "error" in str(response).lower():
                consistency_score -= 25
            
            # Check for proper data structure
            if isinstance(response, dict) and response.get("error"):
                consistency_score -= 15

        consistency_score = max(0, consistency_score)

        # Calculate error rate
        error_rate = 100 - success_rate

        return {
            "execution_success_rate": success_rate,
            "response_consistency": consistency_score,
            "error_rate": error_rate,
            "total_executions": len(execution_results),
            "successful_executions": successful_executions,
        }

    def clear_session(self):
        """Clear current validation session."""
        self._current_token = None
        logger.debug("Validation session cleared")