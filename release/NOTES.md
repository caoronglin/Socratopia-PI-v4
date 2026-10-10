# Socratopia PI v4.2.0-rc.1 · Rust CLI 原生安装包

## 主要更新

- **原生 Rust CLI**：统一入口 `socratopia`；已打包编译产物，用户不需要安装 Rust 或执行 Cargo 编译。
- **四个平台**：Linux x86_64、Windows x86_64、macOS Intel (x86_64)、macOS Apple Silicon (arm64)。
- **引导初始化**：`socratopia init wizard`，或 `init plan/apply`；幂等、不会覆盖课程事实。
- **多导师学习小组**：`socratopia group ...` 配置 2–3 位 D/E/F 导师，按顺序讨论并等待学生参与。
- **45 分钟有效课堂计时**：`socratopia timer ...`，支持心跳、暂停/恢复、未达时长拒绝标记完成。
- **按章节备课**：`socratopia prep chapter ...`，支持课程 SOURCES 的补充资料。
- **Cherry Studio Pi 适配**：精简入口提示词、按需加载 Skill，不把多导师模拟误报为真实并行 Agent。
- 四平台各自经过 ZIP SHA-256 核验、解压后本机 CLI 命令冒烟测试；完整 Python 回归和 Rust 单元测试作为发布门禁。

## 下载与使用

按操作系统选 **一个完整项目安装包**，每个 ZIP 都包含源码、Skills、提示词、脚本和 `bin/socratopia`（Windows 为 `bin/socratopia.exe`）：

| 平台 | ZIP 文件名 |
|---|---|
| Linux x86_64 | `Socratopia-PI-v4-v4.2.0-rc.1-linux-x86_64.zip` |
| Windows x86_64 | `Socratopia-PI-v4-v4.2.0-rc.1-windows-x86_64.zip` |
| macOS Intel | `Socratopia-PI-v4-v4.2.0-rc.1-macos-x86_64.zip` |
| macOS Apple Silicon | `Socratopia-PI-v4-v4.2.0-rc.1-macos-arm64.zip` |

解压并进入目录；Linux/macOS 执行 `./bin/socratopia --version`，Windows 执行 `bin\socratopia.exe --version`。之后运行：

```bash
./bin/socratopia init plan --course "遗传学"
./bin/socratopia preflight
./bin/socratopia timer status --course "遗传学"
```

**重要：Rust CLI 是现有 Python 后端的入口，并非纯 Rust 独立应用。** 使用初始化、计时、备课、小组等功能仍需要系统安装 **Python 3.11 或更新版本**，能运行 `python3`（Windows 为 `python`），必要时通过 `SOCRATOPIA_PYTHON` 选定解释器。仅运行 `--version` / `status` 不调用 Python。CLI 不需要 Rust 运行时。

使用前备份已有项目，**不得删除原有 DATA/ 与 TEXTBOOK/**；发布包不包含这些私人课程文件。macOS/Linux 解压工具如果丢失可执行位，可对解压后的 `bin/socratopia` 执行 `chmod +x`。每个包对应 `.zip.sha256` 校验文件。

## 验证边界

此版本为预发行版，CI 仅保证打包的代码与 CLI 运行链可验证。Cherry Studio 内实际工具权限、连续 45 分钟课堂和多导师教学质量仍需客户端实测；不声称发布包提供后台服务或已自动安装 Cherry Agent。
