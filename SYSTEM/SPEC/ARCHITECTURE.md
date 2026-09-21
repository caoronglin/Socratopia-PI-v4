# Architecture Contract

## 分层

1. **Kernel** — `AGENTS.md`：永远成立的最小规则。
2. **Workflow** — `.pi/skills/`：按意图加载的流程。
3. **Contract** — `SYSTEM/SPEC/`：数据/状态/安全事实源。
4. **State** — `DATA/<course>/`：课堂事实、证据与 runtime。
5. **Content** — `TEXTBOOK/<course>/`：主课本、来源、PREP。
6. **Execution** — `scripts/`：确定性检查/迁移/生成。
7. **Presentation** — tutor profile/social：只控制可见表达。

## 设计约束

- 同一规则只有一个权威文件；其他位置用链接/文件名引用，不复制完整规则。
- 宿主特定规则只放宿主层；SPEC 不出现 Claude/Cherry/PI 专属工具细节。
- 课堂事实与机器状态分离；PREP 与完成事实分离；social 与 handoff 分离。
- 功能缺失时允许降级，但不得伪造成功。

## PI 适配

- `AGENTS.md` 为项目常驻上下文。
- `.pi/skills/` 利用 progressive disclosure。
- `.pi/prompts/` 保存显式重复工作流。
- 不默认提供 `.pi/SYSTEM.md`。
- Extensions/subagents 可增强，但不进入正确性前提。
