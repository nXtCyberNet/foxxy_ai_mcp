"""
Core validation service implementation.
"""
import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from uuid import uuid4

from app.models import ValidationRequest, ValidationResponse, CredibilityMetrics, ExecutionDetail
from app.armoriq_service import ArmorIQValidationService, ValidationPlan, ValidationPlanStep
from app.credibility import CredibilityAnalyzer
from app.config import settings, ValidationConstants

logger = logging.getLogger(__name__)


class ValidationService:
    """
    Core validation service that orchestrates the validation workflow.
    
    Workflow:
    1. Parse and validate input
    2. Create ArmorIQ execution plan  
    3. Capture plan with ArmorIQ
    4. Generate intent token
    5. Execute tools securely
    6. Analyze results and calculate credibility
    7. Return pass/fail decision
    """

    def __init__(self):
        """Initialize validation service."""
        self.start_time = time.time()
        self.metrics = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "total_processing_time": 0.0,
            "credibility_scores": [],
        }

    def _update_metrics(self, success: bool, processing_time: float, credibility: float):
        """Update service metrics."""
        self.metrics["total_validations"] += 1
        self.metrics["total_processing_time"] += processing_time
        self.metrics["credibility_scores"].append(credibility)
        
        if success:
            self.metrics["successful_validations"] += 1
        else:
            self.metrics["failed_validations"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get current service metrics."""
        uptime = time.time() - self.start_time
        total_validations = self.metrics["total_validations"]
        
        avg_credibility = 0.0
        if self.metrics["credibility_scores"]:
            avg_credibility = sum(self.metrics["credibility_scores"]) / len(self.metrics["credibility_scores"])
        
        avg_processing_time = 0.0
        if total_validations > 0:
            avg_processing_time = self.metrics["total_processing_time"] / total_validations

        return {
            "total_validations": total_validations,
            "successful_validations": self.metrics["successful_validations"],
            "failed_validations": self.metrics["failed_validations"],
            "average_credibility": avg_credibility,
            "average_processing_time_ms": avg_processing_time * 1000,
            "uptime_seconds": uptime,
        }

    async def validate_llm_output(self, request: ValidationRequest) -> ValidationResponse:
        """
        Validate LLM output through complete ArmorIQ workflow.
        
        Args:
            request: Validation request with LLM output
            
        Returns:
            Validation response with credibility assessment
        """
        start_time = time.time()
        session_id = request.session_id or f"validation_{uuid4().hex[:8]}"
        
        try:
            logger.info(f"Starting validation session {session_id}")
            
            # Initialize services
            threshold = request.credibility_threshold or settings.validation_threshold
            armoriq_service = ArmorIQValidationService(
                user_id=request.user_id,
                agent_id=f"validation_{session_id}"
            )
            analyzer = CredibilityAnalyzer(threshold=threshold)
            
            # Initialize response data
            execution_details = []
            plan_captured = False
            token_generated = False
            plan_id = None
            
            # Process tool calls if any exist
            if request.tool_calls:
                logger.info(f"Processing {len(request.tool_calls)} tool calls")
                
                # Create validation plan
                plan_steps = []
                for tool_call in request.tool_calls:
                    mcp_name, action_name = armoriq_service.parse_tool_name(tool_call.name)
                    
                    step = ValidationPlanStep(
                        action=action_name,
                        mcp=mcp_name,
                        description=f"Validate execution of {tool_call.name}",
                        params=tool_call.args,
                    )
                    plan_steps.append(step)
                
                validation_plan = ValidationPlan(
                    steps=plan_steps,
                    reasoning="ArmorIQ validation workflow for credibility assessment",
                    user_id=request.user_id,
                    session_id=session_id,
                )
                
                # Phase 1: Capture plan with ArmorIQ
                try:
                    captured_plan = await armoriq_service.capture_plan(
                        llm_provider=request.llm_provider,
                        llm_model=request.llm_model,
                        user_prompt=request.user_prompt,
                        plan=validation_plan,
                    )
                    plan_captured = True
                    plan_id = getattr(captured_plan, 'plan_hash', session_id)
                    logger.info("Plan captured successfully")
                    
                except Exception as e:
                    logger.error(f"Plan capture failed: {e}")
                    captured_plan = None
                
                # Phase 2: Generate intent token
                token = None
                if captured_plan:
                    try:
                        token = await armoriq_service.get_intent_token(
                            captured_plan=captured_plan,
                            expires_in=settings.execution_timeout,
                        )
                        token_generated = True
                        logger.info("Intent token generated")
                        
                    except Exception as e:
                        logger.error(f"Token generation failed: {e}")
                
                # Phase 3: Execute tools securely
                if token:
                    for tool_call in request.tool_calls:
                        execution_detail = ExecutionDetail(
                            tool_name=tool_call.name,
                            status="failed",
                            response=None,
                            error=None,
                            execution_time_ms=None,
                        )
                        
                        try:
                            exec_start_time = time.time()
                            
                            # Parse tool name and execute
                            mcp_name, action_name = armoriq_service.parse_tool_name(tool_call.name)
                            
                            result = await armoriq_service.execute_tool(
                                mcp_name=mcp_name,
                                action=action_name,
                                token=token,
                                params=tool_call.args,
                            )
                            
                            exec_time = (time.time() - exec_start_time) * 1000
                            
                            # Update execution detail
                            execution_detail.status = "success"
                            execution_detail.response = getattr(result, 'result', result)
                            execution_detail.execution_time_ms = exec_time
                            
                            logger.info(f"Tool {tool_call.name} executed successfully")
                            
                        except Exception as e:
                            exec_time = (time.time() - exec_start_time) * 1000
                            execution_detail.error = str(e)
                            execution_detail.execution_time_ms = exec_time
                            logger.error(f"Tool execution failed: {tool_call.name} - {e}")
                        
                        execution_details.append(execution_detail.dict())
            
            # Phase 4: Analyze credibility
            plan_steps = [step.dict() for step in validation_plan.steps] if request.tool_calls else []
            
            metrics = analyzer.analyze_full_credibility(
                plan_steps=plan_steps,
                execution_results=execution_details,
                plan_captured=plan_captured,
                token_used=token_generated,
                plan_hash=plan_id,
                token_valid=True,
            )
            
            # Determine final status
            status = analyzer.determine_pass_fail(metrics.overall_credibility)
            credibility_assessment = analyzer.get_credibility_assessment(metrics.overall_credibility)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Update service metrics
            self._update_metrics(
                success=(status == "pass"),
                processing_time=processing_time,
                credibility=metrics.overall_credibility
            )
            
            # Build response
            response = ValidationResponse(
                status=status,
                credibility_score=metrics.overall_credibility,
                metrics=CredibilityMetrics(**metrics.to_dict()),
                user_id=request.user_id,
                execution_details={
                    "tools": execution_details,
                    "plan_steps": plan_steps,
                },
                tools_executed=len(execution_details),
                plan_captured=plan_captured,
                token_generated=token_generated,
                plan_id=plan_id,
                session_id=session_id,
                processing_time_ms=processing_time * 1000,
                credibility_assessment=credibility_assessment,
            )
            
            logger.info(
                f"Validation completed: {status} "
                f"(credibility: {metrics.overall_credibility:.1f}%, "
                f"time: {processing_time:.2f}s)"
            )
            
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            # Update metrics for error
            self._update_metrics(
                success=False,
                processing_time=processing_time,
                credibility=0.0
            )
            
            logger.error(f"Validation failed: {e}")
            
            # Return error response
            return ValidationResponse(
                status="error",
                credibility_score=0.0,
                metrics=CredibilityMetrics(
                    plan_integrity=0.0,
                    execution_success=0.0,
                    response_consistency=0.0,
                    security_compliance=0.0,
                    overall_credibility=0.0,
                ),
                user_id=request.user_id,
                execution_details={"error": str(e)},
                tools_executed=0,
                plan_captured=False,
                token_generated=False,
                session_id=session_id,
                error_message=str(e),
                processing_time_ms=processing_time * 1000,
                credibility_assessment="error",
            )

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check of the validation service.
        
        Returns:
            Health status information
        """
        try:
            # Check ArmorIQ configuration and connection
            armoriq_connected = False
            if settings.has_armoriq_config:
                try:
                    test_service = ArmorIQValidationService(
                        user_id="health_check_user",
                        agent_id="health_check_agent"
                    )
                    armoriq_connected = test_service._client is not None
                except Exception as e:
                    logger.warning(f"ArmorIQ health check failed: {e}")
                    armoriq_connected = False
            else:
                logger.info("ArmorIQ not configured, running in mock mode")
            
            return {
                "status": "healthy",
                "service": settings.service_name,
                "version": settings.service_version,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "armoriq_connected": armoriq_connected,
                "armoriq_configured": settings.has_armoriq_config,
                "mode": "production" if armoriq_connected else "development/mock",
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "service": settings.service_name,
                "version": settings.service_version,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "armoriq_connected": False,
                "armoriq_configured": settings.has_armoriq_config,
                "mode": "error",
                "error": str(e),
            }