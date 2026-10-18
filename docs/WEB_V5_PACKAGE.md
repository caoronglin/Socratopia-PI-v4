# Socratopia v5 Alpha.8 · AgentScope-only native Web package

## Runtime and data
- `Socratopia-Web(.exe)`: Python 3.15, FastAPI and AgentScope 2.0.10 (single model runtime).
- `web/dist/`: React 19, Ant Design 6, Ant Design Mobile and AntV.
- `templates/`: non-secret course templates. User `DATA/`, `TEXTBOOK/`, credentials and .env are never included.
- The ZIP contains no Pi SDK, Node model gateway or second agent process. Node is needed only to build the frontend.
- Default workspace `~/.socratopia/workspace`; override with `SOCRATOPIA_ROOT`.
- Desktop binds on `127.0.0.1`; bearer token is printed in terminal, never kept in browser localStorage.

## Run
Extract the complete ZIP and launch `Socratopia-Web` (or `Socratopia-Web.exe`).
Options: `--check`, `--no-browser`, `--port 8888`.
Configure `OPENAI_API_KEY`, optionally `OPENAI_BASE_URL` and `SOCRATOPIA_MODEL`.
Without model credentials, offline textbook, practice and flashcard features remain usable.

## Quality gates
1. Python 3.15 + AgentScope 2.0.10 API imports and deterministic negative tests.
2. React build, Ant Design CLI, Playwright desktop/mobile.
3. Four platform ZIP extraction, native executable, authenticated HTTP smoke tests, SHA-256.
4. Only green main may publish an alpha prerelease; historical v4 releases are left untouched.

Smoke tests are not real-provider teaching-quality validation.
