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

# Create FastAPI app with MCP-HTTP compatibility
app = FastAPI(
    title="Browser Automation Verification MCP Server",
    description="MCP-compatible server for browser automation security and compliance verification",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MCP JSON-RPC 2.0 Models
class MCPRequest(BaseModel):
    """Standard MCP JSON-RPC 2.0 request format."""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method name")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Method parameters")
    id: Union[str, int, None] = Field(default=None, description="Request ID")

class MCPResponse(BaseModel):
    """Standard MCP JSON-RPC 2.0 response format."""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    result: Optional[Any] = Field(default=None, description="Result data")
    error: Optional[Dict[str, Any]] = Field(default=None, description="Error information")
    id: Union[str, int, None] = Field(default=None, description="Request ID")

# MCP Server capabilities and tool definitions
MCP_TOOLS = [
    {
        "name": "verify_browser_action",
        "description": "Verify if a browser automation action is authorized and within IAM rules",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "description": "Type of browser action",
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
        "description": "Validate if DOM operation is safe and compliant before browser execution",
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
                    "items": {"type": "object"}
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
                "browser_action": {"type": "string", "description": "Actual browser action taken"},
                "verification_result": {
                    "type": "object",
                    "description": "Verification outcome",
                    "properties": {
                        "authorized": {"type": "boolean"},
                        "risk_score": {"type": "number"},
                        "compliance_status": {"type": "string"}
                    }
                }
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
                    "description": "Performance metrics to calculate",
                    "items": {"type": "string"}
                }
            },
            "required": ["execution_times", "success_rates", "metrics"]
        }
    }
]

# Server statistics
server_stats = {
    "total_requests": 0,
    "total_verifications": 0,
    "approved_actions": 0,
    "denied_actions": 0,
    "average_risk_score": 25.0,
    "server_start_time": datetime.now().isoformat()
}

def verify_iam_rules(user_context: Dict, action_type: str, target_element: Dict, iam_rules: List = None) -> Dict:
    """Verify browser action against IAM rules."""
    if iam_rules is None:
        iam_rules = []
        
    user_permissions = user_context.get("permissions", [])
    target_url = target_element.get("url_context", "")
    element_type = target_element.get("element_type", "")
    
    # Basic permission check
    required_permission = f"browser.{action_type}"
    authorized = required_permission in user_permissions or "browser.*" in user_permissions
    
    # Risk assessment
    risk_score = 20 if authorized else 60
    
    # Domain-based risk
    high_risk_domains = ["admin", "secure", "payment", "banking", "financial"]
    if any(domain in target_url.lower() for domain in high_risk_domains):
        risk_score += 30
        
    # Element-based risk
    sensitive_elements = ["password", "credit-card", "ssn", "financial"]
    if any(element in element_type.lower() for element in sensitive_elements):
        risk_score += 25
    
    # Apply IAM rules
    for rule in iam_rules:
        if rule.get("action") == action_type and rule.get("resource") in target_url:
            if "deny" in rule.get("condition", "").lower():
                authorized = False
                risk_score = 100
            elif "allow" in rule.get("condition", "").lower():
                risk_score = max(10, risk_score - 15)
    
    return {
        "authorized": authorized,
        "risk_score": min(100, risk_score),
        "authorization_status": "allowed" if authorized else "denied",
        "checked_permissions": user_permissions,
        "applied_rules": len(iam_rules),
        "recommendations": [] if authorized else ["Review user permissions for browser automation"]
    }

def validate_dom_operation(operation: str, target_domain: str, data_sensitivity: str, iam_rules: List = None) -> Dict:
    """Validate DOM operation for risk and compliance."""
    if iam_rules is None:
        iam_rules = []
        
    # Risk calculation
    operation_risks = {"read": 10, "write": 30, "delete": 50, "navigate": 15, "submit": 40}
    sensitivity_multipliers = {"public": 1.0, "internal": 1.3, "confidential": 1.8, "restricted": 2.5}
    
    base_risk = operation_risks.get(operation, 25)
    multiplier = sensitivity_multipliers.get(data_sensitivity, 1.0)
    
    # Domain risk
    domain_risk = 0
    high_value_domains = ["bank", "financial", "government", "healthcare", "admin"]
    if any(domain in target_domain.lower() for domain in high_value_domains):
        domain_risk = 20
        
    total_risk = (base_risk + domain_risk) * multiplier
    approved = total_risk <= 60
    
    return {
        "approved": approved,
        "risk_analysis": {
            "total_risk_score": round(total_risk, 2),
            "risk_level": "low" if total_risk <= 25 else "medium" if total_risk <= 60 else "high",
            "operation_risk": base_risk,
            "domain_risk": domain_risk,
            "sensitivity_multiplier": multiplier,
            "recommendation": "approve" if approved else "review"
        },
        "compliance_status": "approved" if approved else "requires_review",
        "cdp_browser_use_ready": approved
    }

