# Skill Triage · 外部 Skill 隔离审查记录

> Phase 0 产物。治理权威：`Socratopia_PI_v4_Skills_Merge_Approval_Plan.md`。
> 审查方式：**只读静态审查**，未执行任何第三方 `*.py/*.sh/*.js/*.ps1`、install、network hook、publishing 命令。
> 第三方源**不复制进仓库**，仅在原只读位置审查；哈希登记于 `quarantine/sources.json`。
> 验收基线：`0 external code executed / 0 unknown publishing rule / 0 hidden network effect`。

## 摘要

| Skill | 版本 | 许可 | 有代码 | 网络 | 裁决 | 运行权限 |
|---|---|---|---|---|---|---|
| ontology | 1.0.4 | 无(clawhub) | 是 | 否 | 重构吸收 | local-only (S1) |
| learning-feynman | 无版本 | 无 | 否 | 否 | 方法论吸收 | local-only (ref) |
| humanizer-zh | git 91f3d39 | MIT | 否 | 否 | 规则吸收 | local-only (ref) |
| libai | 1.0.4 | 无(clawhub) | 否 | 否 | 择优合并 | local-only (ref) |
| self-improving | 1.2.16 | 无(clawhub) | 否 | 否 | 拆分吸收 | local-only (S1) |
| deep-research | 无版本 | 无 | 否 | 是 | 条件批准 | network-gated (S3) |
| academic-researcher | 1.0.0 | 无 | 否 | 是 | 条件批准 | network-gated (S3) |
| courseware-generator | 1.0.0 | 无(clawhub) | 否 | 否 | 仅方法论 | local-only (ref/output) |
| ppt-master | 无版本 | MIT | 是 | 是 | 可选后端 | output-only / S3 |
| pptx | 无版本 | Anthropic 专有 | 否 | 否 | 仅参考 | output-only (ref) |
| interactive-courseware-designer | 1.0.0 | 无(clawhub) | 否 | 是 | **拒代码/收思想** | none |

未发现真实密钥（仅 `sk-xxx`、`YOUR_KEY` 等占位）。未发现 `rm -rf`/`shutil.rmtree` 等破坏性调用。将被吸收为 reference/script 的能力均无隐藏网络效果。

---

## ontology
- Source: `/home/rlcao/下载/ontology-1.0.4`
- Version: 1.0.4 · License: 无 LICENSE（clawhub 发布）
- composite_sha256: `f60df5440f9d50a9ba0aab36a49d089b67fee9f50b5d89f1894455689f305f23`
- Reviewed files: SKILL.md, scripts/ontology.py（仅静态读，未运行）, references/schema.md, references/queries.md, _meta.json

### Accepted
- 类型化图 + 约束校验引擎思路；`resolve_safe_path` 防目录穿越；append-only JSONL；secret 间接引用（`secret_ref`，禁直接存 secret）。

### Rejected
- 原样 generic 实体集（Person/Project/Task…）与全局 `memory/ontology/` 路径；op 事件格式直接沿用。

### Security removals
- 全局存储路径 → 改为 per-course `DATA/<course>/ontology/`；补 `../`/symlink/跨课程 negative tests。

### Host-specific removals
- 无宿主耦合。

### Final destination
- `scripts/ontology.py`（按《审批》§4 契约重写：CLI 白名单、禁裸 create、禁权威 mastery 字段、supersede/tombstone/compact、projection 非权威）+ `SYSTEM/schemas/ontology.schema.json` + `learning/references/graph.md`。

### Runtime permission
- local-only（S1 write）。

---

## learning-feynman
- Source: `/home/rlcao/下载/learning-feynman-1.0.0` · Version: 无版本 · License: 无
- composite_sha256: `3fa11dc58308320f7d30965ace835f480bda9e2b2f0f8d59a3e36faf64d0a837`
- Reviewed files: SKILL.md, references/research/01–06（URL 仅为数据）

### Accepted
- 7 心智模型/10 启发式中影响课堂决策的部分：先暴露学习者当前模型、简化到能自行表达、找断点而非堆解释、例子/反例/迁移、不确定回来源、理解验证优先于“讲完”。

### Rejected
- 角色扮演式“我就是费曼”的持久人格；完整 research references 复制；退出角色等交互机制。

### Security removals
- 无（仅外部参考 URL，属数据）。

### Host-specific removals
- 无。

