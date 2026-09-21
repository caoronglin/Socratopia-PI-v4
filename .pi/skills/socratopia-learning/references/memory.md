# Memory & Post-Lesson Workflow

权威合同见 `SYSTEM/SPEC/MEMORY_CONTRACT.md`。

## 三层记忆

- 热：`CONTEXT_INDEX.md` + runtime；每课读取。
- 温：`LESSON_SUMMARIES.md` 最近 2–3 课；需要时读取。
- 冷：ARCHIVE / 历史原文；只在回查、复盘或争议时读取。

## 下课提交顺序

仅用户明确结束课堂后执行：

### Commit — 必须先完成

1. 更新 `PROGRESS.md`：实际覆盖、理解证据、混淆、未完成项、下次入口；
2. 更新 `runtime/course_state.json`；
3. 更新 `CONTEXT_INDEX.md`；
4. 轮换导师时更新 `runtime/handoff.json`。

### Review — 紧接 Commit

5. 生成/登记退出练习；
6. 为真实混淆生成卡片或复习项；
7. 将失败的可重试任务加入 `runtime/tasks.json`。

### Maintenance — 可延迟

8. 日记、可选 SOCIAL、图谱增量（用 `scripts/ontology.py` 更新结构/关系，禁写掌握度）、索引、本地导出、GC、报告。

Maintenance 未完成不影响课堂事实提交。只入队时不得声称后台正在运行。

## 日记

只记录跨课连接、元认知变化与未解问题。不要替学习者编造细腻情绪，也不要复述课堂正文。