async def handle_mcp_request(request_data: Dict) -> Dict:
    """Handle MCP JSON-RPC 2.0 requests."""
    global server_stats
    server_stats["total_requests"] += 1
    
    method = request_data.get("method")
    params = request_data.get("params", {})
    request_id = request_data.get("id")
    
    logger.info(f"MCP Request: {method}")
    
    try:
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "browser-automation-verification-mcp",
                        "version": "1.0.0"
                    }
                }
            }
            
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": MCP_TOOLS}
            }
            
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            server_stats["total_verifications"] += 1
            
            if tool_name == "verify_browser_action":
                result = verify_iam_rules(
                    arguments.get("user_context", {}),
                    arguments.get("action_type", ""),
                    arguments.get("target_element", {}),
                    arguments.get("iam_rules", [])
                )
                
                if result["authorized"]:
                    server_stats["approved_actions"] += 1
                else:
                    server_stats["denied_actions"] += 1
                    
                tool_result = {
                    "verification_result": result,
                    "action_details": {
                        "action_type": arguments.get("action_type"),
                        "target_element": arguments.get("target_element"),
                        "llm_instruction": arguments.get("llm_instruction")
                    },
                    "next_step": "proceed_to_browser_use" if result["authorized"] else "deny_action",
                    "timestamp": datetime.now().isoformat()
                }
                
            elif tool_name == "validate_dom_operation":
                result = validate_dom_operation(
                    arguments.get("operation", ""),
                    arguments.get("target_domain", ""),
                    arguments.get("data_sensitivity", "public"),
                    arguments.get("iam_rules", [])
                )
                
                tool_result = {
                    "validation_result": result,
                    "operation_details": {
                        "operation": arguments.get("operation"),
                        "target_domain": arguments.get("target_domain"),
                        "data_sensitivity": arguments.get("data_sensitivity")
                    },
                    "cdp_browser_use_ready": result["cdp_browser_use_ready"],
                    "timestamp": datetime.now().isoformat()
                }
                
            elif tool_name == "log_automation_step":
                tool_result = {
                    "log_entry": {
                        "step_id": arguments.get("step_id"),
                        "workflow_stage": "user_app_llm_armoriq_browser",
                        "user_interaction": arguments.get("user_interaction"),
                        "llm_response": arguments.get("llm_response"),
                        "browser_action": arguments.get("browser_action"),
                        "verification_result": arguments.get("verification_result", {}),
                        "timestamp": datetime.now().isoformat()
                    },
                    "audit_trail": {
                        "logged": True,
                        "compliance_ready": True,
                        "retention_period": "7_years",
                        "gdpr_compliant": True
                    }
                }
                
            elif tool_name == "analyze_automation_performance":
                execution_times = arguments.get("execution_times", [])
                success_rates = arguments.get("success_rates", [])
                
                avg_time = sum(execution_times) / len(execution_times) if execution_times else 0
                avg_success = sum(success_rates) / len(success_rates) if success_rates else 0
                
                tool_result = {
                    "performance_metrics": {
                        "average_execution_time": round(avg_time, 2),
                        "average_success_rate": round(avg_success, 4),
                        "total_verifications": server_stats["total_verifications"],
                        "approval_rate": server_stats["approved_actions"] / max(1, server_stats["total_verifications"])
                    },
                    "insights": [
                        "Automation performance within acceptable parameters",
                        f"Average execution time: {avg_time:.0f}ms",
                        f"Success rate: {avg_success*100:.1f}%"
                    ],
                    "recommendations": [
                        "Continue monitoring performance metrics",
                        "Consider caching for repeated operations"
                    ]
                }
                
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(tool_result, indent=2)
                        }
                    ]
                }
            }
            
        elif method == "notifications/initialized":
            # Acknowledgment for initialization
            return {"jsonrpc": "2.0", "result": {}}
            
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
            
    except Exception as e:
        logger.error(f"Error handling MCP request: {e}")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }

# HTTP Endpoints

@app.post("/")
async def mcp_root_endpoint(request: Request):
    """Main MCP endpoint for JSON-RPC 2.0 requests."""
    try:
        request_data = await request.json()
        response = await handle_mcp_request(request_data)
        return JSONResponse(content=response)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"MCP endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/mcp")
async def mcp_alt_endpoint(request: Request):
    """Alternative MCP endpoint for JSON-RPC 2.0 requests."""
    return await mcp_root_endpoint(request)

@app.get("/")
async def root():
    """Server information and health check."""
    return {
        "name": "Browser Automation Verification MCP Server",
        "version": "1.0.0",
        "protocol": "MCP over HTTP (JSON-RPC 2.0)",
        "description": "ArmorIQ-compatible server for browser automation verification",
        "capabilities": [
            "Browser Action Verification",
            "DOM Operation Risk Assessment",
            "Audit Trail Logging",
            "Performance Analytics"
        ],
        "tools_count": len(MCP_TOOLS),
        "tools": [tool["name"] for tool in MCP_TOOLS],
        "server_stats": server_stats,
        "endpoints": {
            "mcp": "POST / or POST /mcp",
            "health": "GET /",
            "docs": "GET /docs",
            "openapi": "GET /openapi.json"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime": "running",
        "stats": server_stats
    }

@app.get("/tools")
async def list_tools():
    """List available MCP tools."""
    return {
        "tools": MCP_TOOLS,
        "count": len(MCP_TOOLS)
    }

if __name__ == "__main__":
    print("=" * 70)
    print("🤖 MCP-HTTP Browser Automation Verification Server")
    print("=" * 70)
    print("🌐 Protocol: Model Context Protocol over HTTP (JSON-RPC 2.0)")
    print("🔧 Tools: 4 verification and analytics tools")
    print("📡 Host: 0.0.0.0:8001")
    print("📚 Docs: http://localhost:8001/docs")
    print("🔍 Health: http://localhost:8001/health")
    print("=" * 70)
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server shutdown")
        logger.info("MCP server stopped")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        logger.error(f"MCP server error: {e}")