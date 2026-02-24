# GraphRAG Workflow SKILL - 触发问题集合

**目的**: 提供能够触发`graphrag_workflow` SKILL自动选择的测试问题
**SKILL路径**: `skills/builtin/graphrag_workflow/SKILL.md`
**创建日期**: 2025-02-23

---

## SKILL 触发机制说明

### SKILL 元数据

```yaml
name: graphrag_workflow
description: Guide for using GraphRAG knowledge graph tools to search and query entities and relationships. Use this SKILL for knowledge retrieval tasks like "search for X", "find entities about Y", "what is X". This SKILL is NOT for programming, implementation, or code writing tasks.
tags: [graphrag, knowledge, search, query, retrieval, entity, relationship, 知识图谱, 实体, 关系, 检索]
mcp_servers: [graphrag]
recommended_tools: [graphrag_search_graph, graphrag_get_entity, graphrag_query_relationships, graphrag_vector_search]
```

### 自动选择匹配逻辑

FastReAct使用**中文n-gram分词**匹配用户查询与SKILL的以下字段：
- `name` (SKILL名称)
- `description` (SKILL描述)
- `tags` (SKILL标签)

**匹配触发词**（从SKILL.md提取）：
- 知识图谱、GraphRAG、graphrag
- 搜索、查找、查询、query、search
- 实体、关系、entity、relationship
- 检索、retrieval、knowledge
- 向量搜索、语义检索、相似

---

## 高命中问题 (High Confidence)

这些问题是**最可能触发**graphrag_workflow SKILL的查询。

### 中文问题

| 问题 | 命中原因 | 推荐工具 |
|------|---------|----------|
| "搜索知识图谱中的人工智能" | 命中：搜索 + 知识图谱 | `graphrag_search_graph` |
| "查询知识图谱中的实体" | 命中：查询 + 知识图谱 + 实体 | `graphrag_search_graph` |
| "知识图谱里有什么内容？" | 命中：知识图谱 | `graphrag_search_graph` |
| "查找关于机器学习的实体" | 命中：查找 + 实体 | `graphrag_search_graph` |
| "GraphRAG知识图谱搜索" | 命中：GraphRAG + 知识图谱 + 搜索 | `graphrag_search_graph` |
| "使用GraphRAG查询深度学习" | 命中：GraphRAG + 查询 | `graphrag_search_graph` |
| "检索知识图谱中的NLP相关实体" | 命中：检索 + 知识图谱 + 实体 | `graphrag_search_graph` |
| "在知识图谱中搜索神经网络" | 命中：知识图谱 + 搜索 | `graphrag_search_graph` |

### 英文问题

| 问题 | 命中原因 | 推荐工具 |
|------|---------|----------|
| "Search the knowledge graph for AI" | 命中：Search + knowledge + graph | `graphrag_search_graph` |
| "Query entities in GraphRAG" | 命中：Query + entities + GraphRAG | `graphrag_search_graph` |
| "Find entities about machine learning" | 命中：Find + entities | `graphrag_search_graph` |
| "What's in the knowledge graph?" | 命中：knowledge + graph | `graphrag_search_graph` |
| "Search GraphRAG for neural networks" | 命中：Search + GraphRAG | `graphrag_search_graph` |
| "Knowledge graph entity retrieval" | 命中：Knowledge + graph + entity + retrieval | `graphrag_search_graph` |

---

## 中等命中问题 (Medium Confidence)

这些问题包含部分触发词，**可能触发**SKILL。

### 实体详情查询

| 问题 | 命中原因 | 推荐工具 |
|------|---------|----------|
| "告诉我关于人工智能的详细信息" | 命中：实体详情场景 | `graphrag_get_entity` |
| "什么是深度学习？" | 命中：实体详情场景 | `graphrag_get_entity` |
| "你知道哪些关于神经网络的信息？" | 命中：实体详情场景 | `graphrag_get_entity` |
| "告诉我实体entity_1的详情" | 命中：实体 + entity | `graphrag_get_entity` |
| "查询Transformers实体的详细信息" | 命中：查询 + 实体 | `graphrag_get_entity` |

### 关系查询

| 问题 | 命中原因 | 推荐工具 |
|------|---------|----------|
| "AI和机器学习的关系是什么？" | 命中：关系 | `graphrag_query_relationships` |
| "深度学习连接到哪些实体？" | 命中：连接 | `graphrag_query_relationships` |
| "神经网络与Transformers的关联" | 命中：与 + 关联 | `graphrag_query_relationships` |
| "查询GPT和其他实体的关系" | 命中：查询 + 关系 | `graphrag_query_relationships` |
| "Computer Vision与哪些实体相关？" | 命中：与 + 相关 | `graphrag_query_relationships` |

### 相似性查询

