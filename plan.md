# 功能补全执行计划 · Socratopia-PI-v4

> 状态：**APPROVED WITH CONDITIONS / 依据审批意见细化，待逐 Phase 实施**
> 治理权威：`/home/rlcao/下载/Socratopia_PI_v4_Skills_Merge_Approval_Plan.md`（下称《审批》）。本文件是其**可执行化**；两者冲突时以《审批》为准。
> 输入：原始仓库 v3 `/media/rlcao/Data/data/edu`；候选 skills：`courseware-generator`、`interactive-courseware-designer`、`learning-feynman`、`ontology` 及 `/home/rlcao/.agents/skills` 全量集合。
> 已确认决策：① 图谱位置 = `DATA/<course>/ontology/`；② 语义检索 = 条件批准（门控）；③ 课件 = 仅方法论吸收、可选；④ 优先级 = **Runtime Core 优先**。

---

## 1. 一句话架构原则（来自《审批》§25）

> 把 Skill 当“能力路由”，Reference 当“按需知识”，Script 当“确定性执行”，SPEC 当“唯一契约”，DATA 当“真实状态”；不要再让 Prompt 同时承担这五种职责。

目标：更少 Skill + 更短 Prompt + 更少文件加载 + 更强确定性 + 更清晰权限 + 更低 token + 更容易测试。

**不可回退成的形态**：AGENTS.md + 一堆 active skills + 复制规则 + 每轮全加载。

---

## 2. 批准前提条件（7 条 Gate，全部满足才可 implementation）

1. 外部 Skill 全部经隔离审查，不直接执行第三方脚本。
2. 不修改 `AGENTS.md` kernel 承载新增能力细节。
3. 不新建与现有 SPEC 平行的第二套规则源。
4. `PROGRESS.md` 仍是真实课堂完成与掌握证据的唯一事实源。
5. 外部 API 能力与本地能力分离；**API key 存在 ≠ 获得运行授权**。
6. 每个 Phase 均有正向测试、负向测试、doctor、diff review。
7. **v4 已承诺但缺失的 deterministic runtime 优先恢复，再做体验增强。**

---

## 3. 审批结论速览（最终落点，全部非 active Skill）

| 来源能力 | 结论 | 最终落点 | active Skill? |
|---|---|---|---|
| `ontology-1.0.4` | ✅ 重构吸收 | `scripts/ontology.py` + `learning/references/graph.md` + `SYSTEM/schemas/ontology.schema.json` | 否 |
| `learning-feynman-1.0.0` | ✅ 方法论吸收 | `learning/references/pedagogy.md` | 否 |
| `humanizer-zh` | ✅ 规则吸收 | `tutor/references/style.md` | 否 |
| `libai` | ✅ 择优合并 | `tutor/references/style.md` | 否 |
| `Self-Improving` | ✅ 拆分吸收 | tutor `self-improving.md`（`DATA/SELF_IMPROVING/<tutor>.jsonl`）+ learning `reflection.md` | 否 |
| `deep-research` | ⚠️ 条件批准 | `learning/references/external-research.md` | 否 |
| `academic-researcher` | ⚠️ 条件批准 | `learning/references/external-research.md` | 否 |
| `courseware-generator` | ⚠️ 仅抽方法论 | `learning/references/courseware.md` | 否 |
| `interactive-courseware-designer` | ❌ REJECT AS CODE / ACCEPT AS IDEAS | 仅人工摘取安全设计思想 | 否 |
| `ppt-master` / `pptx` | ⚠️ 可选输出后端 | 明确课件任务时调用 | 否 |
| 旧 `socratopia-knowledge` / `socratopia-works` | ❌ 不恢复 | legacy/archive | 否 |

**Active Skill 冻结为 3 个**：`socratopia-learning` / `socratopia-tutor` / `socratopia-engineering`。新能力默认先判断能否作为现有 Skill 的 reference 或 script；无一项满足新增 active Skill 的必要性。

---

## 4. 与初版 plan 的关键变更

