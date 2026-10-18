# Socratopia · AgentScope Learning Platform (v5 Alpha.8)

本地优先、单课程隔离的 AI 学习平台：教材 → 章节备课 → 课堂 → 客观练习 → 闪卡/知识诊断 → 复盘。

**唯一在线模型执行框架：AgentScope 2.0.10。** Python FastAPI 管理课程状态、权限、引用审核、计时及成绩；React 19 + Ant Design 6 / Ant Design Mobile / AntV 负责前端。没有独立的第二模型 SDK 或 Node AI 网关。

## 真实可用功能
- Markdown 教材导入（只创建、不覆盖）、章节目录与来源 SHA-256 验证
- 章节 PREP 草稿/编辑/校验；正式课堂至少 45 分钟的可核验活动时长
- 单门课程独立教学 Agent、按需启用的 AgentScope D/E/F 导师小组
- 按课程隔离的 SQLite 问答、互动题、闪卡、学习计划与基础知识图谱
- 远程快照手动上传 WebDAV/S3（不提供自动覆盖式恢复）
- 浏览器桌面/移动端交互，跨平台单进程 Python/AgentScope Web ZIP

## 源码运行
依赖 Python 3.15、Node.js 22+（仅用来构建前端）、模型提供者凭据。

```bash
python3.15 -m pip install -e ".[dev]"
export SOCRATOPIA_ROOT="$(pwd)"
export SOCRATOPIA_API_TOKEN="your-random-local-token-of-at-least-16-characters"
export OPENAI_API_KEY="your-server-side-credential"
python3.15 -m uvicorn platform_api.app:app --host 127.0.0.1 --port 8000

# 第二个终端：仅用于前端开发
cd web
npm install --ignore-scripts
npm run dev
```

默认禁止向外网暴露本地令牌服务。开发环境前端代理 FastAPI；浏览器不保存凭据到 localStorage。模型凭据保留在服务器环境。

## 可执行包
见 [原生 ZIP / Alpha 验证范围](docs/WEB_V5_PACKAGE.md) 和 [AgentScope-only 迁移说明](docs/AGENTSCOPE_ONLY.md)。GitHub Actions 的四平台 ZIP 须完全通过打包与解压冒烟后才能用于测试；**Alpha 不表示真实模型教学已验收**。

## 业务边界
回答引文通过逐字核对 **不等于** 科学真实性已验证；练习正确率不是权威掌握度。课程原始 `DATA/`、`TEXTBOOK/` 不包含在安装包中，更新前自行备份。

历史 v4.3.2 Git 标签与 Release 只作为兼容归档，不代表 v5 运行时的一部分。
