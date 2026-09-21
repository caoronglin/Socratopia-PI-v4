# single-skills（实验分支）

把主分支「3 active skills + references」里合并的能力，**拆成可独立分发的单 skill**，用于评估另一种打包方式（例如经 IMA/技能市场单独安装）。

> 这是**实验分支**，不进入主控制面。主分支仍维持 active skill = 3（见 `AGENTS.md`/审批意见）。

## 与主分支的关系
- 每个单 skill 是**薄封装**：内含关键规则，确定性引擎指向同一 `scripts/*.py`，完整规则指向 canonical reference。**不复制第二套规则源**。
- 拆出的 7 个：`socratopia-ontology` / `socratopia-feynman` / `socratopia-humanizer` / `socratopia-self-improving` / `socratopia-search` / `socratopia-external-research` / `socratopia-courseware`。

## 取舍（见 issue）
- 单 skill：发现性/模块化/单独分发更好；但增加 discovery 成本与触发歧义，易与 3-skill 方案规则重复。
- 3 skill + references：常驻上下文更小、单一事实源更清晰。

## 打包为独立 skill
每个子目录即一个可分发单元（含 `SKILL.md`）。若要真正独立，需连同其依赖的 `scripts/` 与 `SYSTEM/` 契约一起发布。
