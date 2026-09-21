# Ops & GC Contract

## 原则

先归档，后清理；学习事实不自动删除；可再生缓存才能自动清理。

## 分类

- **Protected**：PROGRESS、book、来源元数据、PREP、错误/复习证据、runtime 当前状态、导师配置、SPEC。
- **Archive-only**：旧 lesson summaries、已解决错题、旧 planning 记录、旧 coursebook 版本。
- **Regenerable**：明确的 `_tmp/`、`_cache/` 与可重新生成中间产物。
- **Confirm-first**：原始 PDF/扫描件、用户手工文件、未知大文件、旧课程目录。

## 重要修正

不要按“PROGRESS 超过 N 条就移动原记录”的方式破坏单一事实源。需要压缩时：

1. 保留 canonical PROGRESS；
2. 生成/更新摘要索引；
3. 如确需分卷，采用显式版本化和索引，不静默搬走课堂事实。

## doctor

健康检查必须只读；不得自动修改 PROGRESS、自动联网或清理文件。GC 失败不阻断课堂核心提交。
