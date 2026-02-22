# SKILL 使用指南

## 概述

FastReAct Nano 的 SKILL 系统通过**语义匹配**自动选择相关的 SKILL。系统会分析你的查询，匹配最相关的 SKILL。

## 工作原理

### 自动选择机制

SKILL 的自动选择基于以下因素（按权重排序）：

1. **SKILL 名称匹配** (权重: 10)
   - 如果查询中包含 SKILL 名称，直接命中

2. **描述关键词重叠** (权重: 2/词)
   - 查询词汇与 SKILL 描述的重叠度

3. **标签匹配** (权重: 2/标签)
   - 查询中包含 SKILL 的标签

### 中文支持

系统支持中文查询，使用 n-gram 分词（unigram, bigram, trigram）：
- "机器学习" → ["机", "器", "学", "习", "机器", "器学", "学习"]

## GraphRAG Workflow SKILL

### 何时使用

**适合的查询**：
- ✅ "查查机器学习"
- ✅ "搜索知识图谱中的 AI 实体"
- ✅ "Query deep learning concepts"
- ✅ "知识图谱里有什么"

**不适合的查询**：
- ❌ "写一个机器学习算法"（编程任务）
- ❌ "实现深度学习模型"（编程任务）
- ❌ "Python 神经网络库"（库查询）

### 为什么有时会误匹配？

GraphRAG SKILL 的描述中包含了"人工智能"、"机器学习"等词汇，因此：
- "机器学习算法实现" → 可能匹配（因为有"机器学习"）
- "写深度学习模型" → 可能匹配（因为有"深度学习"）

### 如何避免误匹配？

**方法 1: 明确你的意图**
- ❌ "机器学习算法"
- ✅ "查询机器学习算法"

**方法 2: 手动指定 SKILL**

如果自动选择不准确，你可以手动指定：

```python
# Python API
agent.run_event_stream(
    "机器学习算法实现",
    skills=["code_review", "python_best_practices"]  # 手动指定
)
```

```bash
# CLI
fastreact "机器学习算法实现" --skills code_review,python_best_practices
```

```javascript
// WebSocket
{
  "type": "query",
  "content": "机器学习算法实现",
  "skills": ["code_review", "python_best_practices"]
}
```

## 编写 SKILL 的最佳实践

### 1. 描述要明确

**好的描述**：
```yaml
description: Guide for using GraphRAG knowledge graph tools to search and query entities. Use for knowledge retrieval tasks like "search for X", "find Y". NOT for programming tasks.
```

**不好的描述**：
```yaml
description: AI and machine learning knowledge graph tool.
# 太宽泛，容易误匹配
```

### 2. Tags 要精准

**好的 tags**：
```yaml
tags: [graphrag, knowledge, search, query, retrieval, entity]
# 功能性关键词
```

**不好的 tags**：
```yaml
tags: [AI, ML, deep learning, neural network]
# 领域关键词，容易误匹配
```

### 3. 提供使用示例

在 SKILL.md 中添加：

```markdown
## When to Use

**Good queries**:
- "Search for AI entities"
- "查询知识图谱"

**Bad queries**:
- "Write ML code" (use code_review instead)
- "Implement algorithm" (programming task)
```

## 常见问题

### Q: 为什么我的查询没有命中期望的 SKILL？

**A**: 检查以下几点：
1. 查询是否包含 SKILL 相关的关键词？
2. SKILL 的描述和 tags 是否包含了这些关键词？
3. 尝试重新表述你的查询

### Q: 为什么我的查询命中了错误的 SKILL？

**A**: 这可能是关键词重叠导致的。解决方案：
1. 使用更具体的查询词汇
2. 手动指定 skills 参数
3. 联系 SKILL 作者改进描述

### Q: 可以禁用自动选择吗？

**A**: 可以。手动指定 `skills=[]` 来禁用：

```python
agent.run_event_stream(
    "my query",
    skills=[]  # 不自动选择 SKILL
)
```

## 总结

- ✅ **自动选择基于语义**，不是硬编码规则
- ✅ **描述和 tags 决定匹配精度**
- ✅ **可以手动覆盖**自动选择
- ✅ **SKILL 作者负责**编写清晰的描述

记住：**如果自动选择不准确，请手动指定 skills 或重新表述查询**。不要为了特定的 SKILL 修改框架代码。
