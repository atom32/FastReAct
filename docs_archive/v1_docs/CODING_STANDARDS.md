# FastReAct 编码规范补充

本文档补充了项目中的文档和测试代码管理规范，作为 [CLAUDE.md](CLAUDE.md) 的补充。

**更新时间**: 2026-02-07

---

## 核心原则

### REUSE Before CREATE
**在创建新文档或测试之前，先检查是否可以更新现有的。**

**理由**:
- 避免文档碎片化和重复
- 保持信息集中和一致性
- 降低维护成本

**实践**:
```bash
# 需要添加文档？先检查
grep -r "<topic>" *.md
cat DOCS_INDEX.md  # 查看相关文档

# 需要添加测试？先检查
ls tests/test_<feature>*.py
grep -r "<function>" tests/
```

---

## 文档管理规则

### 位置规则

**允许的位置**:
- 根目录 - 仅核心文档（20个以内）
- `docs_archive/` - 历史和过时文档

**禁止的位置**:
- `/docs` - **已废弃**，所有内容已归档到 `docs_archive/old_docs_*/`

### 文档创建流程

```
1. 需求: 我需要记录某个功能或问题
   ↓
2. 检查: 查看 DOCS_INDEX.md 寻找相关文档
   ↓
3. 决策:
   ├─ 找到相关文档 → 更新现有文档 ✅
   └─ 没有相关文档 → 继续下一步
   ↓
4. 评估:
   ├─ 临时/过程文档 → docs_archive/temp/ 或 docs_archive/sprints/
   ├─ 永久/用户文档 → 根目录，更新 DOCS_INDEX.md
   └─ 技术文档 → 根目录，更新 DOCS_INDEX.md
   ↓
5. 执行: 创建/更新文档
   ↓
6. 验证:
   - 无emoji
   - UTF-8编码
   - 链接有效
   - 更新 DOCS_INDEX.md
```

### 文档类型与位置

| 类型 | 位置 | 示例 |
|------|------|------|
| 用户指南 | 根目录 | INSTALLATION.md, CLI_TROUBLESHOOTING.md |
| 功能文档 | 根目录 | IEL.md, SESSION_RESUME.md |
| 开发规则 | 根目录 | CLAUDE.md, DEVELOPMENT_LOG.md |
| 项目概述 | 根目录 | README.md, DOCS_INDEX.md |
| Sprint总结 | docs_archive/sprints/ | SPRINT_5_SUMMARY.md |
| Bug修复记录 | docs_archive/bugfixes/ | BUGFIX_*.md |
| 临时分析 | docs_archive/temp/ | analysis_report.md |
| 过时文档 | docs_archive/old_docs_*/ | 原 /docs 目录内容 |

---

## 测试代码管理规则

### 位置规则

**允许的位置**:
- `tests/` - 所有测试代码（pytest风格）
- `examples/` - 示例和演示脚本
- `scripts/` - 开发工具脚本

**禁止的位置**:
- 根目录 - 不允许 `test_*.py` 或 `demo_*.py` 散落在根目录

### 测试创建流程

```
1. 需求: 我需要测试某个功能
   ↓
2. 检查: 查看 tests/ 寻找相关测试
   ↓
3. 决策:
   ├─ 找到相关测试 → 在现有文件中添加测试用例 ✅
   └─ 没有相关测试 → 继续下一步
   ↓
4. 评估:
   ├─ 单元测试 → tests/core/test_<module>.py
   ├─ 集成测试 → tests/test_<feature>_integration.py
   └─ 功能演示 → examples/demo_<feature>.py
   ↓
5. 执行: 创建测试/示例
   ↓
6. 验证:
   - 测试可运行
   - 有清晰文档
   - 遵循命名规范
```

### 测试类型与位置

| 类型 | 位置 | 命名格式 | 示例 |
|------|------|----------|------|
| 单元测试 | tests/core/ | `test_<module>.py` | test_engine.py |
| 集成测试 | tests/ | `test_<feature>_integration.py` | test_mcp_integration.py |
| 功能测试 | tests/ | `test_<feature>_<aspect>.py` | test_sandbox_presets.py |
| 示例脚本 | examples/ | `demo_<feature>.py` | demo_task_chaining.py |
| 工具脚本 | scripts/ | `<tool>.py` | quick_check.py |

