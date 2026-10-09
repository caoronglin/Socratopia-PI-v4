# 长周期课程编排

来源蒸馏：`education-training-program`（SkillHub skillset，纯 markdown，无代码）。
单次课堂见 `references/classroom.md`；章节质量门见 `SYSTEM/SPEC/CLASSROOM_CONTRACT.md`。本文件只管**跨课、跨章的编排**。

## 三个尺度之上再加一层

`Session`（用户控）→ `Teaching Unit`（1–3 核心点）→ `Chapter`（覆盖质量门）→ `Course Program`（本文件）。

课程级编排只回答三件事：

1. 单元之间的**先修依赖**；
2. 每个单元的**可观察证据**；
3. 哪些单元允许**跨会话延展**。

它不回答"这门课要讲多少章"——那是用户意图，不是系统默认值。

## 里程碑

里程碑是**证据检查点**，不是时间点：

| 里程碑类型 | 判定依据 |
|---|---|
| 概念里程碑 | 该概念在 coverage ledger 中有 `verified` |
| 能力里程碑 | 有迁移/综合题证据 |
| 辨析里程碑 | 能对反例/易混项说清差异 |

禁止用"已完成 N 章"或"已学 N 小时"作为里程碑判定——那是进度条，不是理解证据。

## 跨课连接

跨课程的知识关联写入 `DATA/<course>/DIARY.md`（见 `references/reflection.md`）。**不得**为了建立连接而读取或写入其他课程的进度/错题/卡片/PREP/runtime。跨课只共享"通用方法与元认知"，不共享课程事实。

## 知识沉淀

课后总结、会议记录转结构化材料的价值在于**索引与可检索**，不是生成新文档量。生成物默认进热/温层（见 `SYSTEM/SPEC/MEMORY_CONTRACT.md`），且不得改变任何 coverage 状态。

## 明确拒绝

- ❌ 企业员工培训 / 入职合规 / 领导力路径 / 证书模板 / 结业标准：Socratopia 无机构、无证书、无学员档案。
- ❌ 培训营销文案、宣传材料、公开分享材料：属于外发内容，见 `references/trust.md` 的 S3。
- ❌ 学员成长档案 / 家长反馈 / 咨询留档 / 成绩单评语：一人学习模型无此角色；学习者事实只进 `PROGRESS.md` 与 `DIARY.md`。
- ❌ 「一键生成全套培训资料 + 课件」：与最小上下文预算和权威对象分离冲突。
- ❌ 追踪类排程（heartbeat/cron）：`runtime/tasks.json` 是待办状态，不是后台执行器，见 `AGENTS.md`。
