# Socratopia v5 课程 Agent · 设计与验收准则

> 当前实现位于 **PR #28**，不代表 main 已发布。产品目标：**小巧 · 精简 · 快速 · 精准**。

## 单一事实监督：Python 优先

```text
React / Ant Design UI → FastAPI 鉴权 / 课程权限
                            ↓
                 课程状态机 / 教材版本校验
                  ┌─────────┴─────────┐
                  │                   │
           AgentScope 课程 Agent   人工/确定性操作
            ├─ 讲解模型            ├─ PREP 审批
            ├─ 导师模型            ├─ 计时与进度
            ├─ 图谱读取工具         ├─ 练习判分
            └─ 仅受控 JSON 输出     ├─ 课程归档
                  │                 └─ 任务队列 / 快照同步
                  ↓
         逐字引文 / 源 SHA 复核
                  ↓
        本课程 SQLite + 页面显示
```

**不是每个功能都自己运行一个 Agent Loop。** 每门课程有稳定逻辑 Agent ID，但每次请求都使用独立 AgentScope 实例，不允许常驻模型思维或跨课共享消息；Python 一次只批准一次受控调用。ReAct 迭代硬上限为 1，教学 90 秒，复习和可视化角色有更低预算。失败/拒答不推进学习时间或掌握度。

**Pi 兼容性边界：** 旧版原生 Pi SDK 仍保留在仓库和现有多平台打包链中，供兼容性审计；当前普通课程聊天主路径已迁移为课程 AgentScope。未经过打包体积/用户配置迁移的独立验证前，不删除 Pi 运行时，不谎称包体积已缩小。后续应比较“Lite AgentScope”与“Full Pi-compat”体积，分开构建，避免重复循环。

## 模型按任务指派

每门课独立的 `DATA/<course>/runtime/model_roles.json` 配置 `teach/tutor/explain_visual/review` 模型标识；密钥只在服务器环境。前端可以修改模型标识，**不是**配置/泄漏 Provider 密钥。当前 teach、tutor 已通过 AgentScope 路由；visual 和 review 的配置已可用，但自动调用、内容审核链未完成，不声称已集成。

## AgentScope 原生工具：最小权限

默认 **零外部工具**；课程显式开启 graph 时，用 `Toolkit.register_tool_function` 注册只读 `course_outline`，仅返回同课 `book.md` 的原标题、行号与 SHA 摘要。不能直接提供 Shell、任意文件读写、网络、成绩写入、计时器及课程状态控制。所有任务仍由用户明确发起，不能自运行。导师 D/E/F 各自有分明的教学风格，提问质量优先于口头角色表演，每轮必须等待学生继续。Persona 与答复一样不可突破服务端引文验证。

## 教学图谱与互动网页

现有图谱仅由 Markdown 一级至四级章节标题构建，**是目录关系，不是知识因果推断**。前端使用懒加载 SVG + Ant Design 组件，无额外大型图库依赖。选中节点可追溯源行号；教材变化改变 SHA，旧问答引用标记过期。未来生成互动演示应通过预审模板 DSL（SVG、AntV G2 数据声明），禁止直接在网页执行模型生成的任意 JS/HTML；课程状态不得由演示生成器更改。

示范课题（需结合对应实际教材才能启用）：减数分裂染色体分配、DNA/ RNA 配对与复制、玉米 BSA-seq 双亲本 SNP 流程、RNA-seq fastp→STAR→RNASeQC→DE、LightGBM 叶子优先分裂与过拟合。可利用 Exa/Tavily/Firecrawl 在开发期收集案例，但**外部网页不自动成为正式教材**，需教学审核与来源版本固化。生成的插图应有来源和授权标注。

## 生命周期 / 数据隔离

- `setup/ready/in_lesson/post_lesson` 是原课程状态机相位，不因归档改变。
- `archive_state.json` 是独立可恢复标记；归档后禁止在线生成和主要课堂修改，继续允许读取，保留 `PROGRESS.md`、教材、任务和已核验对话。禁止用云端快照替代权威课程状态。
- Chat 的长期历史按课程独立 SQLite，只复用当前教材版本、通过逐字核验的最多四个问答。引用存在**不代表**自然语言论断科学正确。
- WebDAV 与 S3 暂实现**手动、不覆盖的远端快照上传**，包括 SQLite 一致性备份、指定配置及教材，SHA-256 显示；默认关闭自动上传、下载覆盖和恢复。WebDAV 必须 HTTPS 且凭据由服务端注入；S3 使用可选 `boto3` + SSE-S3，不能将存储私有性误判为端到端加密。云端恢复需另外实现双向冲突审查和人工确认，不得直接覆盖课程记录。

## Ant Design CLI：项目现成脚本

```bash
cd web
npm run antd:doctor  # React / antd 兼容、重复安装与样式依赖检查
npm run antd:lint    # deprecated / 无障碍 / 使用方式 / 性能
npm run antd:usage   # 组件与子组件使用统计
npm run build && npm run test:e2e
```

`@ant-design/cli` 负责离线组件 API、Token、迁移和静态审查，**不是**替代 Playwright、类型检查、实际可用性验收或设计系统本身。

官方参考：
- <https://docs.agentscope.io/en/versions/2.0.10/building-blocks/agent/configure-agent>
- <https://doc.agentscope.io/tutorial/task_tool.html>
- <https://ant.design/docs/react/cli-cn/>
- <https://react.dev/reference/react/lazy>
- <https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html>

## 发布硬门禁

Python 3.15 API、3.11/3.13 兼容性、AgentScope SDK 原生 Toolkit、读权限与课程隔离、当前教材引文、React 19/Ant Design 6、移动端浏览器 E2E、WebDAV/S3 模拟测试、四平台 ZIP 解压启动、SHA-256 必须全过。**真实 Provider 端到端正确性没有测试就标记为未验收。** 模型配置、仓库重命名与自动发布均不得跳过测试或 GitHub 权限边界。当前 GitHub 插件没有直接重命名仓库的操作，因此仓库名称不能在本 PR 中声称已改。 
