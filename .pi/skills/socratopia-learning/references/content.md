# Content Workflow

权威模型见 `SYSTEM/SPEC/CONTENT_MODEL.md`。

## 资料进入

`raw/source → 来源登记 → 规范化 book.md → outline/manifest → PREP → 课堂 → PROGRESS/assessment`

原则：

- 原始资料保持不变；
- `book.md` 同一课程仅一个 active 版本；
- `SOURCES/` 只做补充、例证、纠偏、拓展或冲突证据；
- PREP 可重建，不代表已授课；
- 编目与自动备课不得写“已掌握”。

## 上传完成

1. 确定课程；
2. 判断主课本是否存在；
3. 有 active book 时运行 `python scripts/prepare_after_upload.py --course "<课程>"`：补讲候选 → runtime 迁移/投影 → 单课 doctor；缺主课本时先报告编目缺口，不让流水线生成正文。失败分别报告已完成写入、失败阶段和未执行阶段，不把部分成功当作完成；
4. 检查 `book.md`、`_outline.md`、manifest、当前 PREP 与来源元数据；
5. 生成补讲候选，不自动修改掌握状态。

不要在 Skill 中硬编码某个宿主或某台机器的绝对路径。

## 主课本替换

只有用户明确要求更换/重编 active 主课本时才执行。先归档旧版本和映射，重建受影响 PREP，保留 PROGRESS 不变，最后验证。清理旧版本需要再次符合副作用规则。
