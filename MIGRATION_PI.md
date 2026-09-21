# v3 → PI v4 迁移指南

## 1. 文件映射

| v3 | PI v4 |
|---|---|
| 根 `CLAUDE.md` | `AGENTS.md` + `.pi/skills/*` + `.pi/prompts/*` |
| `SYSTEM/SYSTEM.md` | `SYSTEM/SPEC/CLASSROOM_CONTRACT.md` + learning references |
| `AGENT_SYSTEM_PROMPT.md` | 删除 active 角色；仅历史归档 |
| `.claude/skills/socratopia-learning` | `.pi/skills/socratopia-learning` |
| `.claude/skills/socratopia-tutor` | `.pi/skills/socratopia-tutor` |
| `superpowers-engineering` | `socratopia-engineering` |
| `LESSON_CONTENT_SPEC.md` | `CLASSROOM_CONTRACT.md` + `learning/references/classroom.md` |
| `BOOK_MODEL_SPEC + CATALOG + BOOK_REVISION` | `CONTENT_MODEL.md` + content workflow |
| `CONTEXT_COMPRESSION + CROSS_TUTOR_HANDOFF + DIARY` | `MEMORY_CONTRACT.md` + `runtime/handoff.json` |
| `ASSESSMENT + EXAM` | `ASSESSMENT_CONTRACT.md` |
| `CONTENT_TRUST` | `TRUST_EFFECTS.md` |
| `GARBAGE_COLLECTION` | `OPS_CONTRACT.md` |

## 2. 不迁移/不覆盖的数据

`DATA/<course>/PROGRESS.md`、错题、卡片、教材正文和原始来源都属于用户数据；本架构包不自动改写它们。

## 3. 建议迁移顺序

1. 备份项目。
2. 安装新控制面文件。
3. 运行 `pi_arch_doctor.py`。
4. 对每门课程保留原 DATA/TEXTBOOK；仅补 `runtime/handoff.json` 与新版 `course_state.json` 投影。
5. 用新 PREP/coverage 规则处理下一节课；不回写历史课堂为“已验证”。
6. 观察 2–3 节课后再清理旧控制面文件。

## 4. 需要人工确认的语义迁移

### “一节课 = 一章”

改为：一章是完成范围；Teaching Unit 是可消化推进块。一个 Session 可连续完成多个 Unit，用户决定何时下课。

### SOCIAL 承接

旧 SOCIAL 可以保留为叙事历史；从迁移后的下一课开始，教学承接写入 `runtime/handoff.json`。不要自动从历史 SOCIAL 推断学习者状态。

### 旧线性 runtime state

不要简单字符串替换。将旧状态映射为：

- `phase`
- `readiness.catalog/prep/runtime/reteach`
- `blockers[]`

### GC

旧版“超过 N 条就搬走 PROGRESS”停止自动执行。canonical 课堂事实只做索引/摘要；需要分卷时显式迁移并保留索引。
