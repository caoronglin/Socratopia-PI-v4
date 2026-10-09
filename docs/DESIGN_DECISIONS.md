# Design Decisions

## ADR-001 · AGENTS is the kernel

PI 会把项目 context file 作为常驻上下文，因此 kernel 只保留永远成立的规则。具体教学和工程流程移到 Skills。

## ADR-002 · No project `.pi/SYSTEM.md` by default

替换 PI 默认系统提示会增加宿主耦合并可能损失内置工具协议。Socratopia 不需要接管底层 system prompt。

## ADR-003 · Three active skills

仅保留 learning / tutor / engineering。旧 knowledge/works 责任已经合并，不再作为可发现 Skill，避免模型同时加载重复规则。

## ADR-004 · Tutor is presentation

人格不再覆盖工程维护。课堂加载当前 compact profile；背景 lore 和 social 仅按需。

## ADR-005 · Session ≠ Unit ≠ Chapter

解决“慢讲”与“一节课必须整章”的矛盾。章节完整性通过 coverage ledger 和完成质量门保证，而不是用单次会话长度保证。

## ADR-006 · Structured handoff

学习承接来自 `runtime/handoff.json`，SOCIAL 只负责叙事连续性，从根源降低上下文成本与错误推断。

## ADR-007 · Orthogonal runtime state

把旧单一线性状态替换为 phase + readiness + blockers。教材、PREP、补讲可以同时有不同状态，不再强迫进一个枚举链。

## ADR-008 · Queue is not a worker

持久队列只表达“以后要做什么”，不等于异步后台执行。这样无论 PI 是否安装 extension/worker，都不会虚报状态。

## ADR-010 · Token budget is measured, advisory, CJK-aware

`wc -w` 对中文无效，词数阈值形同虚设。`scripts/lib/budget.py` 用中日韩感知估算，doctor 以 WARN（不是 ERROR）报告超限和窗口比例。估算不是 tokenizer：阈值是防止惄性膨胀的预警线，不作精确计量。

## ADR-011 · Hot context is a read-only projection

`scripts/context_pack.py` 只读、只绑定一门课，按 plan §10 顺序压缩输出。它不写文件、不记录掌握、不跟随指向课程外的符号链接；`PROGRESS.md` 仍是唯一掌握事实源，截断段再按需读原文件。

## ADR-012 · Course scope is an execution boundary

教学健康检查与资料流水线必须传递显式课程作用域；`pi_arch_doctor.py --course` 仅检查目标课程数据，但仍验证共享控制层。省略参数保留全仓工程检查。公共 `iter_course_paths` 在给定作用域时直接定位目标，不先枚举其他课程；控制文件遍历剪枝 DATA/TEXTBOOK，课程外符号链接在读取前拒绝。doctor 成功只证明检查通过，不代表 readiness/blockers 已允许开课。

开课 gate 的唯一流程入口是 `learning/references/classroom.md`；下课由 `memory.md` 区分 Core / Derived / Review / Maintenance。派生失败不撤销已保存课堂事实，部分失败必须分阶段报告。导师风格是表达层，handoff 写入不等于 active_tutor 已切换；二者必须分别核验。

## ADR-014 · Tutor layer has two tiers; teaching design is externalized before class

`profiles/` 的 D/E/F 面向学习者，`moe/` 的 A/B/C 是**内部教研组**：只在备课会与下课复盘上出现，结论落 PREP 与 `SELF_IMPROVING`，不产生第三份事实源，也不抢当前导师的舞台。A/B/C 的 ID 保持不变，`SELF_IMPROVING` 与 `handoff` 的键因此稳定。

依据是 MWPTutor 的对照结果：把教学结构外部化后，自由发挥的 GPT-4 用 29 轮没到正确答案，受约束的版本 6 轮就到 [arXiv:2402.09216]。所以教学设计必须**先写下来并有约束力**，不能靠临场发挥。

配套三项加固，全部有据可依：

- **教研会决议是 `ready` 门禁**：PREP 缺 `## 教研会决议`、缺 `## 预期误概念`、或决议没逐项交代（目标粒度 / 期望元素 / 表征路径 / 卡点预案），`prep.py check` 判不 ready，开课 gate 随之挡住。
- **覆盖判到期望元素**：`coverage.md` 要求条目声明 2–7 个独立子元素并逐个取证；元素未证完，条目停在 `introduced`，不允许一段流畅叙述整体升级。对应 AutoTutor 的 expectations + coverage 机制（覆盖分值过阈才算 covered）。
- **陷题深度计数**：`classroom.md` 数连续无进展轮数，1 次换表征、2 次给台阶、3 次停止提问直接纠错。对应 2026 年的真实对话分析：每多卡一轮恢复概率降 12.7%，重复提问的恢复率约 28%、改为直接处理错误约 40%。

边界不变：教研会只改「怎么教」，不改事实、掌握标准与文件状态；`PROGRESS.md` 仍是唯一掌握来源。

## ADR-013 · Host adapters are thin pointers, never a second control plane

Claude Code 原生读取仓库 `AGENTS.md`（替代 `CLAUDE.md`），但只发现 `.claude/skills/*/SKILL.md` 与 `.claude/commands/*.md`。因此 `claude-code` 分支新增 `.claude/` 适配层：三个 SKILL 入口与五个 command 入口**只写 frontmatter 与指向 `.pi/` 权威文件的指针**，不复制任何规则正文；`references/` 仍按相对路径在 `.pi/` 内解析。根 `CLAUDE.md` 保持不存在——它会与 `AGENTS.md` 形成第二份常驻规则（ADR-001），且 doctor 会告警。

占位符按宿主区分：Pi 用 `$@`，Claude Code 用 `$ARGUMENTS`，适配层不得残留 `$@`。`.claude/settings.json` 只把 AGENTS.md §6 已有约束（凭据不外读、远程与删除须逐次授权）在 Claude Code 侧显式化，不放宽任何既有边界。`tests/test_claude_portability.py` 守住集合一致、description 逐字、指向存在、占位符正确与 manifest 登记。控制面文件（`AGENTS.md`、`.pi/skills/*/SKILL.md`、`SYSTEM/SPEC/*.md`）出现 `.claude/` 字样仍是 doctor ERROR：宿主差异只允许存在于适配层本身。

## ADR-009 · Canonical progress is durable

PROGRESS 是事实源，不按固定条数自动搬走。上下文优化通过摘要/索引完成，必要分卷必须显式版本化。
