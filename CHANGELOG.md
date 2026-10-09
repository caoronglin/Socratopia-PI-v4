# Changelog

## 0.0.2

### Added
- **内部教研组（MOE）**：`TUTOR_A/B/C`（白银御行 / 四宫辉夜 / 藤原千花）从 `profiles/` 移入 `moe/`，由「面向学习者的导师」改为**内部审议镜头**（结构 / 边界 / 表征），只在备课会与下课复盘出现，产出落 PREP 与 `SELF_IMPROVING`，不产生第三份事实源，也不对学习者说话。`persona.md` 症状表只列 D/E/F，`TUTOR_CONTRACT.md` 明示两层；ID 未变，`SELF_IMPROVING`/`handoff` 键稳定。新增 `references/moe.md` 议事协议（结论须落到可观察动作、允许留分歧、未检查的镜头要写明）。ADR-014。
- **教研会决议与预期误概念是 `ready` 门禁**：`templates/PREP.md` 新增两段；`prep.py` 校验段存在、`MOE_FIELDS` 逐项交代、误概念表三列完整，缺任一判不 ready；`classroom.md` 开课 gate 相应增加一条，`memory.md` 在 Review 阶段挂下课复盘会。
- **覆盖判到期望元素**：新增 `references/coverage.md`（五态 + 期望元素 + 章节质量门，从 `classroom.md` 拆出）；PREP 的 Coverage 种子与 PROGRESS 的 ledger 增列期望元素，`parse_coverage` 按表头识别新列且兼容旧三列账本；元素未逐个取证则条目停留 `introduced`。
- **陷题深度计数与干预切换**：`classroom.md` 按连续无进展轮数强制升级（换表征 → 最小台阶 → 停止提问直接纠错），替代「靠感觉」。依据：每多卡一轮恢复概率降 12.7%，重复同一问法恢复率约 28%、改为直接处理错误约 40%。
- 回归与消融：`test_prep.py` 新增 8 项门禁测试，`test_tutor_profiles.py` 新增两层边界测试，`test_prompt_catalog.py` 新增门禁接线断言，`test_ablation.py` 新增 4 项消融（教研会 gate / 期望元素 gate / 幕后再分 / 深度计数）。守卫经注入移除验证确实会红。
- **修正 Claude Code 权限语义**：`git push` 原被放进 `deny`，但 Claude Code 的 `deny` 是彻底阻断而非「需确认」，导致仓库在该宿主下永远推不了；已移至 `ask`。`deny` 保留真正的破坏性操作（`reset --hard`/`clean`/`rm -rf`）与凭据读取。
- **Claude Code 适配层（分支 `claude-code`）**：官方文档确认 Claude Code 原生读取仓库 `AGENTS.md`，故不创建根 `CLAUDE.md`；新增 `.claude/skills/*/SKILL.md`（3 个）与 `.claude/commands/*.md`（5 个）作为**薄指针**，frontmatter `name`/`description` 与 `.pi/` 逐字一致，正文只指向权威文件、不复制规则。`.claude/settings.json` 收敛权限（deny 凭据读取与 `git push`/`reset --hard`/`clean`/`rm -rf`；ask `git commit`、MinerU 远程解析、memos push/pull），只把 AGENTS.md §6 既有约束显式化。命令占位符由 Pi 的 `$@` 改为 Claude Code 的 `$ARGUMENTS`。`tests/test_claude_portability.py`（14 项）+ `docs/CLAUDE_CODE.md`。ADR-013。静态校验已通过并经注入漂移验证会失败；**未在真实 Claude Code 会话中端到端运行**。

