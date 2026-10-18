# Tutor Self-Improving（导师自我改进）

只属于 **tutor**，记录导师**自己怎么教**的改进信号。权威规则：`SYSTEM/SPEC/TUTOR_CONTRACT.md`；学习者侧反思见 learning 的 `reflection.md`（两者**不共享状态文件**）。

## 记录什么

- 某种教学动作/类比/追问路线这次**奏效或不奏效**。
- 学习者（或用户）对导师**表达、节奏、策略**的纠正。
- 换一种讲法后理解证据的变化（只记“策略是否更有效”，不记成绩本身）。

## 绝不记录（硬边界）

- 学习者掌握度 / 知识点状态（`mastered`、`verified`、`needs_review`…）——归 `PROGRESS.md`/coverage。
- 考试结果 / 评估分数——归 assessment/review evidence。
- 课程事实、教材内容、跨课连接——归 `book.md`/`PROGRESS.md`/learning `reflection.md`。
- 学习者私人情绪、经历（不替学习者编造）。

## 数据

- 位置：`DATA/SELF_IMPROVING/<tutor>.jsonl`（**按导师，不按课程**；这是唯一非 per-course 存储，因为它描述导师教学策略，而非某课程事实）。
- 格式：append-only JSONL，一行一条：

```json
{"ts":"<ISO-8601>","tutor":"TUTOR_A","kind":"teaching_move|correction|pace|strategy","note":"……","context":"<可选>","outcome":"<可选：更有效/无效/待观察>"}
```

- 写入属 S1（项目内可恢复写）；只在出现**真实信号**时追加，不无事生记。
- **不引入 heartbeat/cron/定时任务**：本系统无后台 worker，仅在导师实际教学复盘时按需读写。

## 何时读

- 同一导师再次上课前，可按需回看自己最近的几条记录，调整策略。
- 用户明确要求“改进导师/导师复盘”时。
- 不默认常驻加载；避免为“人设连续”堆叠无关 token。
