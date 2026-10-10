# Socratopia PI v4

面向 PI coding agent 的 Socratopia 提示词/课程状态架构重构版。

## 核心思想

```text
AGENTS.md          = always-on kernel
.pi/skills/        = on-demand workflows
SYSTEM/SPEC/       = canonical contracts
DATA/<course>/     = learning facts + runtime
TEXTBOOK/<course>/ = content + sources + PREP
scripts/           = deterministic validation/scaffolding
Tutor              = presentation layer only
```

## 安装到现有项目

1. 先备份现有项目。
2. 将本包内容合并到项目根目录。
3. 把旧根级 `CLAUDE.md`、`AGENT_SYSTEM_PROMPT.md` 移到归档，不要让它们与 `AGENTS.md` 同时承担等价规则。
4. 旧 `.claude/skills/` 可保留作历史，但 active Socratopia skills 使用 `.pi/skills/`。
5. 不要默认创建 `.pi/SYSTEM.md`；让 PI 保留自己的系统提示。
6. 运行：

```bash
python scripts/check.py --strict          # doctor + 全部测试（CI 同款）
python scripts/pi_arch_doctor.py --budget # 上下文 token 预算报告
```

## 已编译 CLI 安装包（无需安装 Rust）

前往 [v4.2.0-rc.1 Release](https://github.com/caoronglin/Socratopia-PI-v4/releases/tag/v4.2.0-rc.1)，选择 Linux x86_64、Windows x86_64、macOS Intel 或 Apple Silicon 的对应 ZIP。每个完整安装包都内置 `bin/socratopia`（Windows 为 `bin/socratopia.exe`），包含 Pi Skills/脚本，不需要从源码编译 Rust。

解压后在根目录运行 `./bin/socratopia --version`，并按需运行 `./bin/socratopia init plan --course '遗传学'`。**业务功能仍依赖 Python 3.11+**；个人 `DATA/`、`TEXTBOOK/` 不包含在 ZIP 中，更新前请备份，勿删除已有课程数据。每个 ZIP 附 SHA-256 校验文件。具体见 [release/NOTES.md](release/NOTES.md)。

## 可选 Rust CLI（统一命令入口）

无需重写现有 Python 业务逻辑。安装 Rust 工具链后：

```bash
cargo build --release --locked --manifest-path rust/Cargo.toml
rust/target/release/socratopia init plan --course '遗传学'
rust/target/release/socratopia timer status --course '遗传学'
rust/target/release/socratopia doctor
```

CLI 按当前工作目录发现项目，也支持 `--root`；不使用 shell 转发参数。未编译 Rust 时原来的 Python 命令**完全保留**，状态和课程隔离规则不变。完整用法见 [docs/RUST_CLI.md](docs/RUST_CLI.md)。

## 首次引导与学习小组

`python scripts/initialize.py wizard` 逐步选择课程与主导师（最后需确认），或使用 `initialize.py plan/apply` 无交互初始化。小组允许 D/E/F 中 2–3 位顺序讨论，入口 `scripts/learning_group.py`；轮次受限、每轮等待用户，不自动改变 PROGRESS 或 45 分钟计时。完整操作见 [引导与小组手册](docs/ONBOARDING_AND_GROUP.md)。

## 省 token 工具

```bash
python scripts/context_pack.py --course "课程名" [--budget 3000]   # 只读：开课所需最小热上下文
```

## 新建课程骨架

```bash
python scripts/scaffold_course.py "课程名"
```

脚本只创建缺失文件，不覆盖已有课程数据。

## 推荐使用

- `/start-class [课程/lesson]`
- `/end-class`
- `/materials-ready [课程]`
- `/switch-course <课程>`
- `/health [课程]`

也可以直接自然语言触发对应 Skill。

## 45 分钟课堂（完成时长硬门禁）

正式课堂至少累计 **2700 秒**可核验活动时间；不足时不得标记完成。Pi/Cherry Agent 每轮教学互动使用 `scripts/lesson_timer.py heartbeat`，超 5 分钟无心跳自动暂停，休息用 pause/resume，不把后台空闲算成有效课时。可提前结束并标记 interrupted；课堂事实照实保存。见 [计时使用说明](docs/LESSON_TIMER.md)。

```bash
python scripts/lesson_timer.py start --course "课程名" --lesson-id lesson_001
python scripts/lesson_timer.py heartbeat --course "课程名"
python scripts/lesson_timer.py status --course "课程名"
python scripts/lesson_timer.py finish --course "课程名"  # 不足45分钟返回非零
```

## ZIP 安装包与校验

发布版本见 [GitHub Releases](https://github.com/caoronglin/Socratopia-PI-v4/releases)，可在本地运行 `python scripts/package_release.py` 重建 ZIP 和 SHA-256 文件。打包仅包含 `manifest.json` 明确列出的项目文件，**不包含 DATA/、TEXTBOOK/ 或用户密钥**。安装前备份当前项目，不覆盖个人课堂数据。

## 与 v3 的关键区别

- 不再用一个大型 `CLAUDE.md` 承担路由 + 工具 +教学 + 工程全部规则。
- 不把导师人格常驻到工程任务。
- 不把完整 SOCIAL 当跨导师承接事实源。
- 不把“整章完整覆盖”误写成“一次教学单元的最低容量”。
- runtime 从单一线性状态改为 `phase + readiness + blockers`。
- task queue 明确只是持久待办，不假设存在后台 worker。
- GC 不再按固定条数搬走 canonical PROGRESS。

详细迁移见 `MIGRATION_PI.md`。
