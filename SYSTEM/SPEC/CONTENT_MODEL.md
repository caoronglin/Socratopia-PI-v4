# Content Model Contract

## 权威对象

| 对象 | 路径 | 负责 | 不负责 |
|---|---|---|---|
| Course | `DATA/<course>/` | 课堂事实、证据、上下文、runtime | 教材正文 |
| Active Coursebook | `TEXTBOOK/<course>/book.md` | 当前规范化完整正文 | 课堂完成记录 |
| Navigation | `_outline.md` + `manifest.json` | 章节/锚点/图表映射 | 替代正文 |
| Sources | `SOURCES/` | 补充/例证/纠偏/拓展/冲突 | 无标注覆盖主课本 |
| PREP | `PREP/lesson_XXX.md` | 学习目标、问题链、coverage plan | 宣布掌握 |
| PROGRESS | `DATA/<course>/PROGRESS.md` | 实际发生的课堂与理解证据 | 改写教材 |
| Archive | `ARCHIVE/` | 历史/迁移审阅 | active runtime 输入 |

## 内容流

`source → normalize/catalog → active book → navigation → PREP → classroom → evidence → review/reteach`

## PREP 最小字段

- course / lesson_id / chapter scope
- coursebook version or hash
- anchors
- actually-used source refs
- learning objectives
- question/teaching plan
- coverage ledger seed
- expected evidence

## 按章备课（向后兼容）

默认新建方式为 `prep.py chapter`：一章对应一份逻辑 PREP（`plan_mode: chapter`），按当前教材目录逐项列出小节，并记录章末综合与迁移设计；若内容较多，可跨多个 Session/Teaching Unit 完成。旧 `prep-1` 无 `plan_mode` 的文件继续按旧规则读取。章级 PREP 与课后 Session/PROGRESS 事实分开：同章教案不等于一次会话，也不自动写 mastery。补充资料只允许本课已登记 `SOURCES/`，记录 SHA256；内容变化标记 stale，复核后使用。

## 主课本替换

显式操作：归档旧版本 → 新旧锚点映射 → 生成新书与导航 → 重建受影响 PREP → 生成补讲候选 → 验证。`PROGRESS.md` 永不因换书被重写。

## 教材改进笔记

教材问题属于“修订候选”，不是即时改写授权。按课程存放在 `DATA/<course>/BOOK_REVISION.md`，包含问题、证据、建议、优先级与 lesson_id；避免全局文件混入多课程。
