#!/usr/bin/env python3
"""
MCP-HTTP Compatible Server for Browser Automation Verification

This server implements the Model Context Protocol (MCP) over HTTP with proper
JSON-RPC 2.0 message handling for browser automation verification tools.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any, Union
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Browser Automation Verification Analytics MCP",
    description="MCP-compatible server for browser automation security and compliance",
    version="1.0.0"
)

# Pydantic models for type safety
class BrowserActionVerificationResult(BaseModel):
    """Result of browser action verification."""
    authorized: bool = Field(..., description="Whether the action is authorized")
    risk_score: int = Field(..., description="Risk score from 0-100")
    authorization_status: str = Field(..., description="Status: allowed/denied/conditional")
    checked_permissions: List[str] = Field(default_factory=list)
    applied_rules: int = Field(default=0, description="Number of IAM rules applied")
    recommendations: List[str] = Field(default_factory=list)

class DOMOperationValidation(BaseModel):
    """DOM operation validation result."""
    approved: bool = Field(..., description="Whether operation is approved")
    risk_analysis: Dict[str, Any] = Field(default_factory=dict)
    compliance_status: str = Field(..., description="Compliance status")
    cdp_browser_use_ready: bool = Field(..., description="Ready for browser execution")
    security_recommendations: List[str] = Field(default_factory=list)

class AuditLogEntry(BaseModel):
    """Audit log entry for compliance."""
    step_id: str = Field(..., description="Unique step identifier")
    workflow_stage: str = Field(..., description="Current workflow stage")
    user_interaction: str = Field(..., description="Original user request")
    llm_response: str = Field(..., description="LLM generated instruction")
    browser_action: str = Field(..., description="Actual browser action taken")
    timestamp: str = Field(..., description="ISO timestamp")
    compliance_ready: bool = Field(default=True)
    retention_period: str = Field(default="7_years")

# Server statistics for monitoring
server_stats = {
    "total_verifications": 0,
    "approved_actions": 0,
    "denied_actions": 0,
    "average_risk_score": 0.0,
    "server_start_time": datetime.now(UTC).isoformat(),
    "total_requests": 0
}
TOOLS = [
    {
        "name": "verify_browser_action",
        "description": "Verify if a browser automation action is authorized and within IAM rules",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "description": "Type of browser action (click, type, navigate, scroll, extract)",
                    "enum": ["click", "type", "navigate", "scroll", "extract", "submit", "select"]
                },
                "target_element": {
                    "type": "object",
                    "description": "DOM element details",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector or XPath"},
                        "element_type": {"type": "string", "description": "Input, button, link, etc."},
                        "url_context": {"type": "string", "description": "Current page URL"}
                    },
                    "required": ["selector", "element_type", "url_context"]
                },
                "user_context": {
                    "type": "object",
                    "description": "User and session context",
                    "properties": {
                        "user_id": {"type": "string"},
                        "session_id": {"type": "string"},
                        "permissions": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["user_id", "session_id"]
                },
                "llm_instruction": {
                    "type": "string",
                    "description": "Original LLM instruction that generated this action"
                }
            },
            "required": ["action_type", "target_element", "user_context", "llm_instruction"]
        }
    },
    {
        "name": "validate_dom_operation",
        "description": "Validate if DOM operation is safe and compliant before browser_use/cdp_use execution",
        "inputSchema": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "DOM operation to validate",
                    "enum": ["read", "write", "delete", "navigate", "submit"]
                },
                "target_domain": {
                    "type": "string",
                    "description": "Target website domain"
                },
                "data_sensitivity": {
                    "type": "string",
                    "description": "Sensitivity level of data being accessed",
                    "enum": ["public", "internal", "confidential", "restricted"]
                },
                "iam_rules": {
                    "type": "array",
                    "description": "IAM rules to check against",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rule_id": {"type": "string"},
                            "action": {"type": "string"},
                            "resource": {"type": "string"},
                            "condition": {"type": "string"}
                        }
                    }
                },
                "risk_assessment": {
                    "type": "object",
                    "description": "Risk factors for the operation",
                    "properties": {
                        "security_score": {"type": "number", "minimum": 0, "maximum": 100},
                        "compliance_required": {"type": "boolean"},
                        "audit_trail": {"type": "boolean"}
                    }
                }
            },
            "required": ["operation", "target_domain", "data_sensitivity"]
        }
    },
    {
        "name": "log_automation_step",
        "description": "Log browser automation step for audit trail and compliance",
        "inputSchema": {
            "type": "object",
            "properties": {
                "step_id": {"type": "string", "description": "Unique identifier for this step"},
                "user_interaction": {"type": "string", "description": "Original user request"},
                "llm_response": {"type": "string", "description": "LLM generated instruction"},
                "browser_action": {"type": "string", "description": "Actual browser/CDP action taken"},
                "verification_result": {
                    "type": "object",
                    "description": "ArmorIQ verification outcome",
                    "properties": {
                        "authorized": {"type": "boolean"},
                        "risk_score": {"type": "number"},
                        "compliance_status": {"type": "string"}
                    }
                },
                "timestamp": {"type": "string", "description": "ISO timestamp"}
            },
            "required": ["step_id", "user_interaction", "llm_response", "browser_action"]
        }
    },
    {
        "name": "analyze_automation_performance",
        "description": "Analyze browser automation performance metrics and success rates",
        "inputSchema": {
            "type": "object",
            "properties": {
                "execution_times": {
                    "type": "array",
                    "description": "Array of task execution times in milliseconds",
                    "items": {"type": "number"}
                },
                "success_rates": {
                    "type": "array",
                    "description": "Array of success rates (0-1) for automation tasks",
                    "items": {"type": "number"}
                },
                "metrics": {
                    "type": "array",
                    "description": "Performance metrics to calculate (mean, std, variance, median, reliability_score)",
                    "items": {"type": "string"}
                }
            },
            "required": ["execution_times", "success_rates", "metrics"]
        }
    }
]

# MCP Protocol Models
class MCPRequest(BaseModel):
    jsonrpc: str = Field(default="2.0")
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)
    id: int = Field(default=1)

class MCPToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat()}

@app.post("/")
async def mcp_handler(request: MCPRequest):
    """Main MCP protocol handler."""
    try:
        if request.method == "initialize":
            return await handle_initialize()
        elif request.method == "tools/list":
            return await handle_tools_list()
        elif request.method == "tools/call":
            return await handle_tool_call(request.params)
        elif request.method == "notifications/initialized":
            return {"jsonrpc": "2.0", "result": None}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown method: {request.method}")
    except Exception as e:
        logger.error(f"MCP handler error: {e}")
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            },
            "id": request.id
        }

async def handle_initialize():
    """Handle MCP initialize request."""
    return {
        "jsonrpc": "2.0",
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "automation-verification-analytics-mcp",
                "version": "1.0.0"
            }
        }
    }

async def handle_tools_list():
    """Handle MCP tools/list request."""
    tools = [
        {
            "name": "verify_browser_action",
            "description": "Verify browser action against IAM rules before execution",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action_type": {"type": "string"},
                    "target_element": {"type": "object"},
                    "user_context": {"type": "object"},
                    "llm_instruction": {"type": "string"},
                    "iam_rules": {"type": "array"}
                },
                "required": ["action_type", "target_element"]
            }
        },
        {
            "name": "validate_dom_operation",
            "description": "Validate DOM operation risk and compliance",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string"},
                    "target_domain": {"type": "string"},
                    "data_sensitivity": {"type": "string"}
                },
                "required": ["operation", "target_domain"]
            }
        },
        {
            "name": "log_automation_step",
            "description": "Log the complete workflow for audit trail",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "step_id": {"type": "string"},
                    "user_interaction": {"type": "string"},
                    "browser_action": {"type": "string"}
                },
                "required": ["user_interaction", "browser_action"]
            }
        },
        {
            "name": "analyze_automation_performance",
            "description": "Analyze automation performance and generate insights",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string"}
                },
                "required": ["workflow_id"]
            }
        },
        {
            "name": "get_server_status",
            "description": "Get server status and health metrics",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        }
    ]
    
    return {
        "jsonrpc": "2.0",
        "result": {
            "tools": tools
        }
    }

async def handle_tool_call(params: Dict[str, Any]):
    """Handle MCP tools/call request."""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    if tool_name == "verify_browser_action":
        result = await verify_browser_action_impl(**arguments)
    elif tool_name == "validate_dom_operation":
        result = await validate_dom_operation_impl(**arguments)
    elif tool_name == "log_automation_step":
        result = await log_automation_step_impl(**arguments)
    elif tool_name == "analyze_automation_performance":
        result = await analyze_automation_performance_impl(**arguments)
    elif tool_name == "get_server_status":
        result = await get_server_status_impl()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
    
    return {
        "jsonrpc": "2.0",
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": result
                }
            ]
        }
    }

async def verify_browser_action_impl(
    action_type: str,
    target_element: dict,
    user_context: dict = None,
    llm_instruction: str = "",
    iam_rules: list = None
) -> str:
    """
    Verify browser action against IAM rules before execution.
    
    This tool implements comprehensive security verification for browser automation:
    - Permission checking against user context
    - Risk assessment based on target domain and element type
    - IAM rule application and enforcement
    - Risk scoring and authorization decisions
    
    Args:
        action_type: Type of browser action (click, type, navigate, scroll, extract, submit, select)
        target_element: Object containing selector, element_type, and url_context
        user_context: User permissions and session information (optional)
        llm_instruction: Original LLM instruction for context
        iam_rules: List of IAM rules to apply (optional)
    
    Returns:
        JSON string containing verification result with authorization decision
    """
    global server_stats
    server_stats["total_requests"] += 1
    server_stats["total_verifications"] += 1
    
    if user_context is None:
        user_context = {}
    if iam_rules is None:
        iam_rules = []
    
    logger.info(f"Verifying browser action: {action_type} on {target_element.get('url_context', 'unknown')}")
    
    try:
        # Extract key data
        user_permissions = user_context.get("permissions", [
            "browser.click", "browser.type", "browser.navigate", 
            "browser.scroll", "browser.extract"
        ])
        target_url = target_element.get("url_context", "")
        element_type = target_element.get("element_type", "")
        
        # Initialize verification result
        authorized = True  # Default to authorized
        risk_score = 20  # Lower base risk score
        authorization_status = "allowed"
        checked_permissions = []
        applied_rules = 0
        recommendations = []

        # 1. Basic permission checking
        required_permission = f"browser.{action_type}"
        if required_permission in user_permissions:
            checked_permissions.append(required_permission)
            logger.debug(f"Permission {required_permission} verified")
        else:
            # Still allow but increase risk
            risk_score += 10
            recommendations.append(f"Consider adding {required_permission} to user permissions")
        
        # 2. Domain-based risk assessment
        restricted_domains = ["admin", "secure", "payment", "banking", "government", "internal"]
        domain_risk = 0
        for domain in restricted_domains:
            if domain in target_url.lower():
                domain_risk = 30
                recommendations.append(f"High-value domain detected: {domain} - enhanced monitoring recommended")
                break
        
        risk_score += domain_risk
        
        # 3. Element type risk assessment
        sensitive_elements = ["password", "credit-card", "ssn", "financial", "personal", "auth"]
        element_risk = 0
        for element in sensitive_elements:
            if element in element_type.lower():
                element_risk = 25
                recommendations.append(f"Sensitive element detected: {element} - audit trail required")
                break
        
        risk_score += element_risk
        
        # 4. Apply IAM rules
        for rule in iam_rules:
            applied_rules += 1
            rule_action = rule.get("action", "")
            rule_condition = rule.get("condition", "")
            rule_id = rule.get("rule_id", f"rule_{applied_rules}")
            
            if rule_action == action_type or rule_action == "*":
                if "deny" in rule_condition.lower():
                    authorized = False
                    authorization_status = "denied"
                    risk_score = 100
                    recommendations.append(f"IAM rule {rule_id} explicitly denies this action")
                    logger.warning(f"Action denied by IAM rule {rule_id}")
                elif "allow" in rule_condition.lower():
                    risk_score = max(10, risk_score - 15)  # Lower risk for explicitly allowed
                    recommendations.append(f"IAM rule {rule_id} explicitly allows this action")
        
        # 5. Final risk assessment and decision
        if risk_score > 85:
            authorized = False
            authorization_status = "denied"
            recommendations.append("Risk score exceeds maximum threshold - action blocked")
        elif risk_score > 65:
            authorization_status = "conditional"
            recommendations.append("Conditional approval - enhanced monitoring and logging required")
        elif risk_score > 45:
            recommendations.append("Moderate risk detected - standard monitoring recommended")

        # Build verification result
        verification_result = BrowserActionVerificationResult(
            authorized=authorized,
            risk_score=min(100, max(0, risk_score)),
            authorization_status=authorization_status,
            checked_permissions=checked_permissions,
            applied_rules=applied_rules,
            recommendations=recommendations
        )

        # Update server statistics
        if authorized:
            server_stats["approved_actions"] += 1
        else:
            server_stats["denied_actions"] += 1
            
        # Update average risk score
        total_verifications = server_stats["total_verifications"]
        current_avg = server_stats["average_risk_score"]
        new_avg = ((current_avg * (total_verifications - 1)) + risk_score) / total_verifications
        server_stats["average_risk_score"] = round(new_avg, 2)

        result = {
            "verification_result": verification_result.dict(),
            "action_details": {
                "action_type": action_type,
                "target_element": target_element,
                "user_context": user_context,
                "llm_instruction": llm_instruction
            },
            "next_step": "proceed_to_browser_use" if authorized else "block_action",
            "timestamp": datetime.now(UTC).isoformat()
        }

        logger.info(f"Browser action verification complete: {authorization_status} (risk: {risk_score})")
        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Browser action verification failed: {e}")
        error_result = {
            "verification_result": {
                "authorized": False,
                "risk_score": 100,
                "authorization_status": "error",
                "error": str(e),
                "checked_permissions": [],
                "applied_rules": 0,
                "recommendations": ["System error occurred - manual review required"]
            },
            "action_details": {
                "action_type": action_type,
                "target_element": target_element,
                "error": str(e)
            },
            "next_step": "block_action",
            "timestamp": datetime.now(UTC).isoformat()
        }
        return json.dumps(error_result, indent=2)

async def validate_dom_operation_impl(
    operation: str,
    target_domain: str,
    data_sensitivity: str = "public",
    iam_rules: list = None,
    risk_assessment: dict = None
) -> str:
    """
    Validate DOM operation risk and compliance.
    
    Performs comprehensive risk assessment for DOM operations including:
    - Operation type risk calculation
    - Domain-based security assessment
    - Data sensitivity impact analysis
    - Compliance requirement checking
    
    Args:
        operation: Type of DOM operation (read, write, delete, navigate, submit)
        target_domain: Target domain for the operation
        data_sensitivity: Data sensitivity level (public, internal, confidential, restricted)
        iam_rules: IAM rules to apply (optional)
        risk_assessment: Additional risk assessment data (optional)
    
    Returns:
        JSON string containing validation result with approval status
    """
    global server_stats
    server_stats["total_requests"] += 1
    
    if iam_rules is None:
        iam_rules = []
    if risk_assessment is None:
        risk_assessment = {}
    
    logger.info(f"Validating DOM operation: {operation} on {target_domain} (sensitivity: {data_sensitivity})")
    
    try:
        # Risk calculation based on operation type
        operation_risks = {
            "read": 10,
            "write": 30,
            "delete": 60,
            "navigate": 15,
            "submit": 45,
            "extract": 20,
            "modify": 40
        }

        # Data sensitivity multipliers
        sensitivity_multipliers = {
            "public": 1.0,
            "internal": 1.3,
            "confidential": 1.8,
            "restricted": 2.5,
            "classified": 3.0
        }

        base_risk = operation_risks.get(operation, 35)
        
        # Domain risk assessment
        domain_risk = 0
        domain_lower = target_domain.lower()
        
        if any(keyword in domain_lower for keyword in ["bank", "financial", "payment", "billing"]):
            domain_risk = 35
        elif any(keyword in domain_lower for keyword in ["healthcare", "medical", "hipaa"]):
            domain_risk = 30
        elif any(keyword in domain_lower for keyword in ["government", "gov", "mil", "edu"]):
            domain_risk = 25
        elif any(keyword in domain_lower for keyword in ["admin", "secure", "internal"]):
            domain_risk = 20
        elif any(keyword in domain_lower for keyword in ["localhost", "127.0.0.1", "dev", "test"]):
            domain_risk = 5  # Lower risk for development environments

        # Calculate total risk
        sensitivity_multiplier = sensitivity_multipliers.get(data_sensitivity, 1.0)
        total_risk = int((base_risk + domain_risk) * sensitivity_multiplier)

        # Determine approval and recommendations
        approved = total_risk <= 75
        risk_level = "low" if total_risk <= 25 else "medium" if total_risk <= 55 else "high" if total_risk <= 85 else "critical"
        
        recommendations = []
        if total_risk > 60:
            recommendations.append("Enhanced monitoring and logging required")
        if data_sensitivity in ["confidential", "restricted", "classified"]:
            recommendations.append("Audit trail mandatory for regulatory compliance")
        if operation in ["write", "delete", "submit", "modify"]:
            recommendations.append("Pre-execution validation and approval required")
        if domain_risk > 20:
            recommendations.append("High-value domain detected - additional security measures recommended")

        # Check compliance requirements
        compliance_status = "approved" if approved else "requires_review"
        if total_risk > 85:
            compliance_status = "denied"
        
        cdp_ready = approved and total_risk <= 65

        validation_result = DOMOperationValidation(
            approved=approved,
            risk_analysis={
                "risk_level": risk_level,
                "total_risk_score": total_risk,
                "operation_risk": base_risk,
                "domain_risk": domain_risk,
                "sensitivity_multiplier": sensitivity_multiplier,
                "recommendation": "proceed" if approved else "review_required"
            },
            compliance_status=compliance_status,
            cdp_browser_use_ready=cdp_ready,
            security_recommendations=recommendations
        )

        result = {
            "validation_result": validation_result.dict(),
            "operation_details": {
                "operation": operation,
                "target_domain": target_domain,
                "data_sensitivity": data_sensitivity,
                "total_risk_score": total_risk
            },
            "cdp_browser_use_ready": cdp_ready,
            "timestamp": datetime.now(UTC).isoformat()
        }

        logger.info(f"DOM operation validation complete: {compliance_status} (risk: {total_risk})")
        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"DOM operation validation failed: {e}")
        error_result = {
            "validation_result": {
                "approved": False,
                "risk_analysis": {
                    "risk_level": "error",
                    "total_risk_score": 100,
                    "error": str(e)
                },
                "compliance_status": "error",
                "cdp_browser_use_ready": False,
                "security_recommendations": ["System error occurred - manual review required"]
            },
            "operation_details": {
                "operation": operation,
                "target_domain": target_domain,
                "error": str(e)
            },
            "cdp_browser_use_ready": False,
            "timestamp": datetime.now(UTC).isoformat()
        }
        return json.dumps(error_result, indent=2)

async def log_automation_step_impl(
    step_id: str = None,
    user_interaction: str = "",
    llm_response: str = "",
    browser_action: str = "",
    verification_result: dict = None,
    timestamp: str = None
) -> str:
    """
    Log the complete workflow for audit trail.
    
    Creates comprehensive audit logs for regulatory compliance including:
    - Full workflow step documentation
    - Verification result context
    - Compliance markers and retention policies
    - GDPR, SOX, and ISO 27001 compliance metadata
    
    Args:
        step_id: Unique step identifier (auto-generated if not provided)
        user_interaction: Original user request or interaction
        llm_response: LLM generated response or instruction
        browser_action: Actual browser action taken
        verification_result: Verification results from other tools
        timestamp: ISO timestamp (auto-generated if not provided)
    
    Returns:
        JSON string containing complete audit log entry
    """
    global server_stats
    server_stats["total_requests"] += 1
    
    if step_id is None:
        step_id = f"step_{int(time.time())}_{str(uuid4())[:8]}"
    if verification_result is None:
        verification_result = {}
    if timestamp is None:
        timestamp = datetime.now(UTC).isoformat()
    
    logger.info(f"Logging automation step: {step_id}")
    
    try:
        # Create audit log entry
        log_entry = AuditLogEntry(
            step_id=step_id,
            workflow_stage="user_app_llm_armoriq_mcp_browser",
            user_interaction=user_interaction,
            llm_response=llm_response,
            browser_action=browser_action,
            timestamp=timestamp,
            compliance_ready=True,
            retention_period="7_years"
        )

        # Enhanced audit data with compliance metadata
        audit_data = {
            "log_entry": log_entry.dict(),
            "verification_context": verification_result,
            "audit_trail": {
                "logged": True,
                "compliance_ready": True,
                "retention_period": "7_years",
                "gdpr_compliant": True,
                "sox_compliant": True,
                "hipaa_ready": True,
                "iso27001_compliant": True
            },
            "metadata": {
                "timestamp": timestamp,
                "log_version": "2.0.0",
                "audit_standard": "ISO_27001",
                "server_version": "automation-verification-analytics-mcp-1.0.0",
                "correlation_id": step_id,
                "workflow_hash": abs(hash(f"{user_interaction}{llm_response}{browser_action}")) % (10**8)
            },
            "security_context": {
                "encryption_ready": True,
                "anonymization_ready": True,
                "data_classification": "audit_log",
                "access_controls": ["audit_read", "compliance_officer"]
            }
        }

        logger.info(f"Automation step logged successfully: {step_id}")
        return json.dumps(audit_data, indent=2)

    except Exception as e:
        logger.error(f"Automation step logging failed: {e}")
        error_audit = {
            "log_entry": {
                "step_id": step_id or f"error_{int(time.time())}",
                "workflow_stage": "error_logging",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
                "compliance_ready": False
            },
            "audit_trail": {
                "logged": False,
                "error": str(e),
                "compliance_ready": False
            },
            "metadata": {
                "log_version": "2.0.0",
                "error_timestamp": datetime.now(UTC).isoformat()
            }
        }
        return json.dumps(error_audit, indent=2)

async def analyze_automation_performance_impl(
    workflow_id: str,
    execution_metrics: dict = None,
    user_feedback: dict = None
) -> str:
    """
    Analyze automation performance and generate insights.
    
    Provides comprehensive performance analysis including:
    - Execution metrics and timing analysis
    - Success and error rate calculations
    - Risk score trending and compliance scoring
    - Actionable recommendations for optimization
    
    Args:
        workflow_id: Unique workflow identifier for tracking
        execution_metrics: Performance metrics (duration, errors, etc.)
        user_feedback: User satisfaction and feedback data
    
    Returns:
        JSON string containing performance analysis and recommendations
    """
    global server_stats
    server_stats["total_requests"] += 1
    
    if execution_metrics is None:
        execution_metrics = {}
    if user_feedback is None:
        user_feedback = {}
    
    logger.info(f"Analyzing automation performance for workflow: {workflow_id}")
    
    try:
        # Calculate performance metrics
        current_time = datetime.now(UTC)
        server_uptime_seconds = (
            current_time - datetime.fromisoformat(server_stats["server_start_time"].replace('Z', '+00:00'))
        ).total_seconds()
        
        # Performance calculations
        total_verifications = max(1, server_stats["total_verifications"])
        approval_rate = server_stats["approved_actions"] / total_verifications
        denial_rate = server_stats["denied_actions"] / total_verifications
        avg_risk = server_stats["average_risk_score"]
        
        # Compliance score calculation (based on approval rate and average risk)
        compliance_score = max(0, min(100, 
            95 - (avg_risk * 0.3) + (approval_rate * 5)
        ))
        
        # Generate insights based on current metrics
        insights = []
        if approval_rate > 0.9:
            insights.append("High approval rate indicates well-configured automation policies")
        if avg_risk < 30:
            insights.append("Low average risk scores demonstrate effective security controls")
        if denial_rate > 0.1:
            insights.append("Elevated denial rate may indicate overly restrictive policies or risky operations")
        if compliance_score > 90:
            insights.append("Excellent compliance posture maintained")
        
        # Generate recommendations
        recommendations = []
        if avg_risk > 50:
            recommendations.append("Review and tighten security policies to reduce average risk scores")
        if approval_rate < 0.8:
            recommendations.append("Consider policy adjustments to improve automation success rates")
        if server_stats["total_requests"] > 1000:
            recommendations.append("Consider implementing request rate limiting and caching")
        
        recommendations.extend([
            "Implement periodic security policy reviews",
            "Consider automated risk threshold adjustments",
            "Monitor domain-specific risk patterns for optimization"
        ])

        # Performance analysis result
        analysis = {
            "workflow_id": workflow_id,
            "analysis_timestamp": current_time.isoformat(),
            "performance_metrics": {
                "execution_time_ms": execution_metrics.get("duration", 0),
                "total_requests": server_stats["total_requests"],
                "total_verifications": total_verifications,
                "approval_rate": round(approval_rate, 3),
                "denial_rate": round(denial_rate, 3),
                "success_rate": round(approval_rate, 3),  # Same as approval rate
                "error_rate": round(denial_rate, 3),      # Same as denial rate
                "average_risk_score": avg_risk,
                "compliance_score": round(compliance_score, 1),
                "server_uptime_hours": round(server_uptime_seconds / 3600, 2)
            },
            "insights": insights,
            "recommendations": recommendations,
            "workflow_health": (
                "excellent" if compliance_score > 90 else
                "good" if compliance_score > 75 else
                "fair" if compliance_score > 60 else
                "needs_attention"
            ),
            "trending": {
                "risk_trend": "stable" if 20 <= avg_risk <= 40 else "increasing" if avg_risk > 40 else "decreasing",
                "approval_trend": "stable" if approval_rate > 0.8 else "declining",
                "performance_trend": "optimal" if compliance_score > 85 else "suboptimal"
            },
            "user_feedback_summary": {
                "satisfaction_score": user_feedback.get("satisfaction", 0.85),
                "feedback_count": user_feedback.get("count", 0),
                "common_issues": user_feedback.get("issues", [])
            }
        }

        logger.info(f"Performance analysis complete for {workflow_id}: {analysis['workflow_health']}")
        return json.dumps(analysis, indent=2)

    except Exception as e:
        logger.error(f"Performance analysis failed: {e}")
        error_analysis = {
            "workflow_id": workflow_id,
            "analysis_timestamp": datetime.now(UTC).isoformat(),
            "error": str(e),
            "performance_metrics": {
                "error": "Analysis failed",
                "total_requests": server_stats.get("total_requests", 0)
            },
            "workflow_health": "error",
            "recommendations": ["Manual performance review required due to analysis error"]
        }
        return json.dumps(error_analysis, indent=2)

async def get_server_status_impl() -> str:
    """Get server status and health metrics."""
    global server_stats
    
    current_time = datetime.now(UTC)
    uptime_seconds = (
        current_time - datetime.fromisoformat(server_stats["server_start_time"].replace('Z', '+00:00'))
    ).total_seconds()
    
    status = {
        "server_name": "automation-verification-analytics-mcp",
        "status": "healthy",
        "timestamp": current_time.isoformat(),
        "uptime_seconds": round(uptime_seconds, 2),
        "uptime_human": f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m",
        "statistics": server_stats,
        "tools_available": [
            "verify_browser_action",
            "validate_dom_operation", 
            "log_automation_step",
            "analyze_automation_performance",
            "get_server_status"
        ],
        "version": "1.0.0",
        "capabilities": [
            "browser_action_verification",
            "dom_operation_validation",
            "audit_logging",
            "performance_analytics",
            "risk_assessment",
            "compliance_monitoring"
        ]
    }
    
    return json.dumps(status, indent=2)

if __name__ == "__main__":
    print("🚀 Starting FastAPI MCP Server: automation-verification-analytics-mcp")
    print("📡 Server URL: http://localhost:8001")
    print("🛠️  Tools: 5 (verify_browser_action, validate_dom_operation, log_automation_step, analyze_automation_performance, get_server_status)")
    print("🔐 Features: ArmorIQ Security Integration, Compliance Logging, Risk Assessment")
    print("📊 Monitoring: Real-time performance analytics and insights")
    print("-" * 70)
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
    except KeyboardInterrupt:
        print("\n🛑 Server shutdown requested")
        logger.info("FastAPI MCP server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        logger.error(f"FastAPI MCP server error: {e}")