---

## 文件命名规范

### 文档文件
```
<TOPIC>.md           # 用户文档或技术文档
FEATURE_<NAME>.md    # 功能文档 (大写，用下划线)
<NAME>_GUIDE.md      # 指南类文档
```

### 测试文件
```
test_<module>.py                    # 单元测试
test_<feature>_integration.py       # 集成测试
test_<feature>_<aspect>.py          # 功能测试
```

### 示例文件
```
demo_<feature>.py    # 功能演示
example_<topic>.py   # 使用示例
```

---

## 快速参考

### 常用命令

```bash
# 查找相关文档
grep -r "<keyword>" *.md
cat DOCS_INDEX.md

# 查找相关测试
grep -r "<keyword>" tests/
ls tests/test_*<keyword>*.py

# 查找相关示例
ls examples/demo_*<keyword>*.py

# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_<feature>.py

# 验证代码质量
python scripts/quick_check.py
```

### 检查清单

**创建文档前**:
- [ ] 检查 DOCS_INDEX.md
- [ ] 搜索类似主题
- [ ] 确认是否可更新现有文档
- [ ] 选择正确位置

**创建测试前**:
- [ ] 搜索 tests/ 目录
- [ ] 检查是否可扩展现有测试
- [ ] 选择正确位置和命名
- [ ] 确保测试可运行

---

## 违规后果

### 文档违规
- 根目录文档混乱
- 用户找不到信息
- 维护成本增加
- **解决**: 归档到 docs_archive/

### 测试违规
- 测试文件散落各处
- 难以找到和运行
- 重复测试相同功能
- **解决**: 移动到 tests/ 或 examples/

---

## 相关文档

- [CLAUDE.md](CLAUDE.md) - 开发规则（主文档）
- [DOCS_INDEX.md](DOCS_INDEX.md) - 文档导航
- [tests/README.md](tests/README.md) - 测试说明
- [examples/README.md](examples/README.md) - 示例说明

---

**最后更新**: 2026-02-07

---

## 架构规范

### 模块化原则 (Module Architecture Rule)

**核心原则**: 模块必须保持独立，不允许层级渗透

**层级关系**:
```
CLI 层
    ↓ (通过公开API)
Core 层
    ↓ (通过公开API)
Context/LLM 层
    ↓ (内部实现)
Private/Internal
```

**禁止行为**:
- ❌ 上层直接导入下层 `internal.py`
- ❌ 跨层访问私有属性 (`_private`)
- ❌ 跳过封装边界直接操作内部状态

**正确做法**:
- ✅ 使用公开API/方法
- ✅ 通过构造函数依赖注入
- ✅ 使用工厂方法创建对象

### 层级渗透自查

**检查命令**:
```bash
# 1. 检查导入internal模块
grep -r "from.*internal import" src/fastreact --include="*.py"

# 2. 检查跨模块访问私有属性
grep -r "\.context_monitor\.metrics\." src/fastreact

# 3. 检查直接访问_llm私有属性
grep -r "\._llm_driver\._" src/fastreact

# 4. 检查CLI直接访问core私有状态
grep -r "\._react_agent\._" src/fastreact/cli
```

**修复示例**:
```python
# BAD (层级渗透):
self.context_monitor.metrics.set_current(tokens)  # 直接访问内部

# GOOD (使用公开API):
self.context_monitor.set_current(tokens)  # 使用公开接口
```

### 边界完整性评分

| 模块边界 | 评分标准 |
|---------|---------|
| ⭐⭐⭐⭐⭐ | 完全隔离，无渗透 |
| ⭐⭐⭐⭐☆ | 少量渗透，已修复 |
| ⭐⭐⭐☆☆ | 有渗透，需修复 |
| ⭐⭐☆☆☆ | 严重渗透，重构 |

---

**最后更新**: 2026-02-07 (添加层级渗透检查方法)
