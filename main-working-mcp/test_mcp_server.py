#!/usr/bin/env python3
"""
Test script for MCP HTTP Server
"""

import requests
import json
import time

BASE_URL = "http://localhost:8002"

def test_initialize():
    """Test MCP initialize handshake"""
    print("\n=== Testing MCP Initialize ===")
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    response = requests.post(f"{BASE_URL}/mcp", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_tools_list():
    """Test tools/list request"""
    print("\n=== Testing Tools List ===")
    
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    response = requests.post(f"{BASE_URL}/mcp", json=payload)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if "result" in result and "tools" in result["result"]:
        tools = result["result"]["tools"]
        print(f"\n✓ Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
    
    return response.status_code == 200

def test_verify_browser_action():
    """Test verify_browser_action tool"""
    print("\n=== Testing verify_browser_action Tool ===")
    
    payload = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "verify_browser_action",
            "arguments": {
                "action_type": "click",
                "target_element": {
                    "selector": "#submit-button",
                    "element_type": "button",
                    "url_context": "https://example.com/form"
                },
                "user_context": {
                    "user_id": "test-user",
                    "session_id": "test-session",
                    "permissions": ["browser.click", "browser.navigate"]
                },
                "llm_instruction": "Click the submit button"
            }
        }
    }
    
    response = requests.post(f"{BASE_URL}/mcp", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_sse_stream():
    """Test SSE stream endpoint"""
    print("\n=== Testing SSE Stream ===")
    
    try:
        response = requests.get(f"{BASE_URL}/mcp", stream=True, timeout=5)
        print(f"Status: {response.status_code}")
        print("SSE Stream output (first 10 seconds):")
        
        start_time = time.time()
        for line in response.iter_lines(decode_unicode=True):
            if line:
                print(f"  {line}")
            
            # Stop after 10 seconds
            if time.time() - start_time > 10:
                print("  ... (stream continues)")
                break
        
        return response.status_code == 200
    except requests.exceptions.Timeout:
        print("✓ SSE stream established (timed out as expected)")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_health():
    """Test health endpoint"""
    print("\n=== Testing Health Endpoint ===")
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def main():
    """Run all tests"""
    print("=" * 60)
    print("MCP HTTP Server Test Suite")
    print("=" * 60)
    
    # Wait for server to be ready
    print("\nWaiting for server to be ready...")
    max_retries = 5
    for i in range(max_retries):
        try:
            requests.get(f"{BASE_URL}/health", timeout=2)
            print("✓ Server is ready")
            break
        except:
            if i == max_retries - 1:
                print("✗ Server not responding. Make sure the server is running.")
                return
            print(f"  Retry {i+1}/{max_retries}...")
            time.sleep(2)
    
    # Run tests
    results = []
    
    results.append(("Health Check", test_health()))
    results.append(("Initialize", test_initialize()))
    results.append(("Tools List", test_tools_list()))
    results.append(("Verify Browser Action", test_verify_browser_action()))
    results.append(("SSE Stream", test_sse_stream()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")

if __name__ == "__main__":
    main()
