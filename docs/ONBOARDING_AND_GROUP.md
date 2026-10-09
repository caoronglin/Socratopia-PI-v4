# 首次引导初始化与学习小组

## 引导初始化

终端运行：

```bash
python scripts/initialize.py wizard
```

按提示选择课程名、主导师 D（三月七）/E（丹恒）/F（姬子）、可选的 2–3 位小组成员，最后输入 `YES` 才开始创建。适合 Cherry Studio 的无交互执行方式：

```bash
python scripts/initialize.py plan --course '遗传学'
python scripts/initialize.py apply --course '遗传学' --tutor F --members D E F
```

`plan` 只读；`apply` 只补缺失骨架，保留旧 PROGRESS、book、runtime 与小组配置，不设课程为 ready，也不自动生成教材/教学证据。状态无效时阻断。当前仅初始化**指定课程**，不会更改其他课程或全局指针。

初始化后请提供合法教材、生成并检查 `TEXTBOOK/<course>/book.md` 和 `_outline.md`，用 `prep.py chapter` 备课并通过课程 gate，然后才能开始正式课堂。没有教材的课程可以完成初始化，但不能因此宣称已备课。

## 学习小组

```bash
python scripts/learning_group.py configure --course '遗传学' --tutors D E F --lead F
python scripts/learning_group.py start --course '遗传学' --topic '显性是否等于高频' --rounds 2
python scripts/learning_group.py status --course '遗传学'
```

`next_speaker` 指明下一个应发言的导师；Agent 阅读**该导师**的 `profiles/TUTOR_X.md`，根据真实课程材料生成并展示一段发言。实际呈现后把文本经 stdin 记录：

```bash
python scripts/learning_group.py record --course '遗传学' --speaker D --text-file - < spoken.txt
```

需按成员顺序记录每位发言；整轮完成后小组进入 `awaiting_user`，主持导师只问一个关键问题并等待。学习者要求继续时使用：

```bash
python scripts/learning_group.py continue --course '遗传学' --question '对新问题进一步讨论'
python scripts/learning_group.py stop --course '遗传学'
```

默认最多两轮，可选择 1–3 轮，**不会自动无限续聊**；要修改成员，先停止当前讨论再重新 `configure`。小组记录位于 `DATA/<course>/runtime/learning_group.json`，与课程事实独立，不替代 PROGRESS、active_tutor、PREP 或课堂计时。

## Cherry Studio Pi

- 在 Work 中将本仓库设为 Pi Agent 的工作目录，沿用 `integrations/cherry-studio/AGENT_PROMPT.md`；用户自然语言请求「初始化/开学习小组」时按上述脚本执行。
- 一个 Pi Agent 串行扮演多个导师并展示真实发言；**当前没有自动启动多个模型实例、多个独立 Agent 或并行辩论**。如宿主将来暴露委派能力，需要独立设计和真实授权/实测后才可声明使用。
- 多导师只用于知识讨论，不虚构私人关系、学习者能力、教材引文；内部教研 A/B/C 不进入用户可见讨论。
- 小组不自动满足 45 分钟的课时要求；正式课堂必须按 `lesson_timer.py` 单独记录有效时间。
- 自动测试验证数据隔离、轮次、发言顺序和初始化幂等；实际 Cherry UI 发言质量、上下文预算与工具权限仍需手动评测。
