"""
测试计算器工具

测试CalculatorTool的所有功能
"""

import pytest
from fastreact.tools.calculator import CalculatorTool


class TestCalculatorTool:
    """测试计算器工具"""

    def test_tool_initialization(self):
        """测试工具初始化"""
        calc = CalculatorTool()

        assert calc.name == "CalculatorTool"
        assert "数学计算" in calc.description
        assert "expression" in calc.parameters["properties"]

    @pytest.mark.asyncio
    async def test_basic_addition(self):
        """测试基本加法"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="2 + 2")

        assert "✅" in result
        assert "4" in result

    @pytest.mark.asyncio
    async def test_basic_subtraction(self):
        """测试基本减法"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="10 - 5")

        assert "✅" in result
        assert "5" in result

    @pytest.mark.asyncio
    async def test_basic_multiplication(self):
        """测试基本乘法"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="3 * 4")

        assert "✅" in result
        assert "12" in result

    @pytest.mark.asyncio
    async def test_basic_division(self):
        """测试基本除法"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="20 / 4")

        assert "✅" in result
        assert "5" in result

    @pytest.mark.asyncio
    async def test_complex_expression(self):
        """测试复杂表达式"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="(15 + 25) * 2")

        assert "✅" in result
        assert "80" in result

    @pytest.mark.asyncio
    async def test_power_operator(self):
        """测试幂运算"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="2 ** 8")

        assert "✅" in result
        assert "256" in result

    @pytest.mark.asyncio
    async def test_pow_function(self):
        """测试pow函数"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="pow(2, 10)")

        assert "✅" in result
        assert "1024" in result

    @pytest.mark.asyncio
    async def test_abs_function(self):
        """测试abs函数"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="abs(-5)")

        assert "✅" in result
        assert "5" in result

    @pytest.mark.asyncio
    async def test_min_function(self):
        """测试min函数"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="min(1, 2, 3, 4, 5)")

        assert "✅" in result
        assert "1" in result

    @pytest.mark.asyncio
    async def test_max_function(self):
        """测试max函数"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="max(1, 2, 3, 4, 5)")

        assert "✅" in result
        assert "5" in result

    @pytest.mark.asyncio
    async def test_sum_function(self):
        """测试sum函数"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="sum([1, 2, 3, 4, 5])")

        assert "✅" in result
        assert "15" in result

    @pytest.mark.asyncio
    async def test_round_function(self):
        """测试round函数"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="round(3.14159, 2)")

        assert "✅" in result
        assert "3.14" in result

    @pytest.mark.asyncio
    async def test_division_by_zero(self):
        """测试除零错误"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="10 / 0")

        assert "❌" in result
        assert "除零错误" in result

    @pytest.mark.asyncio
    async def test_invalid_expression(self):
        """测试无效表达式"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="2 + * 3")

        assert "❌" in result
        assert "计算错误" in result

    @pytest.mark.asyncio
    async def test_empty_expression(self):
        """测试空表达式"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="")

        assert "❌" in result
        assert "计算错误" in result

    @pytest.mark.asyncio
    async def test_negative_numbers(self):
        """测试负数运算"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="-5 + 3")

        assert "✅" in result
        assert "-2" in result

    @pytest.mark.asyncio
    async def test_float_operations(self):
        """测试浮点数运算"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="3.14 * 2")

        assert "✅" in result
        assert "6.28" in result

    @pytest.mark.asyncio
    async def test_operator_precedence(self):
        """测试运算符优先级"""
        calc = CalculatorTool()

        # 乘法优先于加法
        result1 = await calc.execute_async(expression="2 + 3 * 4")
        assert "✅" in result1
        assert "14" in result1

        # 括号改变优先级
        result2 = await calc.execute_async(expression="(2 + 3) * 4")
        assert "✅" in result2
        assert "20" in result2

    @pytest.mark.asyncio
    async def test_nested_parentheses(self):
        """测试嵌套括号"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="((2 + 3) * (4 - 1))")

        assert "✅" in result
        assert "15" in result

    @pytest.mark.asyncio
    async def test_complex_calculation(self):
        """测试复杂计算"""
        calc = CalculatorTool()
        result = await calc.execute_async(
            expression="(pow(2, 3) + abs(-5)) * max(1, 2, 3)"
        )

        assert "✅" in result
        # (8 + 5) * 3 = 39
        assert "39" in result

    @pytest.mark.asyncio
    async def test_safety_no_dangerous_functions(self):
        """测试安全性：阻止危险函数"""
        calc = CalculatorTool()

        # 尝试使用危险函数（应该失败）
        result = await calc.execute_async(expression="__import__('os').system('ls')")

        assert "❌" in result
        assert "计算错误" in result

    @pytest.mark.asyncio
    async def test_safety_no_builtin_access(self):
        """测试安全性：阻止访问builtins"""
        calc = CalculatorTool()

        # 尝试直接访问builtins（应该失败）
        result = await calc.execute_async(expression="print('hello')")

        assert "❌" in result
        assert "计算错误" in result

    def test_sync_execution(self):
        """测试同步执行"""
        calc = CalculatorTool()
        result = calc.execute(expression="5 + 5")

        assert "✅" in result
        assert "10" in result

    def test_parameters_schema(self):
        """测试参数schema"""
        calc = CalculatorTool()
        schema = calc.parameters

        assert schema["type"] == "object"
        assert "expression" in schema["properties"]
        assert schema["properties"]["expression"]["type"] == "string"
        assert "expression" in schema["required"]

    def test_tool_description(self):
        """测试工具描述"""
        calc = CalculatorTool()
        description = calc.description

        assert "数学计算" in description
        assert "+" in description
        assert "-" in description
        assert "*" in description
        assert "/" in description

    @pytest.mark.asyncio
    async def test_large_numbers(self):
        """测试大数运算"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="999999 * 999999")

        assert "✅" in result
        assert "999998000001" in result

    @pytest.mark.asyncio
    async def test_decimal_operations(self):
        """测试小数运算精度"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="0.1 + 0.2")

        assert "✅" in result
        # Python浮点数精度问题
        assert "0.3" in result or "0.300" in result

    @pytest.mark.asyncio
    async def test_modulo_operation(self):
        """测试取模运算"""
        calc = CalculatorTool()
        result = await calc.execute_async(expression="10 % 3")

        assert "✅" in result
        assert "1" in result
