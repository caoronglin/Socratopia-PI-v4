---
description: 选择多位导师围绕当前知识点讨论
argument-hint: "[课程名与讨论主题，可省略]"
---
学习小组请求参数：$@。使用 socratopia-tutor，按 `references/study-group.md` 在唯一课程内执行。

用户选 2–3 位可见导师 D/E/F 和主持人。先通过 `python scripts/learning_group.py status --course "课程"` 核对现状；需要时明确配置 `configure`，再以具体主题 `start`。逐位只读当前导师 profile 后，生成一段实际展示给学习者的有依据发言，用 `record` 经 stdin 记录，不伪造其他发言；每轮结束只提出一个问题并等待，用户说继续才运行 `continue`，最多三轮。用户随时可停止；不修改 active_tutor/PROGRESS/正式课堂计时。单一 Pi Agent 模拟多个导师视角，不宣称已经启动多独立模型。
