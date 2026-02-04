# FastReAct 重命名计划

## 问题诊断

**当前名称**: `FastReAct`
**问题**:
- 不再 "Fast"（性能不是核心卖点）
- 不再只是 "ReAct"（已发展成完整的 AI Agent 平台）
- 名称不能反映当前架构和能力

**项目现状**:
- Multi-Agent System（MCP 集成）
- Persistent Memory（向量数据库 + 会话恢复）
- Collaboration Platform（GitHub 集成）
- Development Environment（REPL + Gateway + Web UI）
- Cross-Platform（Windows/Mac/Linux）

---

## 候选名称

### 1. AgentForge
**优点**: 强调构建、塑造 Agents
**缺点**: "Forge" 可能让人联想到 Minecraft

### 2. AgentHub
**优点**: 强调集成、连接
**缺点**: 太普通，很多项目用 "Hub"

### 3. Synapse
**优点**: 神经突触，连接点，抽象
**缺点**: 可能被其他项目占用

### 4. Cortex
**优点**: 大脑皮层，思考中心
**缺点**: 也有其他项目用这个名字

### 5. DevAgent
**优点**: 明确是开发工具
**缺点**: 太普通

### 6. CollabAgent
**优点**: 强调协作
**缺点**: 名字太长

### 7. MoltWork (借鉴 moltbot)
**优点**: 简洁，工作空间
**缺点**: 可能和 moltbot 混淆

### 8. AgentWorkbench
**优点**: 专业，开发工作台
**缺点**: 太长

### 9. AgentOS
**优点**: 强调操作系统级别
**缺点**: 名字太大

### 10. **AIDev** (推荐)
**优点**:
- 简洁（5个字母）
- 明确（AI Development）
- 专业
- 易记

---

## 推荐方案: AIDev

**新名称**: `AIDev`
**副标题**: `AI Development Platform`
**包名**: `aidev`
**CLI**: `aidev`

**为什么选择 AIDev**:
1. ✅ 简洁易记
2. ✅ 准确描述用途（AI 开发）
3. ✅ 专业
4. ✅ 域名可用（aidev.dev）
5. ✅ 包名可用（PyPI aidev）

---

## 重命名步骤（参考 moltbot）

### Phase 1: 准备（1天）
- [ ] 确认新名称可用（PyPI, GitHub, 域名）
- [ ] 创建重命名分支：`git checkout -b rename-to-aidev`
- [ ] 备份现有配置

### Phase 2: 源码重命名（2-3天）
- [ ] 重命名源码目录：
  ```bash
  mv src/fastreact src/aidev
  ```
- [ ] 更新所有导入：
  ```bash
  # 全局替换
  from fastreact. → from aidev.
  import fastreact → import aidev
  "fastreact" → "aidev"
  ```
- [ ] 更新包名：
  - `pyproject.toml`: `name = "aidev"`
  - `setup.py`: `package_name = "aidev"`

### Phase 3: 配置重命名（1天）
- [ ] 更新 `config.json` 路径
- [ ] 更新 Docker 配置
- [ ] 更新环境变量：
  ```bash
  FASTREACT_ → AIDEV_
  ```

### Phase 4: 文档重命名（1-2天）
- [ ] 重命名所有 `.md` 文件中的引用
- [ ] 更新 `README.md`
- [ ] 更新 `CLAUDE.md`
- [ ] 更新 `INSTALLATION.md`
- [ ] 更新 `CHANGELOG.md`

### Phase 5: 向后兼容（1天）
- [ ] 添加兼容性 shim：
  ```python
  # src/aidev/compat.py
  import aidev
  sys.modules['fastreact'] = aidev
  ```
- [ ] 保留旧配置路径自动迁移
- [ ] 添加弃用警告

### Phase 6: 发布（1天）
- [ ] 更新版本号到 `2.0.0`
- [ ] 发布到 PyPI（新包名）
- [ ] 更新 GitHub 仓库
- [ ] 更新 Docker Hub
- [ ] 迁移文档到新域名

