"""
Pydantic models for validation service API.
"""
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field, validator


class ToolCall(BaseModel):
    """Tool call from LLM output."""
    name: str = Field(..., description="Tool name", max_length=200)
    args: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    id: Optional[str] = Field(default=None, description="Tool call ID")

    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Tool name cannot be empty")
        return v.strip()


class ValidationRequest(BaseModel):
    """Request model for validation endpoint."""
    content: str = Field(..., description="LLM response content", max_length=100000)
    tool_calls: List[ToolCall] = Field(default_factory=list, description="Tool calls from LLM")
    llm_provider: str = Field(..., description="LLM provider name")
    llm_model: str = Field(..., description="LLM model name") 
    user_prompt: str = Field(..., description="Original user prompt", max_length=10000)
    
    # Optional validation parameters
    user_id: Optional[str] = Field(default=None, description="User ID for session")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    credibility_threshold: Optional[float] = Field(
        default=None, 
        ge=0.0, 
        le=100.0,
        description="Custom credibility threshold (0-100)"
    )

    @validator('tool_calls')
    def validate_tool_calls(cls, v):
        if len(v) > 50:  # Reasonable limit
            raise ValueError("Too many tool calls (max 50)")
        return v

    @validator('user_id', pre=True, always=True)
    def set_default_user_id(cls, v):
        return v or f"validation_user_{uuid4().hex[:8]}"

    @validator('session_id', pre=True, always=True)
    def set_default_session_id(cls, v):
        return v or f"session_{uuid4().hex[:8]}"


class CredibilityMetrics(BaseModel):
    """Credibility assessment metrics."""
    plan_integrity: float = Field(..., ge=0, le=100, description="Plan integrity score (0-100)")
    execution_success: float = Field(..., ge=0, le=100, description="Execution success rate (0-100)")
    response_consistency: float = Field(..., ge=0, le=100, description="Response consistency (0-100)")
    security_compliance: float = Field(..., ge=0, le=100, description="Security compliance (0-100)")
    overall_credibility: float = Field(..., ge=0, le=100, description="Overall credibility (0-100)")


class ExecutionDetail(BaseModel):
    """Details of tool execution."""
    tool_name: str
    status: str  # success, failed, timeout
    response: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None


class ValidationResponse(BaseModel):
    """Response model for validation endpoint."""
    status: str = Field(..., description="Validation result: pass, fail, or error")
    credibility_score: float = Field(..., ge=0, le=100, description="Overall credibility score")
    metrics: CredibilityMetrics = Field(..., description="Detailed credibility metrics")
    
    # User information
    user_id: Optional[str] = Field(default=None, description="User ID for the validation session")
    
    # Execution details
    execution_details: Dict[str, Any] = Field(default_factory=dict, description="Execution details")
    tools_executed: int = Field(default=0, description="Number of tools executed")
    plan_captured: bool = Field(default=False, description="Whether plan was captured")
    token_generated: bool = Field(default=False, description="Whether token was generated")
    
    # Optional fields
    plan_id: Optional[str] = Field(default=None, description="ArmorIQ plan ID")
    session_id: Optional[str] = Field(default=None, description="Validation session ID")
    error_message: Optional[str] = Field(default=None, description="Error message if validation failed")
    processing_time_ms: Optional[float] = Field(default=None, description="Total processing time")
    
    # Assessment
    credibility_assessment: Optional[str] = Field(default=None, description="Textual credibility assessment")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: str = Field(..., description="Response timestamp")
    armoriq_connected: bool = Field(..., description="ArmorIQ connection status")
    armoriq_configured: bool = Field(default=True, description="ArmorIQ configuration status")
    mode: str = Field(default="production", description="Service mode (production/development/mock/error)")


class MetricsResponse(BaseModel):
    """Service metrics response."""
    total_validations: int = Field(default=0, description="Total validations performed")
    successful_validations: int = Field(default=0, description="Successful validations")
    failed_validations: int = Field(default=0, description="Failed validations")
    average_credibility: float = Field(default=0.0, description="Average credibility score")
    average_processing_time_ms: float = Field(default=0.0, description="Average processing time")
    uptime_seconds: float = Field(default=0.0, description="Service uptime")
    
    
class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Error details")
    timestamp: str = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(default=None, description="Request ID")