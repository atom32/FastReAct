"""
Tavily 搜索工具

Tavily 是一个专门为 AI 优化的搜索 API。
提供实时、准确的网络搜索结果。

文档: https://docs.tavily.com/
"""

import os
import asyncio
from typing import List, Dict, Optional
import logging

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from ..core.tool import Tool

logger = logging.getLogger(__name__)


class TavilySearchTool(Tool):
    """
    Tavily 搜索工具

    使用 Tavily API 进行网络搜索，提供实时、准确的搜索结果。

    需要安装:
        pip install httpx

    获取 API Key:
        https://tavily.com/

    Usage:
        from fastreact.tools import TavilySearchTool

        search = TavilySearchTool(api_key="your-tavily-api-key")
        results = await search.execute_async("Python asyncio tutorial")
    """

    def __init__(
        self,
        api_key: str = None,
        search_depth: str = "basic",
        max_results: int = 10,
        include_answer: bool = True,
        include_raw_content: bool = False,
        include_images: bool = False,
        include_image_descriptions: bool = False
    ):
        """初始化 Tavily 搜索工具

        Args:
            api_key: Tavily API Key（默认从 TAVILY_API_KEY 环境变量读取）
            search_depth: 搜索深度 ("basic" 或 "advanced")
            max_results: 最大结果数 (1-10)
            include_answer: 是否包含 AI 生成的答案摘要
            include_raw_content: 是否包含原始 HTML 内容
            include_images: 是否包含图片
            include_image_descriptions: 是否包含图片描述
        """
        super().__init__()

        if not HTTPX_AVAILABLE:
            raise ImportError(
                "httpx is required for TavilySearchTool. "
                "Install it with: pip install httpx"
            )

        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            logger.warning("TAVILY_API_KEY not set, will use fallback search")

        self.search_depth = search_depth
        self.max_results = max_results
        self.include_answer = include_answer
        self.include_raw_content = include_raw_content
        self.include_images = include_images
        self.include_image_descriptions = include_image_descriptions

        self.base_url = "https://api.tavily.com/search"
        self.http_client: Optional[httpx.AsyncClient] = None

    def _get_description(self) -> str:
        return """搜索互联网获取最新信息

使用 Tavily 搜索引擎进行实时网络搜索，提供准确、及时的搜索结果。

可以搜索:
- 最新新闻和资讯
- 技术文档和教程
- 学术研究
- 百科知识
- 实时事件和数据

搜索特点:
- AI 优化的搜索结果
- 支持实时搜索
- 智能答案摘要
- 多语言支持
"""

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询，如 'Python asyncio 教程' 或 '2024年AI最新进展'",
                },
                "search_depth": {
                    "type": "string",
                    "enum": ["basic", "advanced"],
                    "description": "搜索深度: basic(快速) 或 advanced(深度搜索)",
                    "default": "basic",
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回结果数量 (1-10)，默认10",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 10,
                },
                "days": {
                    "type": "integer",
                    "description": "搜索最近N天的内容 (1-30)，默认3",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 30,
                },
                "topic": {
                    "type": "string",
                    "enum": ["general", "news"],
                    "description": "搜索主题: general(综合) 或 news(新闻)",
                    "default": "general",
                }
            },
            "required": ["query"],
        }

    async def _get_http_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self.http_client is None or self.http_client.is_closed:
            self.http_client = httpx.AsyncClient(timeout=30.0)
        return self.http_client

    async def execute_async(
        self,
        query: str,
        search_depth: str = None,
        max_results: int = None,
        days: int = 3,
        topic: str = "general"
    ) -> str:
        """异步执行搜索

        Args:
            query: 搜索查询
            search_depth: 搜索深度 (basic/advanced)
            max_results: 最大结果数
            days: 搜索最近N天
            topic: 搜索主题 (general/news)

        Returns:
            格式化的搜索结果
        """
        # 如果没有 API key，使用回退搜索
        if not self.api_key:
            return await self._fallback_search(query, max_results or self.max_results)

        # 使用参数
        search_depth = search_depth or self.search_depth
        max_results = max_results or self.max_results

        # 准备请求参数
        params = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "days": days,
            "topic": topic,
            "include_answer": self.include_answer,
            "include_raw_content": self.include_raw_content,
            "include_images": self.include_images,
            "include_image_descriptions": self.include_image_descriptions,
        }

        try:
            # 发送请求（Tavily API 使用 POST）
            client = await self._get_http_client()
            response = await client.post(self.base_url, json=params)
            response.raise_for_status()

            data = response.json()

            # 格式化结果
            return self._format_results(data, query)

        except httpx.HTTPStatusError as e:
            logger.error(f"Tavily API error: {e.response.status_code} - {e.response.text}")
            return f"搜索失败: API 返回错误 {e.response.status_code}"
        except Exception as e:
            logger.error(f"Search error: {e}")
            return f"搜索失败: {str(e)}"

    def _format_results(self, data: Dict, query: str) -> str:
        """格式化搜索结果

        Args:
            data: Tavily API 返回的数据
            query: 搜索查询

        Returns:
            格式化的结果文本
        """
        output_parts = []

        # 添加 AI 生成的答案（如果有）
        if data.get("answer"):
            output_parts.append(f"📝 **AI 答案摘要**")
            output_parts.append(f"{data['answer']}\n")

        # 添加搜索结果
        results = data.get("results", [])
        if results:
            output_parts.append(f"🔍 **搜索 '{query}' 找到 {len(results)} 条结果**\n")

            for i, result in enumerate(results, 1):
                # 标题
                title = result.get("title", "无标题")
                output_parts.append(f"{i}. **{title}**")

                # 内容摘要
                content = result.get("content", "")
                if content:
                    # 截断过长的内容
                    if len(content) > 300:
                        content = content[:300] + "..."
                    output_parts.append(f"   {content}")

                # URL
                url = result.get("url", "")
                if url:
                    output_parts.append(f"   🔗 {url}")

                # 评分（如果有）
                score = result.get("score")
                if score:
                    output_parts.append(f"   相关性: {score:.2%}")

                # 发布时间（如果有）
                published_date = result.get("published_date")
                if published_date:
                    output_parts.append(f"   📅 {published_date}")

                output_parts.append("")

        # 添加图片（如果有）
        images = data.get("images", [])
        if images and self.include_images:
            output_parts.append(f"🖼️ **相关图片 ({len(images)}张)**")
            for i, image in enumerate(images[:5], 1):  # 最多显示5张
                output_parts.append(f"{i}. {image.get('url', '')}")
                if self.include_image_descriptions:
                    output_parts.append(f"   {image.get('description', '')}")
            output_parts.append("")

        return "\n".join(output_parts)

    async def _fallback_search(self, query: str, max_results: int = 5) -> str:
        """回退搜索（无 API key 时使用）

        使用模拟搜索结果
        """
        await asyncio.sleep(0.5)  # 模拟搜索延迟

        fallback_results = [
            {
                "title": f"'{query}' - 维基百科",
                "content": f"关于 {query} 的详细条目，包括定义、历史、应用等...",
                "url": f"https://zh.wikipedia.org/wiki/{query}",
            },
            {
                "title": f"{query} - 最新资讯和教程",
                "content": f"查看 {query} 的最新发展、教程、最佳实践等...",
                "url": f"https://www.google.com/search?q={query}",
            },
            {
                "title": f"{query} 相关视频教程",
                "content": f"通过视频学习 {query}，包含实战案例和讲解...",
                "url": f"https://www.youtube.com/results?search_query={query}",
            },
            {
                "title": f"{query} - 技术文档和API参考",
                "content": f"官方文档、API 参考、开发指南等...",
                "url": f"https://developer.mozilla.org/search?q={query}",
            },
            {
                "title": f"{query} - Stack Overflow",
                "content": f"开发者社区关于 {query} 的讨论和解决方案...",
                "url": f"https://stackoverflow.com/search?q={query}",
            },
        ]

        # 限制结果数量
        results = fallback_results[:max_results]

        # 格式化输出
        output = [
            f"🔍 搜索 '{query}' (演示模式 - 未配置 Tavily API Key)",
            f"找到 {len(results)} 条模拟结果:\n"
        ]

        for i, result in enumerate(results, 1):
            output.append(f"{i}. **{result['title']}**")
            output.append(f"   {result['content']}")
            output.append(f"   🔗 {result['url']}")
            output.append("")

        output.append("💡 提示: 配置 TAVILY_API_KEY 环境变量以使用真实搜索")
        output.append("   获取 API Key: https://tavily.com/")

        return "\n".join(output)

    async def close(self):
        """关闭 HTTP 客户端"""
        if self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()
            self.http_client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class TavilyNewsTool(TavilySearchTool):
    """
    Tavily 新闻搜索工具

    专门用于搜索新闻资讯。
    """

    def __init__(self, api_key: str = None, max_results: int = 10):
        """初始化新闻搜索工具

        Args:
            api_key: Tavily API Key
            max_results: 最大结果数
        """
        super().__init__(
            api_key=api_key,
            search_depth="basic",
            max_results=max_results,
            topic="news",
            include_answer=True
        )

    def _get_description(self) -> str:
        return """搜索最新新闻资讯

使用 Tavily 搜索引擎获取实时新闻，包括:
- 突发新闻
- 科技新闻
- 财经资讯
- 体育新闻
- 娱乐新闻

特点:
- 实时更新
- 多来源聚合
- AI 摘要生成
"""


class TavilyAdvancedSearchTool(TavilySearchTool):
    """
    Tavily 高级搜索工具

    使用 advanced 搜索深度，提供更全面的结果。
    """

    def __init__(self, api_key: str = None, max_results: int = 10):
        """初始化高级搜索工具

        Args:
            api_key: Tavily API Key
            max_results: 最大结果数
        """
        super().__init__(
            api_key=api_key,
            search_depth="advanced",
            max_results=max_results,
            include_answer=True,
            include_raw_content=False,
            include_images=True,
            include_image_descriptions=True
        )

    def _get_description(self) -> str:
        return """高级网络搜索（深度模式）

使用 Tavily 高级搜索提供更全面、深入的搜索结果。

特点:
- 深度搜索
- 包含图片
- AI 智能摘要
- 更详细的搜索结果

适用于:
- 复杂查询
- 研究需求
- 深度分析
"""