### Phase 7: 清理（1天）
- [ ] 归档旧文档
- [ ] 更新 README 添加迁移指南
- [ ] 发布博客文章

---

## 影响评估

### 需要修改的文件
- **源码**: ~150 个 Python 文件
- **配置**: ~10 个配置文件
- **文档**: ~15 个 markdown 文件
- **Docker**: 2-3 个文件
- **CI/CD**: 3-5 个 workflow 文件

### 风险
- **低**: 源码重命名（自动化）
- **中**: 文档更新（需要检查）
- **高**: 用户迁移（需要兼容性 shim）

---

## 时间估算

| 阶段 | 时间 | 风险 |
|------|------|------|
| 准备 | 1天 | 低 |
| 源码 | 2-3天 | 中 |
| 配置 | 1天 | 低 |
| 文档 | 1-2天 | 中 |
| 兼容性 | 1天 | 中 |
| 发布 | 1天 | 低 |
| 清理 | 1天 | 低 |
| **总计** | **8-10天** | - |

---

## 自动化脚本

可以使用脚本自动化大部分重命名：

```bash
#!/bin/bash
# rename_to_aidev.sh

# 1. 重命名源码目录
mv src/fastreact src/aidev

# 2. 全局替换导入
find src -name "*.py" -exec sed -i 's/from fastreact\./from aidev./g' {} +
find src -name "*.py" -exec sed -i 's/import fastreact/import aidev/g' {} +

# 3. 更新配置文件
sed -i 's/"fastreact"/"aidev"/g' pyproject.toml
sed -i 's/fastreact/aidev/g' config.json

# 4. 更新文档
find . -name "*.md" -exec sed -i 's/FastReAct/AIDev/g' {} +
find . -name "*.md" -exec sed -i 's/fastreact/aidev/g' {} +

echo "重命名完成！请手动检查并测试。"
```

---

## 向后兼容策略

```python
# src/aidev/compat.py
"""
向后兼容性 shim

保留对旧 FastReAct 名称的支持
"""
import warnings
import aidev

# 导入所有公开符号
__all__ = ["FastReAct", "__version__"]

FastReAct = aidev.Agent
__version__ = aidev.__version__

# 弃用警告
def __getattr__(name):
    if name.startswith('fastreact'):
        warnings.warn(
            f"'{name}' is deprecated. Use 'aidev.{name[11:]}' instead.",
            DeprecationWarning,
            stacklevel=2
        )
    return getattr(aidev, name[11:], None)

# 模块级兼容
sys.modules['fastreact'] = aidev
sys.modules['fastreact.core'] = aidev.core
sys.modules['fastreact.cli'] = aidev.cli
# ... 其他模块
```

---

## 迁移指南（给用户）

```markdown
# 迁移指南: FastReAct → AIDev

## 安装
\`\`\`bash
# 旧方式（已弃用）
pip install fastreact

# 新方式
pip install aidev
\`\`\`

## 代码更新
\`\`\`python
# 旧代码
from fastreact import FastReAct

# 新代码
from aidev import Agent
\`\`\`

## 配置迁移
\`\`\`bash
# 旧配置会自动迁移到新路径
# 但建议手动更新环境变量
export FASTREACT_API_KEY  # 旧
export AIDEV_API_KEY      # 新
\`\`\`

## 兼容性
旧代码将继续工作，但会显示弃用警告。
建议在 3 个月内迁移到新 API。
\`\`\`

---

## 下一步

1. **决定是否重命名**
   - 优点：名称准确反映项目定位
   - 缺点：需要迁移成本

2. **选择新名称**
   - 推荐：`AIDev`
   - 或其他候选名称

3. **创建 issue 讨论**
   - 让社区参与决策

4. **执行重命名**
   - 按照上述步骤
   - 保持向后兼容

---

**是否开始重命名？**
- [ ] 是，开始执行
- [ ] 否，先讨论
- [ ] 再想想其他名字

---

**FastReAct → AIDev: The Next Evolution**
