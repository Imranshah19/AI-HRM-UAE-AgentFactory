"""
Agent Factory — API v1 agents package.

Exposes the unified agent_router that mounts:
  - /agent/webhooks/*   (triggers/webhook.py)
  - /agent/triggers/*   (triggers/api_trigger.py)
  - /agent/status       (status + health dashboard)
  - /agent/logs         (DB-backed execution history)
"""
