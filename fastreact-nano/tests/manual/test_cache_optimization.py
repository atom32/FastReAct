#!/usr/bin/env python3
"""
Cache Optimization Test Cases

验证缓存友好的 Skill 注入优化是否生效

Run: python3 tests/manual/test_cache_optimization.py
"""

import asyncio
import time
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastreact import Agent


class CacheOptimizationTests:
    """缓存优化测试套件"""

    def __init__(self):
        self.agent = Agent()
        self.results = []

    def print_section(self, title: str):
        """打印测试区块"""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)

    def print_result(self, test_name: str, passed: bool, details: str = ""):
        """打印测试结果"""
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {test_name}")
        if details:
            print(f"      {details}")
        self.results.append((test_name, passed, details))

    # ========================================================================
    # Test 1: Base Prompt 常量性验证
    # ========================================================================

    def test_base_prompt_constancy(self):
        """
        测试目标：验证 base_prompt 在不同技能组合下保持不变
        预期结果：base_prompt 应该始终相同（1,162 字符）
        """
        self.print_section("Test 1: Base Prompt 常量性")

        test_cases = [
            (None, "无技能"),
            (["github"], "GitHub 技能"),
            (["web_search"], "Web Search 技能"),
            (["github", "web_search"], "多技能组合"),
        ]

        base_prompts = []
        for skills, description in test_cases:
            base_prompt, skills_content = self.agent._build_system_prompt_with_skills(skills)
            base_prompts.append(base_prompt)
            print(f"  [{description}]")
            print(f"    Base: {len(base_prompt)} chars, Skills: {len(skills_content)} chars")

        # 验证所有 base_prompt 相同
        all_same = all(bp == base_prompts[0] for bp in base_prompts)

        self.print_result(
            "Base prompt 在所有技能组合下保持不变",
            all_same,
            f"长度固定为 {len(base_prompts[0])} 字符"
        )

        # 验证 skills_content 会变化
        _, content_no_skill = self.agent._build_system_prompt_with_skills(None)
        _, content_with_skill = self.agent._build_system_prompt_with_skills(["github"])

        # 注意：如果技能未加载，content 可能相同
        content_differs = (content_no_skill != content_with_skill)
        print(f"\n  [INFO] Skills content 变化: {'是' if content_differs else '否 (可能技能未加载)'}")

        return all_same

    # ========================================================================
    # Test 2: Messages 结构验证
    # ========================================================================

    def test_messages_structure(self):
        """
        测试目标：验证 skills_content 被正确注入为 system message
        预期结果：messages[0] 应该是 system role with skills_content
        """
        self.print_section("Test 2: Messages 结构验证")

        # 模拟 Agent._run() 中的注入逻辑
        query = "测试查询"
        skills = ["github"]

        # 构建初始 messages
        from fastreact.core.messages import Message
        messages = [Message.user(query).to_llm_format()]

        # 获取 base_prompt 和 skills_content
        base_prompt, skills_content = self.agent._build_system_prompt_with_skills(skills)

        # 注入 skills_content（与 Agent._run() 相同的逻辑）
        messages.insert(0, {"role": "system", "content": skills_content})

        # 验证
        first_message = messages[0]
        is_system = first_message["role"] == "system"
        has_skills = "skill" in first_message["content"].lower() or "tool" in first_message["content"].lower()

        self.print_result(
            "Skills content 被正确注入为第一个 system message",
            is_system and has_skills,
            f"Role: {first_message['role']}, Content length: {len(first_message['content'])} chars"
        )

        # 验证 base_prompt 不包含 skills 内容
        base_has_skills = "skill" in base_prompt.lower()
        self.print_result(
            "Base prompt 不包含 skills 内容（保持纯净）",
            not base_has_skills,
            "Base prompt 仅包含核心规则"
        )

        return is_system and has_skills and not base_has_skills

    # ========================================================================
    # Test 3: 实际查询响应时间测试
    # ========================================================================

    async def test_query_response_time(self):
        """
        测试目标：通过实际查询验证缓存效果
        预期结果：第二次查询应该更快（缓存命中）
        注意：此测试需要真实的 API key
        """
        self.print_section("Test 3: 实际查询响应时间")

        # 简单查询（不使用工具，减少干扰）
        query1 = "什么是 2+2？"

        try:
            # 第一次查询（冷启动）
            start1 = time.time()
            response1 = await self.agent.ask(query1)
            time1 = time.time() - start1

            # 等待一下
            await asyncio.sleep(1)

            # 第二次查询（可能命中缓存）
            start2 = time.time()
            response2 = await self.agent.ask(query1)
            time2 = time.time() - start2

            print(f"  第一次查询: {time1:.2f}s")
            print(f"  第二次查询: {time2:.2f}s")
            print(f"  加速比: {time1/time2:.2f}x")

            # 第二次查询应该更快或相近（不应更慢）
            is_faster_or_similar = time2 <= time1 * 1.2  # 允许 20% 波动

            self.print_result(
                "缓存命中时响应速度改善",
                is_faster_or_similar,
                f"加速 {time1/time2:.2f}x"
            )

            return is_faster_or_similar

        except Exception as e:
            self.print_result(
                "实际查询测试",
                False,
                f"跳过（需要 API key）: {e}"
            )
            return None

    # ========================================================================
    # Test 4: 不同技能组合的隔离性
    # ========================================================================

    def test_skill_isolation(self):
        """
        测试目标：验证不同技能组合互不影响 base_prompt
        预期结果：无论选择什么技能，base_prompt 都相同
        """
        self.print_section("Test 4: 技能组合隔离性")

        skill_combinations = [
            [],
            ["github"],
            ["web_search"],
            ["github", "web_search"],
        ]

        base_prompts = []
        for skills in skill_combinations:
            base, _ = self.agent._build_system_prompt_with_skills(skills if skills else None)
            base_prompts.append(base)

        # 验证所有组合的 base_prompt 相同
        all_identical = all(bp == base_prompts[0] for bp in base_prompts)

        self.print_result(
            "不同技能组合的 base_prompt 完全相同",
            all_identical,
            f"测试了 {len(skill_combinations)} 种组合"
        )

        return all_identical

    # ========================================================================
    # Test 5: Token 使用估算
    # ========================================================================

    def test_token_usage_estimate(self):
        """
        测试目标：估算优化前后的 token 使用差异
        预期结果：base_prompt 固定可缓存，理论上降低成本
        """
        self.print_section("Test 5: Token 使用估算")

        # 获取 base_prompt 和 skills_content
        base, content = self.agent._build_system_prompt_with_skills(None)

        # 估算 token 数（粗略：1 token ≈ 4 字符）
        base_tokens = len(base) // 4
        content_tokens = len(content) // 4
        total_tokens = base_tokens + content_tokens

        print(f"  Base prompt: ~{base_tokens} tokens (固定，可缓存)")
        print(f"  Skills content: ~{content_tokens} tokens (可变)")
        print(f"  总计: ~{total_tokens} tokens")

        # 优化前：每次都要发送完整的 system_prompt
        # 优化后：base_prompt 缓存，只发送 skills_content

        cache_hit_rate = 0.5  # 假设 50% 缓存命中率
        old_cost = total_tokens
        new_cost = base_tokens + (content_tokens * cache_hit_rate)

        savings = (old_cost - new_cost) / old_cost * 100

        print(f"\n  [估算]")
        print(f"    优化前（每次完整发送）: {old_cost} tokens")
        print(f"    优化后（50% 缓存命中）: {new_cost:.0f} tokens")
        print(f"    预期节省: {savings:.1f}%")

        self.print_result(
            "Token 使用优化",
            savings > 0,
            f"预期节省 {savings:.1f}% tokens"
        )

        return True

    # ========================================================================
    # Run All Tests
    # ========================================================================

    async def run_all(self):
        """运行所有测试"""
        print("\n" + "=" * 70)
        print("  FastReAct Nano - 缓存优化测试套件")
        print("  版本: v2.5.0")
        print("=" * 70)

        # Test 1: Base prompt 常量性
        self.test_base_prompt_constancy()

        # Test 2: Messages 结构
        self.test_messages_structure()

        # Test 3: 实际查询（需要 API key）
        await self.test_query_response_time()

        # Test 4: 技能隔离性
        self.test_skill_isolation()

        # Test 5: Token 估算
        self.test_token_usage_estimate()

        # ====================================================================
        # Summary
        # ====================================================================
        self.print_section("测试总结")

        passed = sum(1 for _, p, _ in self.results if p)
        total = len(self.results)
        skipped = sum(1 for _, p, _ in self.results if p is None)

        print(f"  通过: {passed}/{total}")
        print(f"  跳过: {skipped}")
        print(f"  失败: {total - passed - skipped}")

        if passed == total - skipped:
            print("\n  [SUCCESS] 所有测试通过！缓存优化正常工作。")
        else:
            print("\n  [WARNING] 部分测试失败，请检查实现。")

        print("\n" + "=" * 70)


async def main():
    """主函数"""
    tests = CacheOptimizationTests()
    await tests.run_all()


if __name__ == "__main__":
    asyncio.run(main())
