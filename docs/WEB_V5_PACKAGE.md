# Socratopia v5 Web · 原生可执行版打包与 CI

**Alpha 预览版（代码合并入 `main`）**。这是 v5 Web 运行时 ZIP，与旧 v4 CLI 正式 Release 分开；`main` 表示最新开发主线，不表示稳定发布。

## 用户运行

在 GitHub Actions 的 v5 Web Standalone Executables 最新**成功**运行中，下载对应平台的 web-v5-* artifact；确认对应 SHA-256：

- Windows x86_64：解压后双击 Socratopia-Web.exe
- Linux x86_64：解压后执行 ./Socratopia-Web
- macOS Intel/Apple Silicon：解压后执行 ./Socratopia-Web（尚无 Apple 公证/签名）

启动后自动打开 http://127.0.0.1:8765；控制台打印随机 API Token，输入 Web 的令牌框。数据默认保存在 ~/.socratopia/workspace，独立于安装包。SOCRATOPIA_ROOT 可设置其他工作区，不覆盖既有课程资料。`--no-browser` 禁用打开浏览器，`--no-pi` 使用离线习题功能，`--port 8888` 修改端口，`--check` 检查打包内容。

整个 ZIP 含一个原生 Web 启动二进制文件、冻结 Python 3.15、内置 Node 22 和 Pi SDK，以及 Web 构建产物。**不能单独移动 EXE 而丢弃同级 runtime/ 和 web/dist/**；终端用户无需额外安装 Python、Node、Rust、npm。真实在线 AI 功能仍需要有效模型凭据，缺少凭据时明确返回不可用。

## 自动构建与验收

1. 在 Linux、Windows、macOS x86_64/arm64 原生 Actions runner 上安装 Python 3.15、Node22。
2. 构建 React/Ant Design Mobile/AntV 资源；Pi SDK 复制生产依赖。
3. PyInstaller 6.22.3 冻结 Python/FastAPI/AgentScope 到 Socratopia-Web(.exe)。
4. 各平台打包完整运行时到 ZIP，打包清单只包含可信模板、Node/Pi 依赖、Web 静态资源及原生二进制；禁止个人 DATA、TEXTBOOK、Token、.env、软链接。
5. 解压 ZIP 并**真实执行原生文件**，检查 --check、Node/Pi 后端、本地 API、React 静态页面、401/200 鉴权、私有工作区模板。
6. 每个平台上传 ZIP 与 SHA-256；四平台全部通过后校验 4 个 ZIP 的校验和。
7. `main` 的每次相关推送自动构建四平台测试包。只有从 `main` 手动执行 workflow_dispatch 后才发布带 v5.0.0-alpha.web.* 标签的 **GitHub 预发布**，不发布 stable，也不修改旧 v4.3.2 Release。

## 硬性限制

45 分钟、章节 PREP、不可虚构进度和 mastery 门禁不变。单用户 loopback Alpha 不提供多用户安全隔离。macOS 未公证、Windows 未签名，需额外设备兼容性检查；真实模型的 Pi/AgentScope 端到端验收尚未完成。构建测试通过不等于正式版本已可用。
