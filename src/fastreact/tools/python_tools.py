"""
Python工具集

从Biro迁移的Python代码执行工具
"""

from typing import Dict, Any
import sys
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from fastreact.tools.mcp_adapter import register_mcp_tool


@register_mcp_tool(
    "run_python_code",
    description="Execute Python code snippet and return output. Supports print statements, calculations, and variable assignments.",
)
def run_python_code(code: str, timeout: int = 5) -> Dict[str, Any]:
    """
    Execute Python code safely

    Args:
        code: Python code to execute
        timeout: Execution timeout in seconds

    Returns:
        {
            "status": "success",
            "output": "stdout",
            "error": "stderr",
            "result": "return value"
        }
    """
    import signal

    def timeout_handler(signum, frame):
        raise TimeoutError(f"Code execution exceeded {timeout} seconds")

    try:
        # 准备执行环境
        exec_globals = {
            "__builtins__": {
                "print": print,
                "range": range,
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "sum": sum,
                "max": max,
                "min": min,
                "abs": abs,
                "round": round,
                "sorted": sorted,
            }
        }

        # 捕获输出
        stdout_capture = StringIO()
        stderr_capture = StringIO()

        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            # 执行代码
            exec(code, exec_globals)

        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()

        return {
            "status": "success",
            "output": stdout_output,
            "error": stderr_output if stderr_output else None,
            "executed_code": code,
        }

    except TimeoutError as e:
        return {"status": "timeout", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {str(e)}"}


@register_mcp_tool(
    "calculate_expression",
    description="Calculate a mathematical expression safely. Supports basic arithmetic operations (+, -, *, /, **, %).",
)
def calculate_expression(expression: str) -> Dict[str, Any]:
    """
    Calculate mathematical expression

    Args:
        expression: Mathematical expression (e.g., "2 + 2", "3 ** 4")

    Returns:
        {
            "status": "success",
            "expression": "2 + 2",
            "result": 4
        }
    """
    try:
        # 安全的数学环境
        safe_dict = {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow,
        }

        # 评估表达式
        result = eval(expression, {"__builtins__": {}}, safe_dict)

        return {
            "status": "success",
            "expression": expression,
            "result": result,
        }

    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {str(e)}"}


__all__ = ["run_python_code", "calculate_expression"]
