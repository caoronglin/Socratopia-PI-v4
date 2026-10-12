# v5.0.0-alpha.4 — HTML/Ant Design 全局学习流与导师提示词

状态：Alpha 功能候选；`main` 合并前需 CI 全绿。v4.3.2 stable 不变。

## 核心设计

- **一个课程范围**：更换课程或本地 Bearer Token 时立即清理聊天、证据、备课、教材编辑、课号和界面缓存；不将任何 token 写入 localStorage。新 token 必须经 `/api/courses` 校验连接成功才解锁课程选择/创建。
- **一个权威状态**：课程教材、PREP 教案目录、课堂 readiness、计时、学习小组和经过检验的聊天来自带鉴权的 API。React 不推断 mastery。
- **一个学习路径**：课程概览使用 Ant Design Steps 指示“教材→章节备课→正式课堂→练习与复盘”。Steps 只给导航，不代表真实学习成绩；每一跳有可操作按钮。
- **闭合跳转**：无教材提示可直达导入；教材导入后可进入备课；章节教案检查后带课号进入课堂（不自动开始）；点击教材章节立即触发当前课的证据检索。
- **移动/桌面原生统一**：共用服务状态与业务组件；桌面 Menu、移动端 Ant Design Mobile TabBar；不做第二套不一致的数据逻辑。
- **错误与加载**：跨课切换清空旧数据，忙碌期间禁止更换服务令牌或课程；请求后仅向当前课程写回结果；网络失败显示具体错误，不假报成功。

## Tutor prompt boundary

`platform_api/grounding.py` 仅生成有限的教材来源 JSON：问什么答什么、证据足够才说明机制/纠错、直讲时不反问，未知时 abstain。增加 `tests/test_platform_v5_prompt_contract.py` 约束来源数据不可作为指令、响应不额外携带未引证结论或学业状态。导师 `references/style.md` 固定短答、真实反馈以及 UI 学习路径/证据和评价互不替代。

## 必过门禁

Python 3.15 API + prompt contract + 完整 legacy Python 3.11/3.13/Rust 回归；React19/AntD 6 `npm run build`、官方 CLI doctor + **0-warning lint gate**；Chromium PC/移动端从新建课程 → 教材 → 章节 PREP → 课堂 → 练习 → 课程切换 → 新令牌重连；四平台 native ZIP 解包启动与 SHA-256 验证。

## 保留限制

Pi provider 的安全配置界面、完整 PREP 可视化编辑、PDF/网页教材解析和真实在线模型凭据 E2E 尚未完成。不将这些描述为已经交付。
