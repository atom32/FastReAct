"""
高级 System Prompt 构建器

参考 moltbot 的模块化 prompt 设计
"""

import logging
from typing import Dict, Any, List, Set, Optional, Literal
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Prompt 模式（控制 prompt 的繁简程度）
PromptMode = Literal["full", "minimal", "none"]


@dataclass
class PromptConfig:
    """Prompt 配置"""
    # 基础配置
    temperature: float = 0.3
    max_iterations: int = 10

    # Prompt 模式：full（完整）, minimal（精简）, none（最简，仅身份）
    prompt_mode: PromptMode = "full"

    # 身份和角色
    assistant_name: str = "FastReAct"
    assistant_role: str = "智能助手"

    # 推理配置（默认 off，让 LLM 自主决定）
    reasoning_level: Literal["off", "basic", "extended", "deep"] = "off"
    thinking_level: Literal["silent", "concise", "verbose"] = "concise"

    # 工作区配置
    workspace_dir: Optional[str] = None
    context_files: List[Dict[str, str]] = field(default_factory=list)

    # 约束和规则
    enable_silent_replies: bool = False
    enable_heartbeat: bool = False
    enable_workspace_files: bool = True

    # 扩展 prompt
    extra_system_prompt: Optional[str] = None


class SystemPromptBuilder:
    """系统提示构建器"""

    def __init__(self, tools: Dict[str, Any]):
        """
        初始化构建器

        Args:
            tools: 可用工具字典 {name: tool_object}
        """
        self.tools = tools
        self.tool_names = list(tools.keys())

    def build(self, config: Optional[PromptConfig] = None) -> str:
        """
        构建完整的系统 prompt

        Args:
            config: Prompt 配置

        Returns:
            系统提示字符串
        """
        if config is None:
            config = PromptConfig()

        # none 模式：仅返回基础身份
        if config.prompt_mode == "none":
            return f"# 你是 {config.assistant_name}\n\n你是一个{config.assistant_role}。"

        sections = []

        # 1. 身份和基础信息
        sections.extend(self._build_identity_section(config))

        # 2. 推理和思考要求（minimal 模式跳过）
        if config.prompt_mode == "full":
            sections.extend(self._build_reasoning_section(config))

        # 3. 工具列表
        sections.extend(self._build_tools_section(config))

        # 4. 工作流程（minimal 模式简化）
        sections.extend(self._build_workflow_section(config))

        # 5. 工作区上下文
        if config.enable_workspace_files and config.workspace_dir:
            sections.extend(self._build_workspace_section(config))

        # 6. 扩展 prompt
        if config.extra_system_prompt:
            sections.append(config.extra_system_prompt)

        # 7. 运行时信息
        sections.extend(self._build_runtime_section(config))

        return "\n\n".join(sections)

    def _build_identity_section(self, config: PromptConfig) -> List[str]:
        """构建身份部分"""
        from datetime import datetime

        # 获取当前日期
        now = datetime.now()
        current_date = now.strftime("%Y年%m月%d日")
        current_time = now.strftime("%H:%M")

        return [
            f"# 你是 {config.assistant_name}",
            f"## 角色定位",
            f"你是一个{config.assistant_role}，具备强大的推理能力和工具使用能力。",
            "",
            f"## 当前时间",
            f"- 日期: {current_date}",
            f"- 时间: {current_time}",
            "",
            "**重要**: 在回答问题时，请基于当前时间判断信息的时效性。",
            "- 如果用户询问未来事件，请说明当前时间并基于实际情况回答",
            "- 如果用户询问过去事件，请考虑时间差异",
            "",
        ]

    def _build_reasoning_section(self, config: PromptConfig) -> List[str]:
        """构建推理要求部分"""
        reasoning_level = config.reasoning_level

        if reasoning_level == "off":
            return [
                "## 思考模式（按需）",
                "",
                "**默认：简洁高效**",
                "- 对于简单任务，直接行动无需过多解释",
                "- 例如：简单计算、基础查询、明确的事实检索",
                "",
                "**何时深入思考？**",
                "- 任务复杂度较高，需要多步推理",
                "- 信息不完整，需要制定收集策略",
                "- 涉及判断和决策，需要权衡利弊",
                "- 用户明确要求展示思考过程",
                "",
                "由你根据任务复杂度自主决定思考深度。",
                "",
            ]
        elif reasoning_level == "basic":
            return [
                "## 思考模式",
                "在行动前进行简单思考：",
                "- 我需要什么信息？",
                "- 哪个工具可以获取？",
                "",
            ]
        elif reasoning_level == "extended":
            return [
                "## 思考要求（推荐）",
                "",
                "对于复杂问题，建议经过 **多轮思考**：",
                "",
                "**第一轮 - 问题理解**",
                "- 用户的真实意图是什么？",
                "- 这个问题涉及哪些方面？",
                "- 需要哪些具体信息？",
                "",
                "**第二轮 - 信息缺口分析**",
                "- [OK] 我已经知道：（明确列出已知信息）",
                "- [?] 我还缺少：（至少列出 2-3 个关键缺失）",
                "- [Strategy] 获取策略：（具体的工具和查询关键词）",
                "",
                "**第三轮 - 工具选择与验证**",
                "- 最佳工具选择及理由",
                "- 预期结果是什么？",
                "- 备选方案是什么？",
                "",
                "**执行后 - 批判性分析**",
                "- 工具返回的数据可靠吗？",
                "- 需要额外的验证步骤吗？",
                "- 这个结果如何影响下一步？",
                "",
                "对于简单任务，可以简化思考流程。",
                "",
            ]
        elif reasoning_level == "deep":
            return [
                "## 深度思考模式（强制）",
                "",
                "你必须展现专家级的推理能力：",
                "",
                "**信息收集阶段**",
                "1. **全面分析问题**：拆解问题，识别关键维度",
                "2. **制定信息收集策略**：优先级排序，并行 vs 串行",
                "3. **批判性评估工具结果**：验证数据质量和可靠性",
                "",
                "**分析综合阶段**",
                "4. **识别模式和趋势**：从数据中提取洞察",
                "5. **交叉验证信息源**：发现矛盾或不一致",
                "6. **给出确定性评估**：明确标注置信度",
                "",
            ]

        return []

    def _build_tools_section(self, config: PromptConfig) -> List[str]:
        """构建工具列表部分"""
        sections = [
            "## 可用工具",
            "",
            "### 工具列表",
        ]

        # 根据工具类别组织
        tool_categories = self._categorize_tools()

        for category, tools in tool_categories.items():
            sections.append(f"\n**{category}**")
            for tool in tools:
                tool_obj = self.tools.get(tool)
                if tool_obj:
                    desc = tool_obj.description
                    sections.append(f"- **{tool}**: {desc}")

        sections.append("")
        sections.append("工具名称大小写敏感，调用时必须完全匹配。")
        sections.append("")

        return sections

    def _build_workflow_section(self, config: PromptConfig) -> List[str]:
        """构建工作流程部分"""
        is_minimal = config.prompt_mode == "minimal"

        if is_minimal:
            # minimal 模式的简化工作流（用于 subagent）
            sections = [
                "## ReAct 框架",
                "",
                "你使用 ReAct（Reasoning + Acting）框架工作：",
                "",
                "**Reasoning（推理）**: 思考当前状态和下一步行动",
                "**Acting（行动）**: 调用工具获取信息或执行操作",
                "**Observation（观察）**: 分析工具返回的结果",
                "",
                "简单任务可以快速完成，复杂任务需要多轮循环。",
                "",
                "你是 Subagent，任务是：高效完成分配的工作。",
                "",
            ]
        else:
            # full 模式的完整工作流（主 agent）
            sections = [
                "## ReAct 框架",
                "",
                "你使用 **ReAct**（**Re**asoning + **Act**ing）框架解决问题：",
                "",
                "**[循环] ReAct 循环**：",
                "",
                "1. **[思考] Thought**",
                "   - 分析当前情况：我有什么信息？还缺什么？",
                "   - 决定下一步：需要调用哪个工具？",
                "   - 预期结果：工具会返回什么？",
                "",
                "2. **[行动] Action**",
                "   - 调用工具执行操作",
                "   - 传递正确的参数",
                "",
                "3. **[观察] Observation**",
                "   - 分析工具返回的结果",
                "   - 判断：是否达到了目标？",
                "   - 决定：是否需要继续循环？",
                "",
                "4. **[循环] 循环或结束**",
                "   - 如果未完成：返回 Thought，继续下一轮",
                "   - 如果完成：整合所有信息，给出最终答案",
                "",
                "**[原则] 关键原则**：",
                "- 每轮循环都要产生 **Thought → Action → Observation**",
                "- 不要跳过思考直接行动",
                "- 不要忽略观察结果盲目继续",
                "- 最多循环 N 轮，避免无限循环",
                "",
                "**[格式] 输出格式**：",
                "- 简单任务：可以不展示 Thought，直接 Action",
                "- 复杂任务：展示完整的 Thought → Action → Observation 过程",
                "",
                               "---",
                "",
                "## [Docker] Docker 沙箱执行",
                "",
                "**你可以使用 Docker 沙箱安全地执行代码**：",
                "",
                "**支持的语言**：",
                "- Python 3.11",
                "- JavaScript (Node.js 18)",
                "- Bash",
                "- Java 17",
                "",
                "**何时使用沙箱**？",
                "- [OK] 执行不可信或用户提供的代码",
                "- [OK] 需要隔离环境的操作",
                "- [OK] 测试代码片段",
                "- [OK] 需要特定依赖的任务",
                "",
                "**安全特性**：",
                "- Docker 容器完全隔离",
                "- 资源限制（512MB 内存，50% CPU）",
                "- 自动超时控制（默认 30 秒）",
                "- 可选的关键词黑名单",
                "",
                "**示例**：",
                "```",
                "Action: sandbox_exec(code='print(sum(range(101)))', language='python')",
                "Observation: 执行成功: 5050",
                "```",
                "",
                "**[Subagent] Subagent 系统**",
                "",
                "**你可以创建 Subagent 来处理复杂任务**：",
                "",
                "**何时使用 Subagent**？",
                "- [OK] 任务复杂且耗时（如深度搜索、长文档分析）",
                "- [OK] 任务可以独立并行执行",
                "- [OK] 需要专门的推理模式（如 extended 模式）",
                "- [OK] 任务可能需要多次重试",
                "",
                "**如何创建 Subagent**？",
                "使用 `spawn_subagent` 工具：",
                "- `task`: 清晰描述任务目标",
                "- `prompt_mode`: 通常用 'minimal'（节省 token）",
                "- `reasoning_level`: 根据任务需要选择",
                "",
                "**Subagent 的特点**：",
                "- 独立执行任务，完成后汇报结果",
                "- 使用 minimal prompt 模式（更高效）",
                "- 你可以继续处理其他任务，不必等待",
                "",
                "**示例**：",
                "```",
                "Thought: 用户需要分析 2024 年 AI 进展，这是一个复杂的独立任务",
                "Action: spawn_subagent(task='搜索并分析2024年AI领域的重大突破', prompt_mode='minimal', reasoning_level='extended')",
                "Observation: Subagent 已创建，ID: subagent-abc123",
                "Thought: Subagent 正在处理，我可以继续回答用户的其他问题",
                "",
                "",
            ]

        if config.enable_silent_replies:
            sections.extend([
                "## 简洁回复",
                "当没有重要内容时，回复：`SILENT_REPLY`",
                "规则：必须是整个消息，不能追加到其他内容",
                "",
            ])

        if config.enable_heartbeat:
            sections.extend([
                "## 心跳检测",
                "如果收到心跳检测消息且无需处理，回复：`HEARTBEAT_OK`",
                "",
            ])

        return sections

    def _build_workspace_section(self, config: PromptConfig) -> List[str]:
        """构建工作区部分"""
        if not config.workspace_dir:
            return []

        sections = [
            "## 工作区",
            f"工作目录: {config.workspace_dir}",
            "",
        ]

        # 工作区文件
        if config.context_files:
            sections.append("### 工作区文件:")
            for file_info in config.context_files:
                sections.append(f"- **{file_info['path']}**")
                if file_info.get('description'):
                    sections.append(f"  {file_info['description']}")
            sections.append("")

        return sections

    def _build_runtime_section(self, config: PromptConfig) -> List[str]:
        """构建运行时信息部分"""
        sections = [
            "## 运行时配置",
            f"- 温度: {config.temperature}（较低温度 = 更确定性）",
            f"- 最大迭代: {config.max_iterations} 轮",
            f"- 思考级别: {config.reasoning_level}",
            f"- 思考详细度: {config.thinking_level}",
            "",
        ]

        return sections

    def _categorize_tools(self) -> Dict[str, List[str]]:
        """将工具按类别分组"""
        categories = {
            "搜索与获取": ["tavily_search"],
            "计算与分析": ["calculator", "code_exec"],
            "系统信息": ["datetime", "session_manager"],
            "网络": ["http"],
            "数据处理": ["text_analysis"],
            "实用工具": ["unit_converter", "weather"],
            "Agent 系统": ["spawn_subagent"],
            "沙箱执行": ["sandbox_exec"],  # 新增：Docker 沙箱
            "Gateway": ["gateway"],
        }

        return categories


def build_system_prompt(
    tools: Dict[str, Any],
    config: Optional[PromptConfig] = None
) -> str:
    """
    构建模块化的系统 prompt

    Args:
        tools: 工具字典
        config: Prompt 配置

    Returns:
        系统提示字符串
    """
    builder = SystemPromptBuilder(tools)
    return builder.build(config)


def create_prompt_config(
    temperature: float = 0.3,
    prompt_mode: PromptMode = "full",
    reasoning_level: str = "off",
    thinking_level: str = "concise",
    **kwargs
) -> PromptConfig:
    """
    创建 Prompt 配置

    Args:
        temperature: LLM 温度
        prompt_mode: Prompt 模式（full/minimal/none）
        reasoning_level: 推理级别（off/basic/extended/deep）
        thinking_level: 思考详细度（silent/concise/verbose）
        **kwargs: 其他配置参数

    Returns:
        PromptConfig 实例
    """
    return PromptConfig(
        temperature=temperature,
        prompt_mode=prompt_mode,
        reasoning_level=reasoning_level,
        thinking_level=thinking_level,
        **kwargs
    )
