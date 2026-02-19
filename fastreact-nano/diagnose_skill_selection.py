#!/usr/bin/env python3
"""
诊断 SKILL 选择 - 对比模型基础知识 vs SKILL 指导
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastreact import Agent
from fastreact.core.config import Config


async def diagnose_git_query():
    """诊断 Git 查询 - 是 SKILL 还是模型知识？"""
    print("=" * 70)
    print("诊断：Git 查询是否使用了 SKILL")
    print("=" * 70)

    config = Config.load()
    agent = Agent(config=config, multitenant=False)
    await agent._load_mcp_servers()

    query = "当前在git的什么分支"

    # 步骤 1: 检查 SKILL 自动选择
    print("\n[步骤 1] SKILL 自动选择")
    selected_skills = agent._select_skills_auto(
        query=query,
        max_skills=3,
        user_context=None
    )

    if selected_skills:
        print(f"✓ 选中 SKILL: {selected_skills}")
    else:
        print(f"❌ 没有选中任何 SKILL")

    # 步骤 2: 检查 git_workflow SKILL 内容
    print("\n[步骤 2] 检查 git_workflow SKILL")
    git_skill = agent._skills.get("git_workflow")

    if git_skill:
        print(f"✓ git_workflow 存在")
        print(f"  描述: {git_skill.description}")
        print(f"  标签: {git_skill.metadata.tags}")
        print(f"  推荐工具: {git_skill.metadata.recommended_tools}")

        # 读取 SKILL 内容
        skill_content = git_skill.read_file("SKILL.md")
        if skill_content:
            print(f"\n  SKILL 内容预览（前 500 字符）:")
            print("  " + "-" * 66)
            for line in skill_content.split('\n')[:20]:
                print(f"  {line}")
    else:
        print(f"❌ git_workflow 不存在")

    # 步骤 3: 构建系统提示词对比
    print("\n[步骤 3] 系统提示词对比")

    # 无 SKILL
    prompt_no_skill = agent._build_system_prompt_with_skills([])

    # 有 git_workflow
    prompt_with_skill = agent._build_system_prompt_with_skills(["git_workflow"])

    print(f"  无 SKILL 长度: {len(prompt_no_skill)} 字符")
    print(f"  有 git_workflow 长度: {len(prompt_with_skill)} 字符")
    print(f"  差异: +{len(prompt_with_skill) - len(prompt_no_skill)} 字符")

    # 步骤 4: 查看提示词中关于 git 的内容
    print("\n[步骤 4] 检查系统提示词中的 git 指导")

    if "git" in prompt_with_skill.lower():
        print("✓ git 相关内容在提示词中")

        # 查找包含 git 的行
        lines = prompt_with_skill.split('\n')
        git_lines = [i for i, line in enumerate(lines) if 'git' in line.lower()]

        if git_lines:
            print(f"  找到 {len(git_lines)} 行包含 'git'")
            print("\n  关键内容:")
            for i in git_lines[:3]:  # 只显示前 3 处
                start = max(0, i - 1)
                end = min(len(lines), i + 2)
                for j in range(start, end):
                    print(f"  {j}: {lines[j][:100]}")
                print("  " + "-" * 66)
    else:
        print("❌ git 相关内容不在提示词中")

    # 步骤 5: 结论
    print("\n[步骤 5] 诊断结论")

    if selected_skills and "git_workflow" in selected_skills:
        print("✅ SKILL 被自动选择")
        print("  → Agent 的行为受 SKILL 指导")
        print("  → 使用 exec 工具是 SKILL 推荐的做法")
        print("  → 不是纯粹模型知识，而是 SKILL + 工具定义")
    else:
        print("⚠️  SKILL 未被选择")
        print("  → Agent 可能使用模型基础知识")
        print("  → 知道 git 命令和 exec 工具的使用")
        print("  → 这是 LLM 的训练数据知识")


async def diagnose_time_query():
    """诊断时间查询 - 为什么没有 SKILL 也能调用 MCP？"""
    print("\n" + "=" * 70)
    print("诊断：时间查询 - 为什么没有 SKILL 也能调用 MCP？")
    print("=" * 70)

    config = Config.load()
    agent = Agent(config=config, multitenant=False)
    await agent._load_mcp_servers()

    query = "现在几点了"

    # 步骤 1: 检查 SKILL 自动选择
    print("\n[步骤 1] SKILL 自动选择")
    selected_skills = agent._select_skills_auto(
        query=query,
        max_skills=3,
        user_context=None
    )

    if selected_skills:
        print(f"✓ 选中 SKILL: {selected_skills}")
    else:
        print(f"❌ 没有选中任何 SKILL（符合预期）")

    # 步骤 2: 检查 timeserver MCP 工具定义
    print("\n[步骤 2] 检查 timeserver MCP 工具")
    all_tools = agent._tools.list_all()

    timeserver_tools = [t for t in all_tools if 'timeserver' in t]
    if timeserver_tools:
        print(f"✓ Timeserver 工具可用: {timeserver_tools}")

        # 获取工具定义
        for tool_name in timeserver_tools:
            try:
                tool_def = agent._tools.get_tool_definition(tool_name)
                if tool_def:
                    print(f"\n  工具: {tool_name}")
                    print(f"  描述: {tool_def.get('description', 'N/A')}")
            except:
                pass
    else:
        print(f"❌ Timeserver 工具不可用")

    # 步骤 3: 检查系统提示词（无 SKILL）
    print("\n[步骤 3] 检查系统提示词中的工具定义")

    # 不选择任何 SKILL，构建提示词
    prompt_no_skill = agent._build_system_prompt_with_skills([])

    # 检查是否包含 timeserver 工具
    if 'timeserver' in prompt_no_skill.lower():
        print("✓ timeserver 工具在提示词中（即使没有 SKILL）")
        print("  → 工具定义被自动包含在系统提示词中")
        print("  → LLM 可以直接看到工具并调用")
    else:
        print("❌ timeserver 工具不在提示词中")

    # 步骤 4: 结论
    print("\n[步骤 4] 诊断结论")
    print("✅ MCP 工具被调用，但不需要 SKILL")
    print("  → MCP 工具定义直接在系统提示词中")
    print("  → LLM 看到工具描述后决定调用")
    print("  → 这是工具定义的作用，不是 SKILL 的作用")


async def explain_difference():
    """解释模型知识 vs SKILL vs MCP 工具"""
    print("\n" + "=" * 70)
    print("核心概念：模型知识 vs SKILL vs MCP 工具")
    print("=" * 70)

    print("""
