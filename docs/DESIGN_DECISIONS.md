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

## ADR-009 · Canonical progress is durable

PROGRESS 是事实源，不按固定条数自动搬走。上下文优化通过摘要/索引完成，必要分卷必须显式版本化。
