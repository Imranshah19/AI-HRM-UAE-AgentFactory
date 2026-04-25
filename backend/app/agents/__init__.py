"""
Agent Factory — AI agent orchestration layer for AI-HRMS.

Agents sit ABOVE the existing service/task layer and coordinate
multi-step HR workflows using Claude (Anthropic) as the reasoning engine.

Entry points:
  - openclaw.py   : Main Claude-powered agent (LLM reasoning)
  - paperclip.py  : Orchestrator (routes tasks to sub-agents)
  - leave_agent.py     : Leave lifecycle automation
  - payroll_agent.py   : Payroll calculation & approval flows
  - attendance_agent.py: Daily attendance monitoring & alerts
  - chatbot_agent.py   : Enhanced AI chatbot wrapper

All agents use the existing DB session, Redis, and Celery infrastructure.
No existing files are modified.
"""

from app.agents.openclaw import OpenClaw, get_openclaw
from app.agents.paperclip import Paperclip, get_paperclip

__all__ = [
    "OpenClaw",
    "get_openclaw",
    "Paperclip",
    "get_paperclip",
]
