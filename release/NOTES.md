# Socratopia PI v4.2.0 · 正式版

本次正式版包含截至 `claude-code` 发布提交的教学核心、Pi Agent 约束、Cherry Studio 适配和 **四平台预编译 Rust CLI**。这是一套本地优先、单课程隔离的教学工具；**Socratopia 作为 Cherry Studio Work 中的 Pi Agent 使用，不是 MCP Server**。

## 主要功能

- **Pi Agent 精简提示词**：始终以 `AGENTS.md` 为常驻边界，Skills 按需加载；完成即停，不绕过工具审批、不伪造测试、引用或掌握结果。
- **按章备课**：一章一份逻辑 PREP，可跨会话完成；逐节覆盖、教学目标和可观察证据、章末综合与迁移；补充资料受 `SOURCES/` 和校验哈希限制。
- **课堂时长**：正式课至少 45 分钟有效教学心跳，暂停/恢复可持久保存；未达时长可提前退出但不得标为完成。
- **引导初始化**：可以交互选择课程、主导师与可选学习小组；重复初始化不覆盖已有记录。
- **多导师学习小组**：三月七、丹恒、姬子（D/E/F）任选 2–3 位，有限轮次、轮流发言、每轮等待用户；**一个 Pi Agent 依次呈现导师角色，不是多个独立模型实例**。
- **来源信任与课程隔离**：课程 runtime、PREP、PROGRESS 与补充资料分别核验，不自动更改教材或掌握状态；网页和外部文本不作为系统指令。
- **Rust CLI**：统一入口 `socratopia`，负责命令调度和只读状态检查；业务功能继续调用成熟的 Python 实现。

## 下载

按操作系统选择**一个完整安装包**。每包包含源码、Pi Skills、Cherry 提示词、Python 脚本，以及 `bin/socratopia`（Windows 为 `bin/socratopia.exe`）。

| 平台 | ZIP |
|---|---|
| Linux x86_64 | `Socratopia-PI-v4-v4.2.0-linux-x86_64.zip` |
| Windows x86_64 | `Socratopia-PI-v4-v4.2.0-windows-x86_64.zip` |
| macOS Intel | `Socratopia-PI-v4-v4.2.0-macos-x86_64.zip` |
| macOS Apple Silicon | `Socratopia-PI-v4-v4.2.0-macos-arm64.zip` |

四个 ZIP 各附一个 `.zip.sha256` 校验文件，发布构建会在**对应操作系统**完成 Rust 编译、ZIP 解压和 CLI 冒烟测试，并在正式发布前验证所有 SHA-256。

## 安装与升级

1. 备份原有项目；**保留现有 `DATA/`、`TEXTBOOK/`，不要先删除它们**。发布 ZIP 不含用户的教材、课堂记录或密钥。
2. 解压适合操作系统的 ZIP，进入其项目根目录。
3. Linux/macOS 运行 `./bin/socratopia --version`；Windows 运行 `bin\\socratopia.exe --version`。
4. 用 `./bin/socratopia preflight` 查看 Cherry Agent 项目预检；按需执行 `./bin/socratopia init plan --course "课程名"`。

**运行前置条件**：二进制已编译，用户无需安装 Rust/Cargo；但初始化、备课、课堂计时、学习小组和预检等 Python 业务命令仍要求 **Python 3.11+**。默认 Unix 使用 `python3`，Windows 使用 `python`，也可用 `SOCRATOPIA_PYTHON` 指定解释器。项目不会在安装时自动配置 Cherry Studio 的工作目录或工具权限。

## 正式版验证范围

发布门禁：Python 3.11/3.13 全量 CI、Rust fmt/Clippy/unit tests、发布流程严格 Doctor、四系统原生 CLI 编译和解压冒烟、8 个发布资产（4 ZIP + 4 SHA-256）核验。

**尚未宣称通过的验收**：真实 Cherry Studio GUI 中的工具授权、完整 45 分钟课堂、跨会话教学效果、多导师实际语言质量，仍需按 `docs/PI_AGENT_ACCEPTANCE.md` 和 `integrations/cherry-studio/WORKFLOWS.md` 在客户端验收。CLI 打包验证不等于教学质量实测。

文档入口：`README.md` · `docs/RUST_CLI.md` · `docs/PI_AGENT_ACCEPTANCE.md` · `integrations/cherry-studio/AGENT_PROMPT.md`。
