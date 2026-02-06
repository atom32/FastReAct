# 归档文档索引

本目录包含已归档的历史文档，仅供参考。

---

## 目录结构

### bugfixes/
各类Bug修复记录文档

**已归档文件**:
- BUGFIX_BUILTIN_TOOLS.md
- BUGFIX_GRAPGAGENT.md (多个版本)
- BUGFIX_HOTFINISH.md (多个版本)
- BUGFIX_HOTFIX.md
- BUGFIX_IS_ASYNC_DETECTION.md
- BUGFIX_TOOL_SCHEMAS.md
- BUGFIX_TOOLNODE_EXECUTE.md

**归档时间**: 2026-02-07
**归档原因**: Bug已修复，文档仅作为历史记录

---

### sprints/
Sprint开发总结文档

**已归档文件**:
- RELEASE_v1.0.0.md
- REPL_SPRINT1_SUMMARY.md
- REPL_SPRINT2_SUMMARY.md
- REPL_ENHANCEMENT_PLAN.md
- PROJECT_STATUS.md
- SPRINT_4_SUMMARY.md
- SPRINT_5_SUMMARY.md (多个版本)
- SPRINT3_FINAL_REPORT.md
- SPRING3_INTERACTIVITY_REFACTOR.md
- SESSION_FIX_VERIFICATION.md
- UNIFIED_REPL_REFACTOR.md

**归档时间**: 2026-02-07
**归档原因**: Sprint已完成，总结文档仅供参考

---

### temp/
临时分析报告和测试文件

**已归档文件**:
- analysis_report.md (代码分析报告)
- AUDIT_REPORT.md (审计报告)
- test_output.txt (测试输出)
- SUCCESS.txt (成功标记文件)
- code_audit.py (审计脚本)

**归档时间**: 2026-02-07
**归档原因**: 临时文件，已完成使命

---

## 访问建议

这些文档仅供参考，不建议作为当前开发依据。

**获取最新信息**，请查看根目录下的核心文档：
- [README.md](../README.md) - 项目概述
- [DOCS_INDEX.md](../DOCS_INDEX.md) - 文档导航
- [CLAUDE.md](../CLAUDE.md) - 开发规则

---

**归档策略**:
- Bug修复文档: 保留30天后删除
- Sprint总结: 永久保留作为历史记录
- 临时文件: 保留7天后删除

**最后更新**: 2026-02-07

---

## 更新记录 (2026-02-07)

### 新增归档
- **old_docs_2026-02_07/** - 原根目录 `/docs` 目录
  - 早期架构文档 (ARCHITECTURE*.md)
  - 项目规划文档 (PROJECT_VISION.md, PROJECT_COMPLETION_REPORT.md)
  - 技术对比文档 (architecture-comparison-moltbot.md, embedding-solutions.md)
  - 过时指南 (QUICKSTART*.md, USAGE_GUIDE.md)
  - 共 80 个 markdown 文件

**归档原因**: 
- 与根目录核心文档重复
- 内容过时，反映早期开发状态
- 根目录已有更新的文档替代

**如需访问**: 
```bash
cd docs_archive/old_docs_2026-02_07
```

