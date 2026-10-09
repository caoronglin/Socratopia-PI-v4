# Cross-Tutor Handoff

承接的权威载体是 `DATA/<course>/runtime/handoff.json`，不是完整 `SOCIAL.md`。

最小字段：

- `from_tutor / to_tutor / lesson_id`
- `carry[]`：knowledge point、status、evidence、recommended_angle
- `opening_anchor`
- `tone_note`：可选、简短、不得推断私人情绪

读写入口：`python scripts/handoff.py show --course X`、`python scripts/handoff.py validate --course X`；`set`/`clear` 需 `--apply`。`set` 必须带 `--lesson-id`、`--from-tutor`、`--to-tutor`、`--carry`（JSON 列表，含真实 evidence）；`--opening-anchor`、`--tone-note` 可选。空 carry 或同一导师没有承接，`set` 不会写入。无真实承接时保留全 null/空 carry，不为切换导师伪造历史。

## 持久切换边界

- `handoff.json` 只保存承接内容；`set`、`clear` 都不更新 `course_state.json.active_tutor`，`clear` 也不撤销导师选择。临时风格与持久切换的区分见 `persona.md`。
- 持久切换前核对绑定课程、合法 runtime、真实 lesson/断点和当前 `active_tutor`。已有 carry 须匹配该课程事实、来源导师与目标导师；缺失、非法、过期或不匹配时不据此假装已承接，改查真实记录/报告待修复。
- 有真实承接时先保存已发生的课堂事实，再通过上述 `set` 参数写入、`show/validate` 核验；不能仅凭退出码或 `validate` PASS 声称写入成功（缺失文件也会加载合法的无承接默认值）。同课同 lesson/导师/内容重试先查现有记录，不重复制造事实；不无条件覆盖未处理的其他承接。
- `course_runtime.py` 仅有 `status/validate/render/migrate`，无导师切换或 `active_tutor` setter。`handoff.py set` 成功只可报告“承接已保存”；要说“导师已持久切换”，还须通过获准的文件编辑实际保存 `active_tutor`（保留其他课程状态），核对值与课程并校验。无法完成该写入时明确持久切换未完成，不编造命令、自动用 migrate 替代或把临时表达当成功。
- 承接与 active_tutor 写入不是跨文件原子事务；部分失败分别报告已保存/未保存项，停止依赖完整切换的操作，不自动撤销真实课堂事实。没有 carry 的首次选择可只设置导师，不能声称跨导师承接已发生。
- 只有承接已实际处理并保存相关事实后，才按需 `python scripts/handoff.py clear --course X --apply`；不因读过记录或一条角色开场就清除。

下一位导师：先消化信息，再用自己的教学方法处理。不要逐条念记录，也不要假装不知道上一课发生了什么。

`SOCIAL.md` 只提供可选的叙事质感。只有用户明确查看群聊、摘要冲突或需要恢复特定互动语气时读取。