三层架构：

1. LLM 基础知识（模型训练数据）
   → 知道 git 是什么
   → 知道 git branch 命令
   → 知道如何用 bash 查询分支

2. MCP 工具定义（工具能力）
   → timeserver_get-current-time 工具
   → 描述：获取当前时间
   → LLM 看到描述后可以调用

3. SKILL 系统（认知模式和工作流）
   → git_workflow: 如何使用 git 工具
   → graphrag_workflow: 如何进行知识图谱查询
   → 提供最佳实践、使用模式、工具组合

关系：

[查询] → [SKILL 自动选择] → [系统提示词注入]
                      ↓
              [包含工具定义]
                      ↓
                  [LLM 决策]
                      ↓
              [调用工具]

关键点：

✓ 没有 SKILL 也能工作
  - LLM 可以根据工具定义直接调用
  - 例如：timeserver 工具没有 SKILL 也能调用

✓ SKILL 提供指导而非强制
  - 告诉 LLM 何时用哪个工具
  - 告诉 LLM 如何组合工具
  - 告诉 LLM 最佳实践

✓ 模型知识 vs SKILL 指导
  - Git 查询：可能是模型知识 + SKILL 指导
  - GraphRAG：必须有 SKILL，因为模型不知道具体工具

如何区分？

1. 查看 metadata.skills 字段
   - 有 SKILL → SKILL 指导生效
   - 无 SKILL → 模型知识 + 工具定义

2. 查看工具调用模式
   - 简单工具调用 → 可能是模型知识
   - 复杂工作流 → SKILL 指导

3. 对比有无 SKILL 的行为
   - 禁用 SKILL 后行为不同 → SKILL 有作用
    """)


async def main():
    """运行所有诊断"""
    await diagnose_git_query()
    await diagnose_time_query()
    await explain_difference()

    print("\n" + "=" * 70)
    print("总结")
    print("=" * 70)

    print("""
你的观察是正确的：

1. Git 分支查询
   → 使用 exec 工具
   → 可能是模型基础知识（知道 git 命令）
   → 如果 git_workflow SKILL 被选择，则是 SKILL 指导

2. 时间查询
   → 使用 timeserver MCP 工具
   → 没有 SKILL 也能工作
   → MCP 工具定义直接在系统提示词中

验证方法：

在前端展开 session_start 事件：
  metadata.skills: ["git_workflow"]  ← 有这个就是 SKILL

或者运行此脚本：
  python3 diagnose_skill_selection.py
    """)


if __name__ == "__main__":
    asyncio.run(main())
