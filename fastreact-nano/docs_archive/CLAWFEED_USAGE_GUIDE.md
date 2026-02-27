# ClawFeed 使用指南 - FastReAct Nano vs OpenClaw

**Date**: 2025-02-27

---

## 🎯 核心区别

### FastReAct Nano: 自然语言交互
- ✅ **用法**: 用自然语言提问，Agent 自动选择技能
- ✅ **优势**: 直观、灵活、无需记忆命令

### OpenClaw: 命令/技能调用
- ⚠️ **用法**: 需要知道技能名称和调用方式
- ⚠️ **限制**: 需要了解具体技能和参数

---

## 📝 FastReAct Nano 使用方式

### 在前端页面提问（推荐）

**访问**: http://localhost:3000

### 触发 news_aggregator 技能的关键词

当查询包含以下关键词时，Agent 会自动选择 `news_aggregator` 技能：

**中文**:
- `新闻`
- `获取新闻`
- `最新消息`
- `聚合`
- `摘要`
- `HackerNews` / `hackernews`
- `RSS`

**英文**:
- `news`
- `latest news`
- `headlines`
- `digest`
- `aggregation`
- `hackernews`
- `rss`

---

## 💬 具体使用示例

### 示例 1: 获取 HackerNews 热门新闻

**前端输入**:
```
获取 HackerNews 最新的 3 条热门新闻并生成中文摘要
```

**Agent 处理流程**:
1. 识别关键词: `HackerNews` + `新闻` + `摘要`
2. 自动选择: `news_aggregator` 技能
3. 调用工具: `fetch_fetch` (MCP fetch 服务器)
4. 获取数据: HackerNews Firebase API
5. 生成摘要: 使用 LLM
6. 返回结果: 格式化的新闻摘要

---

### 示例 2: 获取科技新闻

**前端输入**:
```
今天有什么科技新闻？
```

或

```
给我看看最新的 AI 和机器学习新闻
```

**Agent 处理流程**:
1. 识别关键词: `科技新闻` / `AI` + `机器学习`
2. 自动选择: `news_aggregator` 技能
3. 可能的来源: TechCrunch RSS, HackerNews
4. 过滤关键词: AI, 机器学习
5. 返回结果: 相关新闻摘要

---

### 示例 3: 定制新闻摘要

**前端输入**:
```
获取 HackerNews 和 RSS 的科技新闻，生成每日摘要
```

**Agent 处理流程**:
1. 识别多个来源: `HackerNews` + `RSS`
2. 识别格式: `每日摘要`
3. 调用多个数据源
4. 去重和排序
5. 生成摘要日报

---

### 示例 4: 特定主题新闻

**前端输入**:
```
有什么关于创业公司的新闻吗？
```

或

```
获取最新的加密货币相关新闻
```

**Agent 处理流程**:
1. 识别主题: `创业公司` / `加密货币`
2. 搜索和过滤
3. 生成主题摘要

---

## 🔄 OpenClaw/ClawFeed 原始用法

### OpenClaw 的技能系统

OpenClaw 也有 59 个技能，但用法不同：

**可能的方式**（推测，需要确认）:

1. **命令式调用**:
   ```
   /news_aggregator --source hackernews --limit 5
   /news_aggregator --source rss --url https://techcrunch.com/feed/
   ```

2. **自然语言**（类似 FastReAct）:
   ```
   Get latest news from HackerNews
   ```

3. **配置文件/定时任务**:
   ```yaml
   # clawfeed config
   schedule:
     - time: "09:00"
       action: news_aggregator
       params:
         sources: [hackernews, rss]
         limit: 10
   ```

---

## 📊 功能对比

| 功能 | FastReAct Nano | OpenClaw/ClawFeed |
|------|----------------|-------------------|
| **数据源** | HackerNews, RSS (通过 fetch MCP) | Twitter, RSS, HackerNews, Reddit, GitHub |
| **交互方式** | 自然语言 | 命令/技能调用 |
| **技能选择** | 自动（关键词匹配） | 手动指定 |
| **定时任务** | 需要外部 cron | 内置调度 |
| **存储** | 无内置存储 | SQLite 存储 |
| **去重** | 手动 | 自动去重 |
| **多频率** | 手动 | 4h/daily/weekly/monthly |
| **前端** | Next.js 14 (实时) | Web Dashboard |

---

## 🚀 FastReAct Nano 完整测试流程

### Step 1: 打开前端
```
http://localhost:3000
```

### Step 2: 测试基础查询

**测试 1 - 简单查询**:
```
获取 HackerNews 最新新闻
```

**预期结果**:
- Agent 选择 `news_aggregator` 技能
- 调用 HackerNews API
- 返回 3-5 条热门新闻

---

**测试 2 - 带摘要**:
```
获取 HackerNews Top 5 并生成中文摘要
```

