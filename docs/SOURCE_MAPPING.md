# 原设计保留/调整清单

## 保留

- active `book.md`、SOURCES、PREP、PROGRESS 职责分离；
- 课程隔离；
- 热/温/冷上下文；
- 不可信来源与副作用确认；
- 苏格拉底循环 + 直出降级；
- 章节 coverage 质量门；
- 评估题必须有目标/来源/解析；
- 导师差异化追问；
- 课后核心状态优先。

## 调整

- `CLAUDE.md` 路由 → PI `AGENTS.md + skills + prompts`；
- 导师全局人格 → 课堂 presentation layer；
- “一节课最低整章” → “章节完成必须完整，Unit 可分块”；
- PROGRESS/SOCIAL/RELATIONS 多路承接 → `handoff.json` 单一承接对象；
- 线性 course state → 正交 readiness；
- background queue → durable pending queue；
- 全局 `BOOK_REVISION.md` → 课程级 `DATA/<course>/BOOK_REVISION.md`；
- 固定 token 数 → 相对预算；
- 固定 N 条自动搬移 canonical 课堂记录 → 摘要/索引优先。

## 删除/降级为 legacy

- 根级 `AGENT_SYSTEM_PROMPT.md`；
- active 兼容 skills `socratopia-knowledge` / `socratopia-works`；
- Claude 专属 subagent 强依赖；
- Windows 绝对路径与 Read-tool 专属参数规则。
