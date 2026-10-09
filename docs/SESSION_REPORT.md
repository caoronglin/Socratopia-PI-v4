# 会话总结报告 · Socratopia-PI-v4

## 当前验证 · 架构与提示词协议优化

本轮保留 Kernel / 三个 Skills / 按需 References / 显式 Prompts，没有替换宿主系统提示或新增 active Skill。

- 执行层：doctor 支持 `--course`，共享控制层仍检查，课程树直接按作用域定位；顶层容器、课程根和跨课符号链接在内容读取前拒绝。资料流水线使用公共路径校验、单课 doctor，失败分别报告已完成写入与未执行阶段。
- 提示词：开课先 runtime/PREP gate，显式课号冲突不静默替换；下课分 Core / Derived / Review / Maintenance，派生失败不撤销课堂事实；临时风格、handoff、持久 active_tutor 不互相冒充。
- memos：pull 仅接收首行完整标记且课程完全相等的记录，支持内部空格课名，分类报告异课/无标记跳过数。
- 上下文：压缩重复措辞至既有 reference 预算内，没有提高阈值或弱化测试。
- **教研组分层**：A/B/C 移入 `moe/`，成为不面向学习者的内部审议机构，只在备课会与下课复盘出现；产出落 PREP 与 `SELF_IMPROVING`。
- **教学设计外部化**：教研会决议与预期误概念成为 `ready` 门禁；覆盖判到期望元素（未逐个取证就停在 `introduced`）；陷题按连续无进展轮数强制升级干预。

实际验证：

```bash
PYTHONDONTWRITEBYTECODE=1 python scripts/check.py --strict
# doctor PASS: 0 warning(s)；471 passed, 35 subtests passed（含 25 项消融）
PYTHONDONTWRITEBYTECODE=1 python scripts/pi_arch_doctor.py --budget
# PASS: 0 warning(s)；128000 窗口下 kernel+routing ≈2212，classroom references ≈6731
# 估算值，不是精确 tokenizer

git diff --check
# 返回 0
```

新增守卫经**注入移除**验证会真的失败（不是空跑）：移除教研会 gate、移除期望元素 gate、去掉成员层级标记、删掉深度计数，四种注入都导致对应测试变红。

未验证：真实 MinerU/memos 远程端到端、真实模型课堂行为。未上传资料、修改真实课程数据或 commit/push。MinerU 当前仅 `plan` / `remote`（API-only），下文旧的本地抽取记录已被该决定取代。

---

## 历史阶段记录

范围：从架构审查 → 修复真实缺陷 → 外部能力吸收 → 消融验证。
以下测试数量与 API 描述属于当时状态；当前结果以上方验证为准。
所有结论均附可复现命令；**未验证项单独列出**，不以「看起来没问题」代替证据。

```bash
python scripts/pi_arch_doctor.py              # PASS: 0 warning(s)
python -m unittest discover -s tests          # Ran 206 tests — OK
```

---

## 1. 起点：一次诚实的自审

先跑通项目自检（`doctor PASS` + 80 测试 OK），再逐文件读代码找问题。审查发现的每一条
都用**实际运行**验证，而不是靠阅读推断 —— 其中两条因此被推翻：

| 初判 | 实际运行结果 |
|---|---|
| 4 个 education 包名是编造的（`/api/v1/download?slug=` 全 404） | **错**。pack 走 `skillsets` registry（`skills_store_cli.py:3693`），4 个名字都真实 |
| `@ant-design/cli` 是脚手架 | **错**。它是离线组件知识查询工具，不生成项目 |

---

## 2. 修复的两处真实缺陷

### 2.1 脚手架伪造教学承接史（最严重）

**证据**：`scaffold_course.py "X"` 产出的 `runtime/handoff.json` 为

```json
{ "lesson_id": "lesson_001", "from_tutor": "TUTOR_A", "to_tutor": "TUTOR_B", "carry": [] }
```

ADR-006 明确该文件是跨导师承接的**权威载体**。于是每门新课程一开局就携带一条
「TUTOR_A 交给了 TUTOR_B，且已完成 lesson_001」的假记录，且 schema 合法。
直接撞 `AGENTS.md` §3 与 tutor SKILL 的「不伪造老师之间发生过的事」。

**修复**：

- `templates/handoff.json` → 三字段改 `null` + 空 `carry`（「尚未承接」）
- `SYSTEM/schemas/handoff.schema.json` → `oneOf` 表达「全 null」/「真实承接」两种合法形态
- 新增 `scripts/lib/handoff.py`：额外拒绝**部分填写**与**有承接人但 carry 为空**

