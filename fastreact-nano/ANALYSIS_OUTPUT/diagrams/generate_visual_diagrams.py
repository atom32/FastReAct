#!/usr/bin/env python3
"""
Generate comprehensive visual ASCII diagrams comparing FastReAct Nano, OpenClaw, and nanobot
"""

from pathlib import Path


def generate_fastreact_diagram():
    """Generate FastReAct Nano architecture diagram"""

    diagram = """
╔════════════════════════════════════════════════════════════════════════════════════════╗
║                    FASTREACT NANO - BRAIN-BODY ARCHITECTURE (6-LAYER)                  ║
╚════════════════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 6: BRAIN (Pure Intent Generator - Stateless Reasoning)                        │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────────┐       │
│   │  agent.py (Agent Class)                                                 │       │
│   │  - Event-driven orchestration                                           │       │
│   │  - Session state management                                             │       │
│   │  - Tool execution coordination                                          │       │
│   │  - Safety monitoring                                                    │       │
│   └─────────────────────────────────────────────────────────────────────────┘       │
│                                      │                                              │
│                                      ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────────┐       │
│   │  core.react.py (React/ReAct Engine)                                     │       │
│   │  - Thought generation (THINK)                                           │       │
│   │  - Tool call planning (TOOL_CALL)                                       │       │
│   │  - Prompt engineering                                                   │       │
│   │  - LLM interaction                                                      │       │
│   └─────────────────────────────────────────────────────────────────────────┘       │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: ADAPTER (Protocol Abstraction - "The Body")                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│   │   Feishu     │  │   CLI/REPL   │  │  HTTP/Gateway│  │    Web       │          │
│   │   Adapter    │  │   Adapter    │  │   Adapter    │  │   Adapter    │          │
│   └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                  │                  │                  │                  │
│         └──────────────────┴──────────────────┴──────────────────┘                  │
│                                      │                                              │
│                              [Protocol Translation]                                 │
│                                      │                                              │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: TOOLS (MCP - Model Context Protocol Integration)                           │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────────┐       │
│   │  MCP Manager (mcp/manager.py)                                           │       │
│   │  - Server discovery & lifecycle                                         │       │
│   │  - Tool registration & invocation                                       │       │
│   │  - Resource access                                                      │       │
│   └─────────────────────────────────────────────────────────────────────────┘       │
│                                      │                                              │
│           ┌──────────────────────────┼──────────────────────────┐                  │
│           ▼                          ▼                          ▼                  │
│   ┌──────────────┐          ┌──────────────┐          ┌──────────────┐             │
│   │ File System │          │   Bash/Exec  │          │   Web Fetch  │             │
│   │    Tools    │          │    Tools     │          │    Tools     │             │
│   └──────────────┘          └──────────────┘          └──────────────┘             │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: SKILLS (Reusable, Composable Capabilities)                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────────┐       │
│   │  Skill System (skills/)                                                 │       │
│   │  - Base skill class                                                     │       │
│   │  - Skill loader & parser                                                │       │
│   │  - YAML/Markdown skill definitions                                      │       │
│   └─────────────────────────────────────────────────────────────────────────┘       │
│                                      │                                              │
│           ┌──────────────────────────┼──────────────────────────┐                  │
│           ▼                          ▼                          ▼                  │
│   ┌──────────────┐          ┌──────────────┐          ┌──────────────┐             │
│   │  GitHub      │          │  GraphRAG    │          │   Feishu     │             │
│   │  Integration │          │  Workflow    │          │   Bot SDK    │             │
│   └──────────────┘          └──────────────┘          └──────────────┘             │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: CORE (Configuration, State, Messaging)                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│   │   Config     │  │   Context    │  │   Events     │  │   Messages   │          │
│   │  Management  │  │  Management  │  │   Stream     │  │  Formatting  │          │
│   └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                  │                  │                  │                  │
│         └──────────────────┴──────────────────┴──────────────────┘                  │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: FOUNDATION (LLM Providers, Base Classes)                                   │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────────┐       │
│   │  Providers (providers/litellm.py)                                      │       │
│   │  - Multi-LLM support (OpenAI, Anthropic, etc.)                         │       │
│   │  - Streaming responses                                                  │       │
│   │  - Error handling & retries                                             │       │
│   └─────────────────────────────────────────────────────────────────────────┘       │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

╔════════════════════════════════════════════════════════════════════════════════════════╗
║                            KEY ARCHITECTURAL PRINCIPLES                                ║
╠════════════════════════════════════════════════════════════════════════════════════════╣
║ 1. BRAIN-BODY SEPARATION                                                              ║
║    - Brain (agent.py + core.react): Pure reasoning, no protocol details              ║
║    - Body (adapters): Protocol-specific execution, state management                   ║
║    - Clean interface via AgentEvent stream                                           ║
║                                                                                        ║
║ 2. PROTOCOL AGNOSTIC                                                                  ║
║    - Agent logic has ZERO knowledge of Feishu, Slack, CLI, etc.                      ║
║    - Adding new protocol = implement adapter interface                               ║
║    - No protocol code in brain/core layers                                           ║
║                                                                                        ║
║ 3. MCP STANDARDIZATION                                                                ║
║    - All tools accessed via Model Context Protocol                                   ║
║    - Consistent tool interface across implementations                                ║
║    - Easy to add new tools/servers                                                   ║
║                                                                                        ║
║ 4. EVENT-DRIVEN ORCHESTRATION                                                         ║
║    - AsyncIterator[AgentEvent] as only communication channel                         ║
║    - No callbacks, no direct method calls across layers                              ║
║    - Testable, composable, observable                                                ║
╚════════════════════════════════════════════════════════════════════════════════════════╝
"""

    return diagram


