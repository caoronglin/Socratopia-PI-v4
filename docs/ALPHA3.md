# v5 Alpha.3 — Ant Design CLI and Web PREP

Status: development candidate, not stable. Keep v4.3.2 stable release unchanged.

## Ant Design official CLI

Official reference: https://ant.design/docs/react/cli-cn/

Use the native Ant Design 6 components and React 19 + Vite; the official CLI is a **diagnostic, lint and component knowledge tool** and does not replace the build tool. Install pinned @ant-design/cli@6.6.5 via web devDependencies. From web/: npm install --ignore-scripts; npm run antd:doctor; npm run antd:lint; npm run antd:usage; npm run build.

The platform-v5 workflow runs doctor, lint and usage. Environment disables optional automatic reporting and update checks. Never run antd migrate --apply or antd setup in CI; configuration changes require review.

## Chapter PREP

GET /api/courses/{course}/prep — list course-scoped PREP status.
POST /api/courses/{course}/prep/chapter/plan — apply=false previews the validated chapter draft; apply=true creates only when absent.
GET /api/courses/{course}/prep/{lesson_id} — inspect deterministic validation errors and warnings.

The PREP UI uses Ant Design Select, Card, Steps, Collapse, List and Alert. Both desktop and mobile share the same API. The imported book can be selected by real chapter headings even while its generated _outline.md is still an empty scaffold placeholder; a populated and authored outline remains authoritative. New drafts never become ready automatically.

## Pi session boundary

The Node Pi SDK now uses SessionManager.continueRecent with a private DATA/<course>/runtime/pi_sessions folder, instead of a process-only global in-memory session. Each course has its own cwd/sessionDir. The launcher continues to require a local bearer token. Unsafe symlink directories are refused. Pi sessions contain raw conversation context and should be protected as private user data; they are NOT an authoritative learning record. The separate verified SQLite chat transcript continues to be the classroom-facing source. Restoring a Pi SDK context does not mean restoring verified mastery and does not prove that online model credentials work.

Model provider authentication remains managed by the SDK's local credential configuration or its environment; do not enter API keys into the Web UI. Full secure in-Web model selection and live provider E2E remain future work.

## Acceptance gates

Python 3.15 chapter PREP API tests, unchanged v4 course gating and >2700s lesson timer; original Python 3.11/3.13 and Rust CLI regression; React/Vite build, official CLI doctor/lint/usage, Chromium desktop/mobile E2E, native Windows/Linux/macOS x86+ARM executable smoke. Do not merge or release as stable before these pass.

Known limits: PREP editing/ready review is not a full graphical authoring flow, provider model configuration in Web is not yet done, PDF/article ingest and session/multi-user permissions remain future releases.
