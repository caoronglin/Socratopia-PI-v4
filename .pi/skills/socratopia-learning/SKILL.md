---
name: socratopia-learning
description: 处理 Socratopia 的教材、资料编目、PREP、课堂、章节覆盖、复习、评估、考试、错题、卡片、上下文压缩与课程级状态。用户说开始上课、资料上传完成、复习、出题、考试、查看进度、补讲、搜教材时使用。
---

# Socratopia Learning

先确定 `course`、当前意图和是否处于课堂，只读取完成任务所需的 reference。

## 路由

| 意图 | 读取 |
|---|---|
| 开始/继续上课、章节推进、补讲 | `references/classroom.md` + `references/memory.md` |
| 深入解释、卡住、换表征、理解验证 | `references/pedagogy.md` |
| 教材上传、编目、重编、来源冲突 | `references/content.md` |
| 知识图谱、先修关系、概念结构 | `references/graph.md` |
| 搜教材、本地检索、定位锚点 | `references/local-search.md` |
| 外部研究、最新论文、外部事实（显式意图） | `references/external-research.md` |
| 生成课件、教学 PPT、设计课堂材料（显式） | `references/courseware.md` |
| 复习、卡片、错题、出题、考试 | `references/assessment.md` |
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
