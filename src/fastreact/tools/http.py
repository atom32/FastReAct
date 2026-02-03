"""
HTTP请求工具

发送HTTP请求获取数据
"""

import asyncio
import httpx
from typing import Dict, Any, Optional
from ..core.tool import Tool


class HTTPTool(Tool):
    """
    HTTP请求工具

    支持发送GET/POST请求获取数据
    """

    def __init__(self, timeout: float = 10.0):
        super().__init__()
        self.timeout = timeout
        self._client = None

    def _get_description(self) -> str:
        return """发送HTTP请求获取数据

支持：
- GET请求：获取数据
- POST请求：提交数据
- 自定义请求头
- 超时控制
"""

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "description": "HTTP方法，支持 GET 或 POST，默认GET",
                    "enum": ["GET", "POST"],
                },
                "url": {
                    "type": "string",
                    "description": "请求URL",
                },
                "headers": {
                    "type": "object",
                    "description": "请求头（可选）",
                },
                "data": {
                    "description": "POST请求的数据（可选）",
                },
            },
            "required": ["url"],
        }

    async def _get_client(self):
        """获取或创建HTTP客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def execute_async(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Any] = None,
    ) -> str:
        """异步执行HTTP请求"""
        client = await self._get_client()

        try:
            # 发送请求
            if method.upper() == "POST":
                response = await client.post(url, headers=headers, json=data)
            else:
                response = await client.get(url, headers=headers)

            # 格式化输出
            output = f"""📡 HTTP请求结果

🔗 URL: {url}
[LIST] 方法: {method}
[CHART] 状态码: {response.status_code}
[FILE] 内容类型: {response.headers.get('content-type', 'N/A')}

[NOTE] 响应内容:
{response.text[:1000]}  # 限制长度
"""

            if len(response.text) > 1000:
                output += f"\n... (内容已截断，总共{len(response.text)}字符)"

            return output

        except httpx.TimeoutException:
            return f"[ERROR] 请求超时: {url}"
        except Exception as e:
            return f"[ERROR] 请求失败: {str(e)}"

    async def close(self):
        """关闭HTTP客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