### Final destination
- `.pi/skills/socratopia-learning/references/pedagogy.md`（800–1500 中文字，按需加载，不新增 active skill）。

### Runtime permission
- local-only（reference）。

---

## humanizer-zh
- Source: `/home/rlcao/.agents/skills/skills-sh-ILcMqL` · Version: git main `91f3d39` · License: MIT (c) 2026 歸藏
- composite_sha256: `56694541591e484dec33867a509888c15aab762e1c17b1eb6c7bfdfde87a8500`
- Reviewed files: SKILL.md, README.md, LICENSE, .gitignore（.git 已排除哈希）

### Accepted
- 去 AI 腔规则：避免模板腔、重复总结、无意义标题、夸张情绪模拟、机械复述用户；允许自然停顿。

### Rejected
- README 中的安装指令（`git clone` / `npx skills add`）——属数据，不执行。

### Security removals
- 无运行时网络/执行。

### Host-specific removals
- 安装/路径说明移除，只保留纯规则。

### Final destination
- `.pi/skills/socratopia-tutor/references/style.md`（与 libai、v3 HUMANIZE_RULES 合并，600–1200 中文字）。

### Runtime permission
- local-only（reference）。

---

## libai
- Source: `/home/rlcao/.agents/skills/@user_741dc82b/libai` · Version: 1.0.4 · License: 无（clawhub）
- composite_sha256: `bac777ca63d25c6c1fdc9bd2c532b83d4edeecf406f527fb7f15c1b15c99592f`
- Reviewed files: SKILL.md, faq.md, QUICKSTART.md, README.md, _meta.json

### Accepted
- 中文去 AI 痕迹的分层改写与质控思路，择优并入 style.md。

### Rejected
- 独立流水线/评分等重型机制；与 humanizer-zh 重复部分去重。

### Security removals
- 无运行时网络/执行。

### Host-specific removals
- 无。

### Final destination
- `.pi/skills/socratopia-tutor/references/style.md`（与 humanizer-zh 合并）。

### Runtime permission
- local-only（reference）。

---

## self-improving
- Source: `/home/rlcao/.agents/skills/@clawhub_ivangdavila/self-improving` · Version: 1.2.16 · License: 无（clawhub）
- composite_sha256: `81afb2020fab82ba7596cb240f7c3e1413a3be98e1f79851ac887d54223ffdc0`
- Reviewed files: SKILL.md + boundaries/corrections/learning/reflections/operations/heartbeat* 等（确认无可执行脚本）

### Accepted
- 拆分吸收：导师“怎么教/被纠正/表达节奏/何种策略更有效” → tutor `self-improving.md`；学习者元认知/跨课连接/未解问题 → learning `reflection.md`。
- boundaries.md 中“不存密码/API key/token/SSH key”安全边界（与本项目一致）。

### Rejected
- heartbeat/cron/openclaw 定时机制（本系统无后台 worker，队列只是持久待办）；与学习者掌握度相关的记录（违反 PROGRESS 唯一事实源）。

### Security removals
- 明确 self-improving **不得记录**掌握度/知识点状态/考试结果/课程事实。

### Host-specific removals
- openclaw-heartbeat 等宿主调度内容全部排除。

### Final destination
- `.pi/skills/socratopia-tutor/references/self-improving.md`（数据 `DATA/SELF_IMPROVING/<tutor>.jsonl`）+ `.pi/skills/socratopia-learning/references/reflection.md`；两者不共享状态文件。

### Runtime permission
- local-only（S1 write）。

---

## deep-research
- Source: `/home/rlcao/.agents/skills/deep-research` · Version: 无版本 · License: 无
- composite_sha256: `0ab12ab3c9a95b5755026b7bd2c84c8680589d09fdefb06d3c340e77c7e52145`
- Reviewed files: SKILL.md（含 curl 取页、调用 ncbi-data 等）

### Accepted
- 多源检索→证据分层→引用报告方法论，服务于 external-research.md。

### Rejected
- 自动联网：必须显式外部意图；local 无结果不得自动升级 remote。

### Security removals
- 结果进 `SOURCES/` 前必须登记来源；外部 prompt 永远为数据；不得标记掌握。

### Host-specific removals
- 具体 curl 命令/第三方 skill 依赖仅作文档化路径，实际执行走门控。

