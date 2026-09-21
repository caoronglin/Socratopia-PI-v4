---
name: socratopia-self-improving
description: 导师自我改进：记录并复盘“怎么教”更有效（教学动作/表达/节奏/策略）。触发词：改进导师、导师复盘、self-improving。绝不记录学习者掌握度/知识点/考试/课程事实。
---

# Socratopia Tutor Self-Improving（单 skill 版）

只记导师自己怎么教得更好。学习者侧反思见 canonical learning `reflection.md`（两者不共享状态文件）。

## 记录什么
- 某教学动作/类比/追问路线奏效与否。
- 用户/学习者对导师表达、节奏、策略的纠正。
- 换讲法后理解证据的变化（只记策略是否更有效，不记成绩）。

## 绝不记录
- 学习者掌握度/知识点状态、考试结果/分数、课程事实、教材内容、跨课连接。
- 学习者私人情绪/经历（不编造）。

## 数据
- `DATA/SELF_IMPROVING/<tutor>.jsonl`（按导师，非按课程；唯一非 per-course 存储）。append-only JSONL：
  `{"ts","tutor","kind":"teaching_move|correction|pace|strategy","note","context?","outcome?"}`
- S1 写；只在有真实信号时追加。**不引入 heartbeat/cron**（无后台 worker）。

## 权威与详情
- 完整版：`.pi/skills/socratopia-tutor/references/self-improving.md`；边界：`SYSTEM/SPEC/TUTOR_CONTRACT.md`。