def generate_openclaw_diagram():
    """Generate OpenClaw architecture diagram"""

    diagram = """
╔════════════════════════════════════════════════════════════════════════════════════════╗
║                         OPENCLAW - MONOLITHIC ARCHITECTURE (7-LAYER)                   ║
╚════════════════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 7: APPLICATION                                                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│   CLI, Desktop App, Browser UI, Extensions (3,133 files, 10,267 imports)            │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 6: AGENT COORDINATION                                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│   - Multi-agent coordination                                                        │
│   - Agent lifecycle management                                                      │
│   - Complex orchestration logic                                                     │
│   - Heavy coupling to protocols                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: SKILL EXECUTION                                                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│   - Custom skill system                                                             │
│   - Skills tightly integrated with agents                                          │
│   - Embedded in agent execution flow                                               │
│   - Not easily reusable across contexts                                            │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: TOOL MANAGEMENT                                                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│   - Proliferation of custom tools                                                  │
│   - No standard tool protocol (MCP)                                                 │
│   - Each tool has unique interface                                                 │
│   - High maintenance overhead                                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: PROTOCOL BRIDGE                                                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│   - Protocol-specific logic mixed with agent logic                                  │
│   - No clean abstraction                                                            │
│   - Adding new protocols requires touching multiple layers                          │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: CORE SERVICES                                                               │
├─────────────────────────────────────────────────────────────────────────────────────┤
│   Config, Runtime, State                                                            │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: FOUNDATION                                                                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│   Base Classes, Utilities                                                           │
└─────────────────────────────────────────────────────────────────────────────────────┘

╔════════════════════════════════════════════════════════════════════════════════════════╗
║                            KEY ARCHITECTURAL CHARACTERISTICS                           ║
╠════════════════════════════════════════════════════════════════════════════════════════╣
║ [X] MONOLITHIC DESIGN                                                                 ║
║     - Tight coupling between layers                                                 ║
║     - Agent logic knows about protocols (Slack, Discord, etc.)                      ║
║     - Hard to modify without affecting multiple layers                               ║
║                                                                                        ║
║ [X] HIGH COMPLEXITY                                                                   ║
║     - 3,133 source files                                                             ║
║     - 10,267 import relationships                                                    ║
║     - Max coupling: 494 (config.js)                                                 ║
║     - Very large codebase for the functionality                                      ║
║                                                                                        ║
║ [X] PROLIFERATION OF TOOLS                                                            ║
║     - No standard tool protocol                                                      ║
║     - Custom tools for each capability                                               ║
║     - High maintenance cost                                                          ║
║                                                                                        ║
║ [X] TIGHT PROTOCOL COUPLING                                                           ║
║     - Agent logic embedded with protocol-specific code                               ║
║     - Adding new protocols requires changes across layers                            ║
║     - Not protocol-agnostic                                                          ║
╚════════════════════════════════════════════════════════════════════════════════════════╝
"""

    return diagram


