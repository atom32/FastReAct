"""
测试 Graph State - 图状态管理
"""

import pytest
from datetime import datetime
from fastreact.graph import (
    NodeOutput,
    ExecutionContext,
    ReferenceResolver,
    GraphState,
    create_graph_state,
    create_execution_context,
)


# ============================================================================
# 测试 NodeOutput
# ============================================================================

class TestNodeOutput:
    """测试节点输出"""

    def test_create_output(self):
        """测试创建输出"""
        output = NodeOutput(
            node_id="test_node",
            outputs={"result": "value", "count": 10},
        )

        assert output.node_id == "test_node"
        assert output.outputs == {"result": "value", "count": 10}
        assert output.status == "completed"

    def test_get_method(self):
        """测试 get 方法"""
        output = NodeOutput(
            node_id="test",
            outputs={"key": "value"},
        )

        assert output.get("key") == "value"
        assert output.get("missing", "default") == "default"

    def test_dict_style_access(self):
        """测试字典风格访问"""
        output = NodeOutput(
            node_id="test",
            outputs={"key": "value"},
        )

        assert output["key"] == "value"
        assert "key" in output
        assert "missing" not in output


# ============================================================================
# 测试 ExecutionContext
# ============================================================================

class TestExecutionContext:
    """测试执行上下文"""

    def test_create_context(self):
        """测试创建上下文"""
        context = ExecutionContext()

        assert context.variables == {}
        assert context.metadata == {}

    def test_set_and_get(self):
        """测试设置和获取"""
        context = ExecutionContext()

        context.set("key", "value")
        assert context.get("key") == "value"
        assert context.get("missing", "default") == "default"

    def test_update(self):
        """测试批量更新"""
        context = ExecutionContext()

        context.update({"a": 1, "b": 2})
        assert context.variables == {"a": 1, "b": 2}

    def test_with_initial_variables(self):
        """测试带初始变量"""
        context = ExecutionContext(variables={"init": "value"})

        assert context.get("init") == "value"


# ============================================================================
# 测试 ReferenceResolver
# ============================================================================

class TestReferenceResolver:
    """测试引用解析器"""

    @pytest.fixture
    def state(self):
        """创建测试状态"""
        state = GraphState()
        state.set_node_output("node1", {"result": "value1", "count": 5})
        state.set_node_output("node2", {"result": "value2", "nested": {"key": "deep"}})
        state.completed_nodes.add("node1")
        state.completed_nodes.add("node2")
        return state

    def test_resolve_simple_reference(self, state):
        """测试解析简单引用"""
        result = ReferenceResolver.resolve_reference("@node1.result", state)

        assert result == "value1"

    def test_resolve_nested_reference(self, state):
        """测试解析嵌套引用"""
        result = ReferenceResolver.resolve_reference("@node2.nested.key", state)

        assert result == "deep"

    def test_resolve_full_output(self, state):
        """测试解析完整输出"""
        result = ReferenceResolver.resolve_reference("@node1", state)

        assert result == {"result": "value1", "count": 5}

    def test_resolve_missing_node(self, state):
        """测试解析不存在的节点"""
        with pytest.raises(KeyError, match="not found"):
            ReferenceResolver.resolve_reference("@missing.key", state)

    def test_resolve_missing_key(self, state):
        """测试解析不存在的键"""
        result = ReferenceResolver.resolve_reference("@node1.missing", state)

        assert result is None

    def test_resolve_with_default(self, state):
        """测试带默认值的解析"""
        result = ReferenceResolver.resolve_reference(
            "@node1.missing",
            state,
            default="default_value"
        )

        assert result == "default_value"

    def test_extract_references_from_string(self):
        """测试从字符串提取引用"""
        text = "Use @node1.result and @node2.count"

        refs = ReferenceResolver.extract_references(text)

        assert refs == {"@node1.result", "@node2.count"}

    def test_extract_references_from_dict(self):
        """测试从字典提取引用"""
        data = {
            "input": "@node1.result",
            "list": ["@node2.count", "normal"],
        }

        refs = ReferenceResolver.extract_references(data)

        assert refs == {"@node1.result", "@node2.count"}

    def test_extract_references_from_list(self):
        """测试从列表提取引用"""
        data = ["@node1.result", "@node2.count", "normal"]

        refs = ReferenceResolver.extract_references(data)

        assert refs == {"@node1.result", "@node2.count"}

    def test_resolve_value_string(self, state):
        """测试解析字符串值"""
        result = ReferenceResolver.resolve_value("@node1.result", state)

        assert result == "value1"

    def test_resolve_value_dict(self, state):
        """测试解析字典值"""
        value = {
            "input": "@node1.result",
            "count": "@node1.count",
        }

        result = ReferenceResolver.resolve_value(value, state)

        assert result == {
            "input": "value1",
            "count": 5,
        }

    def test_resolve_value_list(self, state):
        """测试解析列表值"""
        value = ["@node1.result", "@node2.result", "static"]

        result = ReferenceResolver.resolve_value(value, state)

        assert result == ["value1", "value2", "static"]

    def test_resolve_value_mixed_string(self, state):
        """测试解析混合字符串"""
        value = "Result: @node1.result, Count: @node1.count"

        result = ReferenceResolver.resolve_value(value, state)

        assert result == "Result: value1, Count: 5"

    def test_resolve_value_no_resolve(self, state):
        """测试不解析引用"""
        value = "@node1.result"

        result = ReferenceResolver.resolve_value(value, state, resolve_strings=False)

        assert result == "@node1.result"


