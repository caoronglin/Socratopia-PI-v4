---
description: 处理新上传或更新的教材/补充资料
argument-hint: "[课程名，可省略]"
---
使用 socratopia-learning 处理资料更新。课程参数：$@

按 `references/course-binding.md` 确定本次课程，不改变当前课程指针；读取 `references/content.md`，有文档解析需求时再读 `references/mineru-ingest.md`。

保持原始资料不变，登记来源，检查 active book、课程教材 manifest、当前 PREP 与补讲候选；使用现有受控流水线，缺能力则报告或生成可审计草案。纯文本/md/html 直接阅读，不要走解析工具。不得自动修改 PROGRESS 掌握事实；「资料已上传」不授权覆盖 active 主课本、删除原件或上传到远程解析服务，这些操作须逐项确认。