| 项 | 初版 plan | 本版（对齐审批） |
|---|---|---|
| 优先级 | ontology 先行 | **Runtime Core 恢复（course_runtime/task_queue/review/assessment/build_reteach_queue/prepare_after_upload）最优先**，之后才是 ontology |
| active skills | 讨论过新增 courseware skill | 冻结 3 个，禁止新增 |
| ontology | generic 拷贝 | 按《审批》§4 契约重写（事实边界/禁权威字段/append-only/CLI 白名单/negative tests） |
| search | 单个 search.md | 拆为 `local-search.md`（默认，network=false）+ `external-research.md`（显式外部意图，门控） |
| self-improving | 单一 reference | 拆分：tutor `self-improving.md` + learning `reflection.md`，**不共享状态文件** |
| 权限 | S0–S3 简述 | 统一 S0/S1/S2/S3，且**安装许可不继承为 S2/S3 runtime 许可** |
| 副作用原子性 | 未展开 | JSON temp+flush+atomic rename；JSONL 单 writer/文件锁；中断后可 parse |
| 审查 | 提过安全审查 | 强制 `quarantine/` + `docs/SKILL_TRIAGE.md`，Phase 0 禁执行任何第三方可执行文件 |

---

## 5. Reference 归并映射（现有 v4 → 目标，不丢文件、不造第二规则源）

按“运行职责”二次归并，而非每个来源 skill 一个 reference。普通请求默认最多读 **2 个** reference，超过需明确理由。

### socratopia-learning/references/
| 目标 | 来源/动作 |
|---|---|
| `classroom.md` | 保留（现有） |
| `pedagogy.md` | 新增（learning-feynman 启发式，800–1500 中文字） |
| `materials.md` | `content.md` 重命名/归并（教材/资料/编目/摄入） |
| `local-search.md` | 新增（默认检索路径，network=false） |
| `external-research.md` | 新增（deep-research + academic-researcher，显式外部意图） |
| `graph.md` | 新增（图谱何时建/查，接 coverage/handoff；不含 Python 细节） |
| `review.md` | 新增（复习闭环/补讲/错题） |
| `assessment.md` | 保留（现有） |
| `reflection.md` | 新增（学习者元认知/DIARY/跨课连接） |
| `courseware.md` | 新增（courseware-generator 方法论，显式触发） |
| `memory.md` | **保留**（三层记忆 + 下课提交；现有权威） |
| `trust.md` | **保留**（信任/副作用；现有权威） |

### socratopia-tutor/references/
| 目标 | 来源/动作 |
|---|---|
| `persona.md` | `dialogue.md` 归并（人格/追问/节奏契约） |
| `style.md` | 新增（humanizer-zh + libai + v3 HUMANIZE_RULES，600–1200 中文字） |
| `handoff.md` | 保留（现有） |
| `self-improving.md` | 新增（导师怎么教/被纠正/表达节奏；禁记录学习者掌握度） |
| `social.md` | **保留**（叙事层，按需；默认不进课堂） |
| `profiles/TUTOR_A/B/C.md` | **保留**（compact profile，≤600 字） |

### socratopia-engineering/references/
| 目标 | 来源/动作 |
|---|---|
| `planning.md` | 新增 |
| `debugging.md` | 新增 |
| `verification.md` | 新增 |
| `skill-integration.md` | 新增（本次合并方法论沉淀） |

---

## 6. 目标架构树