# ============================================================================
# 测试 GraphState
# ============================================================================

class TestGraphState:
    """测试图状态"""

    def test_create_state(self):
        """测试创建状态"""
        state = GraphState()

        assert len(state.node_outputs) == 0
        assert len(state.completed_nodes) == 0
        assert len(state.failed_nodes) == 0

    def test_set_and_get_output(self):
        """测试设置和获取输出"""
        state = GraphState()

        state.set_node_output("node1", {"result": "value"})

        output = state.get_node_output("node1")

        assert output is not None
        assert output.outputs == {"result": "value"}

    def test_set_completed_status(self):
        """测试设置完成状态"""
        state = GraphState()

        state.set_node_output("node1", {"result": "value"}, status="completed")

        assert state.is_completed("node1")
        assert not state.is_failed("node1")

    def test_set_failed_status(self):
        """测试设置失败状态"""
        state = GraphState()

        state.set_node_output("node1", {}, status="failed")

        assert not state.is_completed("node1")
        assert state.is_failed("node1")

    def test_get_output_value(self):
        """测试获取特定输出值"""
        state = GraphState()

        state.set_node_output("node1", {"key": "value", "count": 10})

        assert state.get_output_value("node1", "key") == "value"
        assert state.get_output_value("node1", "missing", "default") == "default"

    def test_resolve_inputs(self):
        """测试解析输入引用"""
        state = GraphState()
        state.set_node_output("node1", {"result": "value1"})
        state.completed_nodes.add("node1")

        inputs = {"input": "@node1.result"}
        resolved = state.resolve_inputs(inputs)

        assert resolved == {"input": "value1"}

    def test_resolve_inputs_no_resolve(self):
        """测试不解析输入"""
        state = GraphState()
        state.set_node_output("node1", {"result": "value1"})

        inputs = {"input": "@node1.result"}
        resolved = state.resolve_inputs(inputs, resolve_references=False)

        assert resolved == {"input": "@node1.result"}

    def test_check_dependencies(self):
        """测试检查依赖"""
        state = GraphState()
        state.completed_nodes.add("node1")
        state.completed_nodes.add("node2")

        assert state.check_dependencies(["node1", "node2"])
        assert not state.check_dependencies(["node1", "node3"])

    def test_get_pending_dependencies(self):
        """测试获取待处理依赖"""
        state = GraphState()
        state.completed_nodes.add("node1")

        pending = state.get_pending_dependencies(["node1", "node2", "node3"])

        assert pending == ["node2", "node3"]

    def test_snapshot_and_restore(self):
        """测试快照和恢复"""
        state = GraphState()
        state.set_node_output("node1", {"result": "value1"})
        state.context.set("var", "value")

        snapshot = state.snapshot()

        # 修改状态
        state.set_node_output("node2", {"result": "value2"})
        state.context.set("var", "changed")

        # 恢复快照
        state.restore(snapshot)

        assert state.get_node_output("node1") is not None
        assert state.get_node_output("node2") is None
        assert state.context.get("var") == "value"

    def test_to_dict(self):
        """测试转换为字典"""
        state = GraphState()
        state.set_node_output("node1", {"result": "value1"})
        state.completed_nodes.add("node1")

        data = state.to_dict()

        assert "node_outputs" in data
        assert "completed_nodes" in data
        assert data["node_outputs"]["node1"] == {"result": "value1"}

    def test_clear(self):
        """测试清空状态"""
        state = GraphState()
        state.set_node_output("node1", {"result": "value1"})
        state.completed_nodes.add("node1")
        state.context.set("key", "value")

        state.clear()

        assert len(state.node_outputs) == 0
        assert len(state.completed_nodes) == 0
        assert len(state.context.variables) == 0

    def test_repr(self):
        """测试字符串表示"""
        state = GraphState()
        state.set_node_output("node1", {"result": "value1"}, status="completed")
        state.set_node_output("node2", {}, status="failed")

        repr_str = repr(state)

        assert "completed=1" in repr_str
        assert "failed=1" in repr_str


# ============================================================================
# 测试工厂函数
# ============================================================================

class TestFactoryFunctions:
    """测试工厂函数"""

    def test_create_graph_state(self):
        """测试创建图状态"""
        state = create_graph_state()

        assert isinstance(state, GraphState)

    def test_create_graph_state_with_context(self):
        """测试带上下文创建图状态"""
        context = ExecutionContext(variables={"init": "value"})
        state = create_graph_state(context=context)

        assert state.context.get("init") == "value"

    def test_create_execution_context(self):
        """测试创建执行上下文"""
        context = create_execution_context()

        assert isinstance(context, ExecutionContext)

    def test_create_execution_context_with_variables(self):
        """测试带变量创建执行上下文"""
        context = create_execution_context(variables={"key": "value"})

        assert context.get("key") == "value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
