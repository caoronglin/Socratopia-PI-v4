# Runtime Contract

旧版线性 `needs_catalog → needs_prepare → ...` 容易把多个独立条件混成一个状态。v4 使用“phase + readiness + blockers”。

## course_state.json

```json
{
  "schema_version": 1,
  "course": "<course>",
  "phase": "setup|ready|in_lesson|post_lesson",
  "lesson_id": "lesson_001",
  "readiness": {
    "catalog": "ok|missing|stale",
    "prep": "ok|missing|stale",
    "runtime": "ok|invalid",
    "reteach": "clear|pending"
  },
  "blockers": [],
  "updated_at": "ISO-8601"
}
```

`phase=ready` 仅表示会话状态，不意味着所有 readiness 都 ok；能否开新内容由 blockers 决定。

## tasks.json

任务状态：`pending / running / completed / failed / blocked / cancelled`。

- `running` 仅用于当前实际执行中的任务；
- durable queue 不等于后台 worker；
- task 需有 idempotency key、kind、course、lesson_id（若适用）、status、attempts、last_error(redacted)。

## handoff.json

结构化跨导师承接，避免从 SOCIAL 推断教学事实。示例见 `schemas/handoff.schema.json`。
