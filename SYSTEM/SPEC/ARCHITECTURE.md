# Socratopia AgentScope Architecture Contract

## Layers
1. Contract: `AGENTS.md` and `SYSTEM/SPEC/` describe immutable safety and learning truth boundaries.
2. Pedagogy: `education/skills/` and `education/prompts/` hold reusable, framework-agnostic teaching reference material.
3. Model runtime: `platform_api/agentscope_runtime.py` creates bounded, course-scoped AgentScope calls; tutor roles are explicit.
4. Server: `platform_api/app.py` handles authentication, state gates, evidence, transactions, lessons and learning records.
5. State: `DATA/<course>/` and `TEXTBOOK/<course>/` are the authority. Models cannot mark mastery or completion.
6. Client: React / Ant Design Web shows server truth, never submits provider secrets.
7. CLI: `scripts/` and optional Rust CLI execute deterministic local routines, not an alternative model runtime.

## Invariants
- One online agent SDK (AgentScope); no parallel model tools, hidden model loop or external sidecar.
- A course must not read another course's user data.
- PREP readiness, verified progress and elapsed lesson time are server authority.
- References are on-demand; do not put entire textbooks or tutor profiles in always-on context.
- No claim of real-model scientific correctness without independent evidence.
