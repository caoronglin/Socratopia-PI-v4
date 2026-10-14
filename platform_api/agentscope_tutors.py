"""Backwards-compatible alias; all tutor execution uses AgentScope core."""
from platform_api.agentscope_runtime import (
    AgentUnavailable as TutorUnavailable,
    PERSONAS as TUTORS,
    generate_tutor_turn,
)
