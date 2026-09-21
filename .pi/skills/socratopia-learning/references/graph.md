# 知识图谱（graph.md）

图谱是**知识结构与关系**的投影，不是掌握度存储。权威工具：`scripts/ontology.py`（课程作用域，append-only JSONL）。规则权威：`SYSTEM/SPEC/CONTENT_MODEL.md` + `SYSTEM/schemas/ontology.schema.json`。

## 什么时候用

- 新教材编目后：把章节/核心概念/先修关系落进图，供后续提问与检索。
- 备课时：按 `prerequisite` 找先修缺口，按 `contrast_with` 设计辨析题。
- 课堂中：定位“这个结论从哪里来”，串联跨节关系。
- 用户明确说“图谱/知识结构/先修关系”时。

普通课堂默认**不强制建图**；没有图也能上课。缺图时按降级规则走，不虚构节点。

## 什么能进图

- 节点类型：Course / Chapter / KnowledgePoint / Concept / Example / Method / Equation / Experiment。
- 关系：contains / prerequisite / related_to / contrast_with / derived_from / example_of / applies_to。
- 允许引用：book anchor、source ref、lesson evidence ref（作为定位，不作成绩）。

## 什么不能进图（硬边界）

- **禁止**写入 mastered / understood / score / passed / failed / current_progress 等权威字段。
- 掌握状态只从 `PROGRESS.md`、assessment、review evidence **派生**；图需要展示状态时必须标 `derived:true, authoritative:false`。
- `projection.json` 是派生投影，可随时删除重建；`graph.jsonl` 才是 append-only 历史。

## 与其它事实源的关系

```text
book.md / SOURCES  →  图谱（结构/关系/锚点）
PROGRESS.md        →  掌握证据（唯一事实源）
coverage ledger    →  章节覆盖（unseen/introduced/verified/needs_review）
handoff.json       →  跨导师承接
图谱派生查询可辅助以上判断，但绝不反向覆盖它们。
```

## 操作（详见 `scripts/ontology.py --help`）

- 写操作需 `--apply`：`init` / `node upsert` / `node tombstone` / `edge relate` / `compact`。
- 只读：`node get` / `query` / `validate` / `stats`。
- 修订用 supersede、删除用 tombstone，均 append 新事件，不改写历史；`compact` 只重建 projection。
- 每次写后跑 `validate`；prerequisite 必须无环，边端点必须存在（无孤儿边）。

## 信任与副作用

- 图谱写入属 S1（项目内可恢复写）；`validate`/`query` 属 S0。
- 跨课程引用、路径穿越（`../`、绝对路径、symlink 越界）一律拒绝；图按课程隔离存放于 `DATA/<course>/ontology/`。
