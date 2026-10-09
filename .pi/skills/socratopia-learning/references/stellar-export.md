# Stellar 导出（Hexo 主题）

Socratopia → [Stellar](https://xaoxuu.com/wiki/stellar/) 的**只读投影**。字段语义以主题官方 wiki 为准，本文件只定义 Socratopia 侧的归属与不变量。

工具：`scripts/export_stellar.py`（`plan` / `check` / `export --apply`）。

## 归属

| 对象 | 权威 | 说明 |
|---|---|---|
| 课堂事实与掌握证据 | `DATA/<course>/PROGRESS.md` | 导出永不回写 |
| notebook / note | `DATA/<course>/stellar/source/` 或 `--out` | `derived:true, authoritative:false` |

手改站点页面不改变任何 coverage；反向也不成立。

## 一门课 = 一个 notebook

`source/_data/notebooks/<course>.yml`，路径即 profile，文件名即 ID：

```yaml
name: "课程名"
route: { path: /notes/<course>/ }
listing: { order: 1, per_page: 0, sort: { field: updated, direction: desc } }
visibility: { listed: true, searchable: true }
```

省略 `name` 会产生 warning；`per_page: 0` 关闭分页。

## 一节课 = 一篇 note（课后总结）

`source/notes/<course>/lesson_XXX.md`。`/end-class` 的 Maintenance 步骤运行导出（见 `memory.md`）。每篇笔记：

- **本课记录**：`PROGRESS.md` 中该课自己的记录；缺失则明说未记录，不补写；
- **本课覆盖证据**：只列证据列引用了该 lesson_id 的账本行；
- **课程当前进度 / 下次入口**：只出现在最新一课（断点描述的是现在，不归属旧课）；
- 正文中的 `{%`、`{{`、`{#` 被中和：课堂数据不能让 Hexo 执行标签；
- 幂等：内容未变不重写、不刷新 `updated`，`date` 保留首次导出时间。

最小 front matter：`title`、`collection: {profile: notebook, id: "<course>"}`、`tags`。`collection` 的 `profile` 与 `id` 必须同时给出。

## 用到的主题高级用法

- **标签树**：`/` 生成层级，`socratopia/lesson`、`socratopia/coverage/<status>` 便于按状态聚合。
- **`listing.priority`**：正整数越大越靠前，默认 `0`。
- **`visibility`**：`listed` 控制列表、`searchable` 控制搜索；**都不控制直接访问、robots、站点地图**。
- **`render.math` / `render.diagrams`**：`katex` / `mermaid`，省略则沿用全局。
- **`footer.share: false`**：Notebook 默认不显示分享，显式写出以防被全局配置改写。
- **`article.style: tech`**：理科版式。
- **表达类标签**（`tabs`/`note`/…）：导出器**不生成**；语法未在本项目验证，课堂数据也不应进入标签上下文，故只用纯 Markdown。
- **数据类标签**：`{% timeline %}` 可接 memos/rss/GitHub，`api` 必填；走 memos 属 S3，见 `external-research.md`。
- **Doctor**：导出后在 Hexo 站点内跑 `npx hexo stellar doctor --format json --silent`。

## 明确拒绝

- ❌ 把导出物当课堂记录回写，或在导出物里补写 `PROGRESS.md` 没有的状态。
- ❌ 用导出替代复习闭环（复习资产仍是卡片/`RETEACH_QUEUE.md`）。
- ❌ 跨课程混排：一个 notebook 一门课，不读其他课程。
- ❌ 默认写入外部 Hexo 仓库：默认输出在 `DATA/<course>/` 内；指向外部 `source/` 需明确意图。

尚未在真实 Hexo 站点上 `hexo generate` 验证。