| 问题 | 命中原因 | 推荐工具 |
|------|---------|----------|
| "查找与深度学习相似的实体" | 命中：相似 + 实体 | `graphrag_vector_search` |
| "类似神经网络的概念有哪些？" | 命中：类似 | `graphrag_vector_search` |
| "查找相关的AI架构" | 命中：相关 | `graphrag_vector_search` |
| "向量搜索Transformers" | 命中：向量搜索 | `graphrag_vector_search` |
| "语义检索NLP相关概念" | 命中：语义检索 | `graphrag_vector_search` |

---

## 低命中问题 (Low Confidence)

这些问题**可能不触发**SKILL，或者依赖Agent的推理。

| 问题 | 命中原因 | 备注 |
|------|---------|------|
| "人工智能是什么？" | 只有实体查询场景，缺少"知识图谱/GraphRAG"关键词 | 可能触发通用SKILL |
| "解释深度学习" | 纯知识问答，缺少"搜索/查询"关键词 | 可能不触发 |
| "TensorFlow vs PyTorch" | 对比问题，缺少"关系/实体"关键词 | 可能不触发 |
| "神经网络的工作原理" | 知识解释，缺少"知识图谱"关键词 | 可能不触发 |
| "如何训练CNN模型？" | 方法论问题，编程相关 | 不应触发（SKILL明确说"NOT for programming"） |

---

## 按工具分类的触发问题

### search_graph 触发问题

**核心关键词**: 搜索、查找、查询、search、find、query、knowledge、graph、实体

| 问题类型 | 示例问题 |
|---------|---------|
| **知识图谱探索** | "搜索知识图谱"、"知识图谱有什么"、"What's in the knowledge graph?" |
| **实体发现** | "查找AI实体"、"Find entities about ML"、"搜索关于神经网络的实体" |
| **关键词检索** | "搜索包含'transformer'的实体"、"Query entities with 'CNN'" |

### get_entity 触发问题

**核心关键词**: 详情、详细信息、tell me about、what do you know、实体、entity

| 问题类型 | 示例问题 |
|---------|---------|
| **具体实体查询** | "告诉我关于AI的详情"、"Get details for entity_1"、"What's Deep Learning?" |
| **实体信息请求** | "你知道Transformers的哪些信息？"、"Tell me more about BERT entity" |

### query_relationships 触发问题

**核心关键词**: 关系、连接、关联、related、connect、relationship、与

| 问题类型 | 示例问题 |
|---------|---------|
| **两实体关系** | "AI和ML的关系"、"How are Transformers related to AI?" |
| **关系探索** | "神经网络连接到什么？"、"What connects to CNN?" |
| **关联查询** | "深度学习与哪些实体相关？"、"Show relationships for GPT" |

### vector_search 触发问题

**核心关键词**: 相似、类似、相关、向量搜索、语义检索、similar、related、semantic

| 问题类型 | 示例问题 |
|---------|---------|
| **相似性查询** | "查找与DL相似的实体"、"Find entities similar to CNN" |
| **语义搜索** | "向量搜索NLP相关概念"、"Semantic search for AI architectures" |
| **相关概念** | "类似神经网络的概念有哪些？"、"What's related to Transformers?" |

---

## 综合测试问题（推荐使用）

这些问题**最有可能**触发完整的GraphRAG workflow：

### 场景1: 知识图谱探索
```
中文： "搜索知识图谱中关于人工智能的内容"
英文： "Search the knowledge graph for artificial intelligence"

预期触发：
1. graphrag_workflow SKILL
2. graphrag_search_graph 工具
3. 可能后续调用 get_entity 获取详情
```

### 场景2: 实体详情查询
```
中文： "查询知识图谱中深度学习实体的详细信息"
英文： "Query details for Deep Learning entity in knowledge graph"

预期触发：
1. graphrag_workflow SKILL
2. graphrag_search_graph 搜索DL实体
3. graphrag_get_entity 获取完整信息
```

### 场景3: 关系探索
```
中文： "使用GraphRAG查询AI和神经网络的关系"
英文： "Use GraphRAG to query relationships between AI and Neural Networks"

预期触发：
1. graphrag_workflow SKILL
2. graphrag_search_graph 找到AI实体
3. graphrag_query_relationships 查询关系
```

### 场景4: 语义搜索
```
中文： "在知识图谱中向量搜索与深度学习相似的概念"
英文： "Vector search for concepts similar to Deep Learning in knowledge graph"

预期触发：
1. graphrag_workflow SKILL
2. graphrag_vector_search 语义搜索
3. graphrag_get_entity 获取相似实体详情
```

### 场景5: 综合分析
```
中文： "使用知识图谱工具分析Transformer架构的相关实体和关系"
英文： "Use knowledge graph tools to analyze entities and relationships related to Transformers"

预期触发：
1. graphrag_workflow SKILL
2. graphrag_search_graph 搜索Transformers
3. graphrag_get_entity 获取详情
4. graphrag_query_relationships 查询关系
5. graphrag_vector_search 搜索相关概念
```