**验证**：同一场景 doctor 改前 `PASS rc=0` → 改后 `FAIL rc=1` 并指出 `占位伪造`。

### 2.2 doctor 完全不校验 canonical state

`plan.md` §13 白纸黑字要求 ERROR 于 `canonical state missing/invalid`，实际只有
`course_runtime.py validate` 在查，而 `/health` prompt 只走 doctor —— **健康检查漏掉了
最严重的一类损坏**。

**验证**（同一份损坏文件）：

```
改前：doctor → PASS rc=0 ； course_runtime validate → rc=1（报 6 条错）
改后：doctor → FAIL rc=1（精确复现那 6 条）
```

**修复**：doctor 新增 `check_canonical_state()`（逐课程校验 `course_state`/`tasks`/`handoff`
并核对 `course` 与所在目录一致）、`check_manifest()`、`--root`（使负向测试可行）。
**这同时抓出了原有的 manifest 漂移**（`LICENSE`、`manifest.json` 未登记）。

---

## 3. 外部能力吸收：4 个专家包

### 3.1 为什么不执行安装器

`skillhub` CLI 实际不可用（shim 依赖的 `~/.skillhub/skills_store_cli.py` 不存在）。
静态审查 `install.sh`（548 行）后决定**不执行**：

- 下载 tarball 后 `tar -xzf` 并 `python3` 执行，**无 sha256/签名校验**
- 默认写 `~/.openclaw/workspace/skills/` —— **不是 Pi 的 skills 路径**
- 站点是 SPA，装之前无法审阅内容

**替代路径**：从 kit 的 `metadata.json` 读出 skillset 端点，直接下 4 个 zip 静态审查。
全程未执行任何第三方可执行文件。

### 3.2 落点（active skill 恒为 3）

| 包 | 落点 | 处理 |
|---|---|---|
| `education-quiz-generation` | 新建 `quiz-generation.md` | 难度分级 / 题型矩阵 / 考点标注 / 举一反三 |
| `education-lesson-planning` | 新建 `lesson-planning.md` | 教学评一致性 / 分层支架 / 单元先修 |
| `education-training-program` | 新建 `course-program.md` | 证据型里程碑 / 跨课连接边界 |
| `education-student-assessment` | **归并进** `assessment.md` | 错因分类 6 类 + Rubric 多维 |

第 4 个**没有**新建 `student-assessment.md` —— 那会与现有 `assessment.md` 形成第二套
规则源，违反 plan.md §10 的单一 owner。

**剔除的糟粕**（每个 reference 都有 `## 明确拒绝` 段 + 测试锁定）：

- 「你已安装以下 Skill」——**前提为假**，24 个 child skill 一个都没装
- **掌握度图谱** —— 直接撞 `ontology.schema.json` 的 mastery 禁令
- 自动批改 / 一键生成 / 确保覆盖全部必考点 —— 批量产物 ≠ 证据
- K12 / 新课标 2022 / 九大学科 / 考点作战地图
- 家长沟通 / 成绩单评语 / 学员档案 / 证书模板 / **营销文案**（外发）
- `Claude Code / Codex 导出` —— 宿主专属，违反 `ARCHITECTURE.md`

### 3.3 三位新导师

| ID | 角色 | 教学法 |
|---|---|---|
| `TUTOR_D` 三月七 | 元气追问型 | 把抽象概念拽进具体情境 |
| `TUTOR_E` 丹恒 | 克制诊断型 | 短问逼出隐藏前提与跳步 |
| `TUTOR_F` 姬子 | 领航统筹型 | 先校准目标与单元再落到可验证问题 |

用户指定的冲突处理：三月七设定里有「记性差、复述不了长句」，与「不复述即证据」的硬规则
相冲突。`TUTOR_D` 显式写明**只取元气追问一面，不取记性差一面**，并钉死「元气 ≠ 降低门槛」。

---

## 4. 新增能力

### 4.1 Stellar（Hexo 主题）导出 — 一门课 = 一个 notebook

读了 wiki 的 `front-matter`/`collection`/`notebook`/`behavior`/`cli`/标签三页。
用到的高级用法：Collection 文件路径即 profile、标签树 `/` 分层、`listing.priority`、
`render.math: katex`、`footer.share: false`、`{% tabs %}`、`npx hexo stellar doctor`。
**发现 Stellar `{% timeline %}` 原生支持 memos 数据源**，与 4.3 打通。

