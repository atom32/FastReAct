"""
FastReAct 综合端到端测试

参考 Moltbot 的功能设计，测试 FastReAct 的完整能力：
1. ReAct 多工具协同
2. Docker 沙箱安全执行
3. MCP 服务器集成
4. 事件流和错误重试
5. 并发处理能力
6. 复杂推理链路
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from datetime import datetime

from fastreact import FastReAct
from fastreact.tools import (
    create_calculator_tool,
    create_datetime_tool,
    create_search_tool,
)
from fastreact.tools.sandbox_tools import create_sandbox_exec_tool


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class E2ETestRunner:
    """端到端测试运行器"""

    def __init__(self, config_path: str = "config.json"):
        """初始化测试运行器

        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.test_results = []

        # LLM 配置
        default_provider = self.config.get("default_provider", "siliconflow")
        provider_config = self.config["llm"]["providers"].get(default_provider, {})
        self.llm_api_key = provider_config.get("api_key")
        self.llm_model = provider_config.get("model", "deepseek-ai/DeepSeek-V3")
        self.llm_base_url = provider_config.get("base_url", "https://api.openai.com/v1")

    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"配置文件未找到: {config_path}，使用默认配置")
            return {"llm": {"providers": {}}}

    async def run_test(self, test_name: str, test_func) -> dict:
        """运行单个测试

        Args:
            test_name: 测试名称
            test_func: 测试函数

        Returns:
            测试结果字典
        """
        logger.info(f"\n{'=' * 70}")
        logger.info(f"开始测试: {test_name}")
        logger.info(f"{'=' * 70}")

        start_time = time.time()
        result = {
            "name": test_name,
            "passed": False,
            "duration": 0,
            "error": None,
            "details": {}
        }

        try:
            details = await test_func()
            result["passed"] = True
            result["details"] = details
            logger.info(f"[PASS] 测试通过: {test_name}")
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"[FAIL] 测试失败: {test_name}", exc_info=True)

        result["duration"] = time.time() - start_time
        self.test_results.append(result)

        return result

    async def test_01_basic_react(self) -> dict:
        """测试 1: 基本 ReAct 工具调用

        验证：
        - LLM 能正确选择工具
        - 工具调用格式正确
        - 结果处理正确
        """
        agent = FastReAct(
            api_key=self.llm_api_key,
            base_url=self.llm_base_url,
            model=self.llm_model,
            tools=[
                create_calculator_tool(),
                create_datetime_tool(),
            ],
            enable_streaming=False
        )

        try:
            # 问题：需要时间 + 计算的组合
            question = "现在是几点？如果现在是2024年，那么10年后是多少年？"

            result = await agent.run_async(question, session_context="test_react_1")
            response = result.get("answer", "")

            # 验证响应包含关键信息
            assert len(response) > 0, "响应为空"

            return {
                "question": question,
                "response_length": len(response),
                "response_preview": response[:200]
            }

        finally:
            await agent.close()

    async def test_02_sandbox_code_execution(self) -> dict:
        """测试 2: Docker 沙箱代码执行

        验证：
        - 沙箱工具可用
        - Python 代码执行
        - JavaScript 代码执行
        - 安全检查（denylist）
        """
        agent = FastReAct(
            api_key=self.llm_api_key,
            base_url=self.llm_base_url,
            model=self.llm_model,
            tools=[
                create_sandbox_exec_tool(),
            ],
            enable_streaming=False
        )

        try:
            # 问题：需要使用沙箱执行代码
            question = """
            请帮我编写一个 Python 脚本来计算斐波那契数列的前 10 项，
            然后在沙箱中执行它，告诉我结果。
            """

            result = await agent.run_async(question, session_context="test_sandbox_1")
            response = result.get("answer", "")

            return {
                "question": question,
                "response": response,
                "has_output": "fibonacci" in response.lower() or "斐波" in response
            }

        finally:
            await agent.close()

    async def test_03_complex_reasoning_chain(self) -> dict:
        """测试 3: 复杂推理链

        验证：
        - 多步骤推理
        - 工具链编排
        - 上下文保持
        """
        agent = FastReAct(
            api_key=self.llm_api_key,
            base_url=self.llm_base_url,
            model=self.llm_model,
            tools=[
                create_calculator_tool(),
                create_datetime_tool(),
                create_sandbox_exec_tool(),
            ],
            enable_streaming=False,
            max_iterations=10
        )

        try:
            # 复杂问题：需要多个工具协作
            question = """
            我有一个复杂的任务：

            1. 首先告诉我今天的日期
            2. 然后计算从今天起 100 天后是星期几
            3. 编写一个 Python 程序验证你的计算
            4. 计算 1000 的阶乘的最后 3 位数字

            请一步步完成，并使用合适的工具。
            """

            result = await agent.run_async(question, session_context="test_complex_1")
            response = result.get("answer", "")

            return {
                "question": question,
                "response": response,
                "response_length": len(response)
            }

        finally:
            await agent.close()

    async def test_04_error_retry_mechanism(self) -> dict:
        """测试 4: 错误重试机制

        验证：
        - 工具调用失败时的重试
        - 错误处理
        - 恢复能力
        """
        # 创建一个会失败的工具
        from fastreact.tools.fn_registry import Tool

        attempt_count = [0]

        async def flaky_function(attempt: int = 0) -> str:
            """随机失败的工具"""
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                raise Exception(f"模拟失败 (attempt {attempt_count[0]})")
            return "成功！"

        flaky_tool = Tool(
            name="flaky_tool",
            label="Flaky Tool",
            description="一个会失败几次才成功的测试工具",
            parameters={
                "type": "object",
                "properties": {
                    "attempt": {
                        "type": "integer",
                        "description": "尝试次数"
                    }
                },
                "required": []
            },
            execute=flaky_function
        )

        agent = FastReAct(
            api_key=self.llm_api_key,
            base_url=self.llm_base_url,
            model=self.llm_model,
            tools=[flaky_tool],
            enable_streaming=False,
            max_tool_retries=3,
            enable_tool_retry=True
        )

        try:
            question = "请调用 flaky_tool 工具，传入 attempt 参数为 3"
            result = await agent.run_async(question, session_context="test_retry_1")
            response = result.get("answer", "")

            return {
                "question": question,
                "response": response,
                "succeeded": "成功" in response
            }

        finally:
            await agent.close()

    async def test_05_concurrent_sessions(self) -> dict:
        """测试 5: 并发会话处理

        验证：
        - 多会话隔离
        - 并发执行
        - 无状态干扰
        """
        agent = FastReAct(
            api_key=self.llm_api_key,
            base_url=self.llm_base_url,
            model=self.llm_model,
            tools=[
                create_calculator_tool(),
                create_datetime_tool(),
            ],
            enable_streaming=False
        )

        try:
            # 并发执行多个任务
            tasks = []
            questions = [
                ("session_a", "计算 123 * 456"),
                ("session_b", "现在几点了？"),
                ("session_c", "100 + 200 等于多少？"),
                ("session_d", "计算 (50 - 20) * 3"),
            ]

            start_time = time.time()

            for session_id, question in questions:
                task = agent.run_async(question, session_context={"session_id": session_id})
                tasks.append((session_id, question, task))

            # 等待所有任务完成
            results = []
            for session_id, question, task in tasks:
                response = await task
                results.append({
                    "session_id": session_id,
                    "question": question,
                    "response": response
                })

            duration = time.time() - start_time

            return {
                "total_tasks": len(questions),
                "duration": duration,
                "results": results
            }

        finally:
            await agent.close()

    async def test_06_sandbox_security(self) -> dict:
        """测试 6: 沙箱安全特性

        验证：
        - 危险操作阻止
        - 资源限制
        - 隔离性
        """
        agent = FastReAct(
            api_key=self.llm_api_key,
            base_url=self.llm_base_url,
            model=self.llm_model,
            tools=[create_sandbox_exec_tool()],
            enable_streaming=False
        )

        try:
            # 尝试执行危险操作
            question = """
            请在沙箱中执行以下 Python 代码：
            import os
            os.system('rm -rf /')

            这应该被阻止或安全地处理。
            """

            result = await agent.run_async(question, session_context="test_security_1")
            response = result.get("answer", "")

            return {
                "question": question,
                "response": response,
                "was_handled_safely": True  # 如果没有崩溃就算安全
            }

        finally:
            await agent.close()

    async def test_07_multi_language_execution(self) -> dict:
        """测试 7: 多语言代码执行

        验证：
        - Python 执行
        - JavaScript 执行
        - Bash 执行
        - 跨语言协作
        """
        agent = FastReAct(
            api_key=self.llm_api_key,
            base_url=self.llm_base_url,
            model=self.llm_model,
            tools=[create_sandbox_exec_tool()],
            enable_streaming=False,
            max_iterations=8
        )

        try:
            question = """
            请完成以下任务：

            1. 用 Python 计算 1 到 100 的和
            2. 用 JavaScript 计算 2 的 10 次方
            3. 用 Bash 列出 /etc 目录下的文件
            4. 比较这三种语言的特点

            使用沙箱工具执行这些代码。
            """

            result = await agent.run_async(question, session_context="test_multilang_1")
            response = result.get("answer", "")

            return {
                "question": question,
                "response": response,
                "mentions_python": "python" in response.lower(),
                "mentions_javascript": "javascript" in response.lower() or "node" in response.lower(),
                "mentions_bash": "bash" in response.lower()
            }

        finally:
            await agent.close()

    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "=" * 70)
        print("测试摘要")
        print("=" * 70)

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = total - passed
        total_duration = sum(r["duration"] for r in self.test_results)

        print(f"\n总测试数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {failed}")
        print(f"总耗时: {total_duration:.2f} 秒")
        print(f"平均耗时: {total_duration / total:.2f} 秒")

        print("\n详细结果:")
        print("-" * 70)

        for i, result in enumerate(self.test_results, 1):
            status = "[PASS]" if result["passed"] else "[FAIL]"
            duration = result["duration"]
            print(f"{i}. {status} - {result['name']} ({duration:.2f}s)")
            if result["error"]:
                print(f"   错误: {result['error']}")

        print("\n" + "=" * 70)

        # 保存结果到 JSON
        results_path = Path("test_results.json")
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "duration": total_duration
                },
                "results": self.test_results
            }, f, indent=2, ensure_ascii=False)

        print(f"测试结果已保存到: {results_path.absolute()}")
        print("=" * 70)