**预期结果**:
- 获取 5 条新闻
- 每条新闻生成 2-3 句话中文摘要
- 包含标题、链接、摘要

---

**测试 3 - 主题过滤**:
```
HackerNews 上有什么 AI 相关的新闻？
```

**预期结果**:
- 获取 HackerNews 新闻
- 过滤 AI 相关主题
- 返回相关新闻摘要

---

**测试 4 - 多来源**:
```
获取最新的科技新闻摘要
```

**预期结果**:
- 可能尝试多个来源（HackerNews, RSS）
- 生成综合摘要
- 按主题分组

---

## ⚙️ 技术细节

### FastReAct 的技能自动选择

**代码位置**: `src/fastreact/agent.py`

```python
def _select_skills_auto(self, query: str, top_k: int = 3) -> list[str]:
    """自动选择相关技能"""

    # 1. 提取关键词（中文 + 英文）
    keywords = self._extract_keywords(query)

    # 2. 为每个技能评分
    skill_scores = []
    for skill_name, skill in self._skills.items():
        score = self._score_skill_relevance(skill, keywords)
        if score > 0:
            skill_scores.append((skill_name, score))

    # 3. 返回 Top K
    skill_scores.sort(key=lambda x: x[1], reverse=True)
    return [name for name, _ in skill_scores[:top_k]]
```

**评分逻辑**:
- 技能名称匹配: +2.0 分
- 技能描述匹配: +1.0 分
- 标签匹配: +1.5 分

### news_aggregator 技能配置

**文件**: `skills/builtin/news_aggregator/SKILL.md`

```yaml
---
name: news_aggregator
description: AI-powered news aggregation and summarization
tags: [news, aggregation, summary, rss, hackernews]
mcp_servers: [fetch]
recommended_tools: [fetch_fetch]
---
```

**触发条件**:
- 查询包含 `news`, `新闻`, `hackernews`, `rss` 等关键词
- 匹配技能描述或标签

---

## 🎨 实际使用示例

### 场景 1: 每日新闻早餐

**输入**:
```
早报：今天有什么重要的科技新闻？
```

**输出示例**:
```
# 今日科技新闻早餐

## 🔥 热门新闻

### 1. Anthropic 发布新模型
Anthropic 今天发布了 Claude 4，性能提升 40%...
[Read more](https://...)

### 2. OpenAI 开源部分模型
OpenAI 宣布将开源其小型语言模型...
[Read more](https://...)

## 📊 来源统计
- HackerNews: 5 条
- TechCrunch: 3 条
```

---

### 场景 2: 特定领域追踪

**输入**:
```
有什么关于 Rust 编程语言的新进展？
```

**输出示例**:
```
# Rust 相关新闻

## 最新动态

### Rust 1.80 发布
带来了新的异步特性...
[Read more](https://...)

### AWS 增加 Rust 支持
AWS SDK 现在正式支持 Rust...
[Read more](https://...)
```

---

## 💡 最佳实践

### 1. 使用明确的查询

✅ **好的查询**:
```
获取 HackerNews Top 5 新闻并生成中文摘要
```

❌ **不好的查询**:
```
新闻
```

### 2. 指定数据源（可选）

✅ **指定来源**:
```
从 HackerNews 获取最新的 AI 新闻
```

✅ **不指定来源**（让 Agent 决定）:
```
获取最新的科技新闻摘要
```

### 3. 说明输出格式

✅ **明确格式**:
```
生成今日科技新闻摘要，包含标题、链接和一句话概括
```

---

## 🔧 故障排查

### 问题 1: Agent 没有选择 news_aggregator 技能

**原因**: 查询关键词不明确

**解决**:
```
# 使用明确的关键词
"获取 HackerNews 新闻"  ✅
"告诉我消息"            ❌
```

### 问题 2: 没有返回新闻

**原因**: MCP fetch 服务器可能未加载

**检查**:
```bash
# 检查 Gateway 日志
# 应该看到: [OK] MCP server 'fetch' registered
```

### 问题 3: 返回结果不完整

**原因**: 网络问题或 API 限制

**解决**:
- 减少请求的数量（3-5 条而不是 10 条）
- 检查网络连接
- 查看 Gateway 错误日志

---

## 📝 总结

### FastReAct Nano 的优势

1. **自然语言交互** - 无需记忆命令
2. **自动技能选择** - Agent 智能匹配
3. **实时通信** - WebSocket 双向通信
4. **多主题支持** - 57 个技能可用
5. **前后端分离** - 现代化架构

### 使用建议

- ✅ 使用明确的关键词（`新闻`, `HackerNews`, `摘要`）
- ✅ 说明数据源（可选）
- ✅ 指定输出格式（可选）
- ✅ 限制结果数量（3-10 条）

---

**维护者**: FastReAct Team
**最后更新**: 2025-02-27
