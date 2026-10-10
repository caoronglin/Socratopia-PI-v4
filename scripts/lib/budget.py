"""Context-budget estimation and soft thresholds (plan.md §10, read-only).

`wc -w` counts a Chinese paragraph as a handful of "words", so word-based caps
never fire on this repository. This module estimates tokens with a CJK-aware
heuristic instead. It is a *planning* estimate, not a tokenizer: CJK characters
are weighted ~1.3 tokens, everything else ~1 token per 3.8 characters.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

_CJK = re.compile(r"[\u3400-\u9fff\uff00-\uffef\u3000-\u303f]")
_FRONTMATTER_DESC = re.compile(r"^description:\s*(.+)$", re.MULTILINE)

# Soft caps in estimated tokens. Exceeding one is a doctor WARN, never an ERROR.
LIMITS = {
    "kernel": 2000,      # AGENTS.md: always loaded
    "skill": 1200,       # SKILL.md: loaded when routed
    "reference": 1500,   # references/*.md: loaded per task
    "profile": 700,      # visible tutor compact profile: one per classroom
    "moe": 600,          # internal review member: one lens per deliberation
}

# Plan §10 proportional budget, relative to the model context window `C`.
KERNEL_AND_ROUTING_SHARE = 0.05
TASK_REFERENCES_SHARE = 0.08
DEFAULT_WINDOW = 128_000

SCENARIOS: dict[str, tuple[str, ...]] = {
    "classroom": (
        ".pi/skills/socratopia-learning/SKILL.md",
        ".pi/skills/socratopia-learning/references/classroom.md",
        ".pi/skills/socratopia-learning/references/memory.md",
        ".pi/skills/socratopia-tutor/SKILL.md",
        ".pi/skills/socratopia-tutor/references/persona.md",
        "profile:max",
    ),
    "assessment": (
        ".pi/skills/socratopia-learning/SKILL.md",
        ".pi/skills/socratopia-learning/references/assessment.md",
        ".pi/skills/socratopia-learning/references/quiz-generation.md",
    ),
    "prep": (
        ".pi/skills/socratopia-learning/SKILL.md",
        ".pi/skills/socratopia-learning/references/lesson-planning.md",
        ".pi/skills/socratopia-learning/references/content.md",
    ),
    "tutor-style": (
        ".pi/skills/socratopia-tutor/SKILL.md",
        ".pi/skills/socratopia-tutor/references/persona.md",
        ".pi/skills/socratopia-tutor/references/style.md",
        "profile:max",
    ),
    "onboarding": (
        ".pi/skills/socratopia-learning/SKILL.md",
        ".pi/skills/socratopia-learning/references/onboarding.md",
    ),
    "study-group": (
        ".pi/skills/socratopia-tutor/SKILL.md",
        ".pi/skills/socratopia-tutor/references/study-group.md",
        "profile:max",
    ),
}


def estimate_tokens(text: str) -> int:
    """Conservative CJK-aware token estimate."""
    cjk = len(_CJK.findall(text))
    other = len(_CJK.sub(" ", text))
    return int(cjk * 1.3 + other / 3.8)


def file_tokens(path: Path) -> int:
    return estimate_tokens(path.read_text(encoding="utf-8", errors="replace"))


def routing_tokens(root: Path) -> int:
    """Kernel plus the frontmatter descriptions every skill pays at startup."""
    total = file_tokens(root / "AGENTS.md") if (root / "AGENTS.md").exists() else 0
    for skill in sorted((root / ".pi/skills").glob("*/SKILL.md")):
        match = _FRONTMATTER_DESC.search(skill.read_text(encoding="utf-8", errors="replace"))
        total += estimate_tokens(match.group(1)) if match else 0
    return total


def _limit_for(rel: str) -> tuple[str, int] | None:
    if rel == "AGENTS.md":
        return "kernel", LIMITS["kernel"]
    if rel.endswith("/SKILL.md"):
        return "skill", LIMITS["skill"]
    if "/profiles/TUTOR_" in rel:
        return "profile", LIMITS["profile"]
    if "/moe/TUTOR_" in rel:
        return "moe", LIMITS["moe"]
    if "/references/" in rel:
        return "reference", LIMITS["reference"]
    return None


def soft_threshold_warnings(root: Path) -> list[str]:
    """One WARN per control file whose estimated tokens exceed its soft cap."""
    candidates: Iterable[Path] = [
        root / "AGENTS.md",
        *sorted(root.glob(".pi/skills/*/SKILL.md")),
        *sorted(root.glob(".pi/skills/*/references/*.md")),
        *sorted(root.glob(".pi/skills/*/profiles/TUTOR_*.md")),
        *sorted(root.glob(".pi/skills/*/moe/TUTOR_*.md")),
    ]
    warnings: list[str] = []
    for path in candidates:
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        limit = _limit_for(rel)
        if limit is None:
            continue
        label, cap = limit
        tokens = file_tokens(path)
        if tokens > cap:
            warnings.append(f"token soft cap exceeded ({label}): {rel} ≈{tokens} > {cap}")
    return warnings


def scenario_costs(root: Path) -> dict[str, int]:
    """Estimated on-demand reference tokens per common task (excludes kernel)."""
    profiles = sorted(root.glob(".pi/skills/socratopia-tutor/profiles/TUTOR_*.md"))
    largest = max((file_tokens(p) for p in profiles), default=0)
    costs: dict[str, int] = {}
    for name, parts in SCENARIOS.items():
        total = 0
        for part in parts:
            if part == "profile:max":
                total += largest
            elif (root / part).exists():
                total += file_tokens(root / part)
        costs[name] = total
    return costs


def budget_warnings(root: Path, window: int = DEFAULT_WINDOW) -> list[str]:
    """Proportional plan §10 checks against a model window of `window` tokens."""
    warnings: list[str] = []
    routing = routing_tokens(root)
    if routing > window * KERNEL_AND_ROUTING_SHARE:
        warnings.append(
            f"kernel+routing ≈{routing} tokens exceeds {KERNEL_AND_ROUTING_SHARE:.0%} of window {window}"
        )
    for name, cost in scenario_costs(root).items():
        if cost > window * TASK_REFERENCES_SHARE:
            warnings.append(
                f"scenario {name!r} references ≈{cost} tokens exceed {TASK_REFERENCES_SHARE:.0%} of window {window}"
            )
    return warnings


def render_report(root: Path, window: int = DEFAULT_WINDOW) -> str:
    """Human-readable budget table."""
    routing = routing_tokens(root)
    lines = [
        f"Context budget (window={window}, 估算值非精确 tokenizer)",
        f"- kernel+routing ≈{routing} ({routing / window:.1%}，上限 {KERNEL_AND_ROUTING_SHARE:.0%})",
    ]
    for name, cost in scenario_costs(root).items():
        lines.append(f"- {name}: references ≈{cost} ({cost / window:.1%}，上限 {TASK_REFERENCES_SHARE:.0%})")
    return "\n".join(lines)