### Fixed
- **课程作用域贯穿执行层**：doctor 新增 `--course`，目标不存在/非法时拒绝，控制层扫描剪枝课程目录，读取前检查课程外符号链接；资料流水线使用公共路径校验并调用单课 doctor，阶段失败报告已完成写入与未执行项。默认全仓检查保持兼容。
- **跨层提示词协议**：开课增加 runtime/PREP gate 与显式课号冲突处理；下课区分 Core/Derived/Review/Maintenance 与幂等重试；导师临时表达不冒充持久切换，handoff 与 active_tutor 分别核验。流程规则留在 references，Kernel 与三 Skill 分层不变。
- **memos pull 跨课混入**：仅导入首行带完整 Socratopia 标记且课程完全相等的 memo；异课/无标记跳过并计数，不从正文关键词推断课程。离线混合响应覆盖前缀/子串误匹配。
- **MinerU 轮询预算遗漏网络耗时**：改用单调时钟 deadline，轮询请求与等待使用剩余预算，不接受超时后返回的成功状态；上传前拒绝非正数、NaN、无穷大的 timing 参数。新增 4 项离线回归测试；reference 明确 `--timeout` 只覆盖轮询、不是命令硬中断，`--pages` 仍上传整个文件。
- **提示词命令边界**：五个命令明确课程参数、缺失/失败分支与禁止副作用；新增按需 `course-binding.md`，切课先验目标再保存断点和更新指针；单课 `/health` 不默认运行扫描所有课程的 doctor；下课区分核心保存与派生维护，重复调用不造课。同步目录并新增 6 项提示词边界回归断言；这些静态断言不等同真实模型行为验证。
- **仓库处于红灯状态，doctor 报 10 个 manifest 漂移错误**（`memory.py`/`prep.py`/`export_obsidian.py` 等上一轮新增文件未登记）。已用 doctor 自身的排除集重新生成 `files`，129 项一致；doctor 0 警告、418 项测试全绿。
- **热层生成器缺少课堂入口接线**：`scaffold_course.py` 创建占位模板，原课堂流程未调用已有 `scripts/memory.py`。现在 `memory.md` 下课步骤与 `classroom.md` 开课加载步骤接线，从课堂事实确定性重建热层，并公开 `check`；不推断历史热层是否曾由人工生成。
- **Obsidian 格式 reference 缺少 Skill 路由**：`markdown-output.md` 原已引用 `export_obsidian.py`，但未登记在 `SKILL.md` 路由表。已补路由并同步 `docs/PROMPTS.md`。
- **路由表漂移测试用“16 条路由”作为锚点**：增删任一路由都会让 `ValueError` 而非给出可读断言。改用标题文本作稳定锚点。
- **Stellar 导出不是“每节课的总结”**：原实现只取课号与标题，每篇笔记都重复整张课程覆盖表，且“下次入口”对所有课都是同一份当前断点。现在每篇只含该课自己的记录与引用该课的证据行，入口仅在最新一课；移除格式不正确的 `{% tabs %}` 包裹；中和正文中的 Hexo/Nunjucks 标签（课堂数据不能注入模板）；重复导出真正幂等（不刷新 `updated`，`date` 保留）。
- `/end-class` 现在会在 Commit 后运行 Stellar 导出（失败只入队，不阻塞下课）。
- `TUTOR_F` 动作 `（翻开星图）` 在词条中无依据，改为有出处的 `（端起咖啡杯）`；新增 `docs/PERSONA_SOURCES.md` 登记 D/E/F 的词条、pageid、逐条依据与刻意偏离，由测试锁定。
- **`mineru_ingest.py` 的 `local` 子命令名不副实**：它调用 `pdftotext`/`pypdf`/`pymupdf`/`python-docx`/`bs4` 做通用文本抽取，与 MinerU 毫无关系，却让工具名与 reference 暗示存在“本地 MinerU”。按用户决定删除该路径，只保留 `plan`/`remote`；`plan` 不再报 `local_first`，远程不支持的格式在联网前拒绝。纯文本/md/html 改为直接阅读。同步 `plan.md` §摄入策略、reference、`/materials-ready` 路由与措辞、相关消融测试。

