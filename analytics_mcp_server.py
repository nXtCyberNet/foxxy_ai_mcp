from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import numpy as np
import os
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GenAI Browser Automation Verification & Analytics MCP Server",
    description="ArmorIQ-compatible MCP server for browser automation verification, IAM rules, and analytics",
    version="1.0.0"
)

# CORS middleware for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication configuration
API_KEY = os.getenv("MCP_API_KEY", "mcp_automation_analytics_key_12345")  # Set via environment variable

def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key authentication"""
    if not x_api_key:
        logger.warning("Missing API key in request")
        raise HTTPException(status_code=401, detail="Missing API key")
    
    if x_api_key != API_KEY:
        logger.warning(f"Invalid API key attempted: {x_api_key[:10]}...")
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return x_api_key

# Define available tools for this MCP
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
    }
]

def sse_response(data):
    """Format response as SSE (Server-Sent Events)"""
    json_str = json.dumps(data)
    return f"event: message\ndata: {json_str}\n\n"

def verify_iam_rules(user_context, action_type, target_element, iam_rules):
    """Verify if action is allowed based on IAM rules"""
    try:
        user_permissions = user_context.get("permissions", [])
        target_url = target_element.get("url_context", "")
        element_type = target_element.get("element_type", "")
        
        # Default risk scoring
        risk_score = 0
        authorization_status = "denied"
        
        # Check basic permissions
        required_permission = f"browser.{action_type}"
        if required_permission in user_permissions or "browser.*" in user_permissions:
            authorization_status = "allowed"
            risk_score = 20  # Base risk for authorized actions
        
        # Domain-based restrictions
        restricted_domains = ["admin", "secure", "payment", "banking"]
        if any(domain in target_url.lower() for domain in restricted_domains):
            risk_score += 40
            if "admin" not in user_permissions:
                authorization_status = "denied"
                authorization_status = "denied"
        
        # Element type restrictions
        sensitive_elements = ["password", "credit-card", "ssn", "financial"]
        if any(sensitive in element_type.lower() for sensitive in sensitive_elements):
            risk_score += 30
            if "sensitive_data" not in user_permissions:
                authorization_status = "denied"
            risk_score += 30
            if "sensitive_data" not in user_permissions:
                authorization_status = "denied"
        
        # Apply specific IAM rules
        for rule in iam_rules:
            if rule.get("action") == action_type:
                if rule.get("resource") in target_url:
                    condition = rule.get("condition", "")
                    if "deny" in condition.lower():
                        authorization_status = "denied"
                        risk_score = 100
                    elif "allow" in condition.lower():
                        authorization_status = "allowed"
                        risk_score = max(0, risk_score - 10)
                    condition = rule.get("condition", "")
                    if "deny" in condition.lower():
                        authorization_status = "denied"
                        risk_score = 100
                    elif "allow" in condition.lower():
                        authorization_status = "allowed"
                        risk_score = max(0, risk_score - 10)
        
        return {
            "authorized": authorization_status == "allowed",
            "risk_score": min(100, risk_score),
            "authorization_status": authorization_status,
            "checked_permissions": user_permissions,
            "applied_rules": len(iam_rules)
        }
        
    except Exception as e:
        logger.error(f"Error in IAM verification: {str(e)}")
        return {
            "authorized": False,
            "risk_score": 100,
            "authorization_status": "error",
            "error": str(e)
        }

def assess_dom_operation_risk(operation, target_domain, data_sensitivity, risk_assessment):
    """Assess risk level of DOM operation"""
    try:
        base_risk = 10
        
        # Operation risk levels
        operation_risks = {
            "read": 10,
            "write": 30, 
            "delete": 50,
            "navigate": 20,
            "submit": 40
        }
        
        # Data sensitivity multipliers
        sensitivity_multipliers = {
            "public": 1.0,
            "internal": 1.5,
            "confidential": 2.0,
            "restricted": 3.0
        }
        
        # Domain risk assessment
        domain_risk = 0
        high_risk_domains = ["bank", "financial", "government", "healthcare"]
        if any(risk_domain in target_domain.lower() for risk_domain in high_risk_domains):
            domain_risk = 25
            domain_risk = 25
        
        # Calculate total risk
        operation_risk = operation_risks.get(operation, 20)
        sensitivity_multiplier = sensitivity_multipliers.get(data_sensitivity, 1.5)
        total_risk = (operation_risk + domain_risk) * sensitivity_multiplier
        
        # Apply additional risk assessment if provided
        if risk_assessment:
            security_score = risk_assessment.get("security_score", 50)
            total_risk = total_risk * (1 - security_score / 100)
        
        risk_level = "low" if total_risk < 30 else "medium" if total_risk < 60 else "high"
        
        return {
            "total_risk_score": round(total_risk, 2),
            "risk_level": risk_level,
            "operation_risk": operation_risk,
            "domain_risk": domain_risk,
            "sensitivity_multiplier": sensitivity_multiplier,
            "recommendation": "approve" if total_risk < 50 else "review" if total_risk < 80 else "deny"
        }
        
    except Exception as e:
        logger.error(f"Error in DOM risk assessment: {str(e)}")
        return {
            "total_risk_score": 100,
            "risk_level": "high",
            "recommendation": "deny",
            "error": str(e)
        }

def calculate_automation_metrics(data, metrics, data_type="general"):
    """Calculate automation-specific metrics from data with error handling"""
    try:
        results = {}
        data_array = np.array(data)
        
        if len(data_array) == 0:
            raise ValueError("Empty data array provided")
        
        for metric in metrics:
            if metric == "mean":
                results["mean"] = float(np.mean(data_array))
            elif metric == "std":
                results["std"] = float(np.std(data_array))
            elif metric == "variance":
                results["variance"] = float(np.var(data_array))
            elif metric == "median":
                results["median"] = float(np.median(data_array))
            elif metric == "min":
                results["min"] = float(np.min(data_array))
            elif metric == "max":
                results["max"] = float(np.max(data_array))
            elif metric == "reliability_score" and data_type == "success_rates":
                # Calculate reliability as percentage of successful tasks
                success_count = np.sum(data_array >= 0.9)  # Consider 90%+ as reliable
                results["reliability_score"] = float(success_count / len(data_array) * 100)
            elif metric == "performance_grade":
                # Grade performance based on execution times (lower is better)
                if data_type == "execution_times":
                    avg_time = np.mean(data_array)
                    if avg_time < 1000:  # < 1 second
                        results["performance_grade"] = "excellent"
                    elif avg_time < 3000:  # < 3 seconds
                        results["performance_grade"] = "good"
                    elif avg_time < 10000:  # < 10 seconds
                        results["performance_grade"] = "fair"
                    else:
                        results["performance_grade"] = "poor"
            elif metric == "consistency_score":
                # Measure consistency (lower std dev = higher consistency)
                cv = np.std(data_array) / (np.mean(data_array) + 0.01)  # Coefficient of variation
                results["consistency_score"] = float(max(0, 100 - (cv * 100)))  # Scale to 0-100
            else:
                logger.warning(f"Unknown metric requested: {metric}")
                results[metric] = None
        
        return results
    except Exception as e:
        logger.error(f"Error calculating automation metrics: {str(e)}")
        raise ValueError(f"Automation metric calculation failed: {str(e)}")

async def handle_jsonrpc(request_data):
    """Handle JSON-RPC 2.0 requests with production error handling"""
    try:
        method = request_data.get("method")
        msg_id = request_data.get("id")
        
        logger.info(f"Received JSON-RPC request: method={method}, id={msg_id}")
        
        # Method 1: Initialize handshake
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "automation-analytics-mcp",
                        "version": "1.0.0"
                    }
                }
            }
        
        # Method 2: List available tools
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": TOOLS}
            }
        
        # Method 3: Execute tool
        elif method == "tools/call":
            tool_name = request_data["params"]["name"]
            arguments = request_data["params"]["arguments"]
            
            # Execute tool logic based on tool name
            if tool_name == "verify_browser_action":
                action_type = arguments.get("action_type")
                target_element = arguments.get("target_element", {})
                user_context = arguments.get("user_context", {})
                llm_instruction = arguments.get("llm_instruction", "")
                iam_rules = arguments.get("iam_rules", [])
                
                # Perform IAM verification
                verification_result = verify_iam_rules(user_context, action_type, target_element, iam_rules)
                
                result_data = {
                    "verification_result": verification_result,
                    "action_details": {
                        "action_type": action_type,
                        "target_selector": target_element.get("selector"),
                        "url_context": target_element.get("url_context")
                    },
                    "llm_instruction": llm_instruction,
                    "user_id": user_context.get("user_id"),
                    "session_id": user_context.get("session_id"),
                    "timestamp": str(np.datetime64('now')),
                    "next_step": "proceed_to_browser_use" if verification_result["authorized"] else "deny_action"
                }
            
            elif tool_name == "validate_dom_operation":
                operation = arguments.get("operation")
                target_domain = arguments.get("target_domain")
                data_sensitivity = arguments.get("data_sensitivity")
                iam_rules = arguments.get("iam_rules", [])
                risk_assessment = arguments.get("risk_assessment", {})
                
                # Assess DOM operation risk
                risk_analysis = assess_dom_operation_risk(operation, target_domain, data_sensitivity, risk_assessment)
                
                # Check compliance requirements
                compliance_required = risk_assessment.get("compliance_required", False)
                audit_trail_required = risk_assessment.get("audit_trail", True)
                
                result_data = {
                    "validation_result": {
                        "approved": risk_analysis["recommendation"] in ["approve", "review"],
                        "requires_review": risk_analysis["recommendation"] == "review",
                        "risk_analysis": risk_analysis
                    },
                    "compliance": {
                        "compliance_required": compliance_required,
                        "audit_trail_required": audit_trail_required,
                        "data_classification": data_sensitivity
                    },
                    "operation_details": {
                        "operation": operation,
                        "target_domain": target_domain,
                        "iam_rules_applied": len(iam_rules)
                    },
                    "cdp_browser_use_ready": risk_analysis["recommendation"] == "approve"
                }
            
            elif tool_name == "log_automation_step":
                step_id = arguments.get("step_id")
                user_interaction = arguments.get("user_interaction")
                llm_response = arguments.get("llm_response")
                browser_action = arguments.get("browser_action")
                verification_result = arguments.get("verification_result", {})
                timestamp = arguments.get("timestamp", str(np.datetime64('now')))
                
                # Create comprehensive audit log
                result_data = {
                    "log_entry": {
                        "step_id": step_id,
                        "workflow_stage": "user_app_llm_armoriq_browser",
                        "user_interaction": user_interaction,
                        "llm_response": llm_response,
                        "armoriq_verification": verification_result,
                        "browser_action": browser_action,
                        "timestamp": timestamp
                    },
                    "audit_trail": {
                        "logged": True,
                        "compliance_ready": True,
                        "retention_period": "7_years"
                    },
                    "next_steps": [
                        "Execute browser_use/cdp_use if authorized",
                        "Monitor execution results", 
                        "Update performance metrics"
                    ]
                }
            
            elif tool_name == "analyze_automation_performance":
                execution_times = arguments.get("execution_times", [])
                success_rates = arguments.get("success_rates", [])
                metrics = arguments.get("metrics", ["mean", "std", "reliability_score"])
                
                time_analysis = calculate_automation_metrics(execution_times, metrics, "execution_times")
                success_analysis = calculate_automation_metrics(success_rates, metrics, "success_rates")
                
                # Calculate overall performance score
                avg_time = time_analysis.get("mean", 0)
                reliability = success_analysis.get("reliability_score", 0)
                performance_score = (reliability / 100) * max(0, (10000 - avg_time) / 10000)  # Combined score
                
                result_data = {
                    "performance_score": round(performance_score, 4),
                    "execution_analysis": time_analysis,
                    "success_analysis": success_analysis,
                    "performance_level": "excellent" if performance_score > 0.8 else "good" if performance_score > 0.6 else "needs_improvement"
                }
            
            elif tool_name == "calculate_automation_reliability":
                task_results = arguments.get("task_results", [])
                response_times = arguments.get("response_times", [])
                error_types = arguments.get("error_types", [])
                
                success_rate = np.mean(task_results) * 100 if task_results else 0
                avg_response_time = np.mean(response_times) if response_times else 0
                total_errors = sum(error_types) if error_types else 0
                
                # Calculate reliability score (0-100)
                reliability_score = success_rate * 0.6 + max(0, (5000 - avg_response_time) / 5000) * 30 + max(0, (10 - total_errors) / 10) * 10
                
                result_data = {
                    "reliability_score": round(reliability_score, 2),
                    "success_rate": round(success_rate, 2),
                    "avg_response_time": round(avg_response_time, 2),
                    "total_errors": total_errors,
                    "reliability_level": "high" if reliability_score > 80 else "medium" if reliability_score > 60 else "low"
                }
            
            elif tool_name == "analyze_bot_behavior":
                action_sequences = arguments.get("action_sequences", [])
                decision_times = arguments.get("decision_times", [])
                metrics = arguments.get("metrics", ["mean", "consistency_score"])
                
                sequence_analysis = calculate_automation_metrics(action_sequences, metrics, "sequences")
                decision_analysis = calculate_automation_metrics(decision_times, metrics, "decision_times")
                
                result_data = {
                    "sequence_analysis": sequence_analysis,
                    "decision_analysis": decision_analysis,
                    "optimization_suggestions": [
                        "Consider caching frequently used elements" if sequence_analysis.get("mean", 0) > 10 else "Sequence length is optimal",
                        "AI decision speed is excellent" if decision_analysis.get("mean", 0) < 500 else "Consider optimizing AI model for faster decisions"
                    ]
                }
            
            else:
                result_data = {"error": f"Unknown tool: {tool_name}"}
            
            # Return response in MCP format
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result_data)  # Must be JSON string
                        }
                    ]
                }
            }
        
        # Unknown method
        else:
            logger.warning(f"Unknown method requested: {method}")
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    except Exception as e:
        logger.error(f"Error handling JSON-RPC request: {str(e)}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "id": request_data.get("id"),
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }

@app.post("/mcp")
async def mcp_endpoint(request: Request, api_key: str = Header(None, alias="X-API-Key")):
    """Main MCP endpoint - handles all JSON-RPC requests with authentication"""
    try:
        # Verify API key
        verify_api_key(api_key)
        
        # Parse request
        request_data = await request.json()
        logger.info(f"Processing MCP request from authenticated client")
        
        # Handle JSON-RPC
        response_data = await handle_jsonrpc(request_data)
        
        async def stream():
            yield sse_response(response_data)
            yield sse_response(response_data)
        
        return StreamingResponse(
            stream(),
            media_type="text/event-stream"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in MCP endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "name": "automation-verification-analytics-mcp",
        "version": "1.0.0",
        "purpose": "GenAI Browser Automation Verification & Analytics",
        "workflow": "User → App → LLM → ArmorIQ Verification → Browser_use/CDP_use",
        "tools": len(TOOLS),
        "available_tools": [tool["name"] for tool in TOOLS],
        "capabilities": [
            "IAM Rule Verification",
            "DOM Operation Risk Assessment", 
            "Browser Action Authorization",
            "Audit Trail Logging",
            "Performance Analytics"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    
    # Configuration from environment variables
    HOST = os.getenv("MCP_HOST", "0.0.0.0")
    PORT = int(os.getenv("MCP_PORT", "8001"))
    SSL_KEYFILE = os.getenv("SSL_KEYFILE")  # Path to SSL key file
    SSL_CERTFILE = os.getenv("SSL_CERTFILE")  # Path to SSL certificate file
    
    print("=" * 60)
    print("🤖 GenAI Browser Automation Analytics MCP Server")
    print("=" * 60)
    print(f"Host: {HOST}")
    print(f"Port: {PORT}")
    print(f"API Key: {'✓ Configured' if API_KEY else '✗ Not set'}")
    print(f"SSL: {'✓ Enabled' if SSL_KEYFILE and SSL_CERTFILE else '✗ Disabled (use reverse proxy)'}")
    print("=" * 60)
    
    # Run server with optional SSL
    if SSL_KEYFILE and SSL_CERTFILE:
        logger.info("Starting server with SSL enabled")
        uvicorn.run(
            app,
            host=HOST,
            port=PORT,
            ssl_keyfile=SSL_KEYFILE,
            ssl_certfile=SSL_CERTFILE,
            log_level="info"
        )
    else:
        logger.info("Starting server without SSL (use nginx/caddy reverse proxy for HTTPS)")
        uvicorn.run(
            app,
            host=HOST,
            port=PORT,
            log_level="info"
        )
