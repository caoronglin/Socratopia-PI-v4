# v5 Alpha.6 · PREP 结构化编辑与 Agent Loop 边界

状态：功能候选（Draft PR）；不得未经 CI 验收直接合并为稳定版。

## 各模块职责

- **Pi SDK**：普通课堂的模型会话、每课程持久会话及内部模型响应循环；现有 `noTools: all`，不提供 Shell/文件工具权限。
- **AgentScope 2.0.9**：学习小组的独立导师实例、人格与模型响应。每次 `Agent.reply()` 生成一位导师发言；**当前没有用 MsgHub / ReActAgent 工具循环管理整场讨论**。
- **Python 课程状态机**：决定发言顺序、讨论轮次、谁在等待学生、教材引用是否可用、记录是否可写入及停止条件。至多三轮，等待用户继续。
- **Web**：请求状态与操作入口，不自行授予 ready、掌握度或有效课时。
- `SYSTEM/SPEC/AGENT_LOOP.md` 是 Pi/Cherry 的**提示词行为契约**，不是硬性运行时 max-turn 限速器。要增加工具自主循环，须另做工具权限、取消、日志和端到端验收。普通教学不要引入重复的外层无限循环。

### 实际一次小组响应

`ROUTE(course) → INSPECT(book, state) → ACT(AgentScope single tutor reply) → VERIFY(citation, session snapshot) → RECORD / BLOCKED → DONE/YIELD`

没有相关教材证据不调用模型；模型引用未通过不写对话；状态变化拒绝过期回复；学员不继续则不自动进入下一轮。

## 本轮增量

增加 **问题链 / 预期证据 / 教研会决议** 的结构化字段保存 API：
`PUT /api/courses/{course}/prep/{lesson_id}/sections`

服务端只接受三个白名单 Markdown 小节、源文件完整 SHA-256、已存在 draft；由同一原子文件编辑器保存，**不更改 YAML 状态、教材锚点、教学评表格、来源或 PROGRESS**。拒绝插入新的二级标题、YAML front matter、版本冲突。后续接 Web 表单（非强制修改 raw Markdown），不自动审批 ready。

## 下一阶段

- 正式人工审核必须具备专门身份/权限、教材版本核验、只对合法 PREP ready 的签署事件与可追溯审计；现有单一 Bearer Token 无法区分学生与审批人，所以**此阶段不开放网页批准**。
- 测试：Python 3.15 结构化输入/冲突/越权/不影响课堂，原有 Rust/Python 回归、Ant Design CLI、桌面/移动 Chromium、四平台 ZIP。