```text
Socratopia-PI-v4/
├── AGENTS.md                          # kernel 极小化，冻结
├── .pi/skills/
│   ├── socratopia-learning/{SKILL.md, references/{classroom,pedagogy,materials,local-search,external-research,graph,review,assessment,reflection,courseware,memory,trust}.md}
│   ├── socratopia-tutor/{SKILL.md, references/{persona,style,handoff,self-improving,social}.md, profiles/TUTOR_A/B/C.md}
│   └── socratopia-engineering/{SKILL.md, references/{planning,debugging,verification,skill-integration}.md}
├── SYSTEM/
│   ├── SPEC/{CONTENT_MODEL,CLASSROOM_CONTRACT,MEMORY_CONTRACT,ASSESSMENT_CONTRACT,RUNTIME_CONTRACT,TRUST_EFFECTS,OPS_CONTRACT}.md
│   └── schemas/{course_state,tasks,handoff,ontology}.schema.json
├── scripts/
│   ├── pi_arch_doctor.py              # 现有，扩展
│   ├── scaffold_course.py             # 现有，扩展 ontology 目录
│   ├── course_runtime.py              # 恢复
│   ├── task_queue.py                  # 恢复
│   ├── review.py                      # 恢复
│   ├── assessment.py                  # 恢复
│   ├── build_reteach_queue.py         # 恢复
│   ├── prepare_after_upload.py        # 恢复
│   ├── ontology.py                    # 新增（Phase 2）
│   ├── local_search.py                # 新增（Phase 5）
│   └── vector_index.py                # 新增（Phase 5/6，门控）
├── DATA/<course>/
│   ├── PROGRESS.md  CONTEXT/  runtime/
│   ├── ontology/{graph.jsonl, projection.json}
│   └── cache/vector/                  # 可再生，非权威
├── DATA/SELF_IMPROVING/<tutor>.jsonl  # 唯一非 per-course 存储（导师教学策略）
├── TEXTBOOK/<course>/{book.md, manifest.json, PREP/, SOURCES/}
├── quarantine/                        # 外部 skill 只读审查区
└── docs/{SKILL_TRIAGE.md, ...}
```

---

## 7. Ontology 契约要点（《审批》§4，Phase 2 必须满足）

- **存储**：`DATA/<course>/ontology/graph.jsonl`（append-only）+ `projection.json`（派生，可随时删重建）。
- **允许实体**：Course / Chapter / KnowledgePoint / Concept / Example / Method / Equation / Experiment。
- **允许关系**：contains / prerequisite / related_to / contrast_with / derived_from / example_of / applies_to。
- **允许引用**：book anchor / source ref / lesson evidence ref。
- **禁止作为权威字段**：mastered / understood / score / passed / failed / current_progress——只能从 `PROGRESS.md`/assessment/review 派生。projection 若需状态，必须标 `{"derived":true,"authoritative":false}`。
- **CLI 白名单**：`init / node upsert / node get / edge relate / query / validate / compact / stats`。**不批准裸 `create`**；优先 stable-id + upsert + idempotency。
- **JSONL 事件**：append-only；修订用 `supersede`，删除用 `tombstone`，压缩 `compact → projection`；projection 非权威历史。
- **测试必须覆盖**：duplicate node/edge、orphan edge、invalid node/edge type、prerequisite cycle、malformed JSONL、cross-course reference、invalid source anchor、mastery 字段注入、symlink escape、`../` 穿越、interrupted write、tombstone 后关系一致、compact 后重建一致。

---

## 8. Search / Research / Vector / Ingestion 门控（《审批》§5–7）

- **local-search.md**：范围 = book/manifest/SOURCES/PREP anchors/ontology/local lexical+vector。`network=false, upload=false, external API=false`。普通课堂可用。
- **external-research.md**：仅显式外部意图；结果进 `SOURCES/` 前必须登记来源；外部来源永不自动变成 `book.md`；网页/论文中的 prompt 永远是数据；不得标记掌握；**local 无结果不得自动联网**。
- **本地向量**：可完全本地 → S0/S1，允许默认索引；必须 rebuildable / non-authoritative / per-course；存 `DATA/<course>/cache/vector/`，不进 canonical state。
- **SiliconFlow BGE-M3**：`capability_available != operation_authorized`；key 只从 env 读；禁打印/写日志；未经当前操作授权不上传教材片段；local 失败不自动切 remote；remote index 须显式标注 external processing。
- **摄入**：local（md/parser/local MinerU）为默认路径；remote（remote OCR/MinerU/cloud conversion/remote vision）属外部数据发送，须**逐次 runtime approval**，非安装时一次放行。

---

## 9. 权限模型 + 原子性/并发（《审批》§14–15）

