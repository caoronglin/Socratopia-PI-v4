# Socratopia v5 Pi/AgentScope 精简职责（PR #28）

> 目标：**小巧 · 精简 · 快速 · 精准**。本 PR 是 Alpha 预览，不等于真实模型 E2E 已通过。

## 唯一执行链

```text
浏览器 / React（只显示服务端状态）
    ↓ 鉴权 + 指定课程
Python FastAPI（课程状态机与事实监督者）
    ├─ 教材证据检索/版本快照 → 原生 Pi SDK session.prompt()
    │      └─ 不暴露工具，单次内存会话，90 秒软中止，无外部 Agent Loop
    ├─ 用户显式开始导师组 → AgentScope 2.0.9（D/E/F 单位发言）
    │      └─ Python learning_group.py 验证顺序、会话 ID、轮次上限
    └─ 回答 JSON/逐字引文/词元关联/最新教材 SHA 检查
           → 课程独立 SQLite → 浏览器显示
```

- **Pi 原生**：仅 Pi SDK 负责普通课堂的模型调用、内部迭代和终止；Python 只有一次请求/响应与并发保护，不再复制其工具/推理循环。SDK 资源加载器禁用**全局 Extensions / Skills / AGENTS.md 上下文 / 主题 / 提示词模板**，避免不同课程通过用户级 Pi 资源泄漏；模型认证仍使用 Pi 默认模型配置。需要自定义扩展注册的第三方模型提供者在此隔离模式不保证可用。
- **AgentScope**：仅两三位导师的独立发言，空工具包，`ReActConfig(max_iters=1)`，每次只允许指定发言人；不代理普通课堂 Pi。
- **Python**：唯一能写入教材记录、PREP 草稿、课程状态、互动题、时长与小组游标的业务层。导师任何语句都不能创建 verified、ready、mastery 或虚构 2700 秒。

## 对抗幻觉：严格区分可验证与不可证明

模型不能保证绝不出错。当前默认严格 fail-closed：没有当前课程相关教材拒答；仅接受结构化 JSON；逐条校验 source_id、真实逐字引文和有限词元关联；生成期间教材变化拒绝写入；未经校验的模型正文不进入课堂或记忆。**引文存在不证明论断蕴含、教材科学正确或模型不会逻辑反转**。全部生成事实继续标记 `fact_verified=false`，不能自动授予分数、完成时间或掌握度。

## 记忆与课程隔离

每课在 `DATA/<course>/runtime/chat_history.sqlite3` 按事务独立保存已检查回复。Pi **每次单独的内存 SDK 会话**，不把原始模型历史写入 Pi session 文件。每轮只把同一门课、**当前 book.md SHA**、有实际引文的最多四次历史摘要作为 `<untrusted_course_memory>` 数据传递；旧版本教材、拒答、未经引文核对的回答不能复用。课程选择切换时清空浏览器草稿/上下文，后端用真实课程参数重新鉴权、定位和校验路径。SQLite 会话记录不是成绩库，不能推进 mastery。暂不支持多账户隔离：本地令牌持有者能访问该本机实例内所有课程。

## 资源与打包

- Web: React.lazy 为互动练习、备课、教材、学习旅程和 AntV 图表分包；零新重型运行时依赖。
- Runtime: Python/FastAPI + 按需 AgentScope + 原生 Pi Node 服务；避免再造外部 loop 和多套持久模型记忆；90 秒 Pi 软中止与 Python 95 秒请求超时，超时后不写课程权威数据。
- 四平台 ZIP：冻结 Python、静态 Web、Pi SDK **生产依赖**和对应平台 Node 二进制；拒绝带入 DATA/TEXTBOOK、密钥、.env、symlink。解压后真实启动 Pi 子进程、验证本机授权健康端点与 Web API。体积以各平台 CI 生成实际字节数为准，不能声称已达成某个体积目标。
- Pi 离线/缺凭据只可显示不可用，不能补造模型回复；群组需另行配置服务端 OPENAI_API_KEY，密钥永不发给 Web UI。Pi 原生认证请遵循 Pi 官方配置。

## CI/CD 验收硬门槛

1. Python 3.15 编译与完整严格回归，Pi 协议负向测试、真实同课记忆/旧教材失效测试、AgentScope 模拟导师组调度。
2. Node Pi SDK `npm ls` + `node --check`，React/Ant Design 构建、Ant Design CLI doctor/lint，桌面/移动端 Chromium E2E。
3. Linux/Windows/macOS Intel/macOS ARM 四平台 PyInstaller + native Node ZIP、解压运行、Pi 网关启动检查、鉴权、前端页面、SHA-256 全部过关。
4. Dependabot 周更 Python/npm/Cargo/Actions **只创建 PR**；审查后合并 main 才进入全量 CI；主分支验证通过后自动生成独立 `v5.0.0-alpha.web.<run_number>` 预发布，**绝不覆写 v4 stable**。
5. 使用真实 Provider 凭据测试 Pi 单轮和 AgentScope D/E 两导师必须单独验收；CI mock 通过不能写「真实模型已可用」。模型事实正确性仍需独立教材/人工核验。

## 官方接口参照

- Pi SDK：<https://github.com/earendil-works/pi-mono/tree/main/packages/coding-agent/docs>（`createAgentSession`、`SessionManager.inMemory`、`session.prompt/abort/dispose`）
- AgentScope 2.0.9：<https://github.com/agentscope-ai/agentscope/tree/v2.0.9>（`Agent`、`Toolkit`、`ReActConfig`）
- GitHub Dependabot：<https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference>
- React lazy/Suspense：<https://react.dev/reference/react/lazy>
