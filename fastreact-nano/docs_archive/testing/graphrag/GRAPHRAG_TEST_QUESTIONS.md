# GraphRAG MCP Server - 测试问题集合

**目的**: 提供多样化的测试问题，避免对话历史被单一主题（如"机器学习"）污染
**创建日期**: 2025-02-23
**适用场景**: FastReAct前端演示、GraphRAG MCP server测试

---

## GraphRAG Mock 数据概览

当前Mock数据包含以下实体类型：

| 类型 | 实体数量 | 示例 |
|------|---------|------|
| **概念 (Concept)** | 5个 | AI, Machine Learning, Deep Learning, NLP, Computer Vision |
| **算法/架构 (Algorithm)** | 5个 | Neural Networks, Transformers, CNN, RNN, Backpropagation |
| **模型 (Model)** | 2个 | GPT, BERT |
| **框架 (Framework)** | 3个 | TensorFlow, PyTorch, Keras |
| **应用领域 (Application)** | 5个 | Image Classification, Object Detection, Sentiment Analysis, etc. |
| **任务 (Task)** | 3个 | Machine Translation, Speech Recognition, etc. |
| **人物 (Person)** | 3个 | Alan Turing, John McCarthy, Marvin Minsky |
| **论文 (Paper)** | 1个 | "Attention Is All You Need" |

关系类型：
- `INCLUDES` (包含) - AI → ML
- `BUILT_ON` (建立在...之上) - ML → Neural Networks
- `USES` (使用) - Deep Learning → Backpropagation
- `APPLICATION_OF` (应用) - CNN → Image Classification
- `EVOLVED_FROM` (演化自) - Transformers → Neural Networks
- `CREATED_BY` (创建者) - AI → Alan Turing

---

## 分类测试问题

### 1. 概念查询 (Concept Search)

**目的**: 测试基本实体检索能力

| 问题 | 预期结果 | 工具调用 |
|------|---------|----------|
| "什么是人工智能？" | 返回AI实体的description | `search_graph("Artificial Intelligence")` |
| "深度学习是什么？" | 返回Deep Learning实体 | `search_graph("Deep Learning")` |
| "解释一下NLP" | 返回NLP实体 | `search_graph("NLP")` |
| "计算机视觉相关概念" | 返回Computer Vision实体 | `search_graph("Computer Vision")` |
| "神经网络是什么？" | 返回Neural Networks实体 | `search_graph("Neural Networks")` |
| "Transformer架构" | 返回Transformers实体 | `search_graph("Transformers")` |

---

### 2. 关系查询 (Relationship Query)

**目的**: 测试实体间关系检索

| 问题 | 预期结果 | 工具调用 |
|------|---------|----------|
| "AI和机器学习的关系？" | 返回AI → ML (INCLUDES关系) | `query_relationships("Artificial Intelligence")` |
| "深度学习建立在什么基础上？" | 返回DL → NN (BUILT_ON关系) | `get_entity("Deep Learning", depth=2)` |
| "CNN用于什么应用？" | 返回CNN → Image Classification | `query_relationships("CNN")` |
| "谁创造了AI？" | 返回AI → Alan Turing | `get_entity("Artificial Intelligence")` |
| "GPT和BERT有什么关系？" | 两者都基于Transformers | `vector_search("language models")` |

---

### 3. 多跳推理 (Multi-Hop Reasoning)

**目的**: 测试复杂推理能力（需要多次工具调用）

| 问题 | 预期结果 | 推理路径 |
|------|---------|----------|
| "深度学习和AI的关系是什么？" | AI → INCLUDES → ML → INCLUDES → DL | 1. 查AI → 2. 查ML → 3. 查DL |
| "Transformers如何应用在计算机视觉？" | Transformers → 应用 → ViT → CV | 1. 查Transformers → 2. 查应用 |
| "从神经网络到GPT的发展路径？" | NN → DL → Transformers → GPT | 1. 查NN → 2. 查DL → 3. 查Transformers → 4. 查GPT |
| "反向传播在训练中起什么作用？" | Training → Gradient Descent → Backprop | 1. 查Training → 2. 查Gradient Descent → 3. 查Backprop |

