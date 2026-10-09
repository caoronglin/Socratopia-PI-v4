# 45 分钟有效课堂计时

一节正式课堂**最少 45 分钟（2700 秒）**。只能在累积的课堂活动心跳达到最低时长后通过 `finish`。未达到可以继续，也可以提前退出并保存为 **interrupted（未完成）**；不强制用户久坐或无法退出。

## 为什么不用一次开始与 45 分钟后结束来判断

Cherry Studio / Pi Agent 不是持续运行的后台计时服务。仅依据 `started_at` 与当前墙钟之差，会把失联、浏览器关闭或长期闲置误算成教学时间。因此计时通过显式 `heartbeat` 记录，每两次心跳最多计入 **5 分钟**；间隔超过 5 分钟自动暂停，需 `resume`。不应根据模型自行估计教学时长。

## 使用

```bash
# 先确认课程有已落盘的 runtime 和 ready PREP，且对应课堂 gate 已放行
python scripts/lesson_timer.py start --course '遗传学' --lesson-id lesson_001

# 每轮真实教学交互结束或开始时发送心跳
python scripts/lesson_timer.py heartbeat --course '遗传学'
python scripts/lesson_timer.py status --course '遗传学'

# 休息不计时；再次开始须恢复
python scripts/lesson_timer.py pause --course '遗传学'
python scripts/lesson_timer.py resume --course '遗传学'

# 45 分钟未达到时拒绝完成（返回码 2）
python scripts/lesson_timer.py finish --course '遗传学'

# 允许提前退出，保存真实累计时间，不记作已完成
python scripts/lesson_timer.py interrupt --course '遗传学'
```

## 审计与安全

- 持久化在 `DATA/<course>/runtime/lesson_timer.json`，包含课号、session ID、章节、UTC 时间、累计秒数和状态；归档 `lesson_timer_records/<session_id>.json`，不同课程隔离。
- `start` 检查课程 runtime、无 blocker、ready PREP 与课号；重复 start 幂等。任意时间读取 `status` 不写入，不会单靠查看状态记满 45 分钟。
- `finish` 达标只表示**计时达标**；`PROGRESS.md` 的理解证据、章末综合和迁移仍有独立门槛，不能自动赋值掌握。
- 计时器不联网、不直接修改主课本/PROGRESS；归档仅当前课程。本地时钟异常不补算负时长。
- 自动暂停时需要显式 resume；对话工具失败不假装写盘；真正的 Cherry Agent 工具可用性及连续 45 分钟操作需要在客户端实测。
- **没有后台常驻线程、系统通知或无人值守完成**。若不希望连续学习，可按需要安排休息，休息时按 pause 排除时长。

## 发布和安装

预发行版本：`release/VERSION`；GitHub Release 提供 ZIP 与 SHA-256。运行 `python scripts/package_release.py` 可在本地重建同内容压缩包（文件来自 `manifest.json`，排除私人 `DATA/`、`TEXTBOOK/`）。

下载安装后，先备份原有项目；只把 ZIP 内文件合并到项目根目录，**不要清空真实课程文件**。运行 `python scripts/check.py --strict`，再测试计时命令。单课历史记录必须留在项目本地，压缩包不包含它们。
