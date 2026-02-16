"""
测试配置和共享夹具
"""
import pytest
import asyncio
import os
from pathlib import Path
from typing import Optional

# 尝试加载配置
try:
    from fastreact.core.config import load_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False


@pytest.fixture(scope="session")
def real_api_key() -> Optional[str]:
    """
    从 config.json 加载真实 API Key

    如果没有配置或没有 API Key，返回 None（相关测试会被跳过）
    """
    if not CONFIG_AVAILABLE:
        return None

    try:
        config = load_config()
        api_key = config.get('llm', {}).get('providers', {}).get('openai', {}).get('api_key')
        return api_key
    except Exception:
        return None


@pytest.fixture(scope="session")
def real_api_key_skip_missing(real_api_key: Optional[str]):
    """
    跳过装饰器：如果没有真实 API Key，跳过测试

    使用:
        @pytest.mark.skipif(real_api_key is None, reason="需要真实 API Key")
        def test_with_real_api(real_api_key):
            ...
    """
    return real_api_key is not None


@pytest.fixture(scope="session")
def real_agent(real_api_key_skip_missing):
    """
    创建使用真实 API 的 Agent（如果有 API Key）

    如果没有 API Key，返回 None
    """
    if not real_api_key_skip_missing:
        return None

    from fastreact import FastReAct

    # 使用较便宜的模型
    return FastReAct(
        api_key=real_api_key_skip_missing,
        model="gpt-3.5-turbo",  # 更便宜的模型
        enable_event_stream=True,
        enable_bootstrap=False  # 加快测试速度
    )


@pytest.fixture
def sample_events():
    """
    示例事件列表，用于测试
    """
    return [
        {"type": "lifecycle", "phase": "start"},
        {"type": "assistant", "delta": "Hello"},
        {"type": "tool", "phase": "start", "tool_name": "test"},
        {"type": "tool", "phase": "result", "tool_name": "test", "result": "OK"},
        {"type": "lifecycle", "phase": "end"},
    ]
