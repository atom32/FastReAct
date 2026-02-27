# FastReAct Nano - Scripts Directory

这个目录包含实用脚本和开发工具。

---

## 核心工具

### migrate_skills.py ⭐
**功能**: 从 openclaw 迁移技能到 FastReAct

**用法**:
```bash
python3 scripts/migrate_skills.py \
  --openclaw-dir /path/to/openclaw \
  --output-dir skills/builtin
```

**说明**:
- 自动转换 SKILL.md 格式
- 工具到 MCP 服务器映射

---

### verify_setup.py ⭐
**功能**: 验证环境配置

**检查项**:
- Python 版本
- 依赖安装
- 配置文件
- API key
- Agent 创建

**用法**:
```bash
python3 scripts/verify_setup.py
```

---

## 诊断工具

### diagnose_config.py
**功能**: 诊断配置文件和 API key 问题

**检查项**:
1. 配置文件位置和内容
2. 环境变量
3. Config.load() 加载
4. Credentials.load() 加载
5. Agent 创建内存追踪

**用法**:
```bash
python3 scripts/diagnose_config.py
```

---

### diagnose_skill_selection.py
**功能**: 诊断和分析技能选择过程

**功能**:
- 分析查询与技能匹配度
- 显示技能评分详情
- 调试自动选择问题

**用法**:
```bash
python3 scripts/diagnose_skill_selection.py "你的查询"
```

---

## 快速参考

| 任务 | 使用脚本 |
|------|----------|
| **迁移技能** | `migrate_skills.py` |
| **验证环境** | `verify_setup.py` |
| **诊断配置** | `diagnose_config.py` |
| **调试技能选择** | `diagnose_skill_selection.py` |

---

## 维护规则

**添加新脚本时**:
1. 确保脚本是完整实现，不是临时测试
2. 添加清晰的注释和文档字符串
3. 更新本 README.md

**删除脚本时**:
1. 确保功能已由其他脚本提供
2. 更新本 README.md
3. 确保没有其他依赖


## 维护规则

**添加新脚本时**:
1. 确保脚本是完整实现，不是临时测试
2. 添加清晰的注释和文档字符串
3. 更新本 README.md

**删除脚本时**:
1. 确保功能已由其他脚本提供
2. 更新本 README.md
3. 确保没有其他依赖

---

**最后更新**: 2025-02-27
**维护者**: FastReAct Team
