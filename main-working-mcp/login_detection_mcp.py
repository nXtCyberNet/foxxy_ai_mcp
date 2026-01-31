#!/usr/bin/env python3
"""
Login Page Detection MCP Server

MCP-HTTP server with tools for detecting and analyzing login pages
for browser automation security verification.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Any
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Login Page Detection MCP Server",
    description="MCP server for detecting and validating login pages in browser automation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MCP Tool Definitions
MCP_TOOLS = [
    {
        "name": "detect_login_page",
        "description": "Analyze a webpage to detect if it contains a login form. Checks for username/email fields, password fields, and submit buttons.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the page to check"
                },
                "page_html": {
                    "type": "string",
                    "description": "The HTML content of the page (optional, for offline analysis)"
                },
                "dom_elements": {
                    "type": "array",
                    "description": "List of DOM elements on the page",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tag": {"type": "string"},
                            "type": {"type": "string"},
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "class": {"type": "string"},
                            "placeholder": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "validate_login_action",
        "description": "Validate if a login action is safe and authorized before execution. Checks credentials handling, domain trust, and security policies.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The login page URL"
                },
                "username_field": {
                    "type": "object",
                    "description": "Username/email input field details",
                    "properties": {
                        "selector": {"type": "string"},
                        "type": {"type": "string"},
                        "name": {"type": "string"}
                    }
                },
                "password_field": {
                    "type": "object",
                    "description": "Password input field details",
                    "properties": {
                        "selector": {"type": "string"},
                        "type": {"type": "string"},
                        "name": {"type": "string"}
                    }
                },
                "submit_button": {
                    "type": "object",
                    "description": "Submit button details",
                    "properties": {
                        "selector": {"type": "string"},
                        "text": {"type": "string"}
                    }
                },
                "user_id": {
                    "type": "string",
                    "description": "User performing the login action"
                },
                "trusted_domains": {
                    "type": "array",
                    "description": "List of trusted domains for login",
                    "items": {"type": "string"}
                }
            },
            "required": ["url", "username_field", "password_field"]
        }
    }
]

# Login detection patterns
LOGIN_PATTERNS = {
    "username_indicators": [
        "username", "user", "email", "login", "userid", "account",
        "user_name", "user-name", "user_id", "user-id", "uname"
    ],
    "password_indicators": [
        "password", "pass", "pwd", "passwd", "secret", "credential"
    ],
    "submit_indicators": [
        "login", "sign in", "signin", "log in", "submit", "enter",
        "continue", "next", "authenticate"
    ],
    "form_indicators": [
        "login", "signin", "sign-in", "auth", "authenticate", "session"
    ]
}

# Trusted domain patterns (for demo)
DEFAULT_TRUSTED_DOMAINS = [
    "google.com", "github.com", "microsoft.com", "apple.com",
    "amazon.com", "facebook.com", "twitter.com", "linkedin.com"
]


def detect_login_elements(dom_elements: List[Dict]) -> Dict[str, Any]:
    """Analyze DOM elements to detect login form components."""
    
    detected = {
        "username_fields": [],
        "password_fields": [],
        "submit_buttons": [],
        "login_forms": []
    }
    
    for element in dom_elements:
        tag = element.get("tag", "").lower()
        elem_type = element.get("type", "").lower()
        elem_id = element.get("id", "").lower()
        elem_name = element.get("name", "").lower()
        elem_class = element.get("class", "").lower()
        placeholder = element.get("placeholder", "").lower()
        
        # Combine all text for pattern matching
        all_text = f"{elem_id} {elem_name} {elem_class} {placeholder}"
        
        # Check for username/email fields
        if tag == "input" and elem_type in ["text", "email", ""]:
            for pattern in LOGIN_PATTERNS["username_indicators"]:
                if pattern in all_text:
                    detected["username_fields"].append({
                        "element": element,
                        "confidence": 0.9 if pattern in ["email", "username"] else 0.7,
                        "matched_pattern": pattern
                    })
                    break
        
        # Check for password fields
        if tag == "input" and elem_type == "password":
            detected["password_fields"].append({
                "element": element,
                "confidence": 0.95,
                "matched_pattern": "password_type"
            })
        elif tag == "input":
            for pattern in LOGIN_PATTERNS["password_indicators"]:
                if pattern in all_text:
                    detected["password_fields"].append({
                        "element": element,
                        "confidence": 0.8,
                        "matched_pattern": pattern
                    })
                    break
        
        # Check for submit buttons
        if tag in ["button", "input"] and elem_type in ["submit", "button", ""]:
            text = element.get("text", "").lower()
            for pattern in LOGIN_PATTERNS["submit_indicators"]:
                if pattern in all_text or pattern in text:
                    detected["submit_buttons"].append({
                        "element": element,
                        "confidence": 0.85,
                        "matched_pattern": pattern
                    })
                    break
        
        # Check for login forms
        if tag == "form":
            for pattern in LOGIN_PATTERNS["form_indicators"]:
                if pattern in all_text:
                    detected["login_forms"].append({
                        "element": element,
                        "confidence": 0.8,
                        "matched_pattern": pattern
                    })
                    break
    
    return detected


def calculate_login_probability(detected: Dict[str, Any]) -> float:
    """Calculate probability that page is a login page."""
    
    score = 0.0
    
    # Password field is strong indicator
    if detected["password_fields"]:
        score += 0.4
        best_password = max(detected["password_fields"], key=lambda x: x["confidence"])
        score += best_password["confidence"] * 0.1
    
    # Username field
    if detected["username_fields"]:
        score += 0.25
        best_username = max(detected["username_fields"], key=lambda x: x["confidence"])
        score += best_username["confidence"] * 0.05
    
    # Submit button
    if detected["submit_buttons"]:
        score += 0.15
    
    # Login form
    if detected["login_forms"]:
        score += 0.1
    
    # Bonus for having all components
    if (detected["username_fields"] and 
        detected["password_fields"] and 
        detected["submit_buttons"]):
        score += 0.1
    
    return min(score, 1.0)


def validate_domain_trust(url: str, trusted_domains: List[str]) -> Dict[str, Any]:
    """Check if URL domain is trusted."""
    
    try:
        # Extract domain from URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove www prefix
        if domain.startswith("www."):
            domain = domain[4:]
        
        # Check against trusted domains
        is_trusted = False
        matched_domain = None
        
        for trusted in trusted_domains:
            if domain == trusted or domain.endswith(f".{trusted}"):
                is_trusted = True
                matched_domain = trusted
                break
        
        # Check for HTTPS
        is_https = parsed.scheme.lower() == "https"
        
        return {
            "domain": domain,
            "is_trusted": is_trusted,
            "matched_trusted_domain": matched_domain,
            "is_https": is_https,
            "security_score": 1.0 if (is_trusted and is_https) else 0.5 if is_https else 0.2
        }
    
    except Exception as e:
        return {
            "domain": "unknown",
            "is_trusted": False,
            "is_https": False,
            "security_score": 0.0,
            "error": str(e)
        }


def sse_response(data: Dict) -> str:
    """Format response as SSE event."""
    json_str = json.dumps(data)
    return f"event: message\ndata: {json_str}\n\n"


async def handle_jsonrpc(request_data: Dict) -> Dict:
    """Handle MCP JSON-RPC 2.0 requests."""
    
    method = request_data.get("method")
    params = request_data.get("params", {})
    msg_id = request_data.get("id")
    
    logger.info(f"MCP Request: {method}")
    
    try:
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "froxxy-ai",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": MCP_TOOLS}
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            logger.info(f"Tool call: {tool_name}")
            
            if tool_name == "detect_login_page":
                # Detect login page
                url = arguments.get("url", "")
                dom_elements = arguments.get("dom_elements", [])
                
                # If no DOM elements provided, create mock detection
                if not dom_elements:
                    # Check URL patterns for login indicators
                    url_lower = url.lower()
                    has_login_url = any(
                        pattern in url_lower 
                        for pattern in ["login", "signin", "auth", "account"]
                    )
                    
                    result = {
                        "url": url,
                        "is_login_page": has_login_url,
                        "confidence": 0.7 if has_login_url else 0.3,
                        "detection_method": "url_pattern",
                        "detected_elements": {
                            "username_fields": [],
                            "password_fields": [],
                            "submit_buttons": [],
                            "login_forms": []
                        },
                        "recommendation": "provide_dom_elements" if not has_login_url else "proceed_with_caution",
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    # Full DOM analysis
                    detected = detect_login_elements(dom_elements)
                    probability = calculate_login_probability(detected)
                    
                    result = {
                        "url": url,
                        "is_login_page": probability >= 0.6,
                        "confidence": round(probability, 2),
                        "detection_method": "dom_analysis",
                        "detected_elements": {
                            "username_fields": len(detected["username_fields"]),
                            "password_fields": len(detected["password_fields"]),
                            "submit_buttons": len(detected["submit_buttons"]),
                            "login_forms": len(detected["login_forms"])
                        },
                        "field_details": detected,
                        "recommendation": "proceed" if probability >= 0.6 else "verify_manually",
                        "timestamp": datetime.now().isoformat()
                    }
                
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": result
                }
            
            elif tool_name == "validate_login_action":
                # Validate login action
                url = arguments.get("url", "")
                username_field = arguments.get("username_field", {})
                password_field = arguments.get("password_field", {})
                submit_button = arguments.get("submit_button", {})
                user_id = arguments.get("user_id", "anonymous")
                trusted_domains = arguments.get("trusted_domains", DEFAULT_TRUSTED_DOMAINS)
                
                # Validate domain trust
                trust_result = validate_domain_trust(url, trusted_domains)
                
                # Check field security
                password_is_masked = password_field.get("type", "").lower() == "password"
                
                # Calculate overall safety score
                safety_score = trust_result["security_score"]
                if password_is_masked:
                    safety_score = min(safety_score + 0.2, 1.0)
                
                # Determine if action is authorized
                is_authorized = safety_score >= 0.5 and trust_result["is_https"]
                
                result = {
                    "url": url,
                    "is_authorized": is_authorized,
                    "safety_score": round(safety_score, 2),
                    "domain_validation": trust_result,
                    "field_validation": {
                        "username_field_present": bool(username_field),
                        "password_field_present": bool(password_field),
                        "password_is_masked": password_is_masked,
                        "submit_button_present": bool(submit_button)
                    },
                    "user_id": user_id,
                    "risk_level": "low" if safety_score >= 0.8 else "medium" if safety_score >= 0.5 else "high",
                    "warnings": [],
                    "recommendation": "proceed" if is_authorized else "block",
                    "timestamp": datetime.now().isoformat()
                }
                
                # Add warnings
                if not trust_result["is_https"]:
                    result["warnings"].append("Connection is not secure (HTTP)")
                if not trust_result["is_trusted"]:
                    result["warnings"].append(f"Domain '{trust_result['domain']}' is not in trusted list")
                if not password_is_masked:
                    result["warnings"].append("Password field may not be properly masked")
                
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": result
                }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }
        
        elif method == "notifications/initialized":
            logger.info("Client initialized")
            return {"jsonrpc": "2.0", "result": {}}
        
        elif method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {}
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    except Exception as e:
        logger.error(f"Error handling request: {e}")
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }


@app.api_route("/mcp", methods=["GET", "POST", "OPTIONS"])
async def mcp_endpoint(request: Request):
    """Main MCP endpoint supporting GET (SSE) and POST (JSON-RPC)."""
    
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return JSONResponse(
            content={},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            }
        )
    
    # Handle GET: Establish SSE Stream
    if request.method == "GET":
        async def event_generator():
            # Send endpoint info
            yield "event: endpoint\n"
            yield "data: /mcp\n\n"
            
            # Send server ready message
            init_msg = {
                "jsonrpc": "2.0",
                "method": "server/ready",
                "params": {
                    "serverInfo": {"name": "froxxy-ai", "version": "1.0.0"},
                    "capabilities": {"tools": {}},
                    "protocolVersion": "2024-11-05"
                }
            }
            yield f"event: message\n"
            yield f"data: {json.dumps(init_msg)}\n\n"
            
            # Keep-alive heartbeat
            try:
                while True:
                    await asyncio.sleep(30)
                    yield ":heartbeat\n\n"
            except asyncio.CancelledError:
                logger.info("SSE stream cancelled")
                return
        
        logger.info("SSE Stream established")
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
    
    # Handle POST: Process JSON-RPC requests
    if request.method == "POST":
        try:
            request_data = await request.json()
            logger.info(f"POST request: {request_data.get('method', 'unknown')}")
            
            response_data = await handle_jsonrpc(request_data)
            
            # Check if client wants SSE response
            accept_header = request.headers.get("accept", "")
            if "text/event-stream" in accept_header:
                async def stream():
                    yield sse_response(response_data)
                
                return StreamingResponse(
                    stream(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Access-Control-Allow-Origin": "*",
                    }
                )
            else:
                return JSONResponse(
                    content=response_data,
                    headers={"Access-Control-Allow-Origin": "*"}
                )
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            return JSONResponse(
                {"error": "Invalid JSON"},
                status_code=400
            )
        except Exception as e:
            logger.error(f"POST error: {e}")
            return JSONResponse(
                {"error": str(e)},
                status_code=500
            )


@app.get("/")
async def root():
    """Server info endpoint."""
    return {
        "name": "Froxxy AI - Login Page Detection MCP Server",
        "version": "1.0.0",
        "protocol": "MCP over HTTP (JSON-RPC 2.0)",
        "description": "MCP server for detecting and validating login pages",
        "tools": [tool["name"] for tool in MCP_TOOLS],
        "tools_count": len(MCP_TOOLS),
        "endpoints": {
            "mcp": "GET /mcp (SSE), POST /mcp (JSON-RPC)",
            "health": "GET /health",
            "tools": "GET /tools",
            "docs": "GET /docs"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "tools_available": len(MCP_TOOLS)
    }


@app.get("/tools")
async def list_tools():
    """List available MCP tools."""
    return {
        "tools": MCP_TOOLS,
        "count": len(MCP_TOOLS)
    }


if __name__ == "__main__":
    print("=" * 60)
    print("🔐 Froxxy AI - Login Page Detection MCP Server")
    print("=" * 60)
    print("📡 Host: 0.0.0.0:8002")
    print("📚 Docs: http://localhost:8001/docs")
    print("🔍 Health: http://localhost:8001/health")
    print("🔧 MCP: GET/POST /mcp")
    print("=" * 60)
    print("🛠️  Tools:")
    for tool in MCP_TOOLS:
        print(f"   • {tool['name']}: {tool['description'][:50]}...")
    print("=" * 60)
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8002,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server shutdown")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