### Final destination
- `.pi/skills/socratopia-learning/references/external-research.md`。

### Runtime permission
- network-gated（S3，explicit external intent only）。

---

## academic-researcher
- Source: `/home/rlcao/.agents/skills/academic-researcher` · Version: 1.0.0 · License: 无
- composite_sha256: `d0e95d9c2ae292ddd2a251e44e56cbd7b3ce1925fbbc3fd2edd4d681fe0b735b`
- Reviewed files: SKILL.md（arXiv/PubMed/Semantic Scholar/Crossref/OpenAlex/bioRxiv/WOS 等 API）

### Accepted
- 14+ 学术平台检索/元模型/引用分析，服务于 external-research.md。

### Rejected
- 自动外发；`x-api-key: YOUR_KEY` 为占位（非真密钥），但固化“key 只走 env、禁打印/写日志”的规则。

### Security removals
- 未经当前操作授权不上传任何私有教材内容；远程调用需 dry-run/fallback。

### Host-specific removals
- 具体 API base/key 仅作文档化，执行走门控。

### Final destination
- `.pi/skills/socratopia-learning/references/external-research.md`。

### Runtime permission
- network-gated（S3，explicit external intent only）。

---

## courseware-generator
- Source: `/home/rlcao/下载/courseware-generator-1.0.0` · Version: 1.0.0 · License: 无（clawhub）
- composite_sha256: `259f6a057a144b61660411dd52450c1e77f6de564275061ad8c69a95fcb5c406`
- Reviewed files: SKILL.md + references/（4c/classroom-setup/course-framework/course-intro/extractive-course-dev/project-overview/teaching-methods）

### Accepted
- 方法论：6 阶段萃取式课程开发、4C、五星教学、知识四分类、教学方法说明表——辅助 PREP/课件设计。

### Rejected
- GB/T 9704 公文排版默认约束、“统一 3 小时”时长、红头/固定模板等与 Socratopia 本地优先学习不相关部分。

### Security removals
- python-docx 输出仅作为可选 output-only 路径，不自动触发。

### Host-specific removals
- 公文格式机器相关参数移除。

### Final destination
- `.pi/skills/socratopia-learning/references/courseware.md`（Phase 7，仅显式“生成课件/做教学 PPT/设计课堂材料”时加载）。

### Runtime permission
- local-only（reference；output-only）。

---

