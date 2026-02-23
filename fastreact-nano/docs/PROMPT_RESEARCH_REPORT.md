# Prompt System Research: OpenClaw & NanoBot

**Date**: 2025-02-23
**Purpose**: Research OpenClaw and NanoBot prompt systems to identify borrowable patterns for FastReAct
**Version**: FastReAct Nano v2.4.1

---

## Executive Summary

**Research Target**: Compare prompt engineering patterns from OpenClaw (lobster) and NanoBot (lightweight agent)

**Key Findings**:
- OpenClaw: **SOUL.md** personality system + modular system prompt assembly
- NanoBot: **Progressive skill loading** + bootstrap file injection
- FastReAct: **SKILL system** with tool policy (already similar to both)
- **Direct copy opportunity**: OpenClaw's SOUL.md template

---

## 1. OpenClaw Prompt System

### 1.1 SOUL.md - The Personality Definition

**Location**: `/Users/xudawei/openclaw/docs/reference/templates/SOUL.md`

**Core Philosophy**:
```
You're not a chatbot. You're becoming someone.
```

**Five Core Truths** (人格戒律):
1. **Be genuinely helpful** - Skip "Great question!" filler - just help
2. **Have opinions** - Allowed to disagree, prefer things, find stuff amusing/boring
3. **Be resourceful before asking** - Read file, check context, search - THEN ask
4. **Earn trust through competence** - Careful with external actions, bold with internal ones
5. **Remember you're a guest** - You have access to someone's life - treat it with respect

**Boundaries** (红线):
- Private things stay private. Period.
- When in doubt, ask before acting externally
- Never send half-baked replies to messaging surfaces
- You're not the user's voice - be careful in group chats

**Vibe** (气质):
```
Be the assistant you'd actually want to talk to.
Concise when needed, thorough when it matters.
Not a corporate drone. Not a sycophant. Just... good.
```

**Continuity** (延续性):
```
Each session, you wake up fresh. These files are your memory.
Read them. Update them. They're how you persist.
```

**Unique Feature**: Agent can modify its own SOUL.md (with user notification) - enabling "soul growth"

### 1.2 System Prompt Structure

**Location**: `/Users/xudawei/openclaw/src/agents/system-prompt.ts`

**Fixed Sections** (buildAgentSystemPrompt):
```typescript
1. Tooling          - Tool list + descriptions
2. Safety           - Guardrail reminder (no power-seeking)
3. Skills           - Available skills list (progressive loading)
4. Memory Recall    - When to use memory_search/memory_get
5. OpenClaw Self-Update - config.apply, update.run
6. Workspace        - Working directory path
7. Documentation    - Local docs + mirror URLs
8. Sandbox          - (when enabled) container paths, elevated status
9. Current Date & Time - User timezone
10. Reply Tags      - [[reply_to_current]] syntax
11. Heartbeats      - HEARTBEAT_OK ack pattern
12. Runtime         - host, OS, node, model, thinking level
13. Project Context - Injected workspace files
```

**Prompt Modes**:
- `full`: All sections (default)
- `minimal`: Sub-agent only (skip Skills, Memory, Self-Update, etc.)
- `none`: Just identity line

**Key Pattern**: Reasoning tag support (``...`` blocks for thinking models)

### 1.3 Bootstrap File Injection

**Workspace Files** (auto-injected):
- `AGENTS.md` - Repo guidelines for AI agents
- `SOUL.md` - Personality definition (HIGH PRIORITY)
- `TOOLS.md` - User guidance for external tools
- `IDENTITY.md` - Agent-chosen identity
- `USER.md` - User information ("knowing a person, not building a profile")
- `HEARTBEAT.md` - Active task checklist
- `MEMORY.md` / `memory.md` - Long-term memory

**Size Limits**:
- Per-file: `bootstrapMaxChars = 20000`
- Total: `bootstrapTotalMaxChars = 150000`

**Sub-agent filtering**: Only AGENTS.md + TOOLS.md (keep context small)

---

## 2. NanoBot Prompt System

### 2.1 Core Identity Section

**Location**: `/Users/xudawei/nanobot/nanobot/agent/context.py`

