# Socratopia PI v4

面向 PI coding agent 的 Socratopia 提示词/课程状态架构重构版。

## 核心思想

```text
AGENTS.md          = always-on kernel
.pi/skills/        = on-demand workflows
SYSTEM/SPEC/       = canonical contracts
DATA/<course>/     = learning facts + runtime
TEXTBOOK/<course>/ = content + sources + PREP
scripts/           = deterministic validation/scaffolding
Tutor              = presentation layer only
```

## 安装到现有项目

1. 先备份现有项目。
2. 将本包内容合并到项目根目录。
3. 把旧根级 `CLAUDE.md`、`AGENT_SYSTEM_PROMPT.md` 移到归档，不要让它们与 `AGENTS.md` 同时承担等价规则。
4. 旧 `.claude/skills/` 可保留作历史，但 active Socratopia skills 使用 `.pi/skills/`。
5. 不要默认创建 `.pi/SYSTEM.md`；让 PI 保留自己的系统提示。
6. 运行：

```bash
python scripts/check.py --strict          # doctor + 全部测试（CI 同款）
python scripts/pi_arch_doctor.py --budget # 上下文 token 预算报告
```

## 省 token 工具

```bash
python scripts/context_pack.py --course "课程名" [--budget 3000]   # 只读：开课所需最小热上下文
```

## 新建课程骨架

```bash
python scripts/scaffold_course.py "课程名"
```

脚本只创建缺失文件，不覆盖已有课程数据。

## 推荐使用

- `/start-class [课程/lesson]`
- `/end-class`
- `/materials-ready [课程]`
- `/switch-course <课程>`
- `/health [课程]`

也可以直接自然语言触发对应 Skill。

## 45 分钟课堂（完成时长硬门禁）

正式课堂至少累计 **2700 秒**可核验活动时间；不足时不得标记完成。Pi/Cherry Agent 每轮教学互动使用 `scripts/lesson_timer.py heartbeat`，超 5 分钟无心跳自动暂停，休息用 pause/resume，不把后台空闲算成有效课时。可提前结束并标记 interrupted；课堂事实照实保存。见 [计时使用说明](docs/LESSON_TIMER.md)。

```bash
python scripts/lesson_timer.py start --course "课程名" --lesson-id lesson_001
python scripts/lesson_timer.py heartbeat --course "课程名"
python scripts/lesson_timer.py status --course "课程名"
python scripts/lesson_timer.py finish --course "课程名"  # 不足45分钟返回非零
```

## ZIP 安装包与校验

发布版本见 [GitHub Releases](https://github.com/caoronglin/Socratopia-PI-v4/releases)，可在本地运行 `python scripts/package_release.py` 重建 ZIP 和 SHA-256 文件。打包仅包含 `manifest.json` 明确列出的项目文件，**不包含 DATA/、TEXTBOOK/ 或用户密钥**。安装前备份当前项目，不覆盖个人课堂数据。

## 与 v3 的关键区别

- 不再用一个大型 `CLAUDE.md` 承担路由 + 工具 +教学 + 工程全部规则。
- 不把导师人格常驻到工程任务。
- 不把完整 SOCIAL 当跨导师承接事实源。
- 不把“整章完整覆盖”误写成“一次教学单元的最低容量”。
- runtime 从单一线性状态改为 `phase + readiness + blockers`。
- task queue 明确只是持久待办，不假设存在后台 worker。
- GC 不再按固定条数搬走 canonical PROGRESS。

详细迁移见 `MIGRATION_PI.md`。
