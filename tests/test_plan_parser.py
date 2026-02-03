"""
测试 Plan Parser - LLM 输出解析器
"""

import pytest
from fastreact.graph import (
    PlanParser,
    ParseFormat,
    ExecutionPlan,
    ExecutionStep,
    ParseError,
    create_plan_parser,
    parse_llm_plan,
    generate_planning_prompt,
)


# ============================================================================
# 测试数据
# ============================================================================

VALID_JSON_PLAN = '''```json
{
  "goal": "Research AI trends and generate report",
  "description": "Search for latest AI developments and create a comprehensive report",
  "steps": [
    {
      "step_id": "search_ai",
      "tool": "search",
      "description": "Search for AI trends",
      "inputs": {
        "query": "AI trends 2024"
      },
      "dependencies": [],
      "condition": null
    },
    {
      "step_id": "deep_research",
      "tool": "deep_research",
      "description": "Conduct deep research on AI",
      "inputs": {
        "topic": "Artificial Intelligence trends",
        "depth": "standard"
      },
      "dependencies": ["search_ai"],
      "condition": null
    },
    {
      "step_id": "write_report",
      "tool": "write_file",
      "description": "Write the final report",
      "inputs": {
        "path": "ai_report.md"
      },
      "dependencies": ["deep_research"],
      "condition": null
    }
  ]
}
```'''

VALID_MARKDOWN_PLAN = '''# AI Research Workflow

## Goal: Research AI trends

## Step 1: Search for AI trends
Tool: search
Description: Search for AI trends

## Step 2: Deep research
Tool: deep_research
Description: Conduct deep research on AI
Dependencies: step_1

## Step 3: Write report
Tool: write_file
Description: Write the final report
Dependencies: step_2
'''

INVALID_PLAN_NO_STEPS = '''{
  "goal": "Test plan",
  "steps": []
}'''

INVALID_PLAN_CIRCULAR = '''{
  "goal": "Circular dependency test",
  "steps": [
    {
      "step_id": "step_1",
      "tool": "tool_a",
      "dependencies": ["step_2"]
    },
    {
      "step_id": "step_2",
      "tool": "tool_b",
      "dependencies": ["step_1"]
    }
  ]
}'''

DUPLICATE_STEP_IDS = '''{
  "goal": "Duplicate test",
  "steps": [
    {
      "step_id": "step_1",
      "tool": "tool_a"
    },
    {
      "step_id": "step_1",
      "tool": "tool_b"
    }
  ]
}'''


# ============================================================================
# 测试 ExecutionStep
# ============================================================================

class TestExecutionStep:
    """测试执行步骤"""

    def test_create_step(self):
        """测试创建步骤"""
        step = ExecutionStep(
            step_id="test_step",
            tool_name="test_tool",
            inputs={"param": "value"},
            dependencies=["prev_step"],
            condition="success",
            description="Test step",
        )

        assert step.step_id == "test_step"
        assert step.tool_name == "test_tool"
        assert step.inputs == {"param": "value"}
        assert step.dependencies == ["prev_step"]
        assert step.condition == "success"
        assert step.description == "Test step"

    def test_step_defaults(self):
        """测试步骤默认值"""
        step = ExecutionStep(
            step_id="test",
            tool_name="tool",
        )

        assert step.inputs == {}
        assert step.dependencies == []
        assert step.condition is None
        assert step.description == ""

    def test_to_dict(self):
        """测试转换为字典"""
        step = ExecutionStep(
            step_id="test",
            tool_name="tool",
            inputs={"x": 1},
        )

        data = step.to_dict()

        assert data["step_id"] == "test"
        assert data["tool_name"] == "tool"
        assert data["inputs"] == {"x": 1}


# ============================================================================
# 测试 ExecutionPlan
# ============================================================================