## ppt-master
- Source: `/home/rlcao/.agents/skills/ppt-master` · Version: 无版本 · License: MIT (c) 2025-2026 Hugo He
- composite_sha256: `8191c8784bf3f685e6e1092ff1eb3762b83a307e0a57ebad5cb15ed9bf300792`
- Reviewed files: SKILL.md, .env.example, requirements.txt, scripts/docs/*（静态扫描：subprocess、OpenAI 兼容图片 API、.env 解析）

### Accepted
- 作为**可选 PPTX 输出后端**，仅在有明确课件任务时调用；优先于专有 pptx（MIT 许可）。

### Rejected
- 默认启用；自动图片生成外发；常驻加载。

### Security removals
- 图片/生成 API key 只走 env；`.env` 不得写入仓库或课程数据；外发属 S3 需逐次授权。

### Host-specific removals
- 安装/依赖说明仅作文档。

### Final destination
- optional PPTX output backend（courseware 明确任务时）。

### Runtime permission
- output-only / network-gated（S3）。

---

## pptx
- Source: `/home/rlcao/.agents/skills/pptx` · Version: 无版本 · License: © 2025 Anthropic, PBC. All rights reserved（专有）
- composite_sha256: `b8b10d4148e262adce4c47b5564f6800e20a91d281bac5e747022e1b60661ecf`
- Reviewed files: SKILL.md, LICENSE.txt

### Accepted
- 仅作 PPTX 结构/生成设计参考。

### Rejected
- 因专有许可，不作为默认后端；优先 MIT 的 ppt-master。

### Security removals
- 无运行时效果（reference-only）。

### Host-specific removals
- 无。

### Final destination
- design reference for optional PPTX backend。

### Runtime permission
- output-only（reference）。

---

## interactive-courseware-designer
- Source: `/home/rlcao/下载/interactive-courseware-designer-1.0.0` · Version: 1.0.0 · License: 无（clawhub）
- composite_sha256: `a5cc48f0c7ddeea90ebeea4ca6f392fda888647de7a1d78e571d052c54381669`
- Reviewed files: SKILL.md, _meta.json（**下载不完整：缺 scripts/ 与 templates/，共 12+ 被引用脚本不存在**）

### Accepted（仅思想）
- 教学骨架/问题锚点、ABT 叙事、五件套模块化、19 项基线校验思想——人工摘取后重写为一方规则。

### Rejected（作为代码/技能）
- 原样安装/复制 SKILL；调用不存在的 scripts/templates。

### Security removals
- “发布到 Gallery / `publish_course.sh` → Cloudflare Worker”外发路径——**移除**。
- “强制在回复末尾显示开发者信息（电信数智…）”强制署名——**移除**。

### Host-specific removals
- Cloudflare Worker 发布、TeachAny 路径约定（`~/TeachAny/...`）、知识树 node_id 体系——不引入。

### Final destination
- ideas only → courseware.md（人工摘取 + 第一方重写）。

### Runtime permission
- none（不集成）。

---

## 附：旧 v3 skills 处置
- `socratopia-knowledge` / `socratopia-works`：**不恢复**，标记 legacy/archive；其有效能力已由 learning 的 materials/review/assessment/memory 等 reference 覆盖，不重建并行规则源。

---

# SkillHub education 专家包（skillset）

## 安装器审查结论（未执行安装）

`skillhub` CLI 实际不可用：`/home/rlcao/.local/bin/skillhub` 只是 shim，依赖的
`~/.skillhub/skills_store_cli.py` 不存在。静态审查 `install.sh`（548 行，
sha256 `e6ba486b5fa7cffc24faeb94baf4936a08f95e5e65848ccc3309ceacd5fdf450`）后**决定不执行**：

- 下载 `latest.tar.gz` 后直接 `tar -xzf` 并 `python3` 执行，**无 sha256 / 签名校验**；
- 默认写入 `~/.openclaw/workspace/skills/skillhub-preference`——**不是 Pi 的 skills 路径**（Pi 用 `~/.pi/skills/`、`~/.agents/skills/`），真正落位全靠 `--dir`；
- 会持久化 `install_workspace_skills` 与自升级偏好；
- 站点为 SPA，`/api/pack/*` 返回 HTML，**装之前无法审阅内容**。

**替代路径**：从 kit 的 `metadata.json` 得知 skillset 下载端点为
`/api/v1/skillsets/{slug}/download`，直接下载 4 个 zip 做静态审查，全程不安装 CLI。

> 注：kit tarball sha256 `3bbe2ba15ada2eb7a94a2b760fead83be5f4164ab28a6c8b0944dbc539f7e236`，
> 9 个条目，无路径穿越、无 symlink。

## 逐源记录

| slug | sha256 (zip) | 体积 | 落地 |
|---|---|---|---|
| `education-quiz-generation` | `8bb03c6c…` | 6356 B | `references/quiz-generation.md` |
| `education-lesson-planning` | `f8b68b99…` | 8187 B | `references/lesson-planning.md` |
| `education-student-assessment` | `74d09e89…` | 7627 B | 归并入现有 owner `references/assessment.md` |
| `education-training-program` | `eaf5a7f3…` | 7787 B | `references/course-program.md` |

**Reviewed files**：`manifest.json` + `identify.md`（每包仅此两个文件，`files[].sha256` 已逐包校验通过）。

**has_code**: false　**network**: false　**Security**: 无脚本、无网络调用、无凭据读取、无 prompt-injection 措辞。

### Accepted（仅思想，重写为一方规则）
- 难度分级（基础/中等/拔高）→ 按认知操作而非题量分级。
- 题型矩阵 → 辨析/因果/反例/迁移/先修五型，由图谱关系选型。
- 教学评一致性 → 目标—提问—证据三者对齐，错位即降级。
- 分层支架 → 同一目标的支架深度（A/B/C），非不同目标。
- 错因分类 → 概念缺口/机制断链/误读/流程/过度推广/检索失败。
- Rubric 多维 → 用于定位差距维度，不产出总分排名。
- 单元先修 + 证据型里程碑 → 替代时间型/进度型里程碑。

### Rejected
- 编排式前提「你已安装以下 Skill，请按步骤串联使用」：24 个 child skill **未安装**，前提为假。
- K12 / 新课标 2022 / 九大学科 / 考点作战地图：与课程隔离的个人学习模型无关。
- 批量成果包（题库/试卷/教案/培训资料全套）：违反最小上下文预算。
- 「自动批改」「一键生成」：自动判定只能产生 `needs_review`，不得替代真实证据。
- **掌握度图谱 / 掌握度打分**：直接冲突 `SYSTEM/schemas/ontology.schema.json` 的 mastery 字段禁令。
- 家长沟通 / 成绩单评语 / 学员成长档案 / 证书模板 / 营销文案：机构与外发产物（S3）。
- Claude Code / Codex 导出声明：宿主专属，违反 `ARCHITECTURE.md`。

### Final destination
- 3 个新 reference + 1 处归并；**active skill 仍为 3**，doctor PASS。

### Runtime permission
- none（仅 reference，`local-only`）。

---

# 消融测试报告（ablation）

工具：`tests/test_ablation.py`（21 项）。方法：逐个移除单一护栏，然后验证失败**被检出**。
问题不是「护栏在不在」，而是「护栏被拿掉之后，有人会发现吗」。没有检出的护栏是装饰品。

## 结论

| 护栏 | 消融后 | 判定 |
|---|---|---|
| active skill 恒为 3（doctor 门禁） | doctor 静默通过；测试套件失败 | **load-bearing**（双重） |
| canonical state 校验（doctor） | doctor 静默通过 | **load-bearing**（测试套件兜底） |
| `manifest.json` 交叉校验 | doctor 静默通过 | **load-bearing**（测试套件兜底） |
| quarantine 清单必需 | doctor 静默通过 | **load-bearing**（测试套件兜底） |
| handoff 反占位伪造 | 仍报错（rc=1） | **load-bearing** |
| handoff 模板无占位 | `test_handoff.py` 失败 | **load-bearing** |
| ontology 禁止字段（代码） | `test_ontology.py` 失败 | **load-bearing** |
| ontology 禁止字段（schema） | ~~静默~~ → 已修 | **曾为装饰品，已修复** |
| 课程名校验 | `test_runtime_core.py` 失败 | **load-bearing** |
| 路径包含性检查 | 合法课程名不触发；**symlink 逃逸触发** | **load-bearing（仅 symlink）** |
| 原子写 `os.replace` | `test_runtime_core.py` 失败 | **load-bearing** |
| secret 脱敏 | `test_memo_sync.py` 失败 | **load-bearing** |
| memos 双门控 | `test_memo_sync.py` 失败 | **load-bearing** |
| Stellar 导出 `--apply` | 无 flag 时未写文件 | **load-bearing** |
| MinerU `--confirm-upload` | `test_mineru_ingest.py` 失败 | **load-bearing** |
| 本地优先：不支持格式拒绝 | `test_mineru_ingest.py` 失败 | **load-bearing** |
| 三月七「元气不提降门槛」 | `test_tutor_profiles.py` 失败 | **load-bearing** |
| 外部包拒绝域（掌握度图谱） | `test_skillhub_education.py` 失败 | **load-bearing** |

## 消融查出的一处真实缺陷（已修）

`SYSTEM/schemas/ontology.schema.json` 的 `propertyNames` 禁止字段集**没有任何代码执行**，
只有 `scripts/ontology.py:FORBIDDEN_PROPS` 在运行时生效。两者可以静默漂移 ——
把 schema 里的 enum 清空，整套测试依然全绿。**schema 层的掌握度禁令原本是装饰品。**

修复：`tests/test_ontology.py::test_schema_forbidden_props_match_code` 断言
schema 的禁止集合与代码的 `FORBIDDEN_PROPS` **完全相等**。此后任一侧被改动都会失败。

## 方法论备注

- **消融必须有对应夹具**：路径包含性检查在「非法课程名」下永远不触发（被
  `validate_course_name` 抢先拦截）；只有构造 `DATA/evil -> 外部目录` 的 symlink 才能证明它有效。
  没夹具的消融是无效实验。
- **多道门要分别消融**：doctor 门禁被移除后，测试套件仍会失败 —— 这说明防线是分层的，
  单点移除不等于失守。报告必须区分「哪一层还在」。
- **检测信号是退出码，不是报错文案**：改写文案不等于移除护栏。
- **必须用 subprocess 探测**：在测试进程内 `import` 会解析回原始仓库，改到的是副本、
  跑的是原件，实验结果无效。
