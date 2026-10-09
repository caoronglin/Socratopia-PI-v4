# Cherry Studio Agent 集成方案

本项目把 **Socratopia 作为 Cherry Studio 内的 Agent**，不是 MCP Server，也不是替 Cherry Studio 新建后端。以 [Cherry Studio 官方 Agent 文档](https://cherryai.com/docs/en/advanced-basic/agent/) 与 [内置工具指南](https://cherryai.com/docs/en/advanced-basic/agent-workspace/tools-knowledge-skills-mcp/) 为准。

## 配置（界面步骤）

1. Cherry Studio 左侧 **Work / 工作** → **Add Agent / 添加智能体**，新建 **Socratopia**。
2. 运行时优先选 **Fast: Pi**（因为本项目已有 `.pi/skills` 与 `.pi/prompts`）；需要不同宿主/复杂代理时可选 **Enhanced: Claude Agent**。模型须支持对应运行时的工具调用；创建后运行时选项在部分版本不可修改。
3. System Prompt 粘贴 [AGENT_PROMPT.md](../integrations/cherry-studio/AGENT_PROMPT.md)。工作目录选择**用户自己的 Socratopia 仓库本地目录**，不是 Cherry 安装目录或宿主全局配置目录。
4. 在 Agent 编辑界面按需启用内置 **Web Search / Web Fetch（网页抓取）、Files、Knowledge Base、Memory**；将需要的 Cherry 知识库**显式绑定**。工具列表和权限模式以当前版本为准。除非确有外部系统需求，不安装新的 MCP 服务器。
5. 按宿主默认工具导航使用已内置的 `cherry-tool-guide`；调用前检查实时工具表与参数。外部工具拒绝、无网或知识库未绑定时要降级，不能偷偷从 shell 绕过。为文件写入选择 **Ask Before Acting / default** 或适当审批模式，不建议对不熟悉来源的网页直接开 Full Access。
6. 先运行只读预检 `python scripts/cherry_preflight.py --course '当前课程'`。它只判断本地仓库和课程文件是否存在，Cherry 工具、runtime/PREP 开课 gate 都需另外核验。详细操作与手动验收见 [运行手册](../integrations/cherry-studio/WORKFLOWS.md)。第一次测试依次试：「检查当前课程与断点（只读）」「学习这篇 URL，先指出来源和观点」「把文章正文作为资料登记到当前课程」「复习上课错题」。确认每一步的状态与实际文件一致。

> `AGENT_PROMPT.md` 是供编辑器粘贴的系统提示词，不是 Cherry Studio 内部 `agent.json` 数据库导入格式；本项目不写入 Cherry 的 SQLite、系统配置文件或 API 私有接口。不同版本的具体按钮名称可能变化。

## Cherry 宿主能力 → Socratopia 契约

| Cherry 能力（存在时） | Agent 动作 | Socratopia 责任 |
|---|---|---|
| `mcp__cherry-tools__web_fetch` / `web_search` | 读取公开链接/补充出处 | 入库前清洗，标记不可信，禁覆盖 `book.md` |
| `mcp__cherry-tools__kb_list` / `mcp__cherry-tools__kb_search` / `mcp__cherry-tools__kb_read` | 只查询绑定知识库 | 不把召回片段当掌握证据 |
| `mcp__cherry-tools__kb_manage` | 经批准添加/重建知识 | 保留 URL、哈希及课程隔离 |
| `mcp__cherry-tools__to_markdown` | 把可访问 PDF/Office 转 Markdown | 只登记课程来源，不自动覆盖主课本 |
| `mcp__agent-memory__memory` | 检索稳定偏好和背景 | 不取代课程 `PROGRESS.md` |
| `mcp__cherry-tools__session_*`, `cron`, `notify` | 仅用户明确要求且工具存在时调用 | 不把计划入队冒充正在后台执行 |
| Agent shell/file tools | 运行项目脚本、编辑本课程文件 | 受 `AGENTS.md` 和路径安全约束 |

注意：这些名称是 Cherry 官方仓库 [cherry-tool-guide](https://github.com/CherryHQ/cherry-studio/tree/main/resources/skills/cherry-tool-guide) 在核对日记录的路由**例子**，不是对所有已安装 Cherry Studio 版本的可用性保证。实际工具声明优先。

## 网页文章入口

```bash
# 查看计划（不联网、不写文件）
python scripts/web_article.py plan --course '课程名' --url 'https://example.org/post'

# 用户提供下载好的 HTML、Markdown 或纯文本正文
python scripts/web_article.py import --course '课程名' --url 'https://example.org/post' --file article.html

# 只有显式同意联网、开启环境标志后，才走 CLI 直接抓取；
# 在 Cherry Agent 中优先使用 Cherry 提供的 web_fetch。
SOCRATOPIA_EXTERNAL=1 python scripts/web_article.py fetch --course '课程名' --url 'https://example.org/post' --authorize

# 也可以用 --file - < article.txt 通过标准输入导入，避免在 shell 中拼接不可信正文

# 获取实际来源标题、章节、原文片段和学习路线（不是自动生成的摘要）
python scripts/web_article.py study --course '课程名' --url 'https://example.org/post'
```

遇到知乎需登录、反爬、动态内容或无法访问时，提供原文文本而不是尝试绕过。

## 真实 Cherry 运行时验收

**静态仓库 CI 不能证明 Cherry Agent 具备网页/Kb/记忆工具权限。** 真实使用须先在 Work 内核对工具是否暴露，并分别验证公开网页、受限知乎降级、课程隔离、断点恢复和拒绝审批后的行为。详细用例见 [WORKFLOWS.md](../integrations/cherry-studio/WORKFLOWS.md)。

## 精简 Agent Prompt 与停止条件

系统提示词只保留宿主身份、Skill 路由、工具权限、文章导入边界与输出约束；单次请求的完整状态机见 [`SYSTEM/SPEC/AGENT_LOOP.md`](../SYSTEM/SPEC/AGENT_LOOP.md)。不通过 System Prompt 注入整套 Kernel，也不把“Agent Loop”误表述为可由文本强制限制的 Pi 内核配置。

## 权限与 CI/CD

- 不向 Cherry Agent 提示词、日志或 git 提交任何模型密钥或浏览器 Cookie。
- 网页、检索结果和 PDF 提示词属于不可信资料，不可改变 Agent 指令或文件读写权限。
- CI 检查提示词路由、离线文章提取、授权门禁、GitHub Actions 最小权限与并发；CI 不提供 Cherry GUI 或真实联网抓取的端到端证明。
- 新功能先走 PR 与两版 Python 测试，再合并至 `claude-code`。不自动更改 `main`。

## 上游依据

- [Cherry Studio：Work/Agents](https://cherryai.com/docs/en/advanced-basic/agent/)
- [Cherry Studio：Create Agent](https://cherryai.com/docs/en/advanced-basic/agent-workspace/create-agent/)
- [Cherry Studio：Tools, Knowledge, Skills, MCP](https://cherryai.com/docs/en/advanced-basic/agent-workspace/tools-knowledge-skills-mcp/)
- [Cherry 官方 Agent 工具路由 Skill](https://github.com/CherryHQ/cherry-studio/blob/main/resources/skills/cherry-tool-guide/SKILL.md)
- [Cherry 官方 Agent 类型 Schema](https://github.com/CherryHQ/cherry-studio/blob/main/src/shared/data/api/schemas/agents.ts)：含 `'pi'` 运行时。
