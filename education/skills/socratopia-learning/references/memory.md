# Memory & Post-Lesson Workflow

权威合同：`SYSTEM/SPEC/MEMORY_CONTRACT.md`（热/温/冷与压缩不变量）。开课热层：`python scripts/context_pack.py --course X`，只读预算压缩；温/冷按需。

## 下课顺序

仅用户明确结束课堂后执行。

### Core — 真实记录与操作状态

1. 核对 course/lesson 与已存事实，更新 `PROGRESS.md`：实际覆盖、可观察理解证据、混淆、未完成项、下次入口。下课不自动结章/mastered。
2. 保存 `runtime/course_state.json` 真实断点与 `phase=post_lesson`，保留实际 readiness/blockers；`python scripts/course_runtime.py validate --course X`，确认文件存在、已保存、课程匹配。CLI 无 end/set，render/migrate 不是下课提交。
3. 真实轮换按 tutor `references/handoff.md` 保存 `runtime/handoff.json`；不等于 active_tutor 已切换。轮换部分失败单报，不抹事实、不称轮换完成。

### Derived — 核心保存后，可失败/延迟

热/温层确定性投影，不手写：
- `python scripts/memory.py build --course X --apply`
- `python scripts/memory.py summarize --course X --apply`
- `python scripts/memory.py check --course X`（违反压缩不变量退出 1）

投影来自 PROGRESS，**不写掌握结论**；未变不重写。构建/校验失败单报、保留待办，不撤销 Core；依赖最新投影的步骤暂停或改读真实记录，不用旧投影冒充当前事实。

### Review — 核心保存后

生成/登记退出练习；为真实混淆生成卡片/复习项；失败可重试任务入 `runtime/tasks.json`。依赖派生层时先确认有效。

内部教研组复盘会（`tutor/references/moe.md`）：有效/无效的动作或表征按成员追加到 `DATA/SELF_IMPROVING/<member>.jsonl`；无真实信号不记，**不写掌握度**。

### Maintenance — 可延迟

- 日记、可选 SOCIAL、图谱增量（`scripts/ontology.py` 仅结构/关系，禁写掌握度）、索引、GC、报告。
- 课后总结：`python scripts/export_stellar.py export --course X --apply`。核心已存、依赖可用后执行；幂等，仅写 `DATA/<course>/stellar/`，不联网。失败入队：`python scripts/task_queue.py enqueue --course X --kind export_stellar --key <lesson_id> --lesson-id <lesson_id> --apply`，不阻塞已保存事实。
- 显式意图才 Obsidian 导出：`python scripts/export_obsidian.py export --course X --apply`，只读投影写 `DATA/<course>/obsidian/`；格式见 `markdown-output.md`。

## 失败与幂等

- 无活动课堂/无新事实：无新核心待提交，不新建 lesson、造记录或重复复习资产；原 course/lesson 失败派生/任务可单独重试。
- PROGRESS 或 course_state 写入/校验失败：停 Derived/Review/Maintenance，报已存/未存，不称核心成功、不自动撤销事实。承接/切换失败单列，不掩盖核心状态。
- 重试先查同 course/lesson 已存部分，只补未存事实/失败步骤，不重复追加课堂记录；核心全存不重复提交。
- 资产/导出用现有幂等接口；无接口先查重，不编造通用命令。任务用稳定 kind/key/lesson_id；确认入队成功，失败只报告。
- Maintenance 未完不影响已存事实；收尾分报核心、派生、待办。仅入队说“已加入待处理队列”，不说后台正在运行。

## 日记

仅跨课连接、元认知变化、未解问题；不编造私人情绪，不复述课堂正文。
