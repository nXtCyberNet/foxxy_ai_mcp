"""
Credibility analysis and scoring engine.
"""
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import statistics

from app.config import ValidationConstants

logger = logging.getLogger(__name__)


@dataclass
class CredibilityMetrics:
    """Container for credibility metrics."""
    plan_integrity_score: float
    execution_success_rate: float
    response_consistency_score: float
    security_compliance_score: float
    overall_credibility: float
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "plan_integrity": self.plan_integrity_score,
            "execution_success": self.execution_success_rate,
            "response_consistency": self.response_consistency_score,
            "security_compliance": self.security_compliance_score,
            "overall_credibility": self.overall_credibility,
        }


class CredibilityAnalyzer:
    """
    Analyzes execution results and calculates credibility metrics.
    
    Uses multiple weighted factors:
    - Plan Integrity (20%): Quality of execution plan
    - Execution Success (40%): Tool execution success rate  
    - Response Consistency (30%): Quality of responses
    - Security Compliance (10%): ArmorIQ security usage
    """

    def __init__(self, threshold: float = 75.0):
        """
        Initialize credibility analyzer.
        
        Args:
            threshold: Minimum credibility score for pass (0-100)
        """
        self.threshold = max(0.0, min(100.0, threshold))

    def analyze_plan_integrity(
        self, 
        plan_steps: List[Dict], 
        captured: bool,
        plan_hash: Optional[str] = None
    ) -> float:
        """
        Analyze execution plan integrity.
        
        Args:
            plan_steps: List of plan steps
            captured: Whether plan was captured by ArmorIQ
            plan_hash: ArmorIQ plan hash if available
            
        Returns:
            Plan integrity score (0-100)
        """
        try:
            score = 0.0
            
            # Base score for having a plan
            if plan_steps:
                score += 40.0
            
            # Score for ArmorIQ capture
            if captured:
                score += 30.0
            
            # Score for plan hash (cryptographic verification)
            if plan_hash:
                score += 20.0
            
            # Analyze individual steps
            if plan_steps:
                step_score = 0.0
                for step in plan_steps:
                    # Check required fields
                    if step.get("action"):
                        step_score += 2.5
                    if step.get("mcp"):
                        step_score += 2.5
                    if step.get("params"):
                        step_score += 1.0
                
                # Cap step score at 10 points
                score += min(10.0, step_score)
            
            return min(100.0, score)
            
        except Exception as e:
            logger.error(f"Plan integrity analysis failed: {e}")
            return 0.0

    def analyze_execution_success(self, execution_results: List[Dict]) -> float:
        """
        Analyze tool execution success rate.
        
        Args:
            execution_results: List of tool execution results
            
        Returns:
            Execution success rate (0-100)
        """
        if not execution_results:
            return 0.0
        
        try:
            successful_count = 0
            for result in execution_results:
                status = result.get("status", "").lower()
                if status == "success" or status == "completed":
                    successful_count += 1
                elif result.get("response") and not result.get("error"):
                    # Consider as success if has response without error
                    successful_count += 1
            
            success_rate = (successful_count / len(execution_results)) * 100
            return min(100.0, success_rate)
            
        except Exception as e:
            logger.error(f"Execution success analysis failed: {e}")
            return 0.0

    def analyze_response_consistency(self, execution_results: List[Dict]) -> float:
        """
        Analyze response quality and consistency.
        
        Args:
            execution_results: List of tool execution results
            
        Returns:
            Response consistency score (0-100)
        """
        if not execution_results:
            return 0.0
        
        try:
            total_score = 0.0
            
            for result in execution_results:
                response_score = 100.0
                response = result.get("response", {})
                error = result.get("error")
                
                # Penalize errors
                if error:
                    response_score -= 40.0
                
                # Penalize empty responses
                if not response:
                    response_score -= 30.0
                
                # Analyze response structure
                if isinstance(response, dict):
                    if "error" in response:
                        response_score -= 20.0
                    elif "data" in response or "result" in response:
                        response_score += 0  # Good structure
                    elif len(response) == 0:
                        response_score -= 25.0
                elif isinstance(response, str):
                    if len(response.strip()) == 0:
                        response_score -= 25.0
                    elif "error" in response.lower():
                        response_score -= 20.0
                
                total_score += max(0.0, response_score)
            
            average_score = total_score / len(execution_results)
            return min(100.0, average_score)
            
        except Exception as e:
            logger.error(f"Response consistency analysis failed: {e}")
            return 50.0  # Default moderate score

    def analyze_security_compliance(
        self, 
        plan_captured: bool,
        token_used: bool,
        token_valid: bool = True
    ) -> float:
        """
        Analyze ArmorIQ security compliance.
        
        Args:
            plan_captured: Whether plan was captured
            token_used: Whether intent token was used  
            token_valid: Whether token was valid
            
        Returns:
            Security compliance score (0-100)
        """
        score = 0.0
        
        # Plan capture (50% of security score)
        if plan_captured:
            score += 50.0
        
        # Token usage (40% of security score)  
        if token_used and token_valid:
            score += 40.0
        elif token_used:
            score += 20.0  # Token used but invalid
        
        # Additional security features (10%)
        # This could include encryption, audit logging, etc.
        score += 10.0  # Default for basic security
        
        return min(100.0, score)

    def calculate_overall_credibility(self, metrics: Dict[str, float]) -> float:
        """
        Calculate weighted overall credibility score.
        
        Args:
            metrics: Dictionary of individual metric scores
            
        Returns:
            Overall credibility score (0-100)
        """
        try:
            weights = {
                "plan_integrity": ValidationConstants.PLAN_INTEGRITY_WEIGHT,
                "execution_success": ValidationConstants.EXECUTION_SUCCESS_WEIGHT, 
                "response_consistency": ValidationConstants.RESPONSE_CONSISTENCY_WEIGHT,
                "security_compliance": ValidationConstants.SECURITY_COMPLIANCE_WEIGHT,
            }
            
            total_score = 0.0
            total_weight = 0.0
            
            for metric, score in metrics.items():
                weight = weights.get(metric, 0.0)
                if weight > 0.0:
                    total_score += score * weight
                    total_weight += weight
            
            if total_weight == 0.0:
                return 0.0
            
            overall = total_score / total_weight
            return max(0.0, min(100.0, overall))
            
        except Exception as e:
            logger.error(f"Overall credibility calculation failed: {e}")
            return 0.0

    def analyze_full_credibility(
        self,
        plan_steps: List[Dict],
        execution_results: List[Dict], 
        plan_captured: bool,
        token_used: bool,
        plan_hash: Optional[str] = None,
        token_valid: bool = True,
    ) -> CredibilityMetrics:
        """
        Perform complete credibility analysis.
        
        Args:
            plan_steps: List of execution plan steps
            execution_results: List of tool execution results
            plan_captured: Whether plan was captured by ArmorIQ
            token_used: Whether intent token was used
            plan_hash: ArmorIQ plan hash if available
            token_valid: Whether token was valid
            
        Returns:
            Complete credibility metrics
        """
        # Analyze individual components
        plan_integrity = self.analyze_plan_integrity(
            plan_steps, plan_captured, plan_hash
        )
        
        execution_success = self.analyze_execution_success(execution_results)
        
        response_consistency = self.analyze_response_consistency(execution_results)
        
        security_compliance = self.analyze_security_compliance(
            plan_captured, token_used, token_valid
        )
        
        # Calculate overall score
        metrics_dict = {
            "plan_integrity": plan_integrity,
            "execution_success": execution_success,
            "response_consistency": response_consistency,
            "security_compliance": security_compliance,
        }
        
        overall_credibility = self.calculate_overall_credibility(metrics_dict)
        
        return CredibilityMetrics(
            plan_integrity_score=plan_integrity,
            execution_success_rate=execution_success,
            response_consistency_score=response_consistency,
            security_compliance_score=security_compliance,
            overall_credibility=overall_credibility,
        )

    def determine_pass_fail(self, credibility_score: float) -> str:
        """
        Determine pass/fail based on credibility score.
        
        Args:
            credibility_score: Overall credibility score (0-100)
            
        Returns:
            "pass" or "fail"
        """
        return "pass" if credibility_score >= self.threshold else "fail"

    def get_credibility_assessment(self, credibility_score: float) -> str:
        """
        Get textual assessment of credibility score.
        
        Args:
            credibility_score: Overall credibility score (0-100)
            
        Returns:
            Textual assessment
        """
        if credibility_score >= 90:
            return "excellent"
        elif credibility_score >= 80:
            return "very_good"
        elif credibility_score >= 70:
            return "good"
        elif credibility_score >= 60:
            return "fair"
        elif credibility_score >= 50:
            return "poor"
        else:
            return "very_poor"