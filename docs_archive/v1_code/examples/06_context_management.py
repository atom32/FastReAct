"""
Context Management System - 示例代码

演示新的 Token 感知上下文管理系统
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.fastreact.context import (
    ContextConfig,
    LLMProviderConfig,
    TokenCounter,
    ContextBuilder,
    get_default_context_window,
)


def example_token_counter():
    """示例 1: Token 计数器"""
    print("=" * 60)
    print("示例 1: Token 计数器")
    print("=" * 60)

    # 创建 token 计数器
    counter = TokenCounter(model="gpt-4")

    # 测试文本
    text_zh = "这是一个中文测试句子。"
    text_en = "This is an English test sentence."
    text_mixed = "Hello 世界！This is a mixed 测试。"

    # 计数
    tokens_zh = counter.count_tokens(text_zh)
    tokens_en = counter.count_tokens(text_en)
    tokens_mixed = counter.count_tokens(text_mixed)

    print(f"中文文本: '{text_zh}'")
    print(f"  Tokens: {tokens_zh}")
    print()
    print(f"英文文本: '{text_en}'")
    print(f"  Tokens: {tokens_en}")
    print()
    print(f"混合文本: '{text_mixed}'")
    print(f"  Tokens: {tokens_mixed}")
    print()

    # 计数消息列表
    messages = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "Hello! How can I help you?"},
        {"role": "user", "content": "我想了解天气情况"},
    ]
    total = counter.count_messages_tokens(messages)
    print(f"消息列表总 Tokens: {total}")
    print()


def example_context_config():
    """示例 2: 配置管理"""
    print("=" * 60)
    print("示例 2: 配置管理")
    print("=" * 60)

    # 从字典创建配置（模拟从 config.json 加载）
    config_dict = {
        "context": {
            "max_history_messages": 50,
            "max_history_tokens": 4000,
            "reserve_tokens": 2048,
            "system_prompt_tokens": 1000,
            "smart_truncate": True,
        }
    }

    context_config = ContextConfig.from_dict(config_dict)

    print(f"最大历史消息数: {context_config.max_history_messages}")
    print(f"最大历史 Tokens: {context_config.max_history_tokens}")
    print(f"预留 Tokens: {context_config.reserve_tokens}")
    print(f"智能截断: {context_config.smart_truncate}")
    print()

    # LLM Provider 配置
    provider_dict = {
        "name": "DeepSeek V3",
        "model": "deepseek-ai/DeepSeek-V3",
        "max_tokens": 8192,
        "context_window": 64000,
        "temperature": 0.7,
    }

    llm_config = LLMProviderConfig.from_dict(provider_dict)

    print(f"模型: {llm_config.model}")
    print(f"Context Window: {llm_config.context_window}")
    print(f"Max Tokens: {llm_config.max_tokens}")
    print()

    # 计算预算
    budget = context_config.calculate_budget(llm_config.context_window)
    print(f"可用历史消息预算: {budget} tokens")
    print()


def example_context_builder():
    """示例 3: 上下文构建器"""
    print("=" * 60)
    print("示例 3: 上下文构建器")
    print("=" * 60)

    # 创建配置
    context_config = ContextConfig(
        max_history_messages=10,
        max_history_tokens=2000,
        reserve_tokens=1000,
        smart_truncate=True,
    )

    llm_config = LLMProviderConfig(
        name="Test Model",
        model="gpt-4",
        max_tokens=8192,
        context_window=8192,
    )

    # 创建构建器
    builder = ContextBuilder(
        context_config=context_config,
        llm_config=llm_config,
    )

    # 模拟历史消息
    history = [
        {"role": "user", "content": f"消息 {i}: 这是一条测试消息内容。" * 10}
        for i in range(1, 20)
    ]

    # 构建上下文
    system_prompt = "你是一个有用的 AI 助手。"
    user_query = "请总结前面的对话。"

    messages, metadata = builder.build_context(
        system_prompt=system_prompt,
        user_query=user_query,
        history=history,
    )

    print(f"系统 Prompt Tokens: {metadata['system_prompt_tokens']}")
    print(f"用户查询 Tokens: {metadata['user_query_tokens']}")
    print(f"历史消息使用: {metadata['history_messages_used']}/{metadata['history_messages_total']}")
    print(f"历史 Tokens: {metadata['history_tokens']}")
    print(f"总 Tokens: {metadata['total_tokens']}")
    print(f"剩余预算: {metadata['budget_remaining']}")
    print()

    print("构建的消息列表:")
    for i, msg in enumerate(messages):
        role = msg['role']
        content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
        print(f"  {i+1}. [{role}] {content}")
    print()


def example_default_context_windows():
    """示例 4: 默认 Context Window"""
    print("=" * 60)
    print("示例 4: 默认 Context Window")
    print("=" * 60)

    models = [
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-3.5-turbo",
        "deepseek-ai/DeepSeek-V3",
        "llama3.1",
    ]

    print("模型 Context Window 映射:")
    for model in models:
        window = get_default_context_window(model)
        print(f"  {model:30s} -> {window:,} tokens")
    print()


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("FastReAct Context Management System - 示例")
    print("=" * 60 + "\n")

    example_token_counter()
    example_context_config()
    example_context_builder()
    example_default_context_windows()

    print("=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
