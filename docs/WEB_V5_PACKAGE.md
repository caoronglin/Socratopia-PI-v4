# Socratopia v5 Web · 原生 ZIP 打包与 CI（PR #28）

这是 **Alpha 预览**，与保留的 v4.3.2 稳定版完全分开。PR 合并之前，不视作正式交付。

## 文件组成

- `Socratopia-Web(.exe)`：PyInstaller 冻结的 Python 3.15 / FastAPI / AgentScope。
- `runtime/node(.exe)`：**同平台** Native Node 22。
- `runtimes/pi/server.mjs` 与 `runtimes/pi/node_modules/`：Pi SDK 生产依赖，负责普通课堂的原生模型循环。
- `web/dist/`：Ant Design 6 / Ant Design Mobile / AntV G2 前端，代码分包。
- `templates/`：只含初始化模板，不含任何私有课程或凭据。

解压后保留完整目录运行同级 `Socratopia-Web` 或 `Socratopia-Web.exe`，不能单独移动 EXE。默认打开 `http://127.0.0.1:8765`；令牌显示在本地终端，Web 页面只在内存中持有。默认工作区是 `~/.socratopia/workspace`，可用 `SOCRATOPIA_ROOT` 改成其他位置。

`--no-browser` 禁止自动打开浏览器；`--port 8888` 修改端口；`--check` 检验发行包。Pi 子进程由可执行文件自动启动并在退出时终止；只使用 loopback + Bearer 鉴权和随机空闲端口。`--no-pi` 仅历史兼容占位，不会偷偷改用第二种模型循环。

## 自动 CI/CD

1. Dependabot 每周创建 Python、Web/npm、Pi/npm、Rust/Cargo、GitHub Actions 依赖更新 PR。CI 验证前不得自动合并。
2. PR/主分支运行 Python/AgentScope/Pi SDK/Ant Design UI/Chromium 双尺寸回归和负向门禁。
3. 四平台独立安装 Python/Pi 生产依赖；冻结 Python 并复制同平台 Node；打包 ZIP+SHA256。
4. 每个平台解压真实运行，检查 native Pi 健康端点、API token 鉴权、页面、工作区模板、用户数据不进包；汇总验证四份 SHA。
5. `main` 的上述门禁均通过时自动发独立 `v5.0.0-alpha.web.<run_number>` GitHub **预发布**。不发 stable，不修改 v4.3.2，也不会在 PR 上发布。

## 重要边界

四平台测试只证明安装包和本机 API/Pi 网关可启动，不证明外部大模型凭据、实际模型推理、内容科学真实性、macOS 公证或 Windows 签名。用户须按 Pi 官方方式配置模型凭据；导师小组还需 AgentScope 的 `OPENAI_API_KEY`。引用经过服务器逐字验证并不代表事实已被自动审核。

> 构建体积、前端 chunks 和启动耗时应由 CI 提供实际数值，未测量前不能宣称缩小了百分之多少。
