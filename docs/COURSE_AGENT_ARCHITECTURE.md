# Socratopia Course Agents · AgentScope-only Contract

Version: 2026-10-18. Source of truth: `docs/AGENTSCOPE_ONLY.md`.

### Stable logic
- One stable logical agent ID per course; a fresh bounded AgentScope SDK instance per individual request.
- Normal classroom: `Agent.reply(UserMsg(...))`; explicit D/E/F discussion: same runtime, tutor-specific personas and Python turn gating.
- Models are configured per role via `course_harness.py`; live `teach` and `tutor` roles use AgentScope. `review` and `explain_visual` remain configuration-only until implemented.
- Backend handles JSON schema, citation checking, textbook SHA and SQLite persistence. Quote checking is not a guarantee of scientific accuracy.
- AgentScope native Toolkit: course-specific, opt-in, read-only outline and learning-evidence functions; no shell, arbitrary file access or unbounded external tools.
- The default tool budget is one AgentScope iteration, 90-second timeout and four concurrent turns globally; a single course has at most one active turn per Python process.
- No autonomous agent/scheduled job is inferred from a pending task. Archival, clock and mastery authority remain Python-only.

### Roadmap
- Real-provider classroom and two-tutor evaluations.
- Documented, bounded task harnesses for content preparation/review with human approval and testable source quality.
- Consolidate v4 JSONL ontology and v5 SQLite graph, then add validated prerequisite diagnosis.
- Declarative sandboxed interactive visualizations, manual sync restore conflict checks.

### References
https://docs.agentscope.io/en/versions/2.0.10/
https://github.com/agentscope-ai/agentscope/releases/tag/v2.0.10