def generate_nanobot_diagram():
    """Generate nanobot architecture diagram"""

    diagram = """
╔════════════════════════════════════════════════════════════════════════════════════════╗
║                          NANOBOT - MONOLITHIC ARCHITECTURE (5-LAYER)                    ║
╚════════════════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: APPLICATION                                                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│   CLI (53 files, 139 imports)                                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: AGENT LOGIC                                                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────────┐       │
│   │  agent.loop (Agent Loop)                                               │       │
│   │  - Agent loop tightly coupled with tools                                │       │
│   │  - Direct access to tool implementations                                │       │
│   │  - No abstraction layer between agent and tools                         │       │
│   └─────────────────────────────────────────────────────────────────────────┘       │
│                                      │                                              │
│           ┌──────────────────────────┼──────────────────────────┐                  │
│           ▼                          ▼                          ▼                  │
│   ┌──────────────┐          ┌──────────────┐          ┌──────────────┐             │
│   │ agent.memory │          │agent.context │          │ agent.sub-   │             │
│   │              │          │              │          │    agent     │             │
│   └──────────────┘          └──────────────┘          └──────────────┘             │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: TOOLS                                                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────────┐       │
│   │  agent.tools (Tools embedded in agent module)                           │       │
│   │  - filesystem, shell, web, mcp, cron, spawn                            │       │
│   │  - Direct coupling to agent logic                                       │       │
│   │  - No standardized protocol (MCP not fully used)                        │       │
│   └─────────────────────────────────────────────────────────────────────────┘       │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: SERVICES                                                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│   │   Config     │  │   Channels   │  │     Bus      │  │    Cron      │          │
│   │              │  │  (Protocol)  │  │  (Events)    │  │              │          │
│   └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                  │                  │                  │                  │
│         └──────────────────┴──────────────────┴──────────────────┘                  │
│                                      │                                              │
│                              [Channels tightly coupled to agent]                    │
│                                      │                                              │
│           ┌──────────────────────────┼──────────────────────────┐                  │
│           ▼                          ▼                          ▼                  │
│   ┌──────────────┐          ┌──────────────┐          ┌──────────────┐             │
│   │   Feishu     │          │   DingTalk   │          │   Discord   │             │
│   │              │          │              │          │             │             │
│   └──────────────┘          └──────────────┘          └──────────────┘             │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: FOUNDATION                                                                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│   Base Classes, Providers, Utils                                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘

╔════════════════════════════════════════════════════════════════════════════════════════╗
║                            KEY ARCHITECTURAL CHARACTERISTICS                           ║
╠════════════════════════════════════════════════════════════════════════════════════════╣
║ [X] SIMPLER BUT TIGHTLY COUPLED                                                       ║
║     - Fewer layers (5 vs 6/7)                                                        ║
║     - But tight coupling between agent and tools                                     ║
║     - Agent loop directly accesses tool implementations                              ║
║                                                                                        ║
║ [X] NO PROTOCOL ABSTRACTION                                                           ║
║     - Channels (protocols) directly coupled to agent logic                            ║
║     - Adding new protocol requires modifying agent loop                              ║
║     - No adapter pattern                                                             ║
║                                                                                        ║
║ [X] TOOLS EMBEDDED IN AGENT                                                           ║
║     - agent.tools.* namespace                                                        ║
║     - No separation between agent logic and tool execution                           ║
║     - Harder to test tools in isolation                                              ║
║                                                                                        ║
║ [X] MODERATE COMPLEXITY                                                               ║
║     - 42 modules, 139 dependencies                                                   ║
║     - Max coupling: 17 (bus.events)                                                 ║
║     - Simpler than OpenClaw, but less structured than FastReAct Nano                  ║
╚════════════════════════════════════════════════════════════════════════════════════════╝
"""

    return diagram


