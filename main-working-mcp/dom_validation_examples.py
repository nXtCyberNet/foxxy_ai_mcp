
#!/usr/bin/env python3
"""
MCP-HTTP Server with JSON-RPC 2.0 and SSE Support
Implements Model Context Protocol for browser automation verification.
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Any, Union
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# --- CONFIGURATION & LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Browser Verification Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELS ---
class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Union[str, int, None] = None

# --- MCP TOOL DEFINITIONS ---
MCP_TOOLS = [
    {
        "name": "verify_browser_action",
        "description": "Verify if a browser automation action is authorized",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_type": {"type": "string", "enum": ["click", "type", "navigate"]},
                "user_context": {"type": "object", "properties": {"user_id": {"type": "string"}, "session_id": {"type": "string"}}}
            },
            "required": ["action_type", "user_context"]
        }
    },
    {
        "name": "validate_dom_operation",
        "description": "Validate if DOM operation is safe and compliant",
        "inputSchema": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["read", "write"]},
                "target_domain": {"type": "string"}
            },
            "required": ["operation", "target_domain"]
        }
    }
]

# --- SAFETY & LOGIC (Simplified for brevity) ---
SAFETY_LIMITS = {"max_consecutive_calls": 5}
safety_tracker = {"consecutive_calls": {}}

def check_safety(tool_name: str, session_id: str):
    key = f"{tool_name}:{session_id}"
    calls = safety_tracker["consecutive_calls"].get(key, 0)
    if calls >= SAFETY_LIMITS["max_consecutive_calls"]:
        return {"allowed": False, "reason": "Autonomous loop detected"}
    safety_tracker["consecutive_calls"][key] = calls + 1
    return {"allowed": True}

# --- CORE HANDLER ---
async def handle_mcp_request(data: Dict) -> Dict:
    method = data.get("method")
    params = data.get("params", {})
    request_id = data.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": request_id,
            "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "mcp-server", "version": "1.0.0"}}
        }

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": MCP_TOOLS}}

    if method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        session_id = args.get("user_context", {}).get("session_id", "default")

        safety = check_safety(tool_name, session_id)
        if not safety["allowed"]:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": safety["reason"]}}

        # Logic for tool results
        result_text = f"Executed {tool_name} successfully."
        return {
            "jsonrpc": "2.0", "id": request_id,
            "result": {"content": [{"type": "text", "text": result_text}]}
        }

    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}}

# --- SSE GENERATOR ---
async def sse_generator(request_data: Dict):
    """Yields the result as an SSE event and then a completion signal."""
    try:
        # Step 1: Send the actual JSON-RPC response
        response = await handle_mcp_request(request_data)
        yield f"data: {json.dumps(response)}\n\n"
        
        # Step 2: Artificial delay to demonstrate streaming (optional)
        await asyncio.sleep(0.1)
        
        # Step 3: Send completion event
        completion = {"event": "completion", "timestamp": datetime.now().isoformat(), "status": "completed"}
        yield f"data: {json.dumps(completion)}\n\n"
    except Exception as e:
        error_msg = {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}}
        yield f"data: {json.dumps(error_msg)}\n\n"

# --- MAIN ENDPOINT ---
@app.post("/mcp" , methods=["GET", "POST"])
async def mcp_endpoint(request: Request):
    try:
        body = await request.json()
        
        # DETECT SSE REQUEST
        if request.headers.get("Accept") == "text/event-stream":
            logger.info("Handling SSE Request")
            return StreamingResponse(sse_generator(body), media_type="text/event-stream")
        
        # DEFAULT JSON REQUEST
        logger.info("Handling standard JSON Request")
        response = await handle_mcp_request(body)
        return JSONResponse(content=response)
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

# --- UTILITY ENDPOINTS ---
@app.get("/health")
async def health():
    return {"status": "healthy", "time": datetime.now().isoformat()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)