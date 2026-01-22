"""
天气查询工具

获取天气信息（模拟实现）
"""

import asyncio
from datetime import datetime
from ..core.tool import Tool


class WeatherTool(Tool):
    """
    天气查询工具

    查询指定城市的天气信息（模拟实现）
    可继承此类实现真实的天气API调用
    """

    def _get_description(self) -> str:
        return """查询天气信息

可以查询：
- 当前天气
- 温度
- 湿度
- 风速
- 天气状况
"""

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，如 '北京' 或 '上海'",
                },
            },
            "required": ["city"],
        }

    async def execute_async(self, city: str) -> str:
        """异步查询天气"""
        # 模拟查询延迟
        await asyncio.sleep(0.05)

        # 模拟天气数据（实际应用中应调用真实API）
        mock_weather = {
            "北京": {"temp": 22, "humidity": 45, "wind": 3, "condition": "晴"},
            "上海": {"temp": 25, "humidity": 65, "wind": 4, "condition": "多云"},
            "广州": {"temp": 28, "humidity": 75, "wind": 2, "condition": "阵雨"},
            "深圳": {"temp": 29, "humidity": 70, "wind": 3, "condition": "阴"},
            "杭州": {"temp": 24, "humidity": 60, "wind": 2, "condition": "晴"},
        }

        # 获取天气数据
        weather = mock_weather.get(city, {
            "temp": 20,
            "humidity": 50,
            "wind": 3,
            "condition": "晴"
        })

        # 格式化输出
        output = f"""🌤️ {city}天气信息

📍 城市: {city}
🌡️ 温度: {weather['temp']}°C
💧 湿度: {weather['humidity']}%
💨 风速: {weather['wind']}级
☁️ 天气: {weather['condition']}
🕐 查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

        return output


class RealWeatherTool(WeatherTool):
    """
    真实天气查询工具（需要API密钥）

    可以集成：
    - 和风天气API
    - OpenWeatherMap API
    - 中国天气网API
    """

    def __init__(self, api_key: str = None):
        super().__init__()
        self.api_key = api_key

    async def execute_async(self, city: str) -> str:
        """使用真实API查询天气"""
        if not self.api_key:
            # 如果没有API密钥，回退到模拟天气
            return await super().execute_async(city)

        # TODO: 实现真实的API调用
        # 这里需要根据具体API实现
        return await super().execute_async(city)
