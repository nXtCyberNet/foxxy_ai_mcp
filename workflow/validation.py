"""
Validation API - Processes LLM output through ArmorIQ workflow and returns credibility assessment.
"""
import json
import logging
from typing import Dict, List, Optional, Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUserId, DbSession
from app.config import APIRoutes
from app.services.armoriq_service import ArmorIQService, AgentPlan, PlanStep
from app.services.mcp_manager import get_mcp_manager
from app.services.llm_router import LLMRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix=f"{APIRoutes.PREFIX}/validation", tags=["Validation"])


class ToolCall(BaseModel):
    """Tool call from LLM output."""
    name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    id: Optional[str] = None


class LLMOutput(BaseModel):
    """LLM output containing potential tool calls."""
    content: str
    tool_calls: List[ToolCall] = Field(default_factory=list)
    llm_provider: str
    llm_model: str
    user_prompt: str


class CredibilityMetrics(BaseModel):
    """Credibility assessment metrics."""
    plan_integrity_score: float = Field(ge=0, le=100, description="Plan structural integrity (0-100)")
    execution_success_rate: float = Field(ge=0, le=100, description="Tool execution success rate (0-100)")
    response_consistency_score: float = Field(ge=0, le=100, description="Response consistency (0-100)")
    security_compliance_score: float = Field(ge=0, le=100, description="Security compliance (0-100)")
    overall_credibility: float = Field(ge=0, le=100, description="Overall credibility percentage (0-100)")


class ValidationResult(BaseModel):
    """Validation result with pass/fail decision."""
    status: str = Field(description="pass or fail")
    credibility_metrics: CredibilityMetrics
    plan_id: Optional[str] = None
    execution_details: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class CredibilityAnalyzer:
    """Analyzes execution results and calculates credibility metrics."""
    
    def __init__(self, threshold: float = 75.0):
        self.threshold = threshold  # Minimum credibility for pass
    
    def analyze_plan_integrity(self, plan: AgentPlan, captured_plan: Any) -> float:
        """Analyze plan structural integrity."""
        try:
            score = 100.0
            
            # Check if plan was properly captured
            if not captured_plan or not hasattr(captured_plan, 'plan_hash'):
                score -= 30
            
            # Check if all steps have required fields
            for step in plan.steps:
                if not step.action or not step.mcp:
                    score -= 20
                if not step.params:
                    score -= 5
            
            return max(0, score)
        except Exception as e:
            logger.error(f"Plan integrity analysis failed: {e}")
            return 0.0
    
    def analyze_execution_success(self, execution_results: List[Dict]) -> float:
        """Analyze tool execution success rate."""
        if not execution_results:
            return 0.0
        
        successful_executions = sum(1 for result in execution_results 
                                  if result.get("status") == "success")
        
        return (successful_executions / len(execution_results)) * 100
    
    def analyze_response_consistency(self, execution_results: List[Dict]) -> float:
        """Analyze consistency of responses."""
        try:
            score = 100.0
            
            for result in execution_results:
                response = result.get("response", {})
                
                # Check for empty or error responses
                if not response or "error" in str(response).lower():
                    score -= 25
                
                # Check for data consistency
                if isinstance(response, dict):
                    if response.get("data") and not response.get("error"):
                        score += 0  # Good response
                    elif response.get("error"):
                        score -= 15
            
            return max(0, score)
        except Exception as e:
            logger.error(f"Response consistency analysis failed: {e}")
            return 50.0  # Default moderate score
    
    def analyze_security_compliance(self, token_used: bool, plan_captured: bool) -> float:
        """Analyze security compliance."""
        score = 0.0
        
        if plan_captured:
            score += 50  # Plan was properly captured
        
        if token_used:
            score += 50  # Token was properly used for execution
        
        return score
    
    def calculate_overall_credibility(self, metrics: Dict[str, float]) -> float:
        """Calculate weighted overall credibility score."""
        weights = {
            "plan_integrity_score": 0.2,
            "execution_success_rate": 0.4,
            "response_consistency_score": 0.3,
            "security_compliance_score": 0.1
        }
        
        overall = sum(metrics[key] * weights[key] for key in weights if key in metrics)
        return min(100, max(0, overall))


def parse_tool_name(tool_name: str) -> tuple[str, str]:
    """Parse MCP ID and tool name from prefixed tool name."""
    if "__" in tool_name:
        parts = tool_name.split("__", 1)
        mcp_id = parts[0].replace("mcp_", "").replace("_", "-")
        actual_name = parts[1]
        return mcp_id, actual_name
    return "default-mcp", tool_name


