"""Bounded model routing, chosen by server configuration per course and task.

The model never chooses or mutates its own budget. Role settings are a plain
non-secret identifier; provider API keys remain only in server environment.
"""
from __future__ import annotations
import os
import re
from pathlib import Path
from scripts.lib.repository import course_dir, read_json, validate_course_name, write_json_atomic

ROLES = {"teach": (1, 90), "tutor": (1, 90), "explain_visual": (1, 60), "review": (1, 45)}
MODEL_RE = re.compile(r"^[A-Za-z0-9_.:/-]{1,120}$")

def _path(root: Path, course: str) -> Path:
    base = course_dir(root, validate_course_name(course)) / "runtime"
    if base.is_symlink():
        raise ValueError("Unsafe course model configuration")
    p = base / "model_roles.json"
    if p.is_symlink():
        raise ValueError("Unsafe model role file")
    return p

def routes(root: Path, course: str) -> dict:
    data = read_json(_path(root, course)) or {}
    supplied = data.get("models", {})
    if not isinstance(supplied, dict):
        raise ValueError("Invalid model routes")
    models = {}
    for role, (limit, timeout) in ROLES.items():
        chosen = supplied.get(role) or os.getenv("SOCRATOPIA_MODEL_" + role.upper()) or (
            os.getenv("SOCRATOPIA_TUTOR_MODEL") if role == "tutor" else None
        ) or os.getenv("SOCRATOPIA_MODEL", "gpt-4.1-mini")
        if not isinstance(chosen, str) or not MODEL_RE.fullmatch(chosen):
            raise ValueError("Invalid configured model")
        models[role] = {"model": chosen, "max_iterations": limit,
                        "timeout_seconds": timeout, "can_write_course": False}
    return {"course": validate_course_name(course), "roles": models}

def choose(root: Path, course: str, role: str) -> dict:
    if role not in ROLES:
        raise ValueError("Unknown model role")
    return routes(root, course)["roles"][role]

def assign(root: Path, course: str, role: str, model: str) -> dict:
    if role not in ROLES or not MODEL_RE.fullmatch(model):
        raise ValueError("Invalid model role or identifier")
    path = _path(root, course)
    previous = read_json(path) or {}
    current = previous.get("models", {})
    if not isinstance(current, dict):
        raise ValueError("Invalid model role data")
    updated = {k: v for k, v in current.items() if k in ROLES}
    updated[role] = model
    write_json_atomic(path, {"schema_version": 1, "models": updated})
    return routes(root, course)
