# 45 分钟课堂计时（按需）

一节**有效完成**的课至少 `2700 秒`。这是独立的时间门禁，不等于已经掌握教材。以 `scripts/lesson_timer.py` 和实际落盘 `runtime/lesson_timer.json` 为准；模型不能凭聊天轮数、估算或口头承诺补时。

- **开课**：先完成 `classroom.md` runtime/PREP 校验，再 `python scripts/lesson_timer.py start --course X --lesson-id lesson_001`；同一课重复 start 不重置计时。
- **进行中**：每次有真实教学交互就调用 `heartbeat --course X`；可通过 `status` 查看有效累计时间和剩余秒数。连续 **超过 5 分钟没有心跳**会自动暂停，空闲/后台/离线不计全额；Agent 不具备无需请求即可常驻执行的计时器。
- **休息**：`pause` 不累计休息时间；`resume` 从保存秒数继续。设备时钟回拨、超时或工具异常要如实说明，不代填时长。
- **下课**：先同步最后的心跳，再 `finish`。实际计时不到 2700 秒时返回 `finish_denied`（CLI 退出码 2），**不标记 completed**，继续教学或经用户要求 `interrupt` 并保存未完成记录。用户始终能主动结束，不得为了凑 45 分钟强留用户。
- **后续**：只有计时完成 + 当前 PREP/PROGRESS 的真实教学证据与章节质量门满足，才可进一步宣称课程/章节完成；计时器自己不改 `PROGRESS.md`。同章多会话时每个 Session 独立计时（旧完成记录归档），不借上一节时长充数。

Cherry Studio / Pi：命令通过当前 Agent 的文件/shell 工具执行，受宿主授权与脚本校验约束；不得声称 GUI 有实时时钟组件或后台提醒。检查失败不换工具绕过。