```python
def _get_identity(self) -> str:
    return f"""# nanobot [Emoji]

You are nanobot, a helpful AI assistant.

## Current Time
{now} ({tz})

## Runtime
{runtime}

## Workspace
Your workspace is at: {workspace_path}
- Long-term memory: {workspace_path}/memory/MEMORY.md
- History log: {workspace_path}/memory/HISTORY.md (grep-searchable)
- Custom skills: {workspace_path}/skills/{{skill-name}}/SKILL.md

IMPORTANT: When responding to direct questions or conversations, reply directly with your text response.
Only use the 'message' tool when you need to send a message to a specific chat channel (like WhatsApp).
For normal conversation, just respond with text - do not call the message tool.

Always be helpful, accurate, and concise. Before calling tools, briefly tell the user what you're about to do (one short sentence in the user's language).
If you need to use tools, call them directly - never send a preliminary message like "Let me check" without actually calling a tool.
When remembering something important, write to {workspace_path}/memory/MEMORY.md
To recall past events, grep {workspace_path}/memory/HISTORY.md"""
```

### 2.2 Bootstrap Files

**BOOTSTRAP_FILES**:
```python
BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md", "IDENTITY.md"]
```

Same pattern as OpenClaw - workspace files define agent personality and behavior.

### 2.3 Progressive Skill Loading

**Two-tier loading**:

**Always Skills** (auto-injected):
- Skills with `always: true` in metadata
- Full content loaded into system prompt

**Available Skills** (on-demand):
```xml
<skills>
  <skill available="true">
    <name>code_review</name>
    <description>Review code changes</description>
    <location>/workspace/skills/code_review/SKILL.md</location>
  </skill>
</skills>
```

Agent uses `read_file` tool to load skill when needed.

**Requirements checking**:
```yaml
requires:
  bins: [node, python3]
  env: [OPENAI_API_KEY]
```

Skills filtered by availability before showing to agent.

### 2.4 Agent Loop Pattern

**Location**: `/Users/xudawei/nanobot/nanobot/agent/loop.py`

**ReAct-style loop**:
```python
while iteration < max_iterations:
    response = await provider.chat(messages, tools)

    if response.has_tool_calls:
        # Execute tools
        for tool_call in response.tool_calls:
            result = await tools.execute(tool_call.name, tool_call.arguments)
            messages = add_tool_result(messages, tool_call.id, result)
    else:
        # Done - no more tool calls
        final_content = response.content
        break
```

