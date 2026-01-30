import os
from armoriq_sdk import ArmorIQClient
# Explicit parameters
client = ArmorIQClient(
    api_key="ak_live_185bb59a76ab18e8d7e845096460ece1f135eec8f001cfa423ae2fdc6aedce06",
    user_id="user_12345",
    agent_id="analytics_bot_v1",
    timeout=60
)

print(client)