def generate_comparison_table():
    """Generate detailed comparison table"""

    table = """
╔════════════════════════════════════════════════════════════════════════════════════════╗
║                          COMPREHENSIVE ARCHITECTURE COMPARISON                         ║
╚════════════════════════════════════════════════════════════════════════════════════════╝

┌───────────────────────────────────────────────────────────────────────────────────────┐
│ METRICS SUMMARY                                                                       │
├───────────────────────────────────────────────────────────────────────────────────────┤
│ Metric                │ FastReAct Nano  │ OpenClaw        │ nanobot                 │
├───────────────────────────────────────────────────────────────────────────────────────┤
│ Architecture          │ Brain-Body (6L) │ Monolithic (7L) │ Monolithic (5L)         │
│ Files                 │ 38              │ 3,133           │ 53                      │
│ Modules               │ 22              │ 2,533           │ 42                      │
│ Dependencies          │ 73              │ 10,267          │ 139                     │
│ Circular Dependencies │ 0               │ 0               │ 0                       │
│ Avg Coupling          │ 3.0             │ 3.8             │ 3.3                     │
│ Max Coupling          │ 14 (agent)      │ 494 (config)    │ 17 (bus.events)         │
│ Protocol Abstraction  │ YES (Adapters)  │ NO              │ NO                      │
│ Tool Standardization  │ YES (MCP)       │ NO              │ PARTIAL                 │
│ Skill Reusability     │ HIGH            │ LOW             │ MEDIUM                  │
│ Testability           │ HIGH            │ LOW             │ MEDIUM                  │
└───────────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────────────┐
│ BRAIN-BODY SEPARATION ANALYSIS                                                        │
├───────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                       │
│ FastReAct Nano:                                                                       │
│   ✓ Brain (agent.py + core.react.py) has ZERO protocol knowledge                     │
│   ✓ Body (adapters/) handles all protocol-specific logic                              │
│   ✓ Clean interface: AsyncIterator[AgentEvent]                                       │
│   ✓ Adding new protocol = implement adapter, touch nothing else                       │
│                                                                                       │
│ OpenClaw:                                                                             │
│   ✗ Agent logic contains protocol-specific code                                       │
│   ✗ Channels, CLI, Discord code mixed into agents                                    │
│   ✗ No clear brain-body separation                                                    │
│   ✗ Adding protocol = modify multiple layers                                         │
│                                                                                       │
│ nanobot:                                                                              │
│   ✗ Agent loop (agent.loop) directly calls channels                                  │
│   ✗ No adapter abstraction layer                                                    │
│   ✗ Protocol code in agent.logic.*                                                   │
│   ✗ Adding protocol = modify agent loop                                              │
│                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────────────┐
│ PROTOCOL AGNOSTIC DESIGN COMPARISON                                                   │
├───────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                       │
│ FastReAct Nano Adapters:                                                              │
│   adapters/feishu.py       → Feishu (飞书)                                           │
│   adapters/feishu_sdk.py   → Feishu SDK                                              │
│   adapters/cli.py          → Command Line                                            │
│   adapters/repl.py         → Interactive REPL                                        │
│   adapters/http.py         → HTTP/Gateway                                            │
│   adapters/web.py          → Web Interface                                           │
│   adapters/gateway.py      → Generic Gateway                                         │
│                                                                                       │
│   → Agent code does NOT import any of these!                                         │
│   → Agent works via AgentEvent stream, protocol-agnostic                              │
│                                                                                       │
│ OpenClaw:                                                                             │
│   src/cli/             → Agent code contains CLI logic                                │
│   src/discord/         → Agent code contains Discord logic                            │
│   src/channels/        → Agent code contains channel logic                           │
│                                                                                       │
│   → Agent directly imports and uses protocol modules                                 │
│   → Tight coupling, hard to modify                                                   │
│                                                                                       │
│ nanobot:                                                                              │
│   agent.loop → channels.feishu (direct import)                                       │
│   agent.loop → channels.discord (direct import)                                      │
│   agent.loop → channels.slack (direct import)                                        │
│                                                                                       │
│   → Agent loop imports all protocols directly                                        │
│   → No abstraction layer                                                             │
│                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────────────┐
│ MCP (MODEL CONTEXT PROTOCOL) INTEGRATION COMPARISON                                   │
├───────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                       │
│ FastReAct Nano:                                                                       │
│   ✓ First-class MCP integration (mcp/manager.py, mcp/client.py)                      │
│   ✓ All tools accessed via MCP                                                       │
│   ✓ Consistent tool interface                                                        │
│   ✓ Easy to add new MCP servers                                                      │
│   ✓ Tool discovery and lifecycle management                                          │
│                                                                                       │
│ OpenClaw:                                                                             │
│   ✗ No MCP support                                                                   │
│   ✗ Proliferation of custom tools (~200+ tools)                                      │
│   ✗ Each tool has unique interface                                                   │
│   ✗ High maintenance cost                                                            │
│                                                                                       │
│ nanobot:                                                                              │
│   ~ Partial MCP support (agent.tools.mcp)                                            │
│   ~ But also many custom tools (filesystem, shell, web, etc.)                        │
│   ~ Not standardized on MCP                                                          │
│   ~ Tool interfaces inconsistent                                                      │
│                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────────────┐
│ COUPLING ANALYSIS                                                                     │
├───────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                       │
│ FastReAct Nano: Max Coupling = 14                                                    │
│   → agent.py (orchestration hub, acceptable)                                         │
│   → Well-controlled dependencies                                                     │
│   → Clean layer boundaries                                                           │
│                                                                                       │
│ OpenClaw: Max Coupling = 494                                                          │
│   → config.js (massive coupling, warning sign)                                       │
│   → Many modules with >100 dependencies                                              │
│   → Tight coupling across layers                                                     │
│   → High ripple effect on changes                                                    │
│                                                                                       │
│ nanobot: Max Coupling = 17                                                            │
│   → bus.events, agent.loop, config.schema                                            │
│   → Moderate coupling, but tight coupling between agent and channels                 │
│   → Better than OpenClaw, but less structured than FastReAct Nano                    │
│                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────────────┐
│ MAINTAINABILITY SCORE                                                                 │
├───────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                       │
│ Aspect                  │ FastReAct Nano │ OpenClaw │ nanobot                        │
├───────────────────────────────────────────────────────────────────────────────────────┤
│ Code Size              │ ★★★★★ (38)     │ ★☆☆☆☆    │ ★★★☆☆ (53)                    │
│ Dependency Complexity  │ ★★★★★ (73)     │ ★☆☆☆☆    │ ★★★★☆ (139)                   │
│ Coupling Control       │ ★★★★★ (max 14) │ ★☆☆☆☆    │ ★★★☆☆ (max 17)                │
│ Protocol Flexibility   │ ★★★★★          │ ★☆☆☆☆    │ ★★☆☆☆                         │
│ Testability            │ ★★★★★          │ ★★☆☆☆    │ ★★★☆☆                         │
│ Skill Reusability      │ ★★★★★          │ ★★☆☆☆    │ ★★★☆☆                         │
│ Overall Maintainability│ ★★★★★          │ ★★☆☆☆    │ ★★★☆☆                         │
└───────────────────────────────────────────────────────────────────────────────────────┘

╔════════════════════════════════════════════════════════════════════════════════════════╗
║                                   CONCLUSION                                            ║
╠════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                        ║
║ FastReAct Nano demonstrates SUPERIOR ARCHITECTURAL DESIGN compared to competitors:    ║
║                                                                                        ║
║ 1. BRAIN-BODY SEPARATION                                                              ║
║    - Clean separation between reasoning (brain) and execution (body)                  ║
║    - Agent logic is protocol-agnostic                                                 ║
║    - Adding new protocols doesn't require touching agent code                         ║
║                                                                                        ║
║ 2. PROTOCOL AGNOSTIC DESIGN                                                           ║
║    - Adapter pattern abstracts all protocol details                                   ║
║    - Easy to add new protocols (Feishu, Slack, HTTP, etc.)                            ║
║    - No protocol code in brain/core layers                                            ║
║                                                                                        ║
║ 3. MCP STANDARDIZATION                                                                ║
║    - First-class MCP integration for tools                                            ║
║    - Consistent tool interface across implementations                                 ║
║    - Reduced maintenance overhead                                                     ║
║                                                                                        ║
║ 4. LOWER COMPLEXITY                                                                   ║
║    - 38 files vs 3,133 (OpenClaw)                                                     ║
║    - 73 dependencies vs 10,267 (OpenClaw)                                             ║
║    - Max coupling 14 vs 494 (OpenClaw)                                                ║
║    - More maintainable, easier to understand                                          ║
║                                                                                        ║
║ 5. BETTER TESTABILITY                                                                 ║
║    - Clean layer boundaries enable isolated testing                                   ║
║    - Event-driven architecture is observable                                          ║
║    - Adapter pattern allows easy mocking                                              ║
║                                                                                        ║
║ This architecture makes FastReAct Nano MORE SUITABLE FOR PRODUCTION where:            ║
║   - Protocol flexibility is required                                                 ║
║   - Multiple integration scenarios are needed                                         ║
║   - Long-term maintenance is critical                                                 ║
║   - Team collaboration requires clear boundaries                                      ║
║                                                                                        ║
╚════════════════════════════════════════════════════════════════════════════════════════╝
"""

    return table


