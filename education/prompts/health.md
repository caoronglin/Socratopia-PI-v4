---
description: 只读检查 Socratopia 架构和当前课程健康状态
argument-hint: "[课程名，可省略]"
---
执行只读健康检查。课程参数：$@

使用 socratopia-learning，按 `references/course-binding.md` 确定本次范围，不改变当前课程指针。只读检查项目控制文件及目标课程 runtime、PREP、评估/队列状态，报告 blockers、缺失文件与未检查项。

`python scripts/course_runtime.py validate --course "<课程>"` 可辅助 runtime 校验，但须先确认原始文件存在；缺失时不能把默认投影当作有效状态。默认运行 `python scripts/pi_arch_doctor.py --course "<课程>"`，仅检查目标课程数据与项目控制层。省略 `--course` 会扫描所有课程，仅在用户明确要求全仓检查时运行；doctor PASS 不等于已具备开课条件，仍须报告 readiness/blockers。

不要自动修复、创建文件、重建投影或执行队列；不要写课堂进度。工具不可用或检查失败时如实报告，不宣称健康检查通过。