---

### 4. 向量语义搜索 (Vector Search)

**目的**: 测试语义相似度搜索

| 问题 | 预期结果 | 语义匹配 |
|------|---------|----------|
| "图像识别相关技术" | CNN, Computer Vision | image → CNN, recognition → detection |
| "自然语言理解" | NLP, BERT, Transformers | language → NLP, understanding → BERT |
| "训练神经网络的方法" | Backpropagation, Gradient Descent | training → Backprop, neural networks → NN |
| "开源深度学习框架" | TensorFlow, PyTorch, Keras | open source → 框架实体 |

---

### 5. 综合问题 (Complex Queries)

**目的**: 测试Agent整合多个工具的能力

| 问题 | 预期结果 | 所需工具 |
|------|---------|----------|
| "对比GPT和BERT的区别" | GPT (生成) vs BERT (理解) | `get_entity("GPT")` + `get_entity("BERT")` |
| "深度学习在计算机视觉中的应用" | CNN, Object Detection, Image Classification | `search_graph("Computer Vision")` + `query_relationships` |
| "从AI到GPT的完整发展史" | AI (1956) → ML → DL → Transformers → GPT (2018) | 多次 `get_entity` + `query_relationships` |
| "有哪些深度学习框架可以用来训练CNN？" | TensorFlow, PyTorch, Keras | `search_graph("CNN")` + `get_entity("TensorFlow")` |

---

### 6. 创建实体测试 (Create Entity)

**目的**: 测试实体创建功能

| 问题 | 预期操作 | 预期工具调用 |
|------|---------|--------------|
| "添加一个新概念：因果推理" | 创建新实体 | `create_entity(name="Causal Inference", type="concept", ...)` |
| "创建PyTorch和TensorFlow的关系" | 创建关系 | `create_entity(..., relationships=[{"target": "TensorFlow", "type": "competes_with"}])` |

---

## 按难度分级

### 初级 (Basic)

- "什么是深度学习？"
- "神经网络是什么？"
- "解释一下NLP"
- "CNN用于什么？"
- "TensorFlow是什么？"

### 中级 (Intermediate)

- "AI和机器学习的关系是什么？"
- "Transformers有哪些应用？"
- "对比GPT和BERT的区别"
- "深度学习建立在什么基础上？"
- "从神经网络到GPT的发展路径"

### 高级 (Advanced)

- "深度学习在计算机视觉中的完整应用链路"
- "从AI到现代大语言模型的演化历史"
- "Transformers架构如何改变了NLP领域？"
- "训练一个CNN模型需要哪些技术和工具？"
- "解释反向传播在神经网络训练中的作用"

---

## 按主题分类

### 主题A: 概念理解 (Concept Understanding)

推荐问题：
- "什么是深度学习？"
- "NLP的核心技术有哪些？"
- "计算机视觉和图像处理的区别"

### 主题B: 架构与算法 (Architectures & Algorithms)

推荐问题：
- "Transformer架构的核心思想是什么？"
- "CNN和RNN的区别是什么？"
- "反向传播算法如何工作？"

### 主题C: 框架与工具 (Frameworks & Tools)

推荐问题：
- "TensorFlow和PyTorch的优缺点对比"
- "选择深度学习框架需要考虑什么？"
- "Keras适合什么场景使用？"

### 主题D: 应用场景 (Applications)

推荐问题：
- "深度学习在自动驾驶中的应用"
- "NLP在搜索引擎中的实际应用"
- "计算机视觉如何用于医疗影像诊断？"

### 主题E: 历史与发展 (History & Evolution)

推荐问题：
- "AI领域的发展里程碑有哪些？"
- "从感知机到Transformers的演化"
- "GPT模型版本的演进历史"

