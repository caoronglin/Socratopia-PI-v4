# v5 Web 产品与课堂互动 · 实施说明

**状态：功能增量 / Draft PR #19，不是完成版。**

## 技术栈和官方依据

- PC Web：React 19 + **原生 Ant Design 6**（Layout、Card、List、Form、Input、Checkbox、Radio、Select、Statistic、Alert、Collapse）。
- 窄屏/触屏：**Ant Design Mobile 5**（TabBar、Radio、Checkbox、Button）；同一路由和同一套课程 API，不建立与 PC 不一致的第二套后端。
- 图表：**AntV G2 5** 的 Chart Spec API（stacked interval）；React effect 创建与销毁实例，不使用外部图表 HTTP 请求；表格和统计显示真实后端数据。
- 官方 API：
  - https://g2.antv.vision/zh/manual/introduction/spec-api/
  - https://mobile.ant.design/zh/components/tab-bar/
  - https://mobile.ant.design/zh/components/checkbox/
  - https://ant.design/components/overview-cn/

## 当前已接入的课堂闭环

1. 课程使用者在 Web「教材」页选择本地 Markdown/TXT 或粘贴内容，后端只创建 TEXTBOOK/<course>/book.md，不覆盖已有教材。GET book 返回教材摘要和目录，点击标题可转到证据检索。PDF/网页导入尚未实现。
2. 在课堂页“录入已核对的课堂题目”输入题干、2–4 个选项、答案解析、人工确认的正确索引、8–500 字逐字教材原文和可选 lesson_id。
3. API 只接受原文确实存在于本课程教材的题目；存储教材 SHA-256，题目、标准答案与解析落到每门课程隔离的 SQLite 数据库。
4. GET 题库不泄漏正确选项和解析；学生在课堂页用 PC AntD 或移动 Ant Design Mobile 原生选择控件提交答案。
5. 后端以相同的不可变正确索引确定性判分；反馈返回正确答案、解析、出处；本题的正确与否不允许修改权威 PROGRESS/mastery。
6. SQLite attempts 记录每次真实新答题；同 request_id 原封重试不重复计入；使用同一 ID 更换内容返回 409；返回实际作答次数、正确数和按日期聚合的时间序列。
7. AntV G2 使用真实日期序列绘制每日正确/错误答题次数叠加图。空数据展示 Empty 而非虚构统计；正确率只是尝试级统计，不是正式掌握率。
8. 教材修改后旧题 source_current=false 并禁止新答案提交（不会自动把旧题判定为仍然权威）；需要重新审核录题。
9. 提交新答案时若课堂正在运行，会调用原 lesson_timer heartbeat；重复请求、缺课、不满足 PREP 或不足 2700 秒都不能虚构完成计时。

- 导入教材不会自动更新 PREP/readiness、课堂完成度、mastery。教材可用仅意味着可进行证据检索及出题，开课仍要过原始门禁。

## 测试门禁

- Py3.15 FastAPI integration：教材缺失/不存在引用、合法创建、未提交前答案保密、单选/多选、答对/答错、幂等重试、跨课、教材版本失效、参数边界、无权访问、无进度伪造、数据库符号链接拒绝。
- Node22 React + G2 + Ant Design Mobile：TypeScript strict compile + Vite production build。
- 遗留系统：scripts/check.py --strict、Rust CLI 与冻结包冒烟 CI 不回退。

## 后续稳定版阻断项

本次工作是可运行闭环的产品增量，尚未完成完整 Web 产品（PDF/网页导入、PREP 图形编辑、历史聊天、长期掌握状态报告、PWA 离线、模型配置、安全模型鉴权、多端真实浏览器/触屏自动化 E2E）。**构建通过不等于实际浏览器验收完成。**

题库目前由本地受信使用者人工维护；不赋予 AI 权限更改正确答案。若未来增加 AI 出题，模型输出必须通过独立可信审核和引用版本校验之后才能进入正式题库；未经审核的 AI 生成题不能自动成为可判分标准答案。
