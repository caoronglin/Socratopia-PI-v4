---
name: socratopia-learning
description: 处理 Socratopia 的教材、资料编目、PREP、课堂、章节覆盖、复习、评估、考试、错题、卡片、上下文压缩与课程级状态。用户说开始上课、资料上传完成、复习、出题、考试、查看进度、补讲、搜教材时使用。
---

# Socratopia Learning

按 `references/course-binding.md` 绑定课程与意图，按需读取 reference。

## 路由

| 意图 | 读取 |
|---|---|
| 首次使用、引导初始化、新建课程 | `references/onboarding.md` |
| 开始/继续上课、章节推进、补讲 | `references/classroom.md` + `references/memory.md` + `references/lesson-timer.md` |
| 覆盖账本、期望元素、章节完成判据、卡住升级 | `references/coverage.md` |
| 备课、PREP 设计、教学评一致性、分层支架 | `references/lesson-planning.md` |
| 长周期课程编排、单元先修、里程碑、跨课连接 | `references/course-program.md` |
| 深入解释、卡住、换表征、理解验证 | `references/pedagogy.md` |
| 教材上传、编目、重编、来源冲突 | `references/content.md` |
| 知识图谱、先修关系、概念结构 | `references/graph.md` |
| 搜教材、本地检索、定位锚点 | `references/local-search.md` |
| 网页文章、知乎/博客、URL 学习（用户提供链接或正文） | `references/web-article.md` + `references/external-research.md` |
| 外部研究、最新论文、外部事实（显式意图） | `references/external-research.md` |
| memos 记忆同步、跨工具记忆（显式意图） | `references/memo-sync.md` |
| 上传 PDF/OCR/MinerU 远程解析（须逐次授权） | `references/mineru-ingest.md` |
| 生成课件、教学 PPT、设计课堂材料（显式） | `references/courseware.md` |
| 导出到 Stellar 站点、一课一笔记本、课后总结成网页 | `references/stellar-export.md` |
| 导出到 Obsidian 笔记、回复/笔记的富 Markdown 格式选择 | `references/markdown-output.md` |
| 复习、卡片、错题、出题、考试、错因归类 | `references/assessment.md`（题型与难度规格见 `references/quiz-generation.md`） |
| 下课、课后更新、断点保存 | `references/memory.md` + `references/classroom.md` + `references/lesson-timer.md` |
| 学习反思、元认知、日记、跨课连接 | `references/reflection.md` |
| 权限/外部资料/删除/上传 | `references/trust.md` |

需要更精确的数据合同时，再读取 `SYSTEM/SPEC/` 中相应规范；不要一次读取整个目录。

## 核心动作

1. 先读本课 runtime 与热上下文。
2. 只读当前 PREP 和必要的 `book.md` 锚点。
3. 教学依据理解证据和 coverage ledger。
4. 先提交课堂事实，再派生复习资产，最后维护。
5. 评估失败只生成 `needs_review`，不得判定掌握。

缺文件按 reference 降级，不编造。
