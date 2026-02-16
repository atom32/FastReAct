# Skills 智能选择系统设计

## 问题分析

**当前实现**: 用户手动指定 skills，全部注入
```python
# 问题：20 个 skills 全部注入
agent.run_event_stream(query, skills=[skill1, skill2, ...])
```

**目标**: 智能选择最相关的 skills

## 解决方案

### 方案 1: 关键词匹配（简单）
```python
# Skills 需要提供 keywords
skill = Skill(
    metadata=SkillMetadata(
        name="git_workflow",
        keywords=["git", "分支", "commit", "merge", "仓库"],
        description="Git 工作流管理"
    )
)

# 匹配算法
def select_skills(query: str, all_skills: list[Skill]) -> list[str]:
    selected = []
    query_lower = query.lower()

    for skill in all_skills:
        # 匹配 keywords
        for keyword in skill.metadata.keywords:
            if keyword in query_lower:
                selected.append(skill.name)
                break

    return selected
```

### 方案 2: 向量相似度（高级）
```python
# 使用 embedding 计算相似度
async def select_skills_embedding(
    query: str,
    all_skills: list[Skill],
    threshold: float = 0.7,
    max_skills: int = 3,
) -> list[str]:
    # 计算 query embedding
    query_vec = await embed(query)

    # 计算 skill 描述的 embedding
    skill_scores = []
    for skill in all_skills:
        desc_vec = await embed(skill.description)
        score = cosine_similarity(query_vec, desc_vec)
        skill_scores.append((skill.name, score))

    # 选择 top-k
    skill_scores.sort(key=lambda x: x[1], reverse=True)
    return [s for s, score in skill_scores[:max_skills] if score > threshold]
```

### 方案 3: LLM 辅助选择（最智能）
```python
# 让 LLM 选择 relevant skills
async def select_skills_llm(
    query: str,
    all_skills: list[Skill],
    llm: LLMProvider,
) -> list[str]:
    # 构建 skills 列表
    skill_list = "\n".join([
        f"- {s.name}: {s.description}"
        for s in all_skills
    ])

    # 让 LLM 选择
    prompt = f"""
Given the user query: "{query}"

Available skills:
{skill_list}

Select the most relevant skills for this task.
Return only skill names, separated by commas.
Return at most 3 skills.
"""

    response = await llm.chat([{"role": "user", "content": prompt}])
    selected = parse_skill_names(response.content)
    return selected
```

## 推荐方案

### 阶段 1: 关键词匹配（立即可用）
- 简单
- 快速
- 不消耗额外 API 调用

### 阶段 2: LLM 辅助选择（可选）
- 更智能
- 理解语义
- 需要一次额外 API 调用（但可以缓存）

## Skill 元数据要求

```python
@dataclass
class SkillMetadata:
    name: str
    description: str
    keywords: list[str] = field(default_factory=list)  # ← 新增
    tags: list[str] = field(default_factory=list)        # 已有
    categories: list[str] = field(default_factory=list) # ← 新增
```

## 实现优先级

P0: 关键词匹配
- 添加 keywords 字段到 SkillMetadata
- 实现 select_skills_by_keywords()

P1: LLM 辅助选择（可选）
- 实现 select_skills_by_llm()
- 添加开关控制是否使用
