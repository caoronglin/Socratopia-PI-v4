# 课前设计与教学评一致性

PREP 字段权威是 `SYSTEM/SPEC/CONTENT_MODEL.md`；课堂循环权威是 `classroom.md`。本文件管**开课前的设计**，并由 `scripts/prep.py` 执行。

## 流程

```bash
python scripts/prep.py new    --course X --lesson-id lesson_003 --chapter "第2章" [--apply]   # 生成骨架
python scripts/prep.py check  --course X --lesson-id lesson_003                              # 一致性/就绪检查
python scripts/prep.py status --course X                                                     # ready/draft/stale/invalid/legacy
```

骨架只用**真实状态**：`PROGRESS.md` 的 `needs_review`、待补讲队列、`unseen/introduced` 条目、`_outline.md` 锚点、当前 `book.md` 哈希。没有就明说“无”，不编造。**绝不覆盖已有 PREP**。

## 教学评一致性

```
学习目标 ──决定──→ 问题/活动 ──决定──→ 可观察证据
```

`prep.py check` 的硬规则（违反为 ERROR）：

- 每个目标必须同时有活动与证据，缺一不可；
- 支架只用 A/B/C，且同一目标最多相邻两级（跨三级说明目标切得太粗，先拆目标）；
- Coverage 种子只能是 `unseen`/`introduced`，**PREP 不能把任何条目写成 verified**；
- PREP 里不得出现掌握声明；`course` 必须等于所在课程；
- `status: ready` 需要：无 TODO、有教材锚点 `anchors`、记录 `book_hash`。

三者错位即降级：活动与目标脱节 → 删活动；证据与目标脱节 → 换证据形式，不换目标。**不得为了凑题型改写目标**。

支架指同一目标的深度：**A** 完整定义+例子；**B** 只给关键线索；**C** 不提示直接变式（迁移证据）。支架等级属于**备课候选方案**，不是给学习者贴的永久能力标签。

备课时为每个主要目标至少预想：一个常见误概念及其判别问题、一个无进展时的替代表征/示范、一项可观察的独立验证。真实课堂依据回答选择其中一条路线，而不是强制走完全部步骤（策略与对照示例只在 `references/pedagogy.md` 定义）。别把一次学生沉默解释为能力或性格特征。

## 过期

`book_hash` 与当前 `book.md` 不一致即 `stale`（doctor WARN）：重建前先对照锚点，不静默沿用。无 front matter 的旧 PREP 为 `legacy`，**不评判、不改写**。

## 单元与来源

多单元之间显式写先修关系，并落成 `prerequisite` 候选边。课文分析、生字词等是**来源侧**事实，进 `SOURCES/` 并登记锚点；不进 `PROGRESS.md`，不自动改写 `book.md`。长章节允许跨单元；未完成保留为未完成。

## 明确拒绝

- ❌ 绑定特定学段课标（如 2022 版课程标准）：本系统是课程隔离的个人学习系统。
- ❌ 教案成果包/批量模板清单：与最小上下文预算冲突。
- ❌ 教案一键转 PPT：课件路径见 `courseware.md`。
- ❌ “你已安装以下 Skill，按步骤串联”的编排前提：active skill 恒为 3。
- ❌ 宿主专属导出声明：`SYSTEM/SPEC/` 不出现宿主细节。