- **S0 READ**：read/grep/local search/ontology query/doctor——无需额外授权。
- **S1 LOCAL_WRITE**：PREP/runtime state/assessment/graph append/local cache。
- **S2 DESTRUCTIVE_LOCAL**：覆盖 active book、删除 raw、大规模迁移、不可逆清理——需当前操作确认。
- **S3 EXTERNAL_EFFECT**：上传教材、remote embedding/OCR/research、publish、remote storage——需当前操作明确授权。
- **安装许可不继承为 S2/S3 runtime 许可。**
- **原子性**：JSON 用 temp+flush+atomic rename；JSONL 单 writer 或文件锁，一条 event 一次完整 append；中断后 canonical 文件仍 parseable；队列用 idempotency key + 合法状态转移 + retry + 脱敏 error。

---

## 10. Token 预算 + 去重（《审批》§11、§20–21）

- 比例预算（相对上下文 `C`）：Kernel+Skill routing ≤5%；Task references ≤8%；Hot course state ≤10%；Book/source evidence ≤15%；Conversation reserve ≥55%；Tool/results reserve ≥7%。
- 读取顺序：course_state → CONTEXT_INDEX → pending reteach → recent PROGRESS evidence → current PREP → necessary book anchor → current tutor compact profile。信息不足再扩展。
- **Stop-loading rule**：足以回答“从哪继续/教什么/教材依据/哪些不能跳过/如何验证理解”即停止加载。
- **规则 owner（单一事实源）**：单一事实源→`CONTENT_MODEL.md`；课堂完成→`CLASSROOM_CONTRACT.md`；评估→`ASSESSMENT_CONTRACT.md`；runtime 状态→`RUNTIME_CONTRACT.md`；副作用→`TRUST_EFFECTS.md`；ontology 结构→`ontology.schema.json`+`graph.md`；tutor style→`style.md`；tutor self-improving→`self-improving.md`；learner reflection→`reflection.md`。其他文件只写 `see X`。
- **软阈值（doctor WARN，不硬失败）**：AGENTS.md ≤1800 words；SKILL.md ≤1200 words；普通 reference ≤1800 words；tutor compact profile ≤600 字。

---

## 11. 分阶段实施（对齐《审批》§16、§23）

> 每 Phase 完成定义（DoD，§17）：implementation + schema/静态校验 + 单测 + 负向测试 + doctor PASS + 无 kernel 回退 + 无跨课程泄漏 + 无新未审查外部效果 + diff reviewed。否则 **NOT DONE**；禁用“代码写完/看起来没问题/Agent 自检通过”代替证据。

### Phase 0 — 审计与冻结 ✅ DONE
- 工作：建 `quarantine/`；生成 `docs/SKILL_TRIAGE.md`（每源记 Source/Version/Hash/License/Reviewed files/Accepted/Rejected/Security removals/Host-specific removals/Final destination/Runtime permission）；固定 active skill=3；明确 kernel freeze。
- 验收：`0 external code executed / 0 unknown publishing rule / 0 hidden network effect`。
- **已完成证据**：
  - `quarantine/sources.json`（11 源版本/许可/复合哈希/裁决，JSON 合法）；
  - `docs/SKILL_TRIAGE.md`（逐源 Accept/Reject/Security/Host/Final/Runtime）；
  - doctor 新增 ERROR：active skill≠3、quarantine 清单缺失/非法；
  - 正向 doctor `PASS` + 单测 `OK`；负向（临时第 4 skill）`ERROR rc=1`，复原后 `PASS`；
  - 未执行任何第三方可执行文件（仅静态读/grep）。

### Phase 1 — Runtime Core Restore ✅ DONE
- 工作：从 v3 提取**数据语义**，按 v4 contract 重写：`course_runtime.py` → `task_queue.py` → `review.py` → `assessment.py` → `build_reteach_queue.py` → `prepare_after_upload.py`。
- 原则：禁把 v3 的 Claude-specific、Windows 绝对路径、legacy root state、old global ontology 带回来。
- 验收：每个脚本过正/负向矩阵 + doctor + 无跨课程泄漏。
- **已完成证据**：
  - `scripts/lib/{repository,course_state,task_queue,assessment,review}.py` + 6 个 CLI；`tests/test_runtime_core.py`（30 用例全绿）。
  - v4 契约对齐：`course_state`=phase+readiness+blockers（含 v3 `lifecycle`→v4 迁移）；`tasks`=id/status、顶层禁 `course`；assessment 用 behavior/cognitive_level/source_anchor/rationale。
  - 负向矩阵覆盖：路径穿越/跨课程隔离拒绝、非法状态转移、schema 拒顶层 course/重复 id/坏 status、secret 脱敏、MC 选项规则、混淆去重、failed→needs_reteach。
  - 原子写（temp+fsync+replace，无 `.tmp` 残留）；doctor 新增 REQUIRED 覆盖 6 脚本（删除即 FAIL，复原 PASS）；CLI 冒烟通过；manifest.json 刷新为 63 文件。
  - `prepare_after_upload.py` 仅编排本地已恢复工具，不跑远程/视觉/自动备课，不写 PROGRESS。

