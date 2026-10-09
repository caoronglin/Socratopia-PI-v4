# Classroom Workflow

## 概念

Session：明确开课至下课；可含多个 Unit（通常1–3核心点）。Chapter：完整教材范围，完成条件见 `coverage.md`；歧义按 `course-binding.md`。

**按章备课**：`prep.py chapter` 一章一份 PREP，按小节拆 Unit，可跨会话；未完成留断点，不重建同章教案。旧 PREP 不迁移，见 `lesson-planning.md`。

## 开课 gate

- 课号须核对 PREP/章节/断点；冲突时确认续课或另开，不静默忽略/递增。无明确课号据 runtime/PROGRESS，不明则问。
- runtime 必须落盘且课程匹配；`course_runtime.py validate --course X`。默认值 PASS≠文件存在；缺/非法/`readiness.runtime=invalid` 禁新授课，仅能澄清/复习。
- phase 不豁免 readiness/blockers：catalog 过期、prep 未就绪、blocker 未解均禁新内容；reteach pending 先补讲后测。
- **教研会已开**：ready 需 `## 教研会决议` 和 `## 预期误概念`（tutor `moe.md`）；缺项不得新授课。
- `python scripts/prep.py status --course X`、`python scripts/prep.py check --course X --lesson-id lesson_XXX`；prep=ok、PASS≠逐课 ready。

| PREP | 分支（未通过不新授课） |
|---|---|
| missing | status 不列缺文件，核对目标；先备课 |
| draft | 补目标/活动/证据/锚点至 ready；可 check PASS |
| stale | 按当前主课本复核设计/锚点再检查，不只改 hash；可仅 WARN |
| invalid | 修复 check 错误，不改 runtime 绕过 |
| legacy | 未 opt in `prep-1`；复核、整理到契约再检查 |
| ready | 课程/课号匹配、check 无错/stale、book/锚点可用、教研会决议与预期误概念已交代、runtime gate 通过 |

`prep.py new` 出骨架（`--apply` 写入），非就绪。course_runtime 仅 `status/validate/render/migrate`，无 start/set；migrate 写入/备份，非就绪证明。获准落盘核验才称持久成功。

## 开课最小加载

按序：`DATA/LEARNER.md` 允许偏好/当前课 → 本课 runtime → `CONTEXT_INDEX.md` → `RETEACH_QUEUE.md` pending/needs_review → PROGRESS 最近课/断点 → 目标 PREP → book 必要锚点 → 当前导师 compact profile（轮换读 handoff）。
`python scripts/context_pack.py --course X [--budget N]` 只读压缩，截断补读；按 runtime 选 PREP，无 `--lesson-id`，也不是 gate 校验器；课号不符单读目标。
模板热层用 `python scripts/memory.py build --course X --apply` 从 PROGRESS 重建，禁手写。不读完整 book/SOCIAL、全历史/导师、异课。

## 教学

有真实前课才检索 3–6 项，分独立正确/提示后正确/失败；纠错后平行再测，无前课不造题。
`定位已有认知 → 选择问题/提示/解释 → 倾听并反馈 → 理解验证 → 变式/迁移`。依真实回答选教学动作，详见 `pedagogy.md`。用户要求「直接讲」「[直出]」时先解释，不用追问拖延。
卡住：**数连续无进展轮数，不靠感觉**。1 次换表征；2 次给最小台阶；3 次直讲并平行验证，未过留 `needs_review`。不可原样重问；用户要求直讲则提前解释。
每轮只问一个主问题并等待回答；深度依目标覆盖定义、机制、正例、边界、反例与验证。

## 覆盖账本

五态、**期望元素**与章节质量门见 `coverage.md`。只做两件事：按元素逐个取证；元素没证完就留在 `introduced`，不许一段流畅叙述整体升级。
