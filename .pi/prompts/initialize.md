---
description: 引导初始化课程与可选多导师学习小组
argument-hint: "[课程名，可省略]"
---
初始化目标参数：$@。使用 socratopia-learning，按 `references/onboarding.md` 操作。

先确认本次课程；缺少课程名只问课程名，不枚举其他课程。先执行 `python scripts/initialize.py plan --course "课程"` 只读检查，并展示已存在的 runtime、教材和待补条件；让学习者选择主导师 D/E/F 与可选学习小组成员（2–3 位）。

获得本次创建的明确确认后执行 `python scripts/initialize.py apply --course "课程" --tutor F [--members D E F]`，用真实选择替换示例值；不要把命令示例中的占位参数当成最终事实。只补缺失文件，原有 PROGRESS/教材/runtime 不覆盖。初始化不代表可以开课，提醒后续教材编目、按章备课和课堂就绪验证。
