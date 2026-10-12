# v5.0.0-alpha.5 — PREP 教案草稿 Web 编辑

## 交付边界

Alpha.5 完成从“章节创建”到“编辑草稿 → 显式保存 → 校验 → 返回课堂”的闭环。网页只允许编辑教案 Markdown 正文；YAML 元数据（schema、课程、lesson_id、章节、小节锚点、来源、book_hash 和 status）由服务端读取原始文件并逐字保留。即使修改了 TODO，保存也不会自动改成 ready、不会生成学习成绩、不会启动 45 分钟授课。

- `GET /api/courses/{course}/prep/{lesson_id}/document` — 返回正文、SHA-256 文件版本、是否可编辑、当前 PREP 结构校验警告；要求 Bearer Token，不缓存。
- `PUT /api/courses/{course}/prep/{lesson_id}/document` — 输入 body 与 expected_sha256，验证后仅修改 draft 正文，写入同目录临时文件并原子替换。
- 支持重新读取及未保存更改确认；本地文件被另一窗口更改时拒绝写入，避免沉默覆盖。页面保留用户未提交的改动并展示冲突信息。

## 保证

- 拒绝目标为软链接、硬链接及非普通文件的 PREP、软链接 PREP 目录；只支持已存在合法课程的 `lesson_XXX`。
- 只读 ready 和 legacy 教案；不通过前端直接“签发 ready”。
- 单次文本大小限制 256 KiB，拒绝空正文及 NUL；SHA-256 前提与文件独占锁共同防止本地多窗口覆盖。
- 对 `PROGRESS.md`、课程教材和计时逻辑无写入权限；不将 AI 生成式回复直接写成已验证学习证据。
- 目录下持久锁文件意味着上一次写入异常中断后可能需要人工检查；不得自动删除其他编辑器的锁。

## 验收要求

Python3.15：授权、CAS 冲突、拒绝 ready/legacy、软链接拒绝、数据完整性、锁文件保留/清理；旧版 Python3.11/3.13 与 Rust CLI 严格回归；Ant Design 6 CLI doctor/无 warning lint/TS Vite；Chromium PC/手机端“草稿编辑 → 保存 → 重读 → 仍为未 ready”；Windows/Linux/macOS Intel/ARM 原生冻结包解压启动及哈希验证。

## 未覆盖

完整结构化字段编辑器、人工审批 ready 的签名与审计、跨设备多用户权限、PDF/网页教材解析及真实在线模型服务商凭据管理仍属于后续 Alpha，不能视为本版本已完成。
