"""
计算器工具

执行数学计算
"""

import asyncio
from ..core.tool import Tool


class CalculatorTool(Tool):
    """
    计算器工具

    支持基本的数学运算：加减乘除、幂运算、括号等
    """

    def _get_description(self) -> str:
        return """执行数学计算

支持操作：
- 基本运算：+, -, *, /
- 幂运算：** 或 pow()
- 括号：()
- 数学函数：abs(), min(), max(), sum()
- 示例："2 + 2", "(15 + 25) * 2", "2 ** 8"
"""

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '2 + 2' 或 '(15 + 25) * 2'",
                }
            },
            "required": ["expression"],
        }

    async def execute_async(self, expression: str) -> str:
        """异步执行计算"""
        # 模拟异步（实际计算是同步的）
        await asyncio.sleep(0)

        try:
            # 安全性检查：只允许数学表达式
            allowed_names = {
                "abs": abs,
                "min": min,
                "max": max,
                "sum": sum,
                "pow": pow,
                "round": round,
            }

            # 使用eval计算（限制可用函数）
            result = eval(expression, {"__builtins__": {}}, allowed_names)

            return f"✅ 计算结果: {expression} = {result}"

        except ZeroDivisionError:
            return f"❌ 计算错误: 除零错误"
        except Exception as e:
            return f"❌ 计算错误: {str(e)}"
