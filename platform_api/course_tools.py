"""AgentScope native Toolkit: register only approved course-scoped read-only tools."""
from __future__ import annotations
import json
from pathlib import Path
from platform_api.course_graph import build
from platform_api.ontology import diagnosis


def build_toolkit(root: Path, course: str, *, graph_enabled: bool):
    """Construct a fresh minimal AgentScope toolkit with no unapproved tools."""
    from agentscope.tool import Toolkit, FunctionTool
    from agentscope.permission import PermissionDecision, PermissionBehavior
    if not graph_enabled:
        return Toolkit(tools=[])

    def course_outline() -> str:
        """Read the current textbook's verifiable chapter outline.

        Returns:
            An exact heading map, source checksum, and line numbers.
        """
        data = build(root, course)
        payload = {"course": data["course"], "source_sha256": data["source_sha256"],
                   "headings": [{"label": n["label"], "line": n["line"]}
                                for n in data["nodes"][:32]]}
        return json.dumps(payload, ensure_ascii=False)

    def course_learning_evidence() -> str:
        """Read only source-linked learning gaps; never assert verified mastery.

        Returns:
            A bounded list of error-linked concepts and prerequisite checks.
        """
        data = diagnosis(root, course)
        payload = {"course": data["course"], "source_sha256": data["source_sha256"],
                   "concepts": [
                       {"concept_id": c["concept_id"], "label": c["label"],
                        "wrong_practice": c["wrong_practice"], "next_action": c["next_action"],
                        "prerequisite_checks": c["prerequisite_checks"][:5]}
                       for c in data["concepts"][:8]
                   ], "mastery_updated": False, "fact_verified": False}
        return json.dumps(payload, ensure_ascii=False)

    return Toolkit(tools=[FunctionTool(
        func=course_outline, is_read_only=True,
        permission=PermissionDecision(behavior=PermissionBehavior.ALLOW,
                                      message="Read-only course outline explicitly enabled by learner"),
    ), FunctionTool(
        func=course_learning_evidence, is_read_only=True,
        permission=PermissionDecision(behavior=PermissionBehavior.ALLOW,
                                      message="Read-only, course-specific learning evidence enabled by learner"),
    )])