def main():
    """Generate all diagrams"""

    output_dir = Path("/Users/xudawei/FastReAct/fastreact-nano/ANALYSIS_OUTPUT/diagrams")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate FastReAct Nano diagram
    fr_diagram = generate_fastreact_diagram()
    with open(output_dir / "fastreact_architecture_visual.txt", 'w') as f:
        f.write(fr_diagram)
    print(f"[OK] Generated FastReAct Nano visual diagram")

    # Generate OpenClaw diagram
    oc_diagram = generate_openclaw_diagram()
    with open(output_dir / "openclaw_architecture_visual.txt", 'w') as f:
        f.write(oc_diagram)
    print(f"[OK] Generated OpenClaw visual diagram")

    # Generate nanobot diagram
    nb_diagram = generate_nanobot_diagram()
    with open(output_dir / "nanobot_architecture_visual.txt", 'w') as f:
        f.write(nb_diagram)
    print(f"[OK] Generated nanobot visual diagram")

    # Generate comparison table
    comparison = generate_comparison_table()
    with open(output_dir / "detailed_comparison.txt", 'w') as f:
        f.write(comparison)
    print(f"[OK] Generated detailed comparison table")

    # Generate combined report
    with open(output_dir / "ARCHITECTURE_ANALYSIS_REPORT.txt", 'w') as f:
        f.write("=" * 150 + "\n")
        f.write("COMPREHENSIVE ARCHITECTURE ANALYSIS REPORT\n".center(150) + "\n")
        f.write("=" * 150 + "\n\n")

        f.write(fr_diagram + "\n\n")
        f.write(oc_diagram + "\n\n")
        f.write(nb_diagram + "\n\n")
        f.write(comparison + "\n")

    print(f"[OK] Generated combined report: ARCHITECTURE_ANALYSIS_REPORT.txt")

    print("\n" + "="*80)
    print("ARCHITECTURE DIAGRAM GENERATION COMPLETE")
    print("="*80)
    print("\nGenerated files:")
    print(f"  {output_dir}/fastreact_architecture_visual.txt")
    print(f"  {output_dir}/openclaw_architecture_visual.txt")
    print(f"  {output_dir}/nanobot_architecture_visual.txt")
    print(f"  {output_dir}/detailed_comparison.txt")
    print(f"  {output_dir}/ARCHITECTURE_ANALYSIS_REPORT.txt")
    print("\nAlso available:")
    print(f"  {output_dir}/fastreact_architecture.txt (layer breakdown)")
    print(f"  {output_dir}/fastreact_dependencies.dot (graphviz format)")
    print(f"  {output_dir}/comparison_architecture.md (markdown summary)")


if __name__ == "__main__":
    main()
