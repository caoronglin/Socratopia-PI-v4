# Socratopia v5 Alpha.7 — AgentScope 全运行时迁移

## 决定与目标

迁移 v5 的**所有在线导师推理**至已固定的 AgentScope Python 2.0.9 SDK。Python 3.15/FastAPI 继续作为课程事实、PREP 和计时的唯一状态来源。旧 Pi Node 子服务从 v5 运行、安装包与 CI 依赖路径中退出；旧源码保留作历史兼容，不在 v5 启动也不打包。**不影响 v4.3.2 stable Release**。本版本为 Alpha，不代表线上模型可用性已通过外部凭据验证。

## Agent Loop：受限循环而非无限自治

单次学习请求：ROUTE → INSPECT（教材检索）→ ACT（AgentScope reply）→ VERIFY（服务器强制引文和来源版本验证）→ RECORD（本课程独立 SQLite，保存审核结果）→ YIELD / BLOCKED / DONE。

- 单课程至多 **1 个在途回合**，一个进程全局至多 4 个回合；额外请求立即返回无可用，而非无限排队。
- 模型代理上限 2 次内部迭代，最多 90 秒，禁止 shell/filesystem/toolkit 执行。模型输出 32K 字符、提示词 24K 字符上限。超时/取消不记录输出，`finally` 释放调度槽。
- AgentScope 模型端**不共享跨课短期内存**，恢复课堂仅通过经过引文核验的 SQLite 历史，严格标注教材版本；未核验 raw LLM reply 不是课程学习事实。
- 两到三位导师角色具有不同的语气、推理与教学侧重点；独立每位导师发言，每轮用户必须明确继续，最多三轮。由 `learning_group.py` 控制状态与落盘。
- 不自行判断 master/ready，不允许伪造 2700 秒，答错的引文不能写进历史或授课成绩。
- 尚未提供有认证角色和审计的 PREP 人工 ready 审批，不能由模型代替。

## 性能与发布

1. 移除额外 Node.js/Pi 服务的启动、进程生命周期与错误链。FastAPI 调用 Python AgentScope，无回环 HTTP。
2. AgentScope 模块推理时按需导入，读取课程列表和编辑 PREP 不需要初始化模型。禁止无边界上下文扩张：导师只接受最多六轮、每轮 900 字符的会话摘要。
3. 单进程原生 ZIP 不包含 `runtime/node` 与 `runtime/pi`；仍包含 Web/Ant Design 资源、Python3.15+AgentScope PyInstaller 可执行文件和缺省模板。macOS/Windows/Linux 分别测试本机 ZIP 解压、启动、鉴权与哈希。
4. 本机通过 `OPENAI_API_KEY` 提供模型认证，支持符合预期的 `OPENAI_BASE_URL` 与 `SOCRATOPIA_MODEL`。仅允许 HTTPS 远程模型地址，HTTP 限 loopback。浏览器只读取是否配置、模型名称与 loop 上限，绝不读出密钥或 base URL。
5. 验证要求：新 Python AgentScope 运行时/并发/取消/禁用旧 Pi 桥测试；完整 legacy Python / Rust 回归、Ant Design CLI 0 issues、Chromium 桌面移动 E2E、四原生 ZIP 和 SHA-256。无实密钥 CI 不能声称完成生产模型 API 实测。

## 后续仍须独立验收

- 真实凭据调用、不同模型兼容（特别是非 OpenAI 协议）、代理断连恢复/用户随时取消与模型流式输出。
- 跨进程全局并发需外置协调；当前内存调度器针对单进程 v5 桌面。生产多 Worker 需要改为共享限流。
- 核验后才考虑清除 v4 PI/Cherry 历史工具源码，不能破坏现有稳定版发行包。
