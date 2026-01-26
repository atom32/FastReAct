"""
FastReAct配置管理器

支持从JSON文件加载LLM和ReACT配置
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class Config:
    """配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置

        Args:
            config_path: 配置文件路径，默认为项目根目录的config.json
        """
        if config_path is None:
            # 默认配置文件路径
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "config.json"

        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not self.config_path.exists():
            # 返回默认配置
            return self._get_default_config()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  加载配置文件失败: {e}")
            print("💡 使用默认配置")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "llm": {
                "providers": {
                    "default": {
                        "enabled": True,
                        "base_url": "https://api.openai.com/v1",
                        "api_key": os.getenv("OPENAI_API_KEY", ""),
                        "model": "gpt-4",
                        "max_tokens": 2048,
                        "temperature": 0.7
                    }
                },
                "default_provider": "default",
                "timeout_seconds": 60,
                "retry_attempts": 3
            },
            "react": {
                "max_iterations": 10,
                "max_concurrent_tools": 3,
                "enable_cache": True,
                "cache_size": 1000,
                "enable_streaming": False
            }
        }

    def get_llm_config(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        获取LLM配置

        Args:
            provider: 提供商名称，不指定则使用默认

        Returns:
            LLM配置字典
        """
        llm_config = self.config.get("llm", {})
        provider_name = provider or llm_config.get("default_provider", "default")

        providers = llm_config.get("providers", {})
        if provider_name not in providers:
            print(f"⚠️  提供商 '{provider_name}' 不存在，使用默认配置")
            provider_name = list(providers.keys())[0] if providers else "default"

        provider_config = providers.get(provider_name, {})

        # 检查是否启用
        if not provider_config.get("enabled", True):
            print(f"⚠️  提供商 '{provider_name}' 未启用")

        return provider_config

    def get_react_config(self) -> Dict[str, Any]:
        """获取ReACT配置"""
        return self.config.get("react", {
            "max_iterations": 10,
            "max_concurrent_tools": 3,
            "enable_cache": True,
            "cache_size": 1000,
            "enable_streaming": False
        })

    def get_all_providers(self) -> Dict[str, Dict[str, Any]]:
        """获取所有LLM提供商"""
        return self.config.get("llm", {}).get("providers", {})

    def get_enabled_providers(self) -> Dict[str, Dict[str, Any]]:
        """获取所有已启用的提供商"""
        all_providers = self.get_all_providers()
        return {
            name: config
            for name, config in all_providers.items()
            if config.get("enabled", True)
        }

    def list_providers(self) -> None:
        """列出所有可用的提供商"""
        print("\n" + "=" * 60)
        print("📋 可用的LLM提供商")
        print("=" * 60)

        providers = self.get_all_providers()
        default_provider = self.config.get("llm", {}).get("default_provider", "")

        for name, config in providers.items():
            enabled = "✅" if config.get("enabled", True) else "❌"
            is_default = " (默认)" if name == default_provider else ""
            model = config.get("model", "N/A")
            base_url = config.get("base_url", "N/A")

            print(f"\n{enabled} {name}{is_default}")
            print(f"   模型: {model}")
            print(f"   API: {base_url}")

        print("\n" + "=" * 60)

    def save_config(self, config_path: Optional[str] = None) -> None:
        """
        保存配置到文件

        Args:
            config_path: 保存路径，不指定则覆盖原文件
        """
        save_path = Path(config_path) if config_path else self.config_path

        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"✅ 配置已保存到: {save_path}")
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")


# 创建全局配置实例
_global_config: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    获取全局配置实例（单例模式）

    Args:
        config_path: 配置文件路径

    Returns:
        Config实例
    """
    global _global_config
    if _global_config is None:
        _global_config = Config(config_path)
    return _global_config


if __name__ == "__main__":
    # 测试配置加载
    config = get_config()
    config.list_providers()

    print("\n🔧 当前LLM配置:")
    llm_config = config.get_llm_config()
    for key, value in llm_config.items():
        if key != "api_key":
            print(f"  {key}: {value}")
        else:
            print(f"  {key}: {'*' * 20}")