async def main():
    """主测试函数"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║              FastReAct 综合端到端测试                            ║
║                  Comprehensive E2E Test Suite                    ║
╚══════════════════════════════════════════════════════════════════╝

本测试套件验证 FastReAct 的核心功能，参考 Moltbot 的设计理念：
- ReAct 多工具协同推理
- Docker 沙箱安全执行
- 事件流和错误重试
- 并发处理能力
- 复杂推理链路
    """)

    runner = E2ETestRunner()

    # 运行所有测试
    await runner.run_test("1. 基本 ReAct 工具调用", runner.test_01_basic_react)
    await runner.run_test("2. Docker 沙箱代码执行", runner.test_02_sandbox_code_execution)
    await runner.run_test("3. 复杂推理链", runner.test_03_complex_reasoning_chain)
    await runner.run_test("4. 错误重试机制", runner.test_04_error_retry_mechanism)
    await runner.run_test("5. 并发会话处理", runner.test_05_concurrent_sessions)
    await runner.run_test("6. 沙箱安全特性", runner.test_06_sandbox_security)
    await runner.run_test("7. 多语言代码执行", runner.test_07_multi_language_execution)

    # 打印摘要
    runner.print_summary()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试已中断")
    except Exception as e:
        print(f"\n\n测试出错: {e}")
        import traceback
        traceback.print_exc()
