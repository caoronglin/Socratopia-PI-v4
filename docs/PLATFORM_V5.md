# Socratopia v5 平台重构 · 架构、运行与验收

状态：**alpha / 第一个可 review 的垂直切片**（不是正式版本）。分支 feat/v5-platform-foundation。
保留 v4.3.2 CLI/发布制品，不在本 PR 中修改、覆盖或删除用户 DATA/TEXTBOOK。

## 架构

```text
React 19 + Ant Design 6 (web/，仅 127.0.0.1 Vite)
    |
    | /api / Bearer token
    v
FastAPI (platform_api/app.py, Python 3.15)
    |  旧 scripts/lib/course_state.py、lesson_timer.py、learning_group.py
    |  确定性门禁：课程隔离、45 分钟课堂、多人小组发言游标
    +---- HTTP loopback ----> Node Pi SDK (runtimes/pi/)
    |                        createAgentSession; per-course in-memory session
    +---- AgentScope 2.0.9 (platform_api/agentscope_tutors.py)
                             each tutor owns a separate Agent; Toolkit([])
```

不是基于 prompt 假装多 Agent：日常课堂使用直接嵌入的 Pi SDK；小组的 D/E/F 是独立 AgentScope Agent，各自模型调用。确定性进度记录只由 Python 状态机更新，模型回答不能改 mastery。当前 AgentScope 的多导师调用是逐个执行，不宣称已实现 TeamPipeline、并发分布式服务或自动备课。

### 运行

依赖：**Python 3.15.0**、**Node.js 22.19+**，外部模型凭据。需在可信、本机使用，不直接向互联网暴露端口。

1. Python 环境：在仓库根目录执行 `python3.15 -m pip install -e ".[dev]"`，然后 `python3.15 -m uvicorn platform_api.app:app --host 127.0.0.1 --port 8000`。
2. 在同一受信环境下设置 `SOCRATOPIA_ROOT` 为项目根目录绝对路径，设置 `SOCRATOPIA_API_TOKEN` 为至少 16 字符的随机字符串。Pi 与 API 两个进程必须使用同一个令牌。
3. 在 `runtimes/pi/` 执行 `npm install --ignore-scripts`、`npm start`。通过 Pi 官方认证配置选择所需模型；无需将模型密钥发送给浏览器。
4. 在 `web/` 执行 `npm install --ignore-scripts`、`npm run dev`；打开 http://127.0.0.1:5173，输入本地访问令牌，创建或选取课程。
5. 学习小组依赖 AgentScope OpenAI provider，请单独设置 `OPENAI_API_KEY`，可选 `SOCRATOPIA_TUTOR_MODEL`。

示例：所有服务的 `SOCRATOPIA_ROOT` 必须相同；不能把个人教材放在代码仓库、浏览器 localStorage 或前端打包目录中。

### 当前已经实现

- 课程列表、无覆盖初始化、状态与 blockers 只读。
- 课程 Pi 对话。Pi 运行时真实调用官方 SDK；会话按课程隔离，但**重启后会话消失**。
- 正式课堂由原有后端计时器开课/暂停/继续/心跳/完成/中断；严格遵守 PREP ready 与至少 2700 秒规则。
- 学习小组导师配置、讨论开始、下一位独立 AgentScope 导师发言、学生确认后进入下一轮。
- 本地令牌保护全部课程 API；Pi 网关仅监听 loopback，固定端口 8787；UI 使用原生 Ant Design 6 组件和 token。
- Python API 回归测试与前端构建 CI（运行结果以 GitHub Actions 为准，提交代码本身不代表通过）。

### 安全边界

- v5 默认 Pi `noTools: 'all'`：没有默认读写/shell 工具；这不是操作系统级沙箱。不要加载不信任的全局 Pi Extensions/Skills；正式部署前必须独立审计资源加载行为。
- AgentScope 工具列表为空，未授权模型对教材/PROGRESS 的写入。模型回答视为建议，不视为课程事实。
- API token 在网页内存中保持；不写入 localStorage。仅用于**可信的单用户本地开发**。没有多用户账号/会话/权限体系。
- 缺少模型凭据、断网和网关失败返回错误，不能伪造导师答复。模型成本由用户配置的 provider 承担。
- 测试 stubs 不等于真实模型 E2E；真实 Pi SDK 和 AgentScope 模型需要配置合法凭据的人工验收。
- 此版本尚无持久会话转录、取消与流式响应、WebSocket、跨设备访问限制、进程守护、退出/重连或备份恢复流程；不能声称企业级部署就绪。

## 后续分阶段实施（硬验收）

P1：真实运行时闭环。使用 Python3.15 官方 release、AgentScope 2.0.9、Pi 1.1.0 安装；真实模型执行 Pi 一轮和 D/E 两位独立 AgentScope 发言；保留全部失败日志（脱敏）。开发者和测试者共同复核 API 字段、角色与 SDK 生命周期。任何失败都阻断完成。

P2：课程知识管理。沿用主教材权威位置，构建上传、PDF/网页解析、分段、来源追溯、向量索引；所有外部文本标为不可信，禁止作为命令执行。不得覆盖现有 book.md；索引可以重建，不迁移已验证掌握状态。

P3：课程状态机与教学调度。将章级备课、提问、评价、复习列队、学习小组 turn scheduling 从 CLI 接入 API；落盘幂等；教师的建议与学生的作答证据分离。计时需真实学生参与，每条事件记录可审计；低于 2700 秒不能进入 completed。

P4：持久对话与异步任务。SQLite（WAL/事务）或兼容持久存储保存会话 ID、消息、事件、调用 trace；课程键隔离；任务可取消/重试/断点恢复。同课排他写，跨课可并发；多进程一致性实测通过。失败不能伪造完成。

P5：产品化 UI。Ant Design token/ConfigProvider 原生交互、响应式布局、键盘访问、错误态和加载态；所有控件对应实际 API。补齐章节面板、参考资料证据展示、导师对比、历史课程、初始化向导，做浏览器 E2E 和截图回归。

P6：交付。为 Windows/Linux/macOS 分别制定可重复安装、升级、回滚及数据备份策略。原 v4 冻结 ZIP 不得谎称包含 v5 UI 或 Python3.15 运行时。稳定版需锁定 Python/npm 依赖、SBOM、CVE 扫描、冒烟测试、端到端用例和 CI Release Gates。

### 永远保持的不可变条件

1. PROGRESS/COURSE STATE/TIMER 权威字段仅确定性程序修改；LLM 不能写入已验证掌握。
2. 教材与用户课程状态不进入 git、镜像、日志、CI 或模型工具默认上下文。
3. 所有课程定位校验路径；禁止跨课程读写；不得通过 symlink 逃逸。
4. 不为通过测试假造模型结果、计时心跳、来源、提交或权威状态。
5. 同课任何有副作用的请求按锁与版本执行，拒绝未知重复动作。
6. 遵循真实运行时权限，禁止从 Pi/AgentScope 工具绕过用户拒绝。
7. 未完成真实 Py3.15 + Node + 浏览器 E2E 和迁移演练前，不得标记 v5 stable 或合并发布。