@router.post("/process", response_model=ValidationResult)
async def process_llm_output(
    llm_output: LLMOutput,
    user_id: CurrentUserId,
    db: DbSession,
    credibility_threshold: float = 75.0
):
    """
    Process LLM output through complete ArmorIQ workflow and return credibility assessment.
    
    Args:
        llm_output: LLM output containing tool calls
        user_id: Current authenticated user ID
        credibility_threshold: Minimum credibility percentage for pass (default: 75%)
    
    Returns:
        ValidationResult with pass/fail status and detailed metrics
    """
    conversation_id = str(uuid4())  # Generate temporary conversation ID
    
    try:
        # Initialize services
        armoriq = ArmorIQService(user_id=user_id, agent_id="validation_agent")
        mcp_manager = get_mcp_manager()
        analyzer = CredibilityAnalyzer(threshold=credibility_threshold)
        
        execution_results = []
        plan_captured = False
        token_used = False
        plan_id = None
        
        # Process tool calls if any
        if llm_output.tool_calls:
            logger.info(f"Processing {len(llm_output.tool_calls)} tool calls")
            
            # Convert to ArmorIQ plan format
            plan = AgentPlan(
                steps=[
                    PlanStep(
                        action=tc.name,
                        mcp=parse_tool_name(tc.name)[0],
                        description=f"Execute {tc.name}",
                        params=tc.args,
                    )
                    for tc in llm_output.tool_calls
                ],
                reasoning="Validation workflow execution plan"
            )
            
            # Phase 1: Capture plan with ArmorIQ
            try:
                captured_plan = armoriq.capture_plan(
                    llm=f"{llm_output.llm_provider}/{llm_output.llm_model}",
                    prompt=llm_output.user_prompt,
                    plan=plan,
                )
                plan_captured = True
                
                # Save plan to database
                plan_id = await armoriq.save_intent_plan(
                    db=db,
                    conversation_id=conversation_id,
                    captured_plan=captured_plan,
                )
                
                logger.info(f"Plan captured successfully: {plan_id}")
                
            except Exception as e:
                logger.error(f"Plan capture failed: {e}")
                captured_plan = None
            
            # Phase 2: Get intent token
            token = None
            if captured_plan:
                try:
                    token = armoriq.get_intent_token(captured_plan)
                    token_used = True
                    logger.info(f"Intent token generated: {token.token_id}")
                except Exception as e:
                    logger.error(f"Token generation failed: {e}")
            
            # Phase 3: Execute tools through ArmorIQ
            if token:
                for tc in llm_output.tool_calls:
                    tool_result = {
                        "tool_name": tc.name,
                        "status": "failed",
                        "response": None,
                        "error": None
                    }
                    
                    try:
                        # Parse tool name and resolve MCP
                        mcp_short_id, actual_tool_name = parse_tool_name(tc.name)
                        mcp_name = mcp_manager.get_mcp_name_by_short_id(mcp_short_id)
                        
                        if not mcp_name:
                            tool_result["error"] = f"MCP not found for ID: {mcp_short_id}"
                        else:
                            # Execute through ArmorIQ
                            result = armoriq.invoke(
                                mcp_name=mcp_name,
                                action=actual_tool_name,
                                token=token,
                                params=tc.args,
                            )
                            
                            tool_result["status"] = "success"
                            tool_result["response"] = result.result if hasattr(result, 'result') else result
                            
                            logger.info(f"Tool {tc.name} executed successfully")
                            
                    except Exception as e:
                        tool_result["error"] = str(e)
                        logger.error(f"Tool execution failed for {tc.name}: {e}")
                    
                    execution_results.append(tool_result)
                
                # Update plan status
                if plan_id:
                    all_success = all(r["status"] == "success" for r in execution_results)
                    await armoriq.update_plan_status(
                        db=db,
                        plan_id=plan_id,
                        status="completed" if all_success else "failed",
                    )
        
        # Calculate credibility metrics
        plan_integrity = analyzer.analyze_plan_integrity(
            plan if llm_output.tool_calls else AgentPlan(steps=[]), 
            captured_plan if plan_captured else None
        )
        
        execution_success = analyzer.analyze_execution_success(execution_results)
        response_consistency = analyzer.analyze_response_consistency(execution_results)
        security_compliance = analyzer.analyze_security_compliance(token_used, plan_captured)
        
        metrics_dict = {
            "plan_integrity_score": plan_integrity,
            "execution_success_rate": execution_success,
            "response_consistency_score": response_consistency,
            "security_compliance_score": security_compliance,
        }
        
        overall_credibility = analyzer.calculate_overall_credibility(metrics_dict)
        
        credibility_metrics = CredibilityMetrics(
            plan_integrity_score=plan_integrity,
            execution_success_rate=execution_success,
            response_consistency_score=response_consistency,
            security_compliance_score=security_compliance,
            overall_credibility=overall_credibility
        )
        
        # Determine pass/fail
        status = "pass" if overall_credibility >= credibility_threshold else "fail"
        
        # Compile execution details
        execution_details = {
            "tool_calls_count": len(llm_output.tool_calls),
            "plan_captured": plan_captured,
            "token_generated": token_used,
            "execution_results": execution_results,
            "conversation_id": conversation_id,
        }
        
        logger.info(f"Validation completed: {status} (credibility: {overall_credibility:.1f}%)")
        
        return ValidationResult(
            status=status,
            credibility_metrics=credibility_metrics,
            plan_id=plan_id,
            execution_details=execution_details,
        )
        
    except Exception as e:
        logger.error(f"Validation process failed: {e}")
        import traceback
        traceback.print_exc()
        
        return ValidationResult(
            status="fail",
            credibility_metrics=CredibilityMetrics(
                plan_integrity_score=0,
                execution_success_rate=0,
                response_consistency_score=0,
                security_compliance_score=0,
                overall_credibility=0
            ),
            error_message=str(e),
        )


@router.get("/health")
async def validation_health():
    """Health check for validation service."""
    return {"status": "ok", "service": "ArmorIQ Validation API"}