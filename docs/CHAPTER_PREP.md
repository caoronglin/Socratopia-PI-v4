# 按章节备课：一章一份逻辑 PREP

## 基本规则

**默认一个教材章节 = 一份逻辑教案（`plan_mode: chapter`）。** 一章有多个小节，允许安排多个 Teaching Unit（单元一般1–3个核心点），也允许跨多个用户会话继续；不强迫一次会话讲完。每次课堂/下课仍遵守 `classroom.md`、`PROGRESS.md` 和 runtime 的真实状态契约。章级计划不产生掌握状态。

旧 `prep-1` 文件、旧课号和 `prep.py new` 均保留：**没有批量迁移、自动重排 lesson_id 或覆盖。**

## 实际工作流

1. **定位教材**：只读当前课程 `book.md`、`_outline.md`，锁定唯一章节标题及其每个子节；找不到/重名即停，不编造目录。
2. **绑定章节**：调用 `chapter` 命令优先复用已有相同章节 PREP；否则分配不与 PREP、runtime、PROGRESS 已使用课号冲突的 ID。
3. **补充资料**：可使用当前课 SOURCES 中已登记的 HTML、博客、文章、PDF、TXT 等。每份列出来源、SHA256、与哪个教材锚点有关、**作用**（例证/纠错/扩展/冲突）和可靠性（待核实/已核实/存在冲突）；不以未读文章代替正文，也不修改主教材。
4. **逐节设计**：逐个小节补充核心知识/活动、可观察理解证据。每项目标仍需 `目标 → 活动 → 证据`，为易错点准备反例、替代表征和至少一种验证方式，不一次逼问所有题。
5. **章末设计**：准备主线复述与至少两条关系、综合题/评分依据、迁移题/适用边界，核对图表、例题、习题及未覆盖项。长章节允许跨会话，未证实的概念保持 `introduced` 或 `needs_review`。
6. **就绪验收**：`status: draft` 不代表可以新授课。填完章节小节表、章末收束、教学评一致性、Coverage 种子、误概念、教研会决议和真实教材锚点，再改 `ready`；运行 `prep.py check`，同时核验课堂 runtime gate。
7. **变更复核**：修改 `book.md` 或已登记补充资料会使教案 `stale`；更新设计与哈希时应复核内容，不能只把新哈希填进去让门禁放行。

## 示例

```bash
# 预览，不写文件、不联网
python scripts/prep.py chapter --course '遗传学' --chapter '第2章'

# 从课程里已登记的 SOURCES 选择文章；生成的是 draft
python scripts/prep.py chapter --course '遗传学' --chapter '第2章' \
  --source 'SOURCES/_external/article.md' --apply

# 回显返回的 lesson_id，注意不是固定序号
python scripts/prep.py status --course '遗传学'
python scripts/prep.py check --course '遗传学' --lesson-id lesson_003
```

**补充资料来源**：知乎/博客网址可在 Cherry Studio 中经当前真实网页工具读取，正文合法取得后用 `scripts/web_article.py import` 登记；再以输出的相对 `SOURCES/` 路径供章级备课使用。CLI 不直接检索互联网；`--source` 绝不自动授权外网或打开登录墙。已存在章级 PREP 时不可带 `--source` 偷偷覆盖，应人工复核后编辑原 PREP。

## 字段与边界

| 字段/章节 | 归属 | 必须保证 |
|---|---|---|
| `chapter / anchors / book_hash` | active 教材 | 能对应真实目录、版本 |
| 章节小节与教学单元 | PREP | 各小节有活动、证据，不隐匿剩余范围 |
| 教学评一致性 / 误概念 / 教研会决议 | PREP | 目标—活动—证据一致，内部审议已完成 |
| 补充资料 / `sources` | 当前课程 SOURCES | 仅已存在且可追溯材料，哈希变化 stale |
| 章末收束 | PREP | 主线、综合、迁移与遗漏均有设计 |
| `PROGRESS.md` / runtime | 学习事实 | 课堂真实答案与断点，不由 PREP 自动赋值 |

## 验证范围

CI 测试：同章复用、不重号、只读预览、路径隔离、补充哈希与 stale、章节缺项阻断 ready、旧 PREP 兼容。真人/模型在 Cherry Studio 实际使用中的教学质量仍需独立多轮评测。

备课对齐的教育学依据：[CMU Eberly Center：对齐学习目标、教学活动与评估证据](https://www.cmu.edu/teaching/assessment/basics/alignment.html)。这支持教学评一致性的设计原则，不意味着本项目已具备可验证的学习成效。
