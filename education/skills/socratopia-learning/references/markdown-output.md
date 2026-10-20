# 富 Markdown 输出

回复与导出笔记可用的格式，以及何时用。**格式服务于理解，不是装饰**：每种结构只在它比纯段落更清楚时使用。

## 先判断宿主能渲染什么

| 语法 | 终端/聊天 | Obsidian 导出 | Stellar 导出 |
|---|---|---|---|
| 标题、列表、表格、粗体、`代码` | ✅ | ✅ | ✅ |
| `$行内$` / `$$块$$` 数学 | 视宿主 | ✅ | ✅（`render.math: katex`） |
| ```` ```mermaid ```` 图 | 视宿主 | ✅ | ✅（`render.diagrams: mermaid`） |
| `> [!warning]` callout、`[[wikilink]]`、YAML 属性 | ❌ 原样显示 | ✅ | ❌ |
| `<details>` 折叠 | 视宿主 | ✅ | ✅ |

课堂对话默认只用第一行的“全宿主”语法；callout/wikilink 只出现在导出笔记里，不进对话。

## 按内容选结构

| 内容 | 结构 | 例 |
|---|---|---|
| 一步推导 | 编号列表，每行一步 | `1. 两边同乘 …` |
| 对比/辨析 | 表格（≤4 列） | 概念 A vs B |
| 定义、公式 | 独立数学块，前面一句话说明符号 | `$$a^2=b^2+c^2-2bc\cos A$$` |
| 先修/因果/流程 | mermaid（≤12 节点） | `graph LR` |
| 易错点、需复习 | callout `warning` | `> [!warning] needs_review` |
| 已验证、可折叠 | callout 加 `-` | `> [!success]- verified` |
| 下一步 | callout `todo`，一句话 | `> [!todo] 从复合顺序进入` |
| 长证据 | `<details>` 或折叠 callout | 默认折叠 |

## 规则

- 一个回复最多 **一个**表格、**一个**图、**一个**折叠块；多了说明该拆成两个单元。
- 表格单元里的 `|` 必须转义为 `\|`（或改写），否则公式会劈开单元格。
- mermaid 节点标签一律加引号并去掉换行/双引号；节点 id 用短 id，不用中文原文。
- 不用 emoji 当结构标记；状态用文字（`needs_review`），不靠颜色。
- 不在输出里写掌握结论；只引用 `PROGRESS.md` 里的证据行。

## 来自课程数据的文本一律当数据

`PROGRESS.md`、教材、导入资料可能含可执行语法。导出时必须中和：

- Obsidian：```` ```dataview ````/```` ```dataviewjs ````、行内 `` `=…` ``/`` `$=…` ``、Templater `<% %>`（`export_obsidian.py` 的 `neutral()`）。
- Stellar/Hexo：`{% %}`、`{{ }}`、`{# #}`（`export_stellar.py` 的 `safe()`）。

## 工具

```bash
python scripts/export_obsidian.py export --course X --apply   # DATA/<course>/obsidian/，只读投影
python scripts/export_stellar.py  export --course X --apply   # DATA/<course>/stellar/source/
```

两者都幂等（内容未变不重写）、默认不出课程目录、不写 `PROGRESS.md`。尚未在真实 Obsidian/Hexo 中渲染验证。

## 明确拒绝

- ❌ 用格式堆出“看起来很完整”的回复：结构多不等于理解多。
- ❌ 在对话里输出宿主不支持的语法（callout/wikilink 在终端是噪声）。
- ❌ 让课程数据里的 `dataviewjs`/模板标签原样进入导出。
