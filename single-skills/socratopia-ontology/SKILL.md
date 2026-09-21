---
name: socratopia-ontology
description: 课程知识图谱：把章节/概念/先修关系建成可校验的 typed graph，用于先修缺口、概念辨析与跨节串联。触发词：知识图谱、先修关系、概念结构、ontology、建图。mastery 绝不入库。
---

# Socratopia Ontology（单 skill 版）

课程隔离的 typed 知识图谱。**图谱是结构与关系，不是掌握度存储。**

## 何时用
- 教材编目后落图；备课时查先修缺口/辨析；用户明确说“图谱/先修关系/概念结构”。

## 实体 / 关系
- 节点：Course / Chapter / KnowledgePoint / Concept / Example / Method / Equation / Experiment。
- 关系：contains / prerequisite / related_to / contrast_with / derived_from / example_of / applies_to。
- 引用：book anchor / source ref / lesson evidence ref。

## 硬边界
- 禁止写入 mastered / understood / score / passed / failed / current_progress；掌握只从 `PROGRESS.md`/assessment/review 派生。
- `projection.json` 派生非权威，可随时删重建；`graph.jsonl` 是 append-only 历史。

## 工具（确定性引擎）
`scripts/ontology.py`：`init / node upsert / node get / node tombstone / edge relate / query / validate / compact / stats`（写操作需 `--apply`；禁裸 create；prerequisite 无环；禁孤儿边；防 `../`/symlink/跨课程越界）。

## 权威与详情
- Schema：`SYSTEM/schemas/ontology.schema.json`；完整规则：`.pi/skills/socratopia-learning/references/graph.md`。
- 副作用：写入 S1；validate/query S0；按课程隔离于 `DATA/<course>/ontology/`。
