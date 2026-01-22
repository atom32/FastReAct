"""
FastReAct + GraphRAG 集成测试

测试MCP适配器、GraphRAG工具和FastReAct引擎的集成
"""

import pytest
import os
from fastreact.tools.mcp_adapter import (
    MCPToolWrapper,
    MCPToolRegistry,
    register_mcp_tool,
    get_global_registry,
    export_tools_to_fastreact,
)


class TestMCPAdapter:
    """测试MCP适配器"""

    def test_register_function(self):
        """测试注册函数为工具"""

        # 定义一个简单的测试函数
        def test_tool(param1: str, param2: int = 10) -> dict:
            """测试工具"""
            return {"param1": param1, "param2": param2}

        # 注册
        registry = MCPToolRegistry()
        tool = registry.register_function("test_tool", test_tool)

        # 验证
        assert tool.name == "test_tool"
        assert tool.description == "测试工具"
        assert "param1" in tool.parameters["properties"]
        assert "param2" in tool.parameters["properties"]

    def test_decorator_registration(self):
        """测试装饰器注册"""

        # 清空全局注册表
        global _global_registry
        _global_registry = MCPToolRegistry()

        # 使用装饰器
        @register_mcp_tool("decorator_test")
        def my_tool(value: str) -> dict:
            """装饰器测试工具"""
            return {"value": value}

        # 验证已注册
        registry = get_global_registry()
        tool = registry.get_tool("decorator_test")
        assert tool is not None
        assert tool.name == "decorator_test"

    @pytest.mark.asyncio
    async def test_tool_execution(self):
        """测试工具执行"""

        async def async_tool(x: int, y: int) -> int:
            """异步工具"""
            return x + y

        # 包装为Tool
        tool = MCPToolWrapper("async_add", async_tool)

        # 执行
        result = await tool.execute_async(x=5, y=3)

        assert result == 8


class TestGraphRAGTools:
    """测试GraphRAG工具"""

    def test_query_graph_rag_tool_exists(self):
        """测试query_graph_rag工具已注册"""
        from fastreact.tools.graph_rag_tools import query_graph_rag

        # 检查函数存在
        assert callable(query_graph_rag)

    def test_analyze_relationships_tool_exists(self):
        """测试analyze_relationships工具已注册"""
        from fastreact.tools.graph_rag_tools import analyze_relationships

        assert callable(analyze_relationships)

    def test_multi_hop_reasoning_tool_exists(self):
        """测试multi_hop_reasoning工具已注册"""
        from fastreact.tools.graph_rag_tools import multi_hop_reasoning

        assert callable(multi_hop_reasoning)

    def test_knowledge_extraction_tool_exists(self):
        """测试knowledge_extraction工具已注册"""
        from fastreact.tools.graph_rag_tools import knowledge_extraction

        assert callable(knowledge_extraction)

    def test_check_graph_rag_config_tool_exists(self):
        """测试check_graph_rag_config工具已注册"""
        from fastreact.tools.graph_rag_tools import check_graph_rag_config

        assert callable(check_graph_rag_config)

    @pytest.mark.skipif(
        not os.getenv("HIPPO_RAG_URL"),
        reason="HIPPO_RAG_URL not set",
    )
    def test_check_graph_rag_config_real(self):
        """测试真实的GraphRAG配置检查"""
        from fastreact.tools.graph_rag_tools import check_graph_rag_config

        result = check_graph_rag_config()

        assert "status" in result
        assert "hippo_rag_url" in result
        print(f"\nGraphRAG配置检查结果: {result}")


class TestPythonTools:
    """测试Python工具"""

    def test_calculate_expression_tool_exists(self):
        """测试calculate_expression工具"""
        from fastreact.tools.python_tools import calculate_expression

        assert callable(calculate_expression)

    def test_calculate_expression_simple(self):
        """测试简单计算"""
        from fastreact.tools.python_tools import calculate_expression

        result = calculate_expression("2 + 2")

        assert result["status"] == "success"
        assert result["result"] == 4

    def test_calculate_expression_complex(self):
        """测试复杂计算"""
        from fastreact.tools.python_tools import calculate_expression

        result = calculate_expression("3 ** 4 + 5 * 2")

        assert result["status"] == "success"
        assert result["result"] == 81 + 10  # 91

    def test_run_python_code_tool_exists(self):
        """测试run_python_code工具"""
        from fastreact.tools.python_tools import run_python_code

        assert callable(run_python_code)

    def test_run_python_code_simple(self):
        """测试简单代码执行"""
        from fastreact.tools.python_tools import run_python_code

        result = run_python_code("x = 5\nprint(x)")

        assert result["status"] == "success"
        assert "5" in result["output"]


class TestToolExport:
    """测试工具导出"""

    def test_export_tools_to_fastreact(self):
        """测试导出工具到FastReAct格式"""
        tools = export_tools_to_fastreact()

        # 验证有工具被导出
        assert len(tools) > 0

        # 验证工具类型
        from fastreact.core.tool import Tool

        for tool in tools:
            assert isinstance(tool, Tool)

        # 验证GraphRAG工具存在
        tool_names = [tool.name for tool in tools]
        assert "query_graph_rag" in tool_names
        assert "analyze_relationships" in tool_names
        assert "multi_hop_reasoning" in tool_names


class TestFastReActIntegration:
    """测试FastReAct引擎集成"""

    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set",
    )
    @pytest.mark.asyncio
    async def test_fastreact_with_graphrag_tools(self):
        """测试FastReAct引擎加载GraphRAG工具"""
        from fastreact.core.engine import FastReAct

        # 创建引擎
        agent = FastReAct(
            api_key=os.getenv("OPENAI_API_KEY", "sk-test"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            max_iterations=2,
        )

        # 注册GraphRAG工具
        tools = export_tools_to_fastreact()
        for tool in tools:
            agent.register_tool(tool)

        # 验证工具已注册
        assert len(agent.tools) > 0
        assert "query_graph_rag" in agent.tools

        await agent.close()

    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY") or not os.getenv("HIPPO_RAG_URL"),
        reason="OPENAI_API_KEY or HIPPO_RAG_URL not set",
    )
    @pytest.mark.asyncio
    async def test_fastreact_graphrag_query(self):
        """测试完整的FastReAct + GraphRAG查询"""
        from fastreact.core.engine import FastReAct

        # 创建引擎
        agent = FastReAct(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            max_iterations=5,
            enable_cache=True,
        )

        # 注册工具
        for tool in export_tools_to_fastreact():
            agent.register_tool(tool)

        # 执行简单查询
        result = await agent.run_async(
            query="检查GraphRAG配置状态",
        )

        # 验证返回结构
        assert "answer" in result
        assert "steps" in result
        assert "stats" in result

        print(f"\n查询结果: {result['answer']}")
        print(f"执行步数: {len(result['steps'])}")
        print(f"统计信息: {result['stats']}")

        await agent.close()


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
