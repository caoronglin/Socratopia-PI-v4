# Classroom Workflow

## 概念

- **Session**：用户从“开始/继续上课”到明确“下课”的连续交互，可包含多个教学单元。
- **Teaching Unit**：一次可消化的推进块，通常 1–3 个核心点，复杂推导可只有 1 个。
- **Chapter**：教材覆盖范围。章节完整覆盖是完成质量门，不是单个 Unit 的最低容量。

## 开课最小加载

按顺序读取，够用即停：

1. `DATA/LEARNER.md` 中允许的学习偏好与当前课程；
2. `DATA/<course>/runtime/course_state.json`；
3. `DATA/<course>/CONTEXT/CONTEXT_INDEX.md`；
4. `DATA/<course>/CONTEXT/RETEACH_QUEUE.md` 中 pending/needs_review；
5. `PROGRESS.md` 最近课堂/当前断点；
6. 当前 `PREP/lesson_XXX.md`；
7. PREP 指向的必要 `book.md` 锚点；
8. 当前导师 compact profile；轮换时再读 `runtime/handoff.json`。

默认不读完整 `book.md`、完整 `SOCIAL.md`、全部历史、全部导师或其他课程。

## 进入新内容前

若存在前课内容，先做 3–6 个检索项目。独立正确、提示后正确、失败必须区分记录；失败项纠正后做平行再测。若是第一次课或无可检索前课，跳过而不是制造题目。

## 核心教学循环

`定位已有认知 → 单一问题 → 倾听 → 诊断 → 一个台阶 → 必要解释 → 可观察验证 → 变式/迁移`

卡住时依次：

1. 缩小问题；
2. 换表征/具体例子；
3. 给关键线索；
4. 直接讲解，并保留 `needs_review`，再让学习者复述或做平行题。

不要连续用同一角度追问。

## 内容深度

核心点至少满足：

- 定义/对象；
- 机制、逻辑或关键推导；
- 一个正例；
- 一个边界、反例或易错点；
- 一项学习者可观察证据。

根据课程性质选择额外维度：应用、关联、完整推导、变式、比较。

## Coverage Ledger

每章维护项目状态：

- `unseen`：尚未处理；
- `introduced`：讲过但未验证；
- `verified`：存在理解证据；
- `needs_review`：存在混淆/失败证据；
- `intentionally_skipped`：仅限用户明确选择跳过。

不得用“讲过”代替 `verified`。

## 章节完成质量门

章节完成需要同时满足：

- 所有 required 小节无 `unseen`；
- 核心概念达到完整深度并有理解证据；
- 图表、例题、注释、习题中新知识已处理或明确记录；
- 学习者能复述章节主线和至少两条关系；
- 至少一题综合题 + 一题迁移题；
- 无未解释的 required 缺口。

coverage auditor 若存在可辅助检查，但它的报告本身不是掌握证据。

## 长课

用户未说下课时，完成一个 Unit 后可以继续：下一 Unit、下一章、补漏、综合练习或复习。不因章末自动结束，也不为了连续推进而降低质量门。
