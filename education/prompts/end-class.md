---
description: 结束当前课堂并提交核心学习状态
---
用户明确结束本次课堂。使用 socratopia-learning，按 `references/memory.md` 执行 Core → Derived → Review → Maintenance，并遵守「提交失败与重复调用」。

只提交当前课程本次真实课堂事实；核心写入失败时停止后续流程并报告，不把部分保存说成全部成功。核心保存后重建记忆投影、按需处理 handoff 与复习资产，再执行课程内 Stellar 导出；维护失败按 reference 登记待处理项，不撤销已保存事实。

没有待提交课堂时不新建 lesson。只入队的任务不要描述成后台正在执行；收尾简报保存结果、未完成项和下次入口，不编造掌握或完成状态。

结束前执行 `python scripts/lesson_timer.py finish --course "<课程>"` 并核对实际结果。不足 2700 秒不得标记 completed；用户明确提前离开时调用 interrupt 并保存未完成事实，不能强留用户。按 `references/lesson-timer.md` 处理暂停/超时，不凭聊天轮数估计课时。