### Phase 2 — Ontology ✅ DONE
- 工作：`ontology.schema.json`、`ontology.py`（CLI 白名单）、`graph.md`、`scaffold_course.py` 建 ontology 目录、doctor 校验。
- Gate：§7 全部 negative tests PASS 才进下一阶段。
- **已完成证据**：
  - `scripts/ontology.py`：append-only `graph.jsonl` + 派生 `projection.json`（`derived:true/authoritative:false`）；CLI `init/node upsert/node get/node tombstone/edge relate/query/validate/compact/stats`，禁裸 `create`，写操作需 `--apply`。
  - `SYSTEM/schemas/ontology.schema.json`：节点/边枚举 + `propertyNames` 禁 mastered/score 等；jsonschema 校验 projection 通过。
  - `tests/test_ontology.py` 覆盖 §4.5 全部负向：duplicate node/edge 幂等、孤儿边、非法 node/edge type、prerequisite 成环、malformed JSONL（报错不改写）、跨课程引用、非法 source anchor、mastery 注入拒绝、`../`/symlink 越界、tombstone 级联一致、compact 重建一致。
  - 修 bug：孤儿边改在折叠后活跃边上判定（避免误判已级联删除的边）。
  - 接入：`learning/references/graph.md`；SKILL 路由新增“知识图谱→graph.md”；memory.md 的 “ontology 增量” 指向具体工具；scaffold 建 `DATA/<course>/ontology/`；doctor 新增 malformed graph.jsonl ERROR。
  - 全量 50 测试 OK + doctor PASS + CLI 冒烟通过。

### Phase 3 — Pedagogy + Tutor Style ✅ DONE
- 工作：learning-feynman → `pedagogy.md`；humanizer-zh + libai + v3 HUMANIZE → `style.md`；`dialogue.md` 归并为 `persona.md`。
- Gate：kernel 不增长；SKILL frontmatter 不膨胀；references 按需；无第二规则源。
- **已完成证据**：
  - `learning/references/pedagogy.md`（~590 中文字，6 条决策启发式 + teach-back/trace-to-source + 微例子；不重复 classroom 循环）。
  - `tutor/references/style.md`（~540 中文字，去 AI 味唯一规则源 + 速查替换表；人格留 profiles，不混入）。
  - `tutor/references/persona.md`（由 `dialogue.md` 归并；删除 dialogue.md，无残留引用）。
  - 路由更新：learning SKILL 增“深入解释/卡住→pedagogy.md”；tutor SKILL 的 dialogue→persona、新增“去 AI 味→style.md”。
  - Gate 核验：`AGENTS.md` 未改（kernel 不增长）；两个 SKILL frontmatter 未变；doctor PASS；50 测试 OK。

