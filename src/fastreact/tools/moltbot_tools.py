"""
代码执行工具 - 安全执行 Python 代码

沙箱化执行，支持数学计算、数据处理等
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from .fn_registry import Tool

logger = logging.getLogger(__name__)


def create_code_exec_tool(timeout: int = 30) -> Tool:
    """创建代码执行工具

    Args:
        timeout: 执行超时时间（秒）
    """
    async def execute(code: str) -> str:
        """执行 Python 代码"""
        import sys
        from io import StringIO
        import traceback

        # 重定向 stdout
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        redirected_output = StringIO()
        redirected_error = StringIO()

        try:
            sys.stdout = redirected_output
            sys.stderr = redirected_error

            # 创建受限的执行环境
            safe_globals = {
                "__builtins__": {
                    # 数学函数
                    "abs": abs,
                    "min": min,
                    "max": max,
                    "sum": sum,
                    "round": round,
                    "pow": pow,
                    "len": len,
                    "range": range,
                    "enumerate": enumerate,
                    "zip": zip,
                    "map": map,
                    "filter": filter,
                    "sorted": sorted,
                    "reversed": reversed,
                    "int": int,
                    "float": float,
                    "str": str,
                    "list": list,
                    "tuple": tuple,
                    "dict": dict,
                    "set": set,
                    "bool": bool,
                    # 常用模块
                    "print": print,
                    "math": __import__("math"),
                    "datetime": __import__("datetime"),
                    "json": __import__("json"),
                    "random": __import__("random"),
                    "statistics": __import__("statistics", None),
                }
            }

            # 使用超时执行
            def run_code():
                try:
                    exec(code, safe_globals, {})
                except Exception as e:
                    print(f"Error: {str(e)}")

            # 异步超时执行
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, run_code),
                timeout=timeout
            )

            # 获取输出
            output = redirected_output.getvalue()
            error = redirected_error.getvalue()

            if output:
                return output.strip()
            elif error:
                return f"执行错误: {error.strip()}"
            else:
                return "代码执行完成（无输出）"

        except asyncio.TimeoutError:
            return f"执行超时（超过 {timeout} 秒）"
        except Exception as e:
            return f"执行失败: {str(e)}"
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    return Tool(
        name="code_exec",
        label="Code Exec",
        description="""安全执行 Python 代码，用于数学计算、数据处理等

支持功能：
- 数学计算：math 模块的所有函数（sin, cos, sqrt, pi 等）
- 数据处理：list, dict, set, map, filter 等内置函数
- 日期时间：datetime 模块
- JSON 处理：json 模块
- 随机数：random 模块
- 统计：statistics 模块

限制：
- 执行超时：30 秒
- 禁用文件 I/O
- 禁用网络访问
- 禁用系统调用

示例：
- 计算：math.sqrt(16) + math.pi
- 数据：sorted([3, 1, 4, 1, 5])
- 日期：datetime.datetime.now().strftime('%Y-%m-%d')
- 列表推导：[x*x for x in range(10)]""",
        parameters={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码"
                }
            },
            "required": ["code"]
        },
        execute=execute,
    )


def create_text_analysis_tool() -> Tool:
    """创建文本分析工具"""
    async def execute(text: str, operation: str = "count") -> str:
        """分析文本"""
        if operation == "count":
            chars = len(text)
            words = len(text.split())
            lines = len(text.split('\n'))
            return f"文本统计：字符数 {chars}，单词数 {words}，行数 {lines}"

        elif operation == "length":
            return f"文本长度：{len(text)} 字符"

        elif operation == "uppercase":
            return text.upper()

        elif operation == "lowercase":
            return text.lower()

        elif operation == "reverse":
            return text[::-1]

        elif operation == "words":
            words = text.split()
            return f"单词列表（共 {len(words)} 个）：\n" + "\n".join(f"  {i+1}. {w}" for i, w in enumerate(words[:20]))

        else:
            return f"未知操作: {operation}"

    return Tool(
        name="text_analysis",
        label="Text Analysis",
        description="""文本分析和处理工具

支持操作：
- count: 统计字符、单词、行数
- length: 计算字符长度
- uppercase: 转为大写
- lowercase: 转为小写
- reverse: 反转文本
- words: 提取单词列表""",
        parameters={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "要分析的文本"
                },
                "operation": {
                    "type": "string",
                    "enum": ["count", "length", "uppercase", "lowercase", "reverse", "words"],
                    "description": "操作类型"
                }
            },
            "required": ["text", "operation"]
        },
        execute=execute,
    )


def create_unit_converter_tool() -> Tool:
    """创建单位转换工具"""
    async def execute(value: float, from_unit: str, to_unit: str, category: str = "length") -> str:
        """单位转换"""
        conversions = {
            "length": {
                "m": 1,
                "km": 1000,
                "cm": 0.01,
                "mm": 0.001,
                "inch": 0.0254,
                "ft": 0.3048,
                "yd": 0.9144,
                "mile": 1609.34,
            },
            "weight": {
                "kg": 1,
                "g": 0.001,
                "mg": 0.000001,
                "lb": 0.453592,
                "oz": 0.0283495,
                "ton": 1000,
            },
            "temperature": {
                # 温度需要特殊处理
                "c": "celsius",
                "f": "fahrenheit",
                "k": "kelvin",
            }
        }

        if category == "temperature":
            # 温度转换
            if from_unit == "c" and to_unit == "f":
                result = (value * 9/5) + 32
            elif from_unit == "f" and to_unit == "c":
                result = (value - 32) * 5/9
            elif from_unit == "c" and to_unit == "k":
                result = value + 273.15
            elif from_unit == "k" and to_unit == "c":
                result = value - 273.15
            else:
                return f"不支持的温度转换: {from_unit} -> {to_unit}"
        else:
            # 普通单位转换
            if category not in conversions:
                return f"不支持的类别: {category}"
            if from_unit not in conversions[category]:
                return f"不支持的源单位: {from_unit}"
            if to_unit not in conversions[category]:
                return f"不支持的目标单位: {to_unit}"

            # 转换为基准单位，再转换为目标单位
            base_value = value * conversions[category][from_unit]
            result = base_value / conversions[category][to_unit]

        return f"{value} {from_unit} = {result:.4f} {to_unit}"

    return Tool(
        name="unit_converter",
        label="Unit Converter",
        description="""单位转换工具

支持类别：
- length: 长度（m, km, cm, mm, inch, ft, yd, mile）
- weight: 重量（kg, g, mg, lb, oz, ton）
- temperature: 温度（c, f, k）

示例：
- 100 米转千米：value=100, from_unit="m", to_unit="km", category="length"
- 摄氏转华氏：value=25, from_unit="c", to_unit="f", category="temperature"
- 磅转千克：value=150, from_unit="lb", to_unit="kg", category="weight" """,
        parameters={
            "type": "object",
            "properties": {
                "value": {
                    "type": "number",
                    "description": "要转换的数值"
                },
                "from_unit": {
                    "type": "string",
                    "description": "源单位"
                },
                "to_unit": {
                    "type": "string",
                    "description": "目标单位"
                },
                "category": {
                    "type": "string",
                    "enum": ["length", "weight", "temperature"],
                    "description": "单位类别",
                    "default": "length"
                }
            },
            "required": ["value", "from_unit", "to_unit"]
        },
        execute=execute,
    )


def create_moltbot_style_tools() -> list:
    """创建 moltbot 风格的工具集合"""
    return [
        create_code_exec_tool(),
        create_text_analysis_tool(),
        create_unit_converter_tool(),
    ]
