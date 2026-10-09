---
name: socratopia-learning
description: 处理 Socratopia 的教材、资料编目、PREP、课堂、章节覆盖、复习、评估、考试、错题、卡片、上下文压缩与课程级状态。用户说开始上课、资料上传完成、复习、出题、考试、查看进度、补讲、搜教材时使用。
---

# Socratopia Learning

先确定 `course`、当前意图与是否在课堂，只读所需 reference。参数解析与切换见 `references/course-binding.md`；已明确时不重复问。

## 路由

| 意图 | 读取 |
|---|---|
| 开始/继续上课、章节推进、补讲 | `references/classroom.md` + `references/memory.md` |
| 覆盖账本、期望元素、章节完成判据、卡住升级 | `references/coverage.md` |
| 备课、PREP 设计、教学评一致性、分层支架 | `references/lesson-planning.md` |
| 长周期课程编排、单元先修、里程碑、跨课连接 | `references/course-program.md` |
| 深入解释、卡住、换表征、理解验证 | `references/pedagogy.md` |
| 教材上传、编目、重编、来源冲突 | `references/content.md` |
| 知识图谱、先修关系、概念结构 | `references/graph.md` |
| 搜教材、本地检索、定位锚点 | `references/local-search.md` |
| 外部研究、最新论文、外部事实（显式意图） | `references/external-research.md` |
| memos 记忆同步、跨工具记忆（显式意图） | `references/memo-sync.md` |
| 上传 PDF/OCR/MinerU 远程解析（须逐次授权） | `references/mineru-ingest.md` |
| 生成课件、教学 PPT、设计课堂材料（显式） | `references/courseware.md` |
| 导出到 Stellar 站点、一课一笔记本、课后总结成网页 | `references/stellar-export.md` |
| 导出到 Obsidian 笔记、回复/笔记的富 Markdown 格式选择 | `references/markdown-output.md` |
| 复习、卡片、错题、出题、考试、错因归类 | `references/assessment.md`（题型与难度规格见 `references/quiz-generation.md`） |
| 下课、课后更新、断点保存 | `references/memory.md` + `references/classroom.md` |
| 学习反思、元认知、日记、跨课连接 | `references/reflection.md` |
| 权限/外部资料/删除/上传 | `references/trust.md` |

需要更精确的数据合同时，再读取 `SYSTEM/SPEC/` 中相应规范；不要一次读取整个目录。

## 核心动作

1. 先读当前课程 runtime 与热上下文。
2. 再读当前 PREP；仅按锚点读取必要 `book.md` 片段。
3. 教学推进以理解证据和 coverage ledger 为准。
4. 写入时先提交核心课堂事实，再生成复习资产，最后处理可延迟维护项。
5. 任何评估失败只生成 `needs_review`，不能自动宣布“不掌握/掌握”。

缺文件时按 reference 中的降级规则执行，不虚构内容。
