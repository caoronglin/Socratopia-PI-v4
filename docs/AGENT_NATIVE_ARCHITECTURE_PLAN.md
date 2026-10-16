# Socratopia Agent-Native Architecture · Implementation Plan

Status: design baseline; not a release approval.

## Core invariants
- One stable logical course agent per course. Course data, textbook snapshots, transcripts, knowledge graph and model policy are isolated by course ID.
- AgentScope owns intelligent orchestration; deterministic Python services own time, grades, permissions, synchronization, archive commits and evidence validation.
- Pi is an optional, replaceable tool adapter, never an independent authority or second persistent learning loop.
- Model output never writes authoritative mastery or course completion directly.
- No uncontrolled autonomous loops, background calls, external tools or silent provider switching.

## Runtime
- Course supervisor selects a task-specific worker: tutor, prep, exercises, evidence/knowledge, visualization, evaluator.
- Each worker has an explicit harness: input/output schema, allowed tools, model profile, max turns, wall-clock timeout, token/cost budget, source requirements, fallback, human approval boundaries.
- Tools registered through AgentScope Toolkit expose typed interfaces; file/network access remains disabled unless a scoped service adapter explicitly grants it.
- Lazy import, bounded concurrency, model-client reuse where safe, no in-memory cross-course conversation history.
- Provider configuration is per task, with per-course overrides and credential references stored outside course exports.
- Suggested budgets: tutoring 1-3 turns, deep explanation 3-6, graph extraction 2-4, visualization build/test/fix max 3, independent question review max 2.

## Course lifecycle
DRAFT -> PREPARING -> READY -> ACTIVE -> PAUSED -> COMPLETED -> ARCHIVED.
RESTORED creates a new version/cycle referencing the archived snapshot. No rewriting historical grades.
Transitions require server-side preconditions and append-only audit events; archival freezes a manifest of all included assets, source versions and SHA256 checksums.

## Knowledge graph
- Nodes: Course, Chapter, Concept, Prerequisite, Evidence, Question, LearningObjective, Misconception.
- Typed edges with provenance, confidence, source span, textbook version, reviewed status and timestamp.
- Separate explicit textbook facts from inferred relationships; unreviewed inferred edges cannot be cited as facts.
- Begin with SQLite adjacency/edge tables; evaluate a dedicated graph database only after scale/performance evidence.
- Retrieval combines text passages and reviewed concept relationships, then runs existing citation checks.

## Interactive learning
- Explain -> example -> student action -> immediate feedback -> transfer challenge.
- Use Ant Design for workspace, AntV for interactive graphs and visualizations, mobile Ant Design components for mobile.
- Visualization agents produce declarative, schema-validated graph specs by default; generated websites must run in sandboxed isolated origins with no credentials, no arbitrary host network and explicit preview approval.
- Course examples can be sourced via opt-in Exa/Firecrawl/Tavily adapters, retaining URL, date, license, quote span and verification status.
- Image generation is optional, task-gated and attributed; no automatic images for every answer.

## Sync and archive
- WebDAV/S3 via separate deterministic service interfaces. Never give model agents raw cloud credentials.
- Default manual upload/download; content-addressed snapshots, checksum verification, encryption options, dry-run diff, conflict detection, rollback.
- Explicit opt-in for scheduled sync; do not silently overwrite newer remote or local data.
- Never export tokens, model credentials or other users' data.

## Implementation phases and gates
P0: fix existing Playwright regression, baseline CI and packaged executable smoke checks.
P1: task router, provider profiles, AgentScope Toolkit adapters, isolated course harnesses, negative tests for unauthorized tools.
P2: knowledge graph schema/extraction/provenance and citation validation; cross-course and textbook-revision tests.
P3: lifecycle state machine, immutable archive manifests, restore and checksum/tamper tests.
P4: visualization sandbox, educator persona evaluation, real lesson examples and mobile accessibility.
P5: WebDAV/S3 manual snapshot flows, network failure/conflict/retry tests.
P6: Linux x86_64, Windows x86_64, macOS arm64/x86_64 packaging and extracted binary smoke tests; release only on green required gates.

## Acceptance criteria
- Offline deterministic unit tests and contract tests pass; no live model required.
- At least two course identities and independent histories verified; zero cross-course leakage.
- Every agent task respects iteration/time/tool budgets; malformed outputs fail closed.
- No graph relation without provenance; inferred links never silently become verified facts.
- Archive/restore round trip matches hashes; tampering and concurrent edits are detected.
- WebDAV/S3 failures do not corrupt local state; no credentials enter exported archives.
- Browser desktop/mobile e2e passes with current UI labels; accessibility checks pass.
- All target platform artifacts pass extraction and launch smoke tests with SHA256 published.
- Release remains blocked if any required job fails. Never report mock-model tests as live-provider validation.

## Execution constraints
Read current repository and official APIs before modifying each module; implement in small PR commits; avoid hard-coded host paths and needless refactors. Maintain a concise reproducible test log and migration notes. Do not rename repository or publish releases until quality gates pass and release name is confirmed.
