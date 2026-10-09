# Socratopia Pi v4.1.0-rc.1 · 45 分钟课堂计时

## 功能
- **正式课堂时长至少 45 分钟（2700 秒）**；不足时 `finish` 拒绝完成，不生成虚假完成状态。
- `start/status/heartbeat/pause/resume/finish/interrupt` 七种明确操作。
- 持久化于单课程 `DATA/<course>/runtime/lesson_timer.json`；多课程隔离，跨 Cherry/Pi 对话可恢复。
- 每轮教学交互由 Agent 显式发送一次心跳；超 5 分钟无心跳后自动暂停，防止离线/闲置时间凑时长。
- 提前退出始终允许，只记录 **interrupted**，不将短课冒充完整课。
- 启动前校验正式课堂 runtime 与 ready PREP；不自动修改 `PROGRESS.md` 的掌握事实。
- 发布 ZIP 按仓库清单构建，**不包括 DATA/、TEXTBOOK/、密钥与个人课堂文件**，同时附 SHA-256 校验文件。

## 安装
下载 ZIP，解压到 Socratopia 项目目录（建议先备份旧版），阅读 `README.md`、`docs/LESSON_TIMER.md`。初次使用：
```bash
python scripts/check.py --strict
python scripts/lesson_timer.py start --course "课程名" --lesson-id lesson_001
python scripts/lesson_timer.py heartbeat --course "课程名"
python scripts/lesson_timer.py status --course "课程名"
```
结束时调用 `finish`，时长不足会返回非零退出码。暂停时使用 `pause`，继续使用 `resume`；需要提前离开可用 `interrupt`，此时课堂不能标成完成。

> 这是正式发布前的预发行版。CI 能测试确定性的时间/状态门禁，真实 Cherry Studio Pi 自动心跳及连续 45 分钟体验仍需在客户端完成端到端验收。运行时没有后台计时服务，工具调用频率决定计时精度。
