# Socratopia AgentScope-only Migration (2026-10-18)

This supersedes the historical dual-runtime PR #28 design. Latest source of truth: [AgentScope-only baseline](AGENTSCOPE_ONLY.md).

## Runtime
Browser → FastAPI authentication and course-state supervision → bounded AgentScope 2.0.10 `Agent.reply()` → deterministic textbook quote/sha verification → course SQLite → browser.

- Normal chat uses `ask_agent()` from `platform_api/agentscope_runtime.py`.
- D/E/F independent tutor turns use the same SDK with an explicit speaker and Python-controlled sequence.
- AgentScope Toolkit is empty unless the user explicitly enables read-only graph evidence.
- Models have no direct ability to write textbooks, marks, 45-minute time, authorization or archived records.
- No Node model server, no Pi runtime/skills/extension or second model execution path.

## Upgrade and audit
The original educational skill/prompt **text** has been moved unchanged under `education/` for follow-up adaptation. It is not automatically loaded as global model authority. Existing private DATA/TEXTBOOK remains untouched.
React/Ant Design remains on tested major versions; update potentially breaking TypeScript/Vite toolchain in separate fully-gated PRs.
Use Python 3.15 and AgentScope ==2.0.10. Real model credentials must be exercised separately from mock tests.
