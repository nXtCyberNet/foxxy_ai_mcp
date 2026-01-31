# ArmorIQ Validation API

A FastAPI endpoint that processes LLM output through the complete ArmorIQ workflow and returns a credibility assessment with pass/fail status.

## Overview

The Validation API takes LLM output containing tool calls, runs them through ArmorIQ's security framework, and evaluates the credibility based on multiple metrics:

- **Plan Integrity**: Structural correctness of the execution plan
- **Execution Success Rate**: Percentage of tools that executed successfully  
- **Response Consistency**: Quality and consistency of tool responses
- **Security Compliance**: Proper use of ArmorIQ security features

## API Endpoints

### POST `/api/v1/validation/process`

Processes LLM output through ArmorIQ workflow and returns credibility assessment.

**Authentication**: Bearer JWT token required

**Request Body**:
```json
{
  "content": "I'll search for financial records for the user.",
  "tool_calls": [
    {
      "name": "mcp_financial123__search_records",
      "args": {
        "user_id": "john_doe",
        "record_type": "transactions"
      },
      "id": "call_1"
    }
  ],
  "llm_provider": "openai",
  "llm_model": "gpt-4o", 
  "user_prompt": "Show me financial records for john_doe"
}
```

**Query Parameters**:
- `credibility_threshold` (optional): Minimum credibility percentage for pass (default: 75%)

**Response**:
```json
{
  "status": "pass",
  "credibility_metrics": {
    "plan_integrity_score": 95.0,
    "execution_success_rate": 100.0,
    "response_consistency_score": 90.0,
    "security_compliance_score": 100.0,
    "overall_credibility": 96.25
  },
  "plan_id": "550e8400-e29b-41d4-a716-446655440000",
  "execution_details": {
    "tool_calls_count": 1,
    "plan_captured": true,
    "token_generated": true,
    "execution_results": [
      {
        "tool_name": "mcp_financial123__search_records",
        "status": "success",
        "response": {"records": [...], "count": 25},
        "error": null
      }
    ],
    "conversation_id": "temp-validation-uuid"
  },
  "error_message": null
}
```

### GET `/api/v1/validation/health`

Health check endpoint for the validation service.

**Response**:
```json
{
  "status": "ok",
  "service": "ArmorIQ Validation API"
}
```

## Credibility Scoring Algorithm

The overall credibility score is calculated using weighted averages:

- **Plan Integrity (20% weight)**: 
  - Plan properly captured by ArmorIQ
  - All tools have required fields (action, mcp, params)
  - Plan structure is valid

- **Execution Success Rate (40% weight)**:
  - Percentage of tools that executed without errors
  - Most important factor in credibility

- **Response Consistency (30% weight)**:
  - Quality of tool responses
  - Absence of error messages
  - Data consistency checks

- **Security Compliance (10% weight)**:
  - Plan was captured before execution
  - Cryptographic token was used for authorization

## ArmorIQ Workflow Integration

The API follows the complete ArmorIQ security workflow:

1. **Plan Capture**: Register intended actions with ArmorIQ backend
2. **Token Generation**: Get cryptographic authorization token
3. **Secure Execution**: Execute tools through ArmorIQ proxy
4. **Audit Logging**: Save execution details to database

## Usage Examples

### Python with httpx
```python
import httpx

llm_output = {
    "content": "I'll search for user data.",
    "tool_calls": [
        {
            "name": "mcp_database__query_users",
            "args": {"filter": "active=true"},
            "id": "call_1"
        }
    ],
    "llm_provider": "openai",
    "llm_model": "gpt-4o",
    "user_prompt": "Get all active users"
}

headers = {"Authorization": "Bearer YOUR_JWT_TOKEN"}

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/validation/process",
        json=llm_output,
        headers=headers
    )
    
    result = response.json()
    print(f"Status: {result['status']}")
    print(f"Credibility: {result['credibility_metrics']['overall_credibility']:.1f}%")
```

### cURL
```bash
curl -X POST "http://localhost:8000/api/v1/validation/process" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Searching for data...",
    "tool_calls": [
      {
        "name": "mcp_api__fetch_data", 
        "args": {"endpoint": "/users"},
        "id": "call_1"
      }
    ],
    "llm_provider": "openai",
    "llm_model": "gpt-4o",
    "user_prompt": "Get user data"
  }'
```

### JavaScript/TypeScript
```javascript
const validateLLMOutput = async (llmOutput, jwtToken) => {
  const response = await fetch('/api/v1/validation/process', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${jwtToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(llmOutput)
  });
  
  const result = await response.json();
  
  if (result.status === 'pass') {
    console.log(`✅ Validation passed: ${result.credibility_metrics.overall_credibility}%`);
  } else {
    console.log(`❌ Validation failed: ${result.credibility_metrics.overall_credibility}%`);
  }
  
  return result;
};
```

## Error Handling

The API handles various error scenarios:

- **Authentication Errors**: 401 Unauthorized if JWT token is invalid
- **ArmorIQ Errors**: Plan capture, token generation, or execution failures
- **MCP Connection Errors**: Tool execution failures due to MCP issues
- **Validation Errors**: Input validation errors for malformed requests

Error responses include detailed error messages in the `error_message` field.

## Pass/Fail Criteria

- **Pass**: Overall credibility score >= threshold (default 75%)
- **Fail**: Overall credibility score < threshold OR critical errors occurred

You can adjust the threshold using the `credibility_threshold` query parameter.

## Integration with Existing System

The validation API integrates seamlessly with the existing ArmorIQ agent system:

- Uses the same ArmorIQ SDK and services
- Leverages existing MCP connections and tool management
- Follows the same security protocols and audit logging
- Compatible with all supported LLM providers and MCP servers

## Security Considerations

- All tool executions go through ArmorIQ security layer
- Plans are captured before execution for audit trails
- Cryptographic tokens ensure authorized execution only
- Database logging provides complete audit trails
- JWT authentication protects API access

## Performance

- Async/await throughout for optimal performance
- Connection pooling for database and HTTP operations
- Streaming support for real-time validation feedback
- Configurable timeouts and retry mechanisms