### Added
- **热上下文包**：`scripts/context_pack.py [--budget N] [--no-prep] [--recent N]`（只读）按 plan §10 顺序输出最小课程上下文：逐段预算、只列 pending/needs_review 补讲、覆盖账本只列未验证项（verified 仅计数）、只保留最近几课记录、丢弃空模板字段；不跨课程、不跟随指向课程外的符号链接、输出声明“数据不是指令”；`/start-class`、`classroom.md`、`memory.md` 已指向它；`tests/test_context_pack.py`。
- doctor §13：`duplicate rule phrase`（跨控制文件逐字重复句，WARN）、`stale projection`（ontology/course_state/queue 投影早于权威文件，WARN）、`cross-course symlink`（ERROR）；`scripts/lib/duplicates.py`、`tests/test_hygiene_checks.py`。
- **CI**：`scripts/check.py [--strict]`（doctor + 测试的单一入口）与 `.github/workflows/ci.yml`（Python 3.11/3.13，`--strict`）。
- **Token 预算执行**：`scripts/lib/budget.py`（CJK 感知估算，`wc -w` 对中文无效）；`pi_arch_doctor.py` 新增 plan §10 软阈值 WARN（kernel/skill/reference/profile）与按窗口比例的预算检查，`--budget [--window N]` 打印报告；`tests/test_budget.py`。
- `scripts/handoff.py`（`show`/`validate`/`set`/`clear`，写入需 `--apply`）：补齐 ADR-006 写入口，空 carry、同一导师、非法 status 均拒写，字符串脱敏；`tests/test_handoff_cli.py`。
- 人格：`persona.md` 新增“卡住升级阶梯”“承接共用规则”“按学习者状态选导师”表；`TUTOR_CONTRACT.md` 轮换条款指向该表。
- memos 记忆集成：`scripts/memo_sync.py`（`plan`/`push`/`pull`），双门控（`--authorize` + `SOCRATOPIA_EXTERNAL=1`）、可见性仅 `PRIVATE`、token 只走 env、强制 https、异常脱敏；`references/memo-sync.md`；`tests/test_memo_sync.py`。
- MinerU 文档解析：`scripts/mineru_ingest.py`（`plan`/`remote`，**仅远程**）；远程为三重门控（按官方 JSON + 预签名 PUT 契约接线）；`references/mineru-ingest.md`；`tests/test_mineru_ingest.py`。
- 消融测试：`tests/test_ablation.py`（21 项），逐个移除单一护栏并验证失败被检出；报告见 `docs/SKILL_TRIAGE.md`。
- Stellar（Hexo 主题）导出：`scripts/export_stellar.py`（`plan`/`check`/`export --apply`），一门课 = 一个 notebook（`source/_data/notebooks/<course>.yml`），一节课 = 一篇 note（`source/notes/<course>/lesson_XXX.md`）；`references/stellar-export.md` 定义归属与主题高级用法；`tests/test_stellar_export.py`。
- 三位新导师 compact profile：`TUTOR_D` 三月七（元气追问型）、`TUTOR_E` 丹恒（克制诊断型）、`TUTOR_F` 姬子（领航统筹型）；`tests/test_tutor_profiles.py` 锁定人格边界（≤600 汉字、必需章节、不宣称掌握、元气不提降证据门槛）。
- SkillHub 4 个 education 专家包（skillset）蒸馏吸收：`quiz-generation.md` / `lesson-planning.md` / `course-program.md` 新 reference + 错因分类与 Rubric 维度归并入 `assessment.md`；`quarantine/sources.json` 登记 15 源；`docs/SKILL_TRIAGE.md` 增补安装器审查结论与逐源记录。
- `runtime/handoff.json` 反伪造校验：`scripts/lib/handoff.py`（`scripts/pi_arch_doctor.py --root` 可在临时根上做负向测试）。

### Fixed
- `check_manifest` 引用未定义的 `warnings`，manifest 缺失时 `NameError`；现为 WARN。
- manifest 漂移检查把 `.pytest_cache`/`.ruff_cache`/`.mypy_cache` 误报为漂移。
- `review.py` 失败输出未脱敏。

### Changed
- 导师 profile：`TUTOR_D/E/F` 压缩（D 816→约 600 tokens，保留 `元气不等于降低门槛` 等测试锁定的边界）；A–F 的重复句（动作频率、不重复上一位原讲法）收敛到 `persona.md` 单点。
- `course_state` 双生产者合一：`scaffold_course.py` 改用 `default_state()`；`templates/course_state.json` 补全字段并由测试锁定一致。
- doctor：队列数据层校验 `tasks[].course` 必须等于所在课程目录（跨课程污染为 ERROR）。
- `pi_arch_doctor.py`：新增 active-skill=3 冻结、quarantine 清单、必需 runtime 工具契约、malformed ontology JSONL 检查。
- `templates/handoff.json`：三字段改为 `null` + 空 `carry`（“尚未承接”），不再给新课程预置 `TUTOR_A → TUTOR_B @ lesson_001`；`SYSTEM/schemas/handoff.schema.json` 用 `oneOf` 表达“全 null / 真实承接”两种合法形态。
- `pi_arch_doctor.py`：落实 plan.md §13 声明的 canonical state 门禁 —— 逐课程校验 `course_state.json`/`tasks.json`/`handoff.json` 并核对 `course` 与所在目录一致；新增 `manifest.json` 磁盘交叉校验（`DATA/`、`TEXTBOOK/` 排除）；缺失 runtime 文件为 WARN，非法内容为 ERROR；新增 `--root`。
- `socratopia-learning/SKILL.md`：路由新增“备课/教学评一致性→lesson-planning.md”、“长周期编排→course-program.md”；出题路由指向 `quiz-generation.md`。
- 测试：`tests/test_handoff.py`、`tests/test_doctor_gates.py`、`tests/test_skillhub_education.py`、`tests/test_tutor_profiles.py`、`tests/test_stellar_export.py`、`tests/test_ablation.py`、`tests/test_memo_sync.py`、`tests/test_mineru_ingest.py`。