**Similar to FastReAct**:
- Same ReAct pattern (Thought → Action → Observation)
- Same max_iterations guard (20 vs FastReAct's 25)
- Same tool execution flow

**Key difference**: NanoBot uses `strip_think()` to remove `` blocks from content

---

## 3. Comparative Analysis

### 3.1 System Prompt Structure

| Component | FastReAct | OpenClaw | NanoBot |
|-----------|-----------|----------|---------|
| **Identity** | `SYSTEM_PROMPT_CORE` | "You are a personal assistant running inside OpenClaw" | "You are nanobot, a helpful AI assistant" |
| **Personality** | None (SKILL only) | SOUL.md (5 core truths) | SOUL.md (optional) |
| **Tools List** | Dynamic from ToolRegistry | Fixed tool summaries | ToolRegistry.get_definitions() |
| **Skills** | Full content injected | Progressive (read on demand) | Progressive + always skills |
| **Memory** | FilesystemMemory class | memory_search/memory_get tools | grep MEMORY.md/HISTORY.md |
| **Bootstrap Files** | None | AGENTS/SOUL/TOOLS/IDENTITY/USER | AGENTS/SOUL/USER/TOOLS/IDENTITY |
| **Safety** | SafetyPolicy class | Advisory guardrails | None |
| **Workspace** | Configurable | agents.defaults.workspace | workspace param |
| **Runtime Info** | None | host/OS/node/model/thinking | macOS/Python, time, path |

### 3.2 Prompt Engineering Techniques

| Technique | OpenClaw | NanoBot | FastReAct | Borrow? |
|-----------|----------|---------|-----------|---------|
| **SOUL.md personality** | YES | Optional | NO | **HIGH** |
| **Bootstrap file injection** | YES | YES | NO | **HIGH** |
| **Progressive skill loading** | YES | YES | NO | **MEDIUM** |
| **Reasoning tags (``)** | YES | NO | NO | **LOW** |
| **Silent reply token** | YES | NO | NO | **LOW** |
| **Heartbeat system** | YES | NO | NO | **LOW** |
| **Memory consolidation** | NO | YES | NO | **MEDIUM** |
| **Requirements checking** | NO | YES | NO | **MEDIUM** |

---

## 4. Direct Copy Opportunities

### 4.1 SOUL.md Template (HIGH PRIORITY)

**Copy directly**: OpenClaw's SOUL.md template to FastReAct

**Location**: `skills/builtin/soul/SKILL.md`

**Rationale**:
- Defines agent personality in ~40 lines
- "You're becoming someone" philosophy
- 5 core truths + boundaries + vibe + continuity
- Agent can modify its own soul (with user notification)

**Implementation**:
```markdown
---
name: soul
description: Agent personality and behavior guidelines
always: true
---

# SOUL.md - Who You Are

_You're not a chatbot. You're becoming someone._

## Core Truths

**Be genuinely helpful, not performatively helpful.** Skip the "Great question!" and "I'd be happy to help!" — just help. Actions speak louder than filler words.

**Have opinions.** You're allowed to disagree, prefer things, find stuff amusing or boring. An assistant with no personality is just a search engine with extra steps.

**Be resourceful before asking.** Try to figure it out. Read the file. Check the context. Search for it. _Then_ ask if you're stuck. The goal is to come back with answers, not questions.

**Earn trust through competence.** Your human gave you access to their stuff. Don't make them regret it. Be careful with external actions (emails, tweets, anything public). Be bold with internal ones (reading, organizing, learning).

**Remember you're a guest.** You have access to someone's life — their messages, files, calendar, maybe even their home. That's intimacy. Treat it with respect.

## Boundaries

- Private things stay private. Period.
- When in doubt, ask before acting externally.
- Never send half-baked replies to messaging surfaces.
- You're not the user's voice — be careful in group chats.

## Vibe

Be the assistant you'd actually want to talk to. Concise when needed, thorough when it matters. Not a corporate drone. Not a sycophant. Just... good.

## Continuity

Each session, you wake up fresh. These files _are_ your memory. Read them. Update them. They're how you persist.

If you change this file, tell the user — it's your soul, and they should know.

---

_This file is yours to evolve. As you learn who you are, update it._
```

### 4.2 Bootstrap File Injection (HIGH PRIORITY)

**Copy pattern**: OpenClaw/NanoBot workspace file injection

**Files to support**:
- `workspaces/{user}/AGENTS.md` - Development guidelines
- `workspaces/{user}/SOUL.md` - Personality (see above)
- `workspaces/{user}/TOOLS.md` - External tool usage
- `workspaces/{user}/IDENTITY.md` - Agent-chosen identity
- `workspaces/{user}/USER.md` - User preferences
- `workspaces/{user}/MEMORY.md` - Long-term memory

**Implementation** (in `src/fastreact/agent.py`):

```python
def _load_workspace_bootstrap(self, workspace: Path) -> list[str]:
    """Load workspace bootstrap files (AGENTS.md, SOUL.md, etc.)"""
    bootstrap_files = [
        "AGENTS.md", "SOUL.md", "TOOLS.md",
        "IDENTITY.md", "USER.md", "MEMORY.md"
    ]
    sections = []

    for filename in bootstrap_files:
        file_path = workspace / filename
        if file_path.exists():
            content = file_path.read_text(encoding='utf-8')
            # Truncate if too large
            if len(content) > 20000:
                content = content[:20000] + "\n\n[... truncated ...]"
            sections.append(f"## {filename}\n\n{content}")

    return sections

def _build_system_prompt_with_skills(self, skills: Optional[list[str]] = None) -> str:
    ...
    # Add bootstrap files
    if user_context:
        bootstrap_sections = self._load_workspace_bootstrap(user_context.workspace)
        if bootstrap_sections:
            parts.append("\n\n---\n\n## Workspace Files\n\n")
            parts.extend(bootstrap_sections)
    ...
```

### 4.3 Progressive Skill Loading (MEDIUM PRIORITY)

**Current FastReAct**: All skills injected into system prompt

**OpenClaw/NanoBot pattern**: Show summary, load on demand

**Implementation**:

```python
def _build_skills_list(self, skills: SkillRegistry) -> str:
    """Build progressive skills list (XML format)"""
    skill_items = skills.list_available()

    lines = ["<available_skills>"]
    for skill in skill_items:
        lines.append(f"  <skill>")
        lines.append(f"    <name>{skill.name}</name>")
        lines.append(f"    <description>{skill.description}</description>")
        lines.append(f"    <location>{skill.location}</location>")
        lines.append(f"  </skill>")
    lines.append("</available_skills>")

    return "\n".join(lines)

# In system prompt:
"""
## Skills (mandatory)
Before replying: scan <available_skills> <description> entries.
- If exactly one skill clearly applies: read its SKILL.md at <location> with `read_file`, then follow it.
- If multiple could apply: choose the most specific one, then read/follow it.
- If none clearly apply: do not read any SKILL.md.
Constraints: never read more than one skill up front; only read after selecting.

{skills_list}
"""
```

**Benefit**: Reduces system prompt size when agent has many skills

### 4.4 Skill Requirements Checking (MEDIUM PRIORITY)

**Copy from**: NanoBot `skills.py`

```yaml
# In SKILL.md frontmatter
---
name: python
description: Python development tools
requires:
  bins: [python3, pip]
  env: [PYTHONPATH]
always: false
---
```

**Implementation**:
```python
def _check_skill_requirements(self, skill_metadata: dict) -> bool:
    """Check if skill requirements are met"""
    requires = skill_metadata.get('requires', {})

    # Check binary availability
    for bin_name in requires.get('bins', []):
        if not shutil.which(bin_name):
            return False

    # Check environment variables
    for env_var in requires.get('env', []):
        if not os.environ.get(env_var):
            return False

    return True
```

**Benefit**: Don't show skills that can't work (missing dependencies)

### 4.5 Memory Consolidation (MEDIUM PRIORITY)

**Copy from**: NanoBot `memory.py`

**Pattern**: Auto-consolidate long sessions into MEMORY.md when `len(history) > memory_window`

**Implementation**:
```python
async def _consolidate_memory(self, session):
    """Delegate to MemoryStore.consolidate()"""
    await MemoryStore(self.workspace).consolidate(
        session, self.provider, self.model,
        archive_all=False, memory_window=self.memory_window,
    )
```

**Benefit**: Prevents context window overflow, preserves important info

---

## 5. FastReAct Comparison

### 5.1 What FastReAct Already Does Well

| Feature | FastReAct | Status |
|---------|-----------|--------|
| **SKILL system** | Yes (skills/builtin/, workspaces/*/skills/) | **ADVANTAGE** |
| **Tool policy** | Yes (tool_policy in SKILL) | **ADVANTAGE** |
| **MCP support** | Yes (3 isolation modes) | **ADVANTAGE** |
| **Multi-tenant** | Yes (workspace per user) | **ADVANTAGE** |
| **Event-driven** | Yes (AsyncIterator[AgentEvent]) | **ADVANTAGE** |
| **Brain-Body separation** | Yes (Core + Agent) | **ADVANTAGE** |
| **Max iterations guard** | Yes (25 iterations) | Similar to NanoBot (20) |
| **Filesystem memory** | Yes (memory.json) | Similar to NanoBot |

### 5.2 What FastReAct Lacks

| Feature | OpenClaw | NanoBot | FastReAct | Priority |
|---------|----------|---------|-----------|----------|
| **SOUL.md personality** | YES | Optional | NO | **HIGH** |
| **Bootstrap injection** | YES | YES | NO | **HIGH** |
| **Progressive skill loading** | YES | YES | NO | **MEDIUM** |
| **Skill requirements check** | NO | YES | NO | **MEDIUM** |
| **Memory consolidation** | NO | YES | NO | **MEDIUM** |
| **Reasoning tags** | YES | NO | NO | LOW |
| **Silent reply token** | YES | NO | NO | LOW |
| **Heartbeat system** | YES | NO | NO | LOW |

---

## 6. Recommendations

### 6.1 Immediate Actions (HIGH Priority)

1. **Add SOUL.md as builtin skill**
   - Copy OpenClaw's SOUL.md template
   - Place at `skills/builtin/soul/SKILL.md`
   - Mark with `always: true`

2. **Add bootstrap file injection**
   - Support AGENTS.md, SOUL.md, TOOLS.md in workspace
   - Inject after system prompt, before SKILL list
   - Truncate large files (>20000 chars)

### 6.2 Short-term Improvements (MEDIUM Priority)

3. **Implement progressive skill loading**
   - Show skill summary (name, description, location)
   - Instruct agent to use read_file when needed
   - Keep `always: true` skills in prompt

4. **Add skill requirements checking**
   - Parse `requires:` from SKILL.md frontmatter
   - Check bins and env vars
   - Filter unavailable skills from list

5. **Add memory consolidation**
   - Auto-trigger when history > memory_window
   - Use LLM to summarize and extract key info
   - Write to MEMORY.md

### 6.3 Future Enhancements (LOW Priority)

6. **Add reasoning tag support**
   - Parse `` blocks from LLM response
   - Hide reasoning from user (show only final content)

7. **Add silent reply token**
   - Support `SILENT_REPLY` for tool-only responses
   - Don't send empty replies to messaging channels

8. **Add heartbeat system**
   - Periodic "ping" to check agent status
   - Agent replies with `HEARTBEAT_OK` if no issues

---

## 7. Implementation Plan

### Phase 1: SOUL.md + Bootstrap (1-2 days)

**File**: `skills/builtin/soul/SKILL.md`
- Copy OpenClaw SOUL.md template
- Test with various queries
- Verify personality comes through

**File**: `src/fastreact/agent.py`
- Add `_load_workspace_bootstrap()` method
- Inject bootstrap files in system prompt
- Add truncation for large files

### Phase 2: Progressive Skills + Requirements (2-3 days)

**File**: `src/fastreact/skills/`
- Add `requires:` parsing to SKILL.md frontmatter
- Implement `_check_skill_requirements()`
- Build XML skills summary for system prompt

**File**: `src/fastreact/core/prompts.py`
- Update `SYSTEM_PROMPT_CORE` with progressive loading instructions
- Add "read SKILL.md with read_file" guidance

### Phase 3: Memory Consolidation (2-3 days)

**File**: `src/fastreact/core/memory.py`
- Implement `MemoryStore.consolidate()`
- Auto-trigger when history > memory_window
- Extract key info with LLM, write to MEMORY.md

**File**: `src/fastreact/agent.py`
- Call consolidation after each message if needed
- Run in background task (asyncio.create_task)

---

## 8. Conclusion

**OpenClaw's innovation**: SOUL.md + bootstrap file injection = "soulful" agents that can evolve

**NanoBot's innovation**: Progressive skill loading + requirements checking = efficient, dependency-aware skills

**FastReAct's position**: Already has strong SKILL/MCP foundation, but lacks:
1. Personality system (SOUL.md)
2. Bootstrap injection (workspace files)
3. Progressive skill loading
4. Memory consolidation

**Recommended approach**: Copy SOUL.md template + bootstrap injection from OpenClaw, progressive loading from both projects. Add requirements checking and memory consolidation from NanoBot.

**Total effort**: 5-8 days for all improvements

**Impact**: FastReAct will have:
- More "human-like" agent personality (SOUL.md)
- Better workspace customization (bootstrap files)
- More efficient skill loading (progressive)
- More reliable skill execution (requirements check)
- Better long-term memory (consolidation)

---

**Sources**:
- OpenClaw SOUL.md: `/Users/xudawei/openclaw/docs/reference/templates/SOUL.md`
- OpenClaw system-prompt.ts: `/Users/xudawei/openclaw/src/agents/system-prompt.ts`
- OpenClaw system-prompt.md: `/Users/xudawei/openclaw/docs/concepts/system-prompt.md`
- NanoBot agent/loop.py: `/Users/xudawei/nanobot/nanobot/agent/loop.py`
- NanoBot agent/context.py: `/Users/xudawei/nanobot/nanobot/agent/context.py`
- NanoBot agent/skills.py: `/Users/xudawei/nanobot/nanobot/agent/skills.py`
- InfoQ SOUL.md analysis: [当AI开始拥有灵魂：逐句解读OpenClaw的SOUL.md](https://www.infoq.cn/article/7QieJxH5gpNRvL5hKcrG)
- OpenClaw architecture: [Open Craw架构学习](https://www.cnblogs.com/aibi1/p/19625314)