---

## 验证SKILL是否触发

### 方法1: 检查Agent日志

在前端WebSocket日志中查找：

```json
{
  "type": "SKILL_LOADED",
  "skill_name": "graphrag_workflow"
}
```

### 方法2: 检查System Prompt

如果SKILL触发，system_prompt中应该包含：

```
## Active Skills
### graphrag_workflow
Guide for using GraphRAG knowledge graph tools...
```

### 方法3: 检查工具调用

如果SKILL成功触发并指导Agent，应该看到：

```
TOOL_CALL: graphrag_search_graph(query="...")
```

而不是：

```
TOOL_CALL: search_files(...)  // 错误的SKILL被触发
```

---

## 常见问题诊断

### 问题1: SKILL没有触发

**可能原因**：
1. 查询缺少触发关键词（知识图谱、GraphRAG、搜索、查询、实体、关系）
2. 问题被其他SKILL抢先匹配（如code_review、git_workflow）

**解决方案**：
- 在问题中明确包含"知识图谱"或"GraphRAG"关键词
- 使用"搜索"、"查询"、"查找"等动词
- 避免使用编程/代码相关词汇（会触发其他SKILL）

### 问题2: SKILL触发但工具未调用

**可能原因**：
1. Agent认为问题不需要工具调用
2. MCP server未正确配置

**解决方案**：
- 检查`~/.fastreact/config.json`中graphrag是否配置为`shared`模式
- 确认GraphRAG MCP server正在运行
- 在问题中明确表达查询意图

### 问题3: 错误的SKILL被触发

**可能原因**：
1. 问题包含编程/代码关键词（触发code_review SKILL）
2. 问题包含Git关键词（触发git_workflow SKILL）

**解决方案**：
- 避免使用"代码"、"编程"、"实现"、"开发"等词汇
- 明确表达"知识图谱查询"、"实体搜索"等意图

---

## 推荐测试顺序

### 基础测试（验证SKILL触发）

1. **搜索知识图谱中的AI实体**
   - 应触发：graphrag_workflow
   - 应调用：graphrag_search_graph

2. **查询知识图谱中深度学习的详细信息**
   - 应触发：graphrag_workflow
   - 应调用：graphrag_search_graph → graphrag_get_entity

3. **使用GraphRAG分析AI和ML的关系**
   - 应触发：graphrag_workflow
   - 应调用：graphrag_search_graph → graphrag_query_relationships

### 进阶测试（验证完整workflow）

4. **在知识图谱中向量搜索与神经网络相似的概念**
   - 应触发：graphrag_workflow
   - 应调用：graphrag_vector_search → graphrag_get_entity

5. **使用知识图谱工具分析Transformer的完整关系链**
   - 应触发：graphrag_workflow
   - 应调用：graphrag_search_graph → graphrag_get_entity → graphrag_query_relationships

---

## 测试检查清单

### 功能验证

- [ ] 输入"搜索知识图谱"能触发graphrag_workflow SKILL
- [ ] 输入"查询实体信息"能触发graphrag_workflow SKILL
- [ ] 输入"向量搜索"能触发graphrag_workflow SKILL
- [ ] SKILL触发后能看到对应的GraphRAG工具调用
- [ ] 不会触发code_review或其他不相关的SKILL

### 日志验证

- [ ] WebSocket日志中看到`SKILL_LOADED: graphrag_workflow`
- [ ] System prompt中包含GraphRAG workflow指导
- [ ] 工具调用使用的是`graphrag_*`前缀的工具

### 结果验证

- [ ] 返回的知识图谱信息准确
- [ ] 关系查询结果正确（AI → ML → DL）
- [ ] 向量搜索返回语义相关的实体
- [ ] 多工具调用能正确组合结果

---

## 附录: SKILL触发词完整列表

### 中文触发词

| 类别 | 触发词 |
|------|--------|
| **核心名词** | 知识图谱、GraphRAG、graphrag、实体、关系 |
| **搜索动作** | 搜索、查找、查询、检索 |
| **关系动作** | 连接、关联、与...相关、与...关系 |
| **相似性** | 相似、类似、相关、向量搜索、语义检索 |
| **信息获取** | 详情、详细信息、告诉我关于、你知道 |

### 英文触发词

| 类别 | 触发词 |
|------|--------|
| **Core Nouns** | knowledge, graph, GraphRAG, entity, relationship |
| **Search Actions** | search, find, query, retrieval, retrieve |
| **Relationship** | connect, related, relationship, how are X and Y related |
| **Similarity** | similar, like, related, vector search, semantic search |
| **Information** | tell me about, what do you know, details, get entity |

---

**文档版本**: 1.0
**最后更新**: 2025-02-23
**维护者**: FastReAct Team
