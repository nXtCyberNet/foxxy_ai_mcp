from armoriq_sdk import ArmorIQClient

client = ArmorIQClient(
    api_key="ak_live_185bb59a76ab18e8d7e845096460ece1f135eec8f001cfa423ae2fdc6aedce06",
    user_id="ntg",
    agent_id="ntg",
    )

# 1. Capture the intent (e.g., from an LLM response)
plan = client.capture_plan(
    llm="gpt-4",
    prompt="Summarize the latest sales data and email it to the manager.",
    plan={
        "steps": [
            {"action": "fetch_sales", "mcp": "db-mcp"},
            {"action": "send_email", "mcp": "comm-mcp"}
        ]
    }
)

# 2. Secure the intent
token = client.get_intent_token(plan, validity_seconds=120)

# 3. Execute the steps securely
try:
    # Step A: Fetch Data
    sales_data = client.invoke("db-mcp", "fetch_sales", token, {"period": "Q4"})
    
    # Step B: Email Results
    if sales_data["success"]:
        client.invoke("comm-mcp", "send_email", token, {
            "to": "manager@company.com",
            "body": f"Sales: {sales_data['data']}"
        })

except TokenExpiredError:
    # Handle token refresh logic here
    print("Execution window closed. Please re-authorize.")
except VerificationError as e:
    # Triggered if you try to call an action NOT in the original plan
    print(f"Security Policy Violation: {e}")