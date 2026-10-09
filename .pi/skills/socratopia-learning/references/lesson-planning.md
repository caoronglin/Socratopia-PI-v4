# 课前设计与教学评一致性

PREP 字段权威是 `SYSTEM/SPEC/CONTENT_MODEL.md`；课堂执行见 `classroom.md`；实际规则由 `scripts/prep.py` 校验。具体章节示例见 `docs/CHAPTER_PREP.md`。

## 默认按章备课

- **一章一份逻辑 PREP**，按真实小节拆成 Teaching Unit（通常1–3个核心点），允许跨会话继续；章末覆盖不足不能宣称完成。
- `python scripts/prep.py chapter --course X --chapter "第2章"` 只读预览，`--apply` 写 draft；按真实目录分配未占用课号。同章已有 PREP 只复用，不能覆盖。
- 可重复加 `--source "SOURCES/_external/article.md"`：资料必须先登记在**当前课程** SOURCES；记录来源、SHA256、用途、教材锚点和可靠性，修改后会报 stale。Cherry 网页工具只负责取得来源，不能代替编目。
- 每节填核心知识/活动/证据，章末设计**主线复述、综合题、迁移题、图表例题与未覆盖项**。缺章或目录不唯一就停止，不造内容。旧 `new --lesson-id`、旧 PREP 继续有效。

```bash
python scripts/prep.py chapter --course X --chapter '第2章' [--apply]
python scripts/prep.py check --course X --lesson-id lesson_003
python scripts/prep.py status --course X
```

## 教学评一致性

学习目标 → 问题/活动 → 可观察证据。ready 的硬要求：

- 每个目标都有活动和证据；支架 A/B/C，同目标最多相邻两级。
- Coverage 种子只能 unseen/introduced；期望元素不能空，绝不在 PREP 写 verified。
- `status: ready` 需真实 `anchors` 与 `book_hash`、无 TODO、已完成预期误概念和 `## 教研会决议`。
- chapter 模式增加逐节覆盖、来源路径与哈希核验，以及章末主线、综合/迁移与遗漏处理。
- 支架 A=完整定义+例子，B=关键线索，C=无提示变式；不是给学习者贴能力标签。

备课至少设计关键误概念、判别问题、卡住时替代表征和独立理解验证。真实课堂按学习者回答选路线，不强迫一次走完。

## 过期与来源

`book_hash` 不匹配即 stale；章级补充资料哈希变化也 stale。复核原文、锚点和教学设计后才能更新记录，**不能只刷新哈希**。无 front matter 的旧 PREP 为 legacy，不自动修改。SOURCES 只补充证据，不自动覆盖 `book.md`、`PROGRESS.md`。

## 明确拒绝

- ❌ 固定学段课标或学员证书/机构培训；
- ❌ 一键教案成果包/批量课件（课件见 `courseware.md`）；
- ❌ 依赖额外安装的 Skill、宿主专属导出或后台心跳。
