"""Legacy Pi gateway retired for v5 AgentScope-only runtime.

This module remains importable for old external integrations but never starts
a child service or accepts a gateway URL. Use agentscope_runtime.ask_agent.
"""
from __future__ import annotations

class PiUnavailable(RuntimeError):
    """The legacy Pi protocol is intentionally disabled."""


async def ask_pi(course: str, prompt: str) -> str:
    raise PiUnavailable("Pi gateway was removed; use AgentScope in the Python API")