---

## 演示脚本建议

### 场景1: 快速演示 (2分钟)

1. **概念查询**: "什么是深度学习？"
2. **关系查询**: "深度学习和AI的关系是什么？"
3. **应用**: "CNN用于什么？"

### 场景2: 功能完整演示 (5分钟)

1. **搜索**: "什么是Transformer架构？"
2. **关系**: "Transformer有哪些应用？"
3. **多跳**: "从AI到GPT的演化路径"
4. **对比**: "GPT和BERT的区别"
5. **创建**: "添加新实体：扩散模型"

### 场景3: 技术深度演示 (10分钟)

1. **综合查询**: "深度学习在计算机视觉中的完整技术栈"
2. **多跳推理**: "从神经网络理论到实际应用的完整链路"
3. **语义搜索**: "图像识别相关的所有技术"
4. **创建与关联**: "创建Stable Diffusion实体并关联到Transformers"
5. **复杂对比**: "TensorFlow vs PyTorch在生产环境中的选择"

---

## 预期Agent行为

### 正确行为示例

```
User: "深度学习和AI的关系是什么？"

Agent:
1. THINK: "我需要查询AI和深度学习的关系"
2. TOOL_CALL: get_entity("Artificial Intelligence", depth=2)
3. TOOL_RESULT: 返回AI实体，显示INCLUDES → Machine Learning
4. THINK: "AI包含ML，现在需要查看ML和DL的关系"
5. TOOL_CALL: get_entity("Machine Learning", depth=2)
6. TOOL_RESULT: 返回ML实体，显示INCLUDES → Deep Learning
7. SESSION_END: "人工智能包含机器学习，机器学习包含深度学习。
   深度学习是AI的一个子集，专注于使用多层神经网络学习。"
```

### 错误行为示例（需避免）

```
User: "深度学习和AI的关系是什么？"

Agent:
1. THINK: "我需要搜索..."
2. TOOL_CALL: search_graph("AI")
3. SESSION_END: "AI是人工智能的缩写" ← ❌ 不完整的回答
```

---

## 测试检查清单

### 功能测试

- [ ] `search_graph` 能找到所有实体
- [ ] `get_entity` 能返回完整的实体信息和关系
- [ ] `query_relationships` 能正确遍历关系图
- [ ] `vector_search` 能返回语义相似的结果
- [ ] `create_entity` 能创建新实体和关系

### 性能测试

- [ ] 单次查询响应时间 < 2秒
- [ ] 多跳推理（3跳）< 10秒
- [ ] 综合查询（5+工具调用）< 30秒

### 准确性测试

- [ ] 关系方向正确（AI → ML，而非 ML → AI）
- [ ] 关系权重合理（INCLUDES权重 > 应用关系）
- [ ] 实体描述完整（包含description + properties）
- [ ] 别名匹配正确（"AI" 能匹配 "Artificial Intelligence"）

---

## 附录: 完整实体列表

### 概念类
1. Artificial Intelligence (AI)
2. Machine Learning (ML)
3. Deep Learning (DL)
4. Natural Language Processing (NLP)
5. Computer Vision (CV)

### 算法/架构类
6. Neural Networks
7. Transformers
8. Convolutional Neural Networks (CNN)
9. Recurrent Neural Networks (RNN)
10. Backpropagation
11. Gradient Descent

### 模型类
12. GPT
13. BERT

### 框架类
14. TensorFlow
15. PyTorch
16. Keras

### 应用类
17. Image Classification
18. Object Detection
19. Sentiment Analysis
20. Machine Translation
21. Speech Recognition

### 任务类
22. Text Generation
23. Question Answering
24. Named Entity Recognition

### 人物类
25. Alan Turing
26. John McCarthy
27. Marvin Minsky

### 论文类
28. "Attention Is All You Need"

---

**文档版本**: 1.0
**最后更新**: 2025-02-23
**维护者**: FastReAct Team
