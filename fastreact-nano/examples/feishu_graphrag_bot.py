"""
FastReAct Nano - Feishu GraphRAG Bot Example

Example Feishu bot with GraphRAG knowledge graph integration.
Demonstrates multi-tenant support and MCP tool integration.
"""

import asyncio
from pathlib import Path

from fastreact import Agent, Config
from fastreact.adapters.feishu import FeishuChannel
from fastreact.core.config import FeishuConfig


async def main():
    """
    Run Feishu GraphRAG bot

    This bot:
    1. Receives messages from Feishu
    2. Creates isolated workspace per user (multi-tenant)
    3. Uses GraphRAG MCP tools for knowledge retrieval
    4. Streams results back to Feishu cards
    """

    # Load Feishu config from environment
    feishu_config = FeishuConfig.from_env()

    # Load or create Agent config with MCP servers
    config_path = Path.cwd() / "config.json"

    if config_path.exists():
        agent_config = Config.load(config_path)
    else:
        # Default config with GraphRAG MCP server
        agent_config = Config()
        # Add GraphRAG MCP server
        agent_config.mcp.servers = [
            {
                "name": "graphrag",
                "command": "python",
                "args": ["examples/graph_rag_server.py"],
            }
        ]

    # Create agent with multi-tenant support
    agent = Agent(
        config=agent_config,
        multitenant=True,  # Enable multi-tenant mode
        base_workspace=Path.cwd() / "workspace",
    )

    # Create Feishu channel
    channel = FeishuChannel(
        agent=agent,
        config=feishu_config,
    )

    # Start webhook server
    print("[INFO] Starting Feishu GraphRAG Bot...")
    print(f"[INFO] Multi-tenant: {feishu_config.enable_multitenant}")
    print(f"[INFO] Workspace: {feishu_config.base_workspace or Path.cwd() / 'workspace'}")
    print(f"[INFO] Listening on {feishu_config.host}:{feishu_config.port}")
    print(f"[INFO] Webhook path: {feishu_config.webhook_path}")
    print("[INFO] Press Ctrl+C to stop")

    await channel.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Bot stopped by user")