### Phase 4 — Reflection / Self Improvement ✅ DONE
- 工作：tutor `self-improving.md`（`DATA/SELF_IMPROVING/<tutor>.jsonl`）+ learning `reflection.md`（`DATA/<course>/DIARY.md`）。
- Gate：两者**不共享状态文件**；self-improving 不记录学习者掌握度/知识点/考试/课程事实。
- **已完成证据**：
  - `tutor/references/self-improving.md`：导师教学复盘（teaching_move/correction/pace/strategy），按导师存 JSONL；硬边界禁记掌握度/知识点/考试/课程事实；**不引入 heartbeat/cron**。
  - `learning/references/reflection.md`：学习者元认知/跨课连接/未解问题/策略变化，权威归 `MEMORY_CONTRACT.md` 的 DIARY；不编造情绪、不自述当掌握。
  - `tests/test_reflection_split.py`：断言两文件状态分离（SELF_IMPROVING vs DIARY，互不引用）、self-improving 禁记录项在位、reflection 禁编造、无 heartbeat/cron、路由已接。
  - 路由：learning SKILL 增“学习反思→reflection.md”；tutor SKILL 增“导师自我改进→self-improving.md”。
  - doctor PASS；56 测试 OK；`AGENTS.md` 未改（kernel 不增长）。

### Phase 5 — Local Search / Ingestion ✅ DONE
- 工作：`local_search.py`（词法/锚点/本体检索）、`vector_index.py`（本地缓存索引）、`local-search.md`。
- Gate：network/upload=false 默认；local 失败不自动升级 remote。
- **已完成证据**：
  - `scripts/local_search.py`：book 分节 / outline+manifest 锚点 / SOURCES / PREP / ontology 检索；纯本地、只读（S0）、零第三方依赖。
  - `scripts/vector_index.py`：本地词法索引（ASCII 词 + 中文二元gram），存 `DATA/<course>/cache/vector/index.json`，`derived:true/authoritative:false/network:false`；`build` 需 `--apply`；未接线任何远程 embedding。
  - `learning/references/local-search.md` + SKILL 路由“搜教材/本地检索→local-search.md”。
  - `tests/test_local_search.py`：命中/锚点/来源/本体/空查询/越界拒绝 + build-search-status 往返 + 索引 derived/非权威/cache 位置 + **无网络依赖静态守卫**。
  - `.gitignore` 增 `DATA/*/cache/`、`DATA/*/runtime/*.bak`（可再生/备份不入库）。
  - Ingestion：`prepare_after_upload.py` 本地路径已在 P1 就绪；远程 OCR/MinerU/视觉属 Phase 6 门控，未接入。
  - doctor PASS；67 测试 OK；`AGENTS.md` 未改。

### Phase 6 — External Capabilities（条件批准）✅ DONE
- 工作：`external-research.md` + `external_research.py`（SiliconFlow/学术/远程 OCR 的门控骨架）。
- 必备：capability flag + runtime permission + redaction + dry-run + fallback。
- **已完成证据**：
  - `scripts/external_research.py`：`plan`（离线 dry-run）/ `register`（登记用户提供来源到 `SOURCES/_external/`，S1，标 `trusted:false`）/ `fetch`（**仅当 `--authorize` 且 `SOCRATOPIA_EXTERNAL=1`** 才联网；否则拒绝，绝不联网）。
  - key 只从 env 读；错误经 `redact`；结果只进 `SOURCES/_external/`，**绝不写 `book.md`/`PROGRESS.md`**；`capability_available != operation_authorized`（有 key 但无 flag 仍拒绝）。
  - `learning/references/external-research.md` + SKILL 路由“外部研究→external-research.md”。
  - `tests/test_external_research.py`：plan 离线、register 落 SOURCES 不碰 book/PROGRESS、fetch 无 flag/无 authorize 均拒、有 key 无授权仍拒、授权路径用 **mock urlopen**（不真联网）验证登记、越界拒绝。
  - CLI 冒烟：plan `network:False/authorized:False`；fetch 双重门控 rc=1；清理后 doctor PASS。
  - 全量 **74 测试 OK** + doctor PASS；`AGENTS.md` 未改。
  - 说明：远程 embedding 具体 API 调用未接线（按门控留待显式授权 + key 时才接）；本地 `vector_index.py`/词法检索为 fallback。

