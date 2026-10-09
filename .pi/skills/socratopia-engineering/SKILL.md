---
name: socratopia-engineering
description: 用于 Socratopia 的多文件架构优化、迁移、脚本修改、系统化调试、提示词重构、测试与完成前验证。普通课堂问答不要使用。
---

# Socratopia Engineering

## 触发

预计涉及多个文件、状态契约、脚本、迁移、长期规则或 >5 个明显步骤时使用。

## 流程

1. **Inventory**：定位事实源、重复规则、宿主耦合和写入边界。
2. **Plan**：列出要改的合同与兼容面；避免先写后想。
3. **Change**：优先单一事实源，其他文件只引用；不复制整段规则。
4. **Verify**：运行与变更相关的测试、静态检查或 `scripts/pi_arch_doctor.py`。
5. **Report**：有验证结果即停止，简报已改/已验/阻断；不额外循环或重复总结。

Agent Loop 的 DONE/YIELD/BLOCKED 边界仅在需要时参考 `SYSTEM/SPEC/AGENT_LOOP.md`；不要用无限迭代或重复自检代替测试。

## PI 约束

- 根入口用 `AGENTS.md`；不要同时维护等价的根级 `CLAUDE.md`。
- 项目 Skill 位于 `.pi/skills/<name>/SKILL.md`，正文按需加载。
- 可重复命令优先放 `.pi/prompts/`，不塞进常驻 Kernel。
- 默认不创建 `.pi/SYSTEM.md`，避免替换 Pi 自带系统提示；只有明确知道为何需要时才使用。
- delegation 是扩展能力；无扩展时必须可顺序完成。

## 规划文件

大型工程任务若需要持久计划，可用 `task_plan.md / findings.md / progress.md`；这些文件只记录工程任务，不得写课堂掌握状态。任务结束后归档或清理。