class TestExecutionPlan:
    """测试执行计划"""

    def test_create_plan(self):
        """测试创建计划"""
        steps = [
            ExecutionStep(step_id="s1", tool_name="tool_a"),
            ExecutionStep(step_id="s2", tool_name="tool_b", dependencies=["s1"]),
        ]

        plan = ExecutionPlan(
            steps=steps,
            goal="Test goal",
            description="Test description",
        )

        assert len(plan.steps) == 2
        assert plan.goal == "Test goal"
        assert plan.description == "Test description"

    def test_validate_valid_plan(self):
        """测试验证有效计划"""
        steps = [
            ExecutionStep(step_id="s1", tool_name="tool_a"),
            ExecutionStep(step_id="s2", tool_name="tool_b", dependencies=["s1"]),
        ]

        plan = ExecutionPlan(steps=steps)
        is_valid, errors = plan.validate()

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_duplicate_ids(self):
        """测试验证重复 ID"""
        steps = [
            ExecutionStep(step_id="s1", tool_name="tool_a"),
            ExecutionStep(step_id="s1", tool_name="tool_b"),
        ]

        plan = ExecutionPlan(steps=steps)
        is_valid, errors = plan.validate()

        assert is_valid is False
        assert any("Duplicate" in err for err in errors)

    def test_validate_missing_dependency(self):
        """测试验证缺失的依赖"""
        steps = [
            ExecutionStep(step_id="s1", tool_name="tool_a", dependencies=["nonexistent"]),
        ]

        plan = ExecutionPlan(steps=steps)
        is_valid, errors = plan.validate()

        assert is_valid is False
        assert any("non-existent" in err for err in errors)

    def test_validate_circular_dependencies(self):
        """测试验证循环依赖"""
        steps = [
            ExecutionStep(step_id="s1", tool_name="tool_a", dependencies=["s2"]),
            ExecutionStep(step_id="s2", tool_name="tool_b", dependencies=["s1"]),
        ]

        plan = ExecutionPlan(steps=steps)
        is_valid, errors = plan.validate()

        assert is_valid is False
        assert any("circular" in err.lower() for err in errors)

    def test_to_dict(self):
        """测试转换为字典"""
        steps = [
            ExecutionStep(step_id="s1", tool_name="tool_a"),
        ]

        plan = ExecutionPlan(steps=steps, goal="Test")
        data = plan.to_dict()

        assert data["goal"] == "Test"
        assert len(data["steps"]) == 1
        assert data["steps"][0]["step_id"] == "s1"


# ============================================================================
# 测试 PlanParser
# ============================================================================

class TestPlanParser:
    """测试计划解析器"""

    def test_create_parser(self):
        """测试创建解析器"""
        parser = create_plan_parser(format=ParseFormat.JSON)

        assert parser.format == ParseFormat.JSON

    def test_parse_json_valid(self):
        """测试解析有效 JSON"""
        parser = create_plan_parser(format=ParseFormat.JSON)
        plan = parser.parse(VALID_JSON_PLAN)

        assert len(plan.steps) == 3
        assert plan.goal == "Research AI trends and generate report"
        assert plan.steps[0].step_id == "search_ai"
        assert plan.steps[0].tool_name == "search"
        assert plan.steps[1].dependencies == ["search_ai"]

    def test_parse_json_no_steps(self):
        """测试解析没有步骤的 JSON"""
        parser = create_plan_parser(format=ParseFormat.JSON)

        with pytest.raises(ParseError, match="No steps found"):
            parser.parse(INVALID_PLAN_NO_STEPS)

    def test_parse_markdown_valid(self):
        """测试解析有效 Markdown"""
        parser = create_plan_parser(format=ParseFormat.MARKDOWN)
        plan = parser.parse(VALID_MARKDOWN_PLAN)

        assert len(plan.steps) == 3
        assert plan.steps[0].tool_name == "search"
        assert plan.steps[1].tool_name == "deep_research"

    def test_parse_auto_json(self):
        """测试自动检测 JSON"""
        parser = create_plan_parser(format=ParseFormat.AUTO)
        plan = parser.parse(VALID_JSON_PLAN)

        assert len(plan.steps) == 3

    def test_parse_auto_markdown(self):
        """测试自动检测 Markdown"""
        parser = create_plan_parser(format=ParseFormat.AUTO)
        plan = parser.parse(VALID_MARKDOWN_PLAN)

        assert len(plan.steps) == 3

    def test_parse_invalid_json(self):
        """测试解析无效 JSON"""
        parser = create_plan_parser(format=ParseFormat.JSON)

        with pytest.raises(ParseError):
            parser.parse("not a json")

    def test_parse_circular_dependencies(self):
        """测试解析循环依赖"""
        parser = create_plan_parser(format=ParseFormat.JSON)

        with pytest.raises(ParseError, match="circular"):
            parser.parse(INVALID_PLAN_CIRCULAR)

    def test_parse_duplicate_step_ids(self):
        """测试解析重复步骤 ID"""
        parser = create_plan_parser(format=ParseFormat.JSON)

        with pytest.raises(ParseError, match="Duplicate"):
            parser.parse(DUPLICATE_STEP_IDS)

    def test_clean_output(self):
        """测试清理输出"""
        parser = create_plan_parser()

        cleaned = parser._clean_output("""
        Line 1

        Line 2


        Line 3
        """)

        assert cleaned == "Line 1\nLine 2\nLine 3"

    def test_validate_tool_names(self):
        """测试验证工具名称"""
        tool_registry = {
            "search": {},
            "deep_research": {},
        }

        parser = create_plan_parser(tool_registry=tool_registry)
        plan = parser.parse(VALID_JSON_PLAN)

        is_valid, invalid = parser.validate_tool_names(plan)

        assert is_valid is False  # write_file 不在注册表中
        assert "write_file" in invalid


