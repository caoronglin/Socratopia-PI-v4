# Memory Contract

## 热/温/冷

- 热：`CONTEXT_INDEX.md` + runtime，目标约 800–1600 中文字。
- 温：`LESSON_SUMMARIES.md` 最近 2–3 课。
- 冷：课程 ARCHIVE、完整 social/历史，仅检索时读取。

启动上下文应给后续对话保留充足空间；不固定绝对 token 数，因为不同模型窗口不同。默认目标：启动材料不超过可用上下文的约 25%，至少保留 50% 给课堂互动与工具输出。

## 热信息必须包含

当前章节/lesson、coverage 状态、2–3 个主要薄弱点、pending reteach、下节入口、必要书本锚点、当前导师、阻塞任务。

## 跨导师承接

权威载体：`runtime/handoff.json`。Social 是叙事层，不是教学承接事实源。

## 日记

按课程保存 `DIARY.md`，只记录可由学习过程支持的跨课连接、元认知变化与未解问题；不得替学习者编造私人情绪。

## 压缩不变量

不得压缩掉：未完成 required coverage、错误根因、needs_review 证据、用户明确节奏偏好、来源锚点。