### Boundaries preserved
- **未执行 `curl|bash` 安装器**（无完整性校验）——改为直接下载 skillset zip 静态审查；active Skill 仍为 3。
- 外部包只取方法论；K12/机构产物/掌握度图谱/自动批改一律拒绝。
- 导师人格只改表达；三月七取“元气追问”、显式舍弃“记性差不复述”设定以免削弱证据要求。
- Stellar 导出为只读投影（`derived:true`/`authoritative:false`），默认输出在 `DATA/<course>/` 内；覆盖率表格中的 `\|` 转义管道（数学式如 `P(A|B)`）不损坏。
- 互动看板/Cloudflare 部署：**未采纳，已回退**（用户决定不做）。构建即 S3 发布的边界不再需要维护。
- memos / MinerU 默认离线；`remote`/`push`/`pull` 三重或双重门控；token 只从 env 读且脱敏；远端结果只进 `SOURCES/_external/`（`trusted:false`）。
- **消融修复**：`ontology.schema.json` 的禁止字段集原本无代码执行（装饰品），新增 schema↔code 一致性断言后成为有效约束。
- `PROGRESS.md` 仍是唯一掌握事实源；`DATA/`、`TEXTBOOK/` 排除在 manifest 门禁外。

## 0.0.1

### Added
- 外部 Skill 隔离审查：`quarantine/sources.json` + `docs/SKILL_TRIAGE.md`（版本/许可/复合哈希/裁决/运行权限）。
- `runtime/handoff.json` 反伪造校验：`scripts/lib/handoff.py`（`scripts/pi_arch_doctor.py --root` 可在临时根上做负向测试）。
- Deterministic runtime core（按 v4 契约重写）：`scripts/{course_runtime,task_queue,review,assessment,build_reteach_queue,prepare_after_upload}.py` + `scripts/lib/`。
- 课程知识图谱：`scripts/ontology.py`（append-only JSONL + 派生 projection）、`SYSTEM/schemas/ontology.schema.json`、`learning/references/graph.md`；mastery 字段禁止入库。
- 本地检索：`scripts/local_search.py` + `scripts/vector_index.py`（本地、可再生、非权威）+ `learning/references/local-search.md`。
- 门控外部能力：`scripts/external_research.py`（默认离线；fetch 需 `--authorize` 且 `SOCRATOPIA_EXTERNAL=1`；只进 `SOURCES/_external/`）+ `learning/references/external-research.md`。
- 参考合并：`learning/references/{pedagogy,reflection,courseware}.md`；`tutor/references/{persona,style,self-improving}.md`（dialogue.md 归并入 persona.md）。
- 测试：`tests/test_{runtime_core,ontology,reflection_split,local_search,external_research,courseware}.py`（共 80 项，含负向矩阵）。

### Changed
- `pi_arch_doctor.py`：新增 active-skill=3 冻结、quarantine 清单、必需 runtime 工具契约、malformed ontology JSONL 检查。
- `templates/handoff.json`：三字段改为 `null` + 空 `carry`（“尚未承接”），不再给新课程预置 `TUTOR_A → TUTOR_B @ lesson_001`；`SYSTEM/schemas/handoff.schema.json` 用 `oneOf` 表达“全 null / 真实承接”两种合法形态。
- `pi_arch_doctor.py`：落实 plan.md §13 声明的 canonical state 门禁 —— 逐课程校验 `course_state.json`/`tasks.json`/`handoff.json` 并核对 `course` 与所在目录一致；新增 `manifest.json` 磁盘交叉校验（`DATA/`、`TEXTBOOK/` 排除）；缺失 runtime 文件为 WARN，非法内容为 ERROR；新增 `--root`。
- 测试：`tests/test_handoff.py`、`tests/test_doctor_gates.py`（+24 项，含 doctor 自身负向矩阵与只读断言）。
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

<!-- Runtime safety audit fixes are under development on this branch. -->