# ============================================================================
# 测试快捷函数
# ============================================================================

class TestUtilityFunctions:
    """测试工具函数"""

    def test_parse_llm_plan(self):
        """测试快捷解析函数"""
        plan = parse_llm_plan(VALID_JSON_PLAN, format=ParseFormat.JSON)

        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) == 3

    def test_generate_planning_prompt(self):
        """测试生成规划提示词"""
        prompt = generate_planning_prompt(
            user_request="Research AI trends",
            tool_list=["search", "deep_research", "write_file"],
        )

        assert "Research AI trends" in prompt
        assert "search" in prompt
        assert "deep_research" in prompt
        assert "write_file" in prompt


# ============================================================================
# 测试边界情况
# ============================================================================

class TestEdgeCases:
    """测试边界情况"""

    def test_empty_inputs(self):
        """测试空输入"""
        parser = create_plan_parser()

        plan_json = '{"goal": "test", "steps": [{"step_id": "s1", "tool": "tool_a", "inputs": {}}]}'
        plan = parser.parse(plan_json)

        assert plan.steps[0].inputs == {}

    def test_null_condition(self):
        """测试空条件"""
        parser = create_plan_parser()

        plan_json = '{"goal": "test", "steps": [{"step_id": "s1", "tool": "tool_a", "condition": null}]}'
        plan = parser.parse(plan_json)

        assert plan.steps[0].condition is None

    def test_nested_dependencies(self):
        """测试嵌套依赖"""
        parser = create_plan_parser()

        plan_json = '''{
          "goal": "nested",
          "steps": [
            {"step_id": "s1", "tool": "tool_a"},
            {"step_id": "s2", "tool": "tool_b", "dependencies": ["s1"]},
            {"step_id": "s3", "tool": "tool_c", "dependencies": ["s2"]},
            {"step_id": "s4", "tool": "tool_d", "dependencies": ["s3"]}
          ]
        }'''

        plan = parser.parse(plan_json)

        is_valid, errors = plan.validate()
        assert is_valid is True
        assert plan.steps[3].dependencies == ["s3"]

    def test_multiple_dependencies(self):
        """测试多个依赖"""
        parser = create_plan_parser()

        plan_json = '''{
          "goal": "multiple deps",
          "steps": [
            {"step_id": "s1", "tool": "tool_a"},
            {"step_id": "s2", "tool": "tool_b"},
            {"step_id": "s3", "tool": "tool_c", "dependencies": ["s1", "s2"]}
          ]
        }'''

        plan = parser.parse(plan_json)

        assert set(plan.steps[2].dependencies) == {"s1", "s2"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