冒烟测试抓到两个真 bug（均已修 + 加回归）：

1. 数学式 `P(A|B)` 的管道符**劈开表格单元格**导致证据截断 → 改为按 markdown 规范
   只在**未转义**的 `|` 处切分
2. `next_entry`/`tutor`/`chapter` 读错了文件（实际在 PROGRESS 的 checkpoint 段）

### 4.2 memos（真实 API，非猜测）

契约取自 `usememos/memos` 的 `proto/api/v1/memo_service.proto`。

**双门控**：`push`/`pull` 需同时 `--authorize` **且** `SOCRATOPIA_EXTERNAL=1`。
实测最关键的一条：

```
env 有 token、无 flag → 拒绝     # capability_available != operation_authorized
```

**可见性只允许 `PRIVATE`**：`PROTECTED/PUBLIC/SPACE` 一律拒绝 —— memo 是课堂记录
派生，`PUBLIC` 等于公开学习者的掌握情况。token 只从 env 读、强制 https、
**无任何命令行 token 参数**、异常经 `redact()`。
`test_no_network_call_when_refused` 断言**拒绝发生在开 socket 之前**。

### 4.3 MinerU：本地优先是真的

本机已有 `pdftotext`/`pypdf`/`pymupdf`/`python-docx`/`bs4`，本地解析**实测可用**
（真实 PDF 提取出正文，pages 计数正确）。两条硬规则：

1. **本地失败绝不自动升级远程**（plan.md §8）。损坏 PDF 实测得到可执行错误信息并 `rc=1`
2. **「免登录」≠「无风险」**。MinerU 的免登录 Agent API 同样按 S3 门控（`remote` 需三重确认）

> **更正（后续会话）**：下面“故意拒绝执行”的理由是错的——官方文档明确不支持 multipart，契约是 JSON + 预签名 PUT。`remote` 现已接线，见 `references/mineru-ingest.md`。

`remote` 当时**故意拒绝执行**：真实上传是 multipart 契约，字段名须逐一核对，
本项目拒绝用未验证的格式发送用户教材。

### 4.5 提示词目录

`docs/PROMPTS.md`：四层提示词（Kernel / Skill / Prompt / Reference）的分层职责、
5 个 `/命令` 提示词逐字正文、16 条 learning 路由、6 位导师档案、常见流程的加载顺序、
以及写新提示词的 8 条规矩。

`tests/test_prompt_catalog.py`（17 项）保证该目录**不漂移**：提示词正文逐字比对、
路由表与 `socratopia-learning/SKILL.md` 完全相等、`description` 与 `argument-hint` 逐字记录。

写完后逐项核对，发现并修掉 3 处自身不准：prompt 正文被我重排换行（已改为逐字抄录）、
skill `description` 折行导致不可比对（已改单行）、导师目录漏了 `TUTOR_E`/`TUTOR_F`。
并用**注入漂移**的方式验证测试真的会红（改 fence 内正文 / 改 frontmatter / 改路由行）。

### 4.6 Cloudflare：已回退

用户决定不做。`build_interactive.py` / `test_interactive_build.py` /
`interactive-dashboard.md` 及全部路由、manifest、CHANGELOG 引用已清除。
残留的 “Cloudflare” 字样仅存在于 `SKILL_TRIAGE.md` 的**拒绝记录**（记录当初拒了
`publish_course.sh → Cloudflare Worker`），应当保留。

---

## 5. 消融测试（21 项）

问题不是「护栏在不在」，而是**拿掉之后有没有人发现**。没有检出的护栏是装饰品。

### 5.1 查出一处真实缺陷并修复

`SYSTEM/schemas/ontology.schema.json` 的 `propertyNames` 禁止字段集
**没有任何代码执行**，只有 `scripts/ontology.py:FORBIDDEN_PROPS` 在运行时生效。
把 schema 的 enum 清空，**整套测试依然全绿** —— schema 层禁令原本是纯装饰品。

**修复**：`test_schema_forbidden_props_match_code` 断言两者**完全相等**，此后任一侧
被改都会失败。

### 5.2 三个无效实验（修正后结论才成立）

| 我的错误 | 真相 |
|---|---|
| 移除路径包含性检查 → 无变化 | 它**只对 symlink 逃逸生效**；合法课程名被 `validate_course_name` 抢先拦截。补 symlink 夹具后确认有效 |
| 断言 doctor 报出的**文案** | 检测信号是**退出码**；改文案 ≠ 移除护栏 |
| 在测试进程内 `import` | 会解析回**原始仓库** —— 改的是副本、跑的是原件，实验无效。必须 subprocess |

