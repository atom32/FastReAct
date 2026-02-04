"""
示例3: 自定义工具

演示如何创建自定义工具
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fastreact import FastReAct, Tool
from typing import Dict, Any


# ===== 自定义工具1: 数据库查询工具 =====

class DatabaseTool(Tool):
    """数据库查询工具（模拟）"""

    def _get_description(self) -> str:
        return """查询数据库中的信息

可以查询：
- 用户信息
- 订单数据
- 产品列表
- 统计数据
"""

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "table": {
                    "type": "string",
                    "description": "表名，如 'users' 或 'orders'",
                },
                "condition": {
                    "type": "string",
                    "description": "查询条件，如 'id=1' 或 'status=active'",
                }
            },
            "required": ["table"],
        }

    async def execute_async(self, table: str, condition: str = "") -> str:
        """异步查询数据库"""
        await asyncio.sleep(0.05)  # 模拟数据库查询延迟

        # 模拟数据库数据
        mock_data = {
            "users": [
                {"id": 1, "name": "张三", "age": 25},
                {"id": 2, "name": "李四", "age": 30},
            ],
            "orders": [
                {"id": 101, "user_id": 1, "amount": 1000},
                {"id": 102, "user_id": 2, "amount": 2000},
            ],
            "products": [
                {"id": 1, "name": "iPhone", "price": 6999},
                {"id": 2, "name": "MacBook", "price": 12999},
            ],
        }

        data = mock_data.get(table, [])
        output = f"🗄️ 查询表 '{table}'"

        if condition:
            output += f" 条件: {condition}"

        output += f"\n\n找到 {len(data)} 条记录:\n"

        for record in data:
            output += f"  - {record}\n"

        return output


# ===== 自定义工具2: 邮件发送工具 =====

class EmailTool(Tool):
    """邮件发送工具（模拟）"""

    def _get_description(self) -> str:
        return """发送邮件

可以发送：
- 通知邮件
- 营销邮件
- 系统邮件
"""

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "收件人邮箱",
                },
                "subject": {
                    "type": "string",
                    "description": "邮件主题",
                },
                "body": {
                    "type": "string",
                    "description": "邮件正文",
                }
            },
            "required": ["to", "subject", "body"],
        }

    async def execute_async(self, to: str, subject: str, body: str) -> str:
        """异步发送邮件"""
        await asyncio.sleep(0.1)  # 模拟发送延迟

        return f"""[OK] 邮件已发送

📧 收件人: {to}
📋 主题: {subject}
📄 正文长度: {len(body)} 字符
🕐 发送时间: {asyncio.get_event_loop().time()}
"""


# ===== 主函数 =====

async def main():
    """主函数"""
    print("=" * 60)
    print("FastReAct 自定义工具示例")
    print("=" * 60)

    # 1. 创建ReACT引擎（使用自定义工具）
    react = FastReAct(
        api_key="your-api-key",
        base_url="https://api.openai.com/v1",
        model="gpt-4",
        tools=[DatabaseTool(), EmailTool()],
        enable_cache=True,
    )

    # 2. 查询示例
    queries = [
        "查询users表中的所有用户",
        "给admin@example.com发一封邮件，主题是'系统报告'，内容是'系统运行正常'",
    ]

    for query in queries:
        print(f"\n[NOTE] 查询: {query}\n")
        print("-" * 60)

        result = await react.run_async(query=query)

        print(f"\n[OK] 答案: {result['answer']}")

    await react.close()


if __name__ == "__main__":
    asyncio.run(main())
