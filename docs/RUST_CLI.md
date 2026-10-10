# Rust CLI · Socratopia

Rust CLI 是**可选的轻量前端**，不是第二套课程引擎。状态写入继续由经过回归测试的 Python 实现负责。无需外部 Rust crates，单二进制仅依赖标准库；正式安装包同时提供冻结的 CPython 后端；初始化、计时、备课等业务命令无需另装 Python，项目脚本仍是唯一业务逻辑源。

## 直接使用已发布的二进制

[v4.3.2 GitHub Release](https://github.com/caoronglin/Socratopia-PI-v4/releases/tag/v4.3.2) 提供四种完整项目 ZIP（Linux x86_64、Windows x86_64、macOS Intel、macOS arm64），CLI 和 `socratopia-backend` 在解压后的 `bin/` 目录，**无需安装 Rust 或 Python**。例如 Linux/macOS：`./bin/socratopia --version`；Windows：`bin\\socratopia.exe --version`。

正式包内的冻结后端包含 Python 运行时；日常命令不需要系统 Python。仅开发者使用的 `doctor`、`package` 或自行从源码编译需要 Python；设置 `SOCRATOPIA_PYTHON` 可主动改用系统解释器。不要覆盖原项目中的 `DATA/` 或 `TEXTBOOK/`；每个安装包附 `.sha256` 文件。下文的 Cargo 步骤仅用于希望自行编译的开发者。

## 独立安装包与开发环境

Release CI 在四个平台分别执行 PyInstaller 和 Rust Release 编译，逐包进行解压测试并确认业务命令确实调用内置后端。构建版本使用 Rust 1.99.0、pytest 9.1.1 和 PyInstaller 6.22.3；后两项仅为 CI/打包依赖，用户无需安装。

## 构建

```bash
cargo build --release --locked --manifest-path rust/Cargo.toml
./rust/target/release/socratopia --version
./rust/target/release/socratopia status --course '遗传学'
```

在 Windows 上为 `rust/target/release/socratopia.exe`。工作目录位于仓库根或子目录时自动向上寻找 `AGENTS.md`、`manifest.json` 和 `scripts/`；在其他位置运行时指定 `--root /实际仓库目录`。**不可假定 Rust 已安装**，安装前继续调用原 Python 命令。

## 命令映射

| Rust CLI | 现有单一实现 | 边界 |
|---|---|---|
| `socratopia status --course X` | Rust 原生只读文件存在性检查 | 不验证 readiness、不创建数据 |
| `socratopia init plan --course X` | `scripts/initialize.py` | 只读 |
| `socratopia init apply --course X ...` | 同上 | 按原初始化权限，幂等且保留课程 |
| `socratopia group ...` | `scripts/learning_group.py` | 仍受限 2–3 位导师、轮次与发言顺序 |
| `socratopia timer ...` | `scripts/lesson_timer.py` | 仍需真实心跳/≥2700s 才能完成课堂 |
| `socratopia prep ...` | `scripts/prep.py` | 章节 PREP gate 不变 |
| `socratopia article ...` | `scripts/web_article.py` | 外网授权与来源真实性 gate 不变 |
| `socratopia preflight [--course X]` | `scripts/cherry_preflight.py` | Cherry 实际工具权限仍为 unverified |
| `socratopia doctor` | `scripts/check.py --strict` | 开发者命令，需要系统 Python |
| `socratopia context ...` | `scripts/context_pack.py` | 原课程隔离 |
| `socratopia course/search/review/handoff/tasks/memory/package` | 对应 `scripts/*.py` | 原各 CLI 参数及安全约束不变 |

示例：

```bash
socratopia init plan --course '遗传学'
socratopia group status --course '遗传学'
socratopia timer status --course '遗传学'
socratopia prep chapter --course '遗传学' --chapter '第2章'
socratopia doctor
```

## 安全与性能边界

- **不使用 shell、eval 或字符串拼接**：Rust 固定子命令到受控 Python 脚本，以分离的原始参数调用 `std::process::Command`。子命令不能指定任意脚本路径。
- **不迁移 runtime/schema**：保持 Python 模块对 PREP、PROGRESS、计时和课程状态的单一写入所有权；只有 Rust `status` 会原生读取**路径存在性**。
- Rust 不扫描其他课程、无网络、无后台服务、无隐式授权；课程名拒绝路径穿越与隐藏目录，项目工作目录必须存在关键标识文件。
- 宿主 Pi/Cherry 仍按自身权限授权每次工具调用；Rust 不会绕过宿主、自动提供原生 Cherry 工具或替代 Skills。
- 发布包默认使用同目录 `bin/socratopia-backend`（Windows 为 `.exe`），其中已内置 CPython；`SOCRATOPIA_PYTHON` 仅用于开发者明确选择系统 Python。若冻结后端缺失，可回退到系统解释器；`SOCRATOPIA_REQUIRE_BUNDLED=1` 可要求必须使用随包后端并在缺失时失败。
- **Rust 主要提升 CLI 入口的一致性、安全参数转发和轻量预检**。因为真实教学逻辑仍运行 Python，此阶段不承诺整体性能提升。下一步只在分析出热点以后才决定迁移具体解析器或索引逻辑。

## 验证

```bash
cargo fmt --manifest-path rust/Cargo.toml --all -- --check
cargo clippy --manifest-path rust/Cargo.toml --all-targets --locked -- -D warnings
cargo test --manifest-path rust/Cargo.toml --locked
python scripts/check.py --strict
```

CI 双线验证 Python 3.11/3.13 及 Rust CLI，避免其中一个环境正常而另一个失效。Rust CLI 自身的单元测试不能替代 Cherry Studio 中的真实教学/工具审批测试。

官方参考：[Rust Cargo Book](https://doc.rust-lang.org/cargo/)、[Rust Clippy](https://doc.rust-lang.org/clippy/)、[Pi Skills/Prompt Templates](https://pi.dev/docs/latest/skills)。

## CLI 运行时完整性（v4.3.2）

安装包的 `bin/socratopia` 会优先使用同目录的 `socratopia-backend` 冻结后端；如果后端缺失，则返回错误，**不会默默依赖电脑上的 Python**。`--root` 参数允许指定另一份已核验的 Socratopia 项目工作区，冻结后端会遵守该目录。源码开发仍可显式设置 `SOCRATOPIA_PYTHON`，保留开发者工具链。

CI 对四个目标平台分别构建、解压和实际运行，并检验跨工作区调用及缺失后端的失败路径。更新策略见 `.github/dependabot.yml`。
