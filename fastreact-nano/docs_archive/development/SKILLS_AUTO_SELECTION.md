# Skills Auto-Selection Implementation

## Overview

FastReAct Nano implements intelligent skill selection with progressive disclosure, following Claude Code's approach to avoid loading 20+ skills into context simultaneously.

## Implementation Status

### Completed Features

#### 1. Auto-Selection Algorithm ✅

**Location**: `src/fastreact/agent.py:150-211`

**Algorithm**: Keyword-based matching with scoring

```python
def _select_skills_auto(self, query: str, max_skills: int = 3) -> list[str]:
    """
    Automatically select relevant skills based on query

    Scoring:
    - Name match: +10 points (high weight)
    - Tag match: +5 points (medium weight)
    - Description word overlap: +2 points per word (low weight)
    """
```

**Matching Rules**:
1. Extract words from query (tokenization)
2. Score each skill based on name, tags, description
3. Return top-k skills with score > 0
4. Limit to max_skills (default: 3)

**Examples**:
```
Query: "创建 git 分支"
  → Matches: git_workflow (name contains "git")

Query: "Review code quality"
  → Matches: code_review (tags: review, code, quality)

Query: "Batch rename files"
  → Matches: file_ops (description contains "files")

Query: "今天天气怎么样"
  → Matches: None (no relevant skills)
```

#### 2. Progressive Disclosure ✅

**Location**: `src/fastreact/agent.py:213-252`

**Implementation**: Only metadata in system prompt

```python
def _build_system_prompt_with_skills(self, skills: Optional[list[str]]) -> str:
    """
    Build system prompt with skills injected

    ONLY includes metadata (progressive disclosure):
    - Skill name
    - Skill description (from YAML)
    - Skill tags (from YAML)

    DOES NOT include:
    - Full SKILL.md content
    - Detailed instructions
    - Examples
    """
```

**Context Impact**:
- Base prompt: ~569 characters
- Per skill: ~230 characters (metadata only)
- 3 skills: ~1,259 characters total

**Comparison**:
- Old approach (load all skills): 20 skills × 2,000 chars = 40,000 chars
- New approach (metadata only): 3 skills × 230 chars = 690 chars
- **Savings**: 98% reduction in context usage

#### 3. On-Demand Loading ✅

**Location**: `src/fastreact/skills/loader.py:184-218`

**Feature**: Load full skill content only when needed

```python
def get_prompt(self, name: str) -> Optional[str]:
    """
    Get the full prompt for a skill

    Progressive disclosure:
    1. Load skill if not loaded
    2. Read SKILL.md
    3. Return parsed prompt (full content)
    """
```

**Usage Pattern**:
1. Selection phase: Use metadata only (name, description, tags)
2. Execution phase: Load full SKILL.md content when skill is actually used
3. Caching: Full content cached in `_loaded_prompts` for reuse

#### 4. User Override ✅

**Feature**: Manual skill selection always available

```python
# Auto-selection (default)
async for event in agent.run_event_stream("Review code"):
    # Skills auto-selected: [code_review]
    ...

# Manual selection (override)
async for event in agent.run_event_stream(
    "Review code",
    skills=["code_review", "security_audit"]  # Force specific skills
):
    ...
```

## Configuration

### Enable/Disable Auto-Selection

```python
# Enable (default)
agent.enable_auto_skill_selection(max_skills=3)

# Disable
agent.disable_auto_skill_selection()
```

### Adjust Selection Threshold

```python
# More aggressive (select more skills)
agent._max_auto_skills = 5

# More conservative (select fewer skills)
agent._max_auto_skills = 1
```

## Testing

**Test Script**: `test_auto_skills.py`

```bash
python3 test_auto_skills.py
```

**Expected Output**:
```
[Query] 帮我创建一个新的 git 分支
[选中的 Skills] git_workflow
[Prompt 长度] 796 字符

[Query] Review the code quality for bugs
[选中的 Skills] code_review
[Prompt 长度] 801 字符

[Query] What is the weather today
[选中的 Skills] (无)
[Prompt 长度] 569 字符
```

## Language Support

### Current: English-Centric

The keyword matching algorithm works best with English queries:
- English queries → English skills: ✅ Works well
- Chinese queries → English skills: ⚠️ Limited (only explicit keyword matches)

### Example: Chinese Query Behavior

```
Query: "审查代码质量"
  → Keywords: [审查, 代码, 质量]
  → code_review tags: [code, review, quality]
  → Match: None (no direct substring match)
```

### Future Improvements

**Option 1: Add Chinese Tags**
```yaml
---
name: code_review
description: Automated code review and quality analysis
tags: [code, review, quality, best-practices]
tags_zh: [代码, 审查, 质量, 最佳实践]  # Add Chinese tags
---
```

**Option 2: Embedding-Based Selection**
- Use sentence embeddings (multilingual)
- Calculate semantic similarity
- Language-agnostic matching

**Option 3: LLM-Assisted Selection**
- Let LLM choose relevant skills
- Single additional API call
- Can understand cross-language semantics

## Architecture Benefits

### 1. Context Efficiency
- Only load relevant skills
- Metadata-only during selection
- Full content on-demand

### 2. Performance
- Fast keyword matching (no API calls)
- Cached skill metadata
- Lazy loading of full content

### 3. Flexibility
- Auto-selection with fallback to manual
- Configurable selection limits
- Easy to add new selection algorithms

### 4. Scalability
- Supports 20+ skills without context bloat
- Progressive disclosure scales linearly
- Each skill adds ~230 chars (vs ~2,000 chars full)

## Usage Example

```python
from fastreact import Agent

# Initialize with auto-selection enabled
agent = Agent()
agent.enable_auto_skill_selection(max_skills=3)

# Query with auto-selection
async for event in agent.run_event_stream(
    "Review this Python code for security issues"
):
    if event.type == EventType.SESSION_START:
        print(f"Session: {event.session_id}")
    elif event.type == EventType.THINK:
        print(f"Thinking: {event.content}")
    elif event.type == EventType.SESSION_END:
        print(f"Answer: {event.content}")

# Auto-selected skills: [code_review]
# Context used: ~800 characters (vs ~40,000 with all skills)
```

## Design Decisions

### Why Keyword Matching?

**Pros**:
- Zero additional API calls
- Fast execution
- Deterministic results
- Easy to debug

**Cons**:
- Limited semantic understanding
- Language-dependent
- Requires good tags/descriptions

### Why Metadata Only?

**Rationale**:
- SKILL.md files can be 2,000+ characters
- Only name/description/tags needed for selection
- Full content rarely needed in system prompt
- LLM can infer usage from metadata

### Why Max 3 Skills?

**Balance**:
- 1 skill: Too narrow, might miss relevant capabilities
- 3 skills: Good coverage, reasonable context (~700 chars)
- 5+ skills: Diminishing returns, more context noise

## Future Enhancements

1. **Hybrid Selection**: Combine keyword + embedding matching
2. **Feedback Learning**: Track which skills were actually useful
3. **Dynamic Thresholds**: Adjust max_skills based on query complexity
4. **Skill Chains**: Load secondary skills based on first skill usage
5. **Multilingual Support**: Add language-agnostic matching

## Related Files

- `src/fastreact/agent.py` - Auto-selection implementation
- `src/fastreact/skills/loader.py` - Progressive disclosure
- `test_auto_skills.py` - Test script
- `SKILLS_SELECTION_DESIGN.md` - Original design doc
- `SKILLS_INTEGRATION_COMPLETE.md` - Integration status