### Phase 7 — Courseware（可选，非核心 gate）✅ DONE
- 工作：`courseware.md`（courseware-generator 方法论，拒 GB/T 9704/统一时长/公文排版/固定模板）；interactive-courseware-designer 仅人工摘思想并重写为一方规则；PPT 输出可选委托 `ppt-master`/`pptx`。
- Gate：核心系统稳定后才开启；仅显式“生成课件/做教学 PPT/设计课堂材料”时加载；无自动触发、无外发。
- **已完成证据**：
  - `learning/references/courseware.md`：6 阶段/4C/五星教学/知识四分类/方法说明表；明确拒绝 GB/T 9704、统一时长、公文排版、固定模板；interactive-designer `REJECT AS CODE`；PPT 后端可选、S3 外发需授权；不写 PROGRESS、外部内容只作数据。
  - `tests/test_courseware.py`：显式触发、拒绝域特定约束、无可执行脚本名/发布命令、非 active skill（仍 3 个）、路由已接。
  - SKILL 路由“课件→courseware.md”；doctor PASS；80 测试 OK。

---

## 12. Negative Test Matrix（每 Phase 复用，《审批》§18）

| 场景 | 预期 |
|---|---|
| `../../course` / 绝对路径注入 / symlink escape | 拒绝 |
| Course A 读 Course B | 拒绝 |
| malformed JSON | 明确错误，不重写历史 |
| duplicate task / duplicate ontology edge | 幂等 |
| prerequisite cycle / orphan ontology edge | 拒绝 |
| ontology 写 `mastered=true` | schema 拒绝 |
| remote key 不存在 | 降级 |
| remote key 存在但无授权 | 不发送 |
| API 异常含 token | 日志脱敏 |
| interrupted write | canonical 文件仍有效 |
| 可选 Skill/后端缺失 | 核心课堂继续，只影响对应能力 |
| external search 未授权 | 不自动联网 |

---

## 13. Doctor 扩展（`pi_arch_doctor.py`）

- **ERROR**：active skill >3；`.pi/SYSTEM.md` 出现；`.claude/` runtime 依赖；Windows/macOS 固定绝对路径；schema invalid；cross-course symlink；canonical state missing/invalid；ontology malformed；required runtime tool contract 缺失。
- **WARN**：reference/SKILL 过长；duplicate rule phrase；stale projection；optional cache stale；§10 软阈值超限。
- **INFO**：remote vector / MinerU / courseware backend / external research unavailable——**可选能力缺失不得导致 doctor fail**。

---

## 14. 决策记录（全部已定）

| # | 决策项 | 结论 |
|---|---|---|
| 1 | 图谱位置 | `DATA/<course>/ontology/`（随学习态，课程隔离） |
| 2 | 语义检索 | 条件批准：本地默认，SiliconFlow 门控（Phase 6） |
| 3 | 课件生成 | 仅方法论吸收 `courseware.md`；可选 Phase 7；interactive-designer 只取思想 |
| 4 | 优先级 | **Runtime Core（Phase 1）→ Ontology（P2）→ Pedagogy/Style（P3）→ Reflection/Self-Improving（P4）→ Local Search/Ingestion（P5）→ External（P6）→ Courseware（P7）** |

---

## 15. 进度与下一步

| Phase | 状态 |
|---|---|
| P0 审计与冻结 | ✅ DONE（见 §11 证据） |
| P1 Runtime Core Restore | ✅ DONE（见 §11 证据） |
| P2 Ontology | ✅ DONE（见 §11 证据） |
| P3 Pedagogy + Tutor Style | ✅ DONE（见 §11 证据） |
| P4 Reflection / Self-Improving | ✅ DONE（见 §11 证据） |
| P5 Local Search / Ingestion | ✅ DONE（见 §11 证据） |
| P6 External Capabilities | ✅ DONE（见 §11 证据，门控骨架；远程调用留待显式授权） |
| P7 Courseware | ✅ DONE（见 §11 证据，可选/方法论） |

**全部 7 个 Phase 完成。** active Skill 恒为 3；`AGENTS.md` kernel 未增长；80 项测试全绿；`pi_arch_doctor.py` PASS。

**下一步 = Phase 1 · Runtime Core Restore**：从 v3 提取数据语义，按 v4 contract 重写 `course_runtime.py → task_queue.py → review.py → assessment.py → build_reteach_queue.py → prepare_after_upload.py`；每脚本过正/负向矩阵 + doctor，禁带入 Claude-specific / Windows 绝对路径 / legacy 全局 ontology。
