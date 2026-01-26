"""
测试Python工具

测试Python代码执行和计算表达式工具
"""

import pytest
from fastreact.tools.python_tools import run_python_code, calculate_expression


class TestRunPythonCode:
    """测试run_python_code工具"""

    def test_simple_print(self):
        """测试简单print语句"""
        result = run_python_code(code='print("Hello, World!")')

        assert result["status"] == "success"
        assert "Hello, World!" in result["output"]

    def test_variable_definition(self):
        """测试变量定义"""
        result = run_python_code(code='x = 42\nprint(x)')

        assert result["status"] == "success"
        assert "42" in result["output"]

    def test_basic_arithmetic(self):
        """测试基本算术运算"""
        result = run_python_code(code='print(2 + 2)')

        assert result["status"] == "success"
        assert "4" in result["output"]

    def test_list_operations(self):
        """测试列表操作"""
        result = run_python_code(
            code='numbers = [1, 2, 3, 4, 5]\nprint(sum(numbers))'
        )

        assert result["status"] == "success"
        assert "15" in result["output"]

    def test_loop(self):
        """测试循环"""
        result = run_python_code(
            code='for i in range(5):\n    print(i)'
        )

        assert result["status"] == "success"
        for i in range(5):
            assert str(i) in result["output"]

    def test_function_definition(self):
        """测试函数定义"""
        result = run_python_code(
            code='def add(a, b):\n    return a + b\nprint(add(3, 4))'
        )

        assert result["status"] == "success"
        assert "7" in result["output"]

    def test_syntax_error(self):
        """测试语法错误"""
        result = run_python_code(code='print("unclosed string)')

        assert result["status"] == "error"
        assert "SyntaxError" in result.get("error", "") or "syntax" in result.get("error", "").lower()

    def test_runtime_error(self):
        """测试运行时错误"""
        result = run_python_code(code='print(1 / 0)')

        assert result["status"] == "error"
        assert "ZeroDivisionError" in result.get("error", "")

    def test_empty_code(self):
        """测试空代码"""
        result = run_python_code(code='')

        assert result["status"] == "success"
        assert result["output"] == "" or result["output"] is None


class TestCalculateExpression:
    """测试calculate_expression工具"""

    def test_simple_addition(self):
        """测试简单加法"""
        result = calculate_expression(expression="2 + 2")

        assert result["status"] == "success"
        assert result["result"] == 4

    def test_simple_subtraction(self):
        """测试简单减法"""
        result = calculate_expression(expression="10 - 4")

        assert result["status"] == "success"
        assert result["result"] == 6

    def test_simple_multiplication(self):
        """测试简单乘法"""
        result = calculate_expression(expression="3 * 7")

        assert result["status"] == "success"
        assert result["result"] == 21

    def test_simple_division(self):
        """测试简单除法"""
        result = calculate_expression(expression="20 / 4")

        assert result["status"] == "success"
        assert result["result"] == 5.0

    def test_complex_expression(self):
        """测试复杂表达式"""
        result = calculate_expression(expression="(2 + 3) * 4")

        assert result["status"] == "success"
        assert result["result"] == 20

    def test_power_operator(self):
        """测试幂运算"""
        result = calculate_expression(expression="2 ** 10")

        assert result["status"] == "success"
        assert result["result"] == 1024

    def test_division_by_zero(self):
        """测试除零错误"""
        result = calculate_expression(expression="10 / 0")

        assert result["status"] == "error"
        assert "division by zero" in result["error"].lower()

    def test_invalid_expression(self):
        """测试无效表达式"""
        result = calculate_expression(expression="2 + * 3")

        assert result["status"] == "error"

    def test_empty_expression(self):
        """测试空表达式"""
        result = calculate_expression(expression="")

        assert result["status"] == "error"


class TestPythonToolsIntegration:
    """测试Python工具集成"""

    def test_both_tools_work(self):
        """测试两个工具都能正常工作"""
        # 测试run_python_code
        result1 = run_python_code(code='print(2 + 2)')
        assert result1["status"] == "success"

        # 测试calculate_expression
        result2 = calculate_expression(expression="2 + 2")
        assert result2["status"] == "success"
        assert result2["result"] == 4
