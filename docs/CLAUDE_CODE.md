# Claude Code 适配

本分支 `claude-code` 在不复制任何规则的前提下，让仓库同时被 Pi 与 Claude Code 使用。

## 核心事实（来自官方文档）

Claude Code 会**直接读取仓库的 `AGENTS.md`**，替代 `CLAUDE.md`
（[memory#agents-md](https://code.claude.com/docs/en/memory#agents-md)）。

因此本项目**不需要也不应该**创建根 `CLAUDE.md`：那会形成第二份常驻规则，与 ADR-001
冲突，且 `pi_arch_doctor.py` 会对根 `CLAUDE.md` 报 `avoid active duplicate/override`。

## 目录映射

| 层 | 权威位置（Pi） | Claude Code 入口 | 说明 |
|---|---|---|---|
| Kernel | `AGENTS.md` | 同文件，**无需映射** | 原生读取 |
| Skill | `.pi/skills/*/SKILL.md` | `.claude/skills/*/SKILL.md` | 薄指针 |
| Prompt | `.pi/prompts/*.md` | `.claude/commands/*.md` | 薄指针 + `$ARGUMENTS` |
| Reference | `.pi/skills/*/references/*.md` | 由 `.pi` 入口按相对路径解析 | 不复制 |
| 权限 | — | `.claude/settings.json` | 本分支新增 |

## 唯一权威源原则

`.claude/` 下的三个 `SKILL.md` 和五个 `commands/*.md` **只写入口，不写规则**：

- frontmatter 的 `name` / `description` 必须与 `.pi/` **逐字一致**
- 正文指向 `.pi/...` 的权威文件并要求先读取它
- 自身长度受限（skill 入口 < 700 字符），防止退化成第二份正文

`tests/test_claude_portability.py`（14 项）守住以上约束，包括：入口与 `.pi/` 的集合
一致、`description` 逐字比对、指向目标真实存在、禁止 `$@` 残留、禁止根 `CLAUDE.md`
与宿主覆盖文件。

## 关键差异：参数占位符

| 宿主 | 占位符 |
|---|---|
| Pi `.pi/prompts` | `$@` |
| Claude Code `.claude/commands` | `$ARGUMENTS` |

`.claude/commands/` 用 `$ARGUMENTS`，测试断言不得出现 `$@`，且有
`argument-hint` 的命令必须实际使用 `$ARGUMENTS`。

## 权限设置

`.claude/settings.json` 只做**收敛**，不放宽任何既有安全边界：

- `deny`：读取 `.env` / `*.pem` / `id_rsa*` / `credentials*`；`git push`、`git reset --hard`、`git clean -f`、`rm -rf`
- `ask`：`git commit`；MinerU 远程解析；memos `push` / `pull`

这与 AGENTS.md §6 的既有要求一致（凭据不外读、远程操作须逐次授权、删除须显式许可），
属于把已有约束在 Claude Code 侧显式化，不是新增策略。

## 使用方式

在 Claude Code 中打开本仓库后：

```
/start-class            # 或 /start-class <课程名>
/health                 # 单课只读检查
/health <课程名>        # 指定课程
/materials-ready        # 资料编目
/switch-course <课程>   # 安全切课
/end-class              # 下课提交
```

skills 会以 `/socratopia-learning`、`/socratopia-tutor`、`/socratopia-engineering`
暴露，且 Claude 也可按 description 自动路由。

## 未验证边界

`.claude/` 适配层由 `tests/test_claude_portability.py` 静态守住（文件存在、指向有效、
description 一致、占位符正确、manifest 登记）。**未在真实 Claude Code 会话中端到端运行过**，
不宣称模型实际行为已被验证。

## 合并回 main 的注意事项

`.claude/` 是宿主适配层，`.pi/` 仍是唯一权威源。若两份控制面同时维护，应始终以
`.pi/` 为准并重跑：

```bash
python scripts/check.py --strict
```

`pi_arch_doctor.py` 的 `STALE_RULES` 会在 `AGENTS.md`、`.pi/skills/*/SKILL.md`、
`SYSTEM/SPEC/*.md` 中检出 `.claude/` 字样并报 ERROR——这是刻意的：控制面文件不应
依赖具体宿主路径，宿主差异只允许存在于 `.claude/` 适配层本身。