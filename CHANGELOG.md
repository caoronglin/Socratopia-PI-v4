# Changelog

## 0.0.1

### Added
- 外部 Skill 隔离审查：`quarantine/sources.json` + `docs/SKILL_TRIAGE.md`（版本/许可/复合哈希/裁决/运行权限）。
- Deterministic runtime core（按 v4 契约重写）：`scripts/{course_runtime,task_queue,review,assessment,build_reteach_queue,prepare_after_upload}.py` + `scripts/lib/`。
- 课程知识图谱：`scripts/ontology.py`（append-only JSONL + 派生 projection）、`SYSTEM/schemas/ontology.schema.json`、`learning/references/graph.md`；mastery 字段禁止入库。
- 本地检索：`scripts/local_search.py` + `scripts/vector_index.py`（本地、可再生、非权威）+ `learning/references/local-search.md`。
- 门控外部能力：`scripts/external_research.py`（默认离线；fetch 需 `--authorize` 且 `SOCRATOPIA_EXTERNAL=1`；只进 `SOURCES/_external/`）+ `learning/references/external-research.md`。
- 参考合并：`learning/references/{pedagogy,reflection,courseware}.md`；`tutor/references/{persona,style,self-improving}.md`（dialogue.md 归并入 persona.md）。
- 测试：`tests/test_{runtime_core,ontology,reflection_split,local_search,external_research,courseware}.py`（共 80 项，含负向矩阵）。

### Changed
- `pi_arch_doctor.py`：新增 active-skill=3 冻结、quarantine 清单、必需 runtime 工具契约、malformed ontology JSONL 检查。
- `scaffold_course.py`：创建 `DATA/<course>/ontology/`。

### Boundaries preserved
- Active Skill 恒为 3；`AGENTS.md` kernel 未增长；`PROGRESS.md` 仍是唯一掌握事实源；外部内容只作数据；外部/远程操作逐次授权、key 只走 env。

## 4.0.0-pi.alpha.1

### Added
- PI-native `AGENTS.md`, three on-demand Skills and five prompt templates.
- Structured runtime schemas for course state, handoff and durable tasks.
- Architecture doctor and non-destructive course scaffold script.

### Changed
- Session/Teaching Unit/Chapter semantics separated.
- Tutor personas reduced to compact classroom profiles.
- Cross-tutor learning handoff moved from SOCIAL/relationship inference to structured runtime state.
- Runtime readiness made orthogonal instead of one linear state chain.
- Context budget made relative to model window rather than fixed absolute token target.

### Removed from active control plane
- Root `CLAUDE.md` as Socratopia router.
- `AGENT_SYSTEM_PROMPT.md` compatibility prompt.
- Legacy knowledge/works skills.
- Hard dependency on Claude subagents and Windows-specific tool rules.
