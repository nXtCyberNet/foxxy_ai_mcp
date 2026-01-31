# ArmorIQ Validation Service

A standalone FastAPI service that validates LLM output through ArmorIQ workflow and returns credibility-based pass/fail decisions.

## Features

- ✅ Standalone validation service (no dependencies on main backend)
- 🔒 Complete ArmorIQ SDK integration
- 📊 Multi-metric credibility scoring
- 🎯 Configurable pass/fail thresholds
- 📝 Audit logging and compliance
- 🚀 High-performance async processing
- 🐳 Docker containerization ready

## Architecture

```
┌─────────────────────┐    ┌─────────────────────┐
│   Client Request    │    │   ArmorIQ Platform  │
│   (LLM Output)      │    │   (Security Layer)  │
└─────────────────────┘    └─────────────────────┘
           │                           │
           ▼                           ▼
┌─────────────────────┐    ┌─────────────────────┐
│  Validation API     │◄───┤  Plan Capture &     │
│  (FastAPI)          │    │  Token Generation   │
└─────────────────────┘    └─────────────────────┘
           │                           │
           ▼                           ▼
┌─────────────────────┐    ┌─────────────────────┐
│  Credibility        │◄───┤  Secure Tool        │
│  Analysis           │    │  Execution          │
└─────────────────────┘    └─────────────────────┘
           │
           ▼
┌─────────────────────┐
│  Pass/Fail Result   │
│  + Detailed Metrics │
└─────────────────────┘
```

## Quick Start

1. **Install Dependencies**:
   ```bash
   cd armoriq-validation-service
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your ArmorIQ API key
   ```

3. **Run Service**:
   ```bash
   uvicorn app.main:app --reload --port 8001
   ```

4. **Test API**:
   ```bash
   curl http://localhost:8001/health
   ```

## API Endpoints

- `POST /validate` - Main validation endpoint
- `GET /health` - Health check
- `GET /metrics` - Service metrics
- `GET /docs` - API documentation

## Environment Variables

```env
ARMORIQ_API_KEY=ak_live_your_api_key_here
ARMORIQ_PROXY_URL=https://customer-proxy.armoriq.ai
ARMORIQ_BACKEND_URL=https://customer-api.armoriq.ai
VALIDATION_THRESHOLD=75.0
LOG_LEVEL=INFO
```

## Docker Usage

```bash
docker build -t armoriq-validation .
docker run -p 8001:8001 --env-file .env armoriq-validation
```

## Example Request

```bash
curl -X POST "http://localhost:8001/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "I will verify browser automation authorization",
    "tool_calls": [
      {
        "name": "verify_browser_action",
        "args": {
          "action_type": "click",
          "target_element": "submit_button",
          "selector": "#form-submit",
          "element_type": "button",
          "url_context": "https://secure-app.example.com",
          "user_context": "authenticated_session",
          "user_id": "user123",
          "session_id": "session_abc",
          "permissions": ["form_submit"],
          "llm_instruction": "Click submit to process form"
        }
      }
    ],
    "llm_provider": "openai", 
    "llm_model": "gpt-4o",
    "user_prompt": "Verify browser action authorization"
  }'
```

## Browser IAM Verification Tool

The service includes support for `verify_browser_action` - a specialized tool for verifying browser automation actions within IAM rules:

### Required Parameters:
- `action_type`* - Type of browser action (click, input, navigate, etc.)
- `target_element`* - Element being targeted
- `user_context`* - User session context
- `llm_instruction`* - LLM instruction for the action

### Optional Parameters:
- `selector` - CSS/XPath selector
- `element_type` - Type of DOM element
- `url_context` - Current page URL
- `user_id` - User identifier
- `session_id` - Browser session ID
- `permissions` - Required permissions array

## Response Format

```json
{
  "status": "pass",
  "credibility_score": 87.5,
  "metrics": {
    "plan_integrity": 95.0,
    "execution_success": 100.0,
    "response_consistency": 85.0,
    "security_compliance": 100.0
  },
  "execution_details": {
    "tools_executed": 1,
    "plan_captured": true,
    "token_generated": true
  }
}
```