# 首次使用与引导初始化（按需）

用户说「初始化」「新建课程」「首次使用」时先检查现状，不猜当前课程。详细步骤见 `docs/ONBOARDING_AND_GROUP.md`。

1. 确认当前工作目录属于 Socratopia 仓库；缺课程名只问课程名。不要枚举其他课程的学习事实。
2. 优先 `python scripts/initialize.py plan --course X` **只读预览**，显示现存 runtime、教材/进度缺口；用户确认新建后运行 `apply --course X --tutor D/E/F [--members D E F]`。本地终端可运行 `python scripts/initialize.py wizard`，逐步选择并最终输入 `YES`。
3. `apply` 重入只补缺失文件；已有 PROGRESS、runtime 的当前导师、书本和小组设置不自动覆盖。状态损坏先报阻断，不替换为默认值。
4. 初始化后仍需用户提供合法教材，建立 `book.md` / `_outline.md`，按章生成并验证 PREP。**初始化完成不等于可开课、掌握或已计时**。
5. 需要小组时当前课配置导师 D/E/F（2–3 位），详见 tutor 的 `references/study-group.md`；不得把多个导师的讨论当作多个独立模型。
