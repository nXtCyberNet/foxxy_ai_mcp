import os
from typing import List, Dict, Any
from armoriq_sdk import ArmorIQClient
from armoriq_sdk.models import PlanCapture, IntentToken

class VerifiedBrowserBridge:
    """
    The Middle-Level Layer that bridges AI Reasoning with Secure Browser Execution.
    """
    def __init__(self, user_id: str, agent_id: str):
        # Initialize the ArmorIQ Client
        self.client = ArmorIQClient(
            api_key="ak_live_185bb59a76ab18e8d7e845096460ece1f135eec8f001cfa423ae2fdc6aedce06",
            user_id=user_id,
            agent_id=agent_id
        )
        self.current_token: IntentToken = None

    async def prepare_session(self, goal: str, steps: List[Dict[str, Any]]):
        """
        Step 1: Capture the intent and get a cryptographic token.
        This binds the browser agent to a specific set of actions.
        """
        # Create the plan structure required by the SDK
        plan_data = {
            "goal": goal,
            "steps": steps # Steps like {"action": "click", "mcp": "browser-mcp", "params": {"selector": "#login"}}
        }
        
        # Capture the plan via the SDK
        capture = self.client.capture_plan(
            llm="gpt-4-browser-specialist",
            prompt=goal,
            plan=plan_data
        )
        
        # Exchange for an Intent Token (valid for 1 hour by default)
        self.current_token = self.client.get_intent_token(capture, validity_seconds=3600)
        return self.current_token

    async def execute_action(self, mcp_name: str, action_name: str, params: Dict[str, Any]):
        """
        Step 2: Execute a browser action. 
        The SDK will automatically generate Merkle Proofs to verify this action 
        against the signed plan.
        """
        if not self.current_token:
            raise Exception("No verified session active. Call prepare_session first.")

        # The invoke method performs IAP Step Verification at the Proxy layer
        result = self.client.invoke(
            mcp=mcp_name,
            action=action_name,
            intent_token=self.current_token,
            params=params
        )
        
        return result