### 5.3 方法论结论

- **消融必须有对应夹具**，否则是无效实验
- **多道门要分别消融**：doctor 门禁移除后测试套件仍失败 → 防线是**分层**的，
  单点失守不等于失守
- 完整 21 项表格见 `docs/SKILL_TRIAGE.md`

---

## 6. 过程中被自己的门禁抓到的错误

| 次数 | 内容 |
|---|---|
| 3 | manifest 漂移（新文件未登记 ×2；我的门禁误把 `DATA/` 当漂移 ×1）|
| 1 | f-string 与 JSX 花括号冲突（改为 token 替换）|
| 1 | 页数多计（`pdftotext` 尾部多一个 form feed）|
| 2 | 测试自身写错（跨课程断言用 `in` 对 list；共享 mock 列表未清空）|
| 1 | 消融夹具缺失（在测试进程内 import 解析回原件）|

均遵循同一流程：**先让测试红，再修，再绿**。

---

## 7. 最终状态

```
doctor            PASS (0 warning)
tests             223 OK  (会话开始 80, +143)
manifest          107 文件（doctor 强制交叉校验）
active skills     3（doctor 强制冻结）
references        17
tutor profiles    6
scripts           15（doctor REQUIRED 15）
test files        16
quarantine        15 个外部源
docs              DESIGN_DECISIONS / SESSION_REPORT / SKILL_TRIAGE
                  SOURCE_MAPPING / PROMPTS
```

按测试文件：runtime_core 27 · ontology 22 · ablation 21 · memo_sync 20 ·
mineru_ingest 20 · stellar_export 17 · prompt_catalog 17 · skillhub_education 14 · handoff 13 ·
doctor_gates 11 · local_search 11 · tutor_profiles 8 · external_research 7 ·
courseware 6 · reflection_split 6 · architecture 3

### 保持不变的边界

- `PROGRESS.md` 仍是**唯一**掌握事实源（grep 全量确认：无任何脚本写入它）
- `AGENTS.md` kernel 未增长
- active skill 恒为 3
- 外部内容只作数据；remote 逐次授权；token 只走 env 且脱敏
- 导出物（Stellar）一律 `derived:true / authoritative:false`

---

## 8. 未验证项（明确标注，不含糊）

| 项 | 状态 | 原因 |
|---|---|---|
| `memo_sync push/pull` 真实网络路径 | **仅 mock 覆盖** | 需用户 token + 实例地址；按 §6 不读取/打印凭据 |
| `mineru_ingest remote` 真实上传 | ~~故意未接线~~ → **已接线，仅模拟网络测试，未在真实服务验证** | 原理由（multipart）不成立 |
| Stellar 主题实际构建 | 未跑 `hexo generate` | 需真实 Hexo 站点；导出物已按 wiki 字段校验 |
| 消融覆盖范围 | 21 项，非穷尽 | 未覆盖每个 reference 的每条规则 |
| 提示词目录 | 已建 `docs/PROMPTS.md` + 17 项防漂移测试 | —— |

**下一步可做**：设好 `MEMOS_TOKEN` / `MEMOS_BASE_URL` 后跑一次 memos 真实端到端；
按 MinerU 文档核对 multipart 字段后接线 `remote`。

---

## 9. 变更清单

**新增 21 个文件**

```
scripts/lib/handoff.py                        96    反伪造校验
scripts/export_stellar.py                    307    Stellar 导出
scripts/memo_sync.py                         268    memos 同步
scripts/mineru_ingest.py                     364    本地优先摄入
tests/test_handoff.py                       160
tests/test_doctor_gates.py                  163
tests/test_skillhub_education.py            143
tests/test_tutor_profiles.py                 78
tests/test_stellar_export.py                202
tests/test_memo_sync.py                     271
tests/test_mineru_ingest.py                 244
tests/test_ablation.py                      360
tests/test_prompt_catalog.py                 防漂移断言
references/{quiz-generation,lesson-planning,course-program,
            stellar-export,memo-sync,mineru-ingest}.md
profiles/TUTOR_{D,E,F}.md
```

**修改 10 个文件**：`pi_arch_doctor.py`、`templates/handoff.json`、
`handoff.schema.json`、`assessment.md`、`SKILL.md`、`test_ontology.py`、
`test_doctor_gates.py`、`docs/SKILL_TRIAGE.md`、`manifest.json`、`plan.md`（+`CHANGELOG.md`）
