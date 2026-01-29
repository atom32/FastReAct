"""
时间工具

提供当前时间和日期相关的功能
"""

from datetime import datetime, timezone
from typing import Optional
from ..core.tool import Tool


class GetCurrentTimeTool(Tool):
    """
    获取当前时间工具

    提供当前日期、时间、时区等信息。

    Usage:
        result = await tool.execute_async(
            timezone="Asia/Shanghai",
            format="full"
        )
    """

    def _get_description(self) -> str:
        return """获取当前时间和日期

可以获取:
- 当前日期和时间
- 指定时区的时间
- 格式化的时间字符串
- Unix 时间戳

返回格式包括:
- 完整日期时间
- 仅日期
- 仅时间
- Unix 时间戳
"""

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "时区，如 'Asia/Shanghai', 'UTC', 'America/New_York'",
                    "default": "Asia/Shanghai",
                },
                "format": {
                    "type": "string",
                    "enum": ["full", "date", "time", "timestamp", "iso"],
                    "description": "返回格式: full(完整), date(日期), time(时间), timestamp(时间戳), iso(ISO格式)",
                    "default": "full",
                }
            },
            "required": [],
        }

    async def execute_async(
        self,
        timezone: str = "Asia/Shanghai",
        format: str = "full"
    ) -> str:
        """异步执行获取时间

        Args:
            timezone: 时区
            format: 返回格式

        Returns:
            格式化的时间信息
        """
        try:
            # 获取指定时区的当前时间
            import pytz

            tz = pytz.timezone(timezone)
            now = datetime.now(tz)

        except ImportError:
            # 如果没有 pytz，使用简单的 UTC 时区
            now = datetime.now()

        except Exception:
            # 时区无效，使用本地时间
            now = datetime.now()

        # 根据格式返回
        if format == "full":
            return now.strftime("%Y-%m-%d %H:%M:%S %Z")
        elif format == "date":
            return now.strftime("%Y-%m-%d")
        elif format == "time":
            return now.strftime("%H:%M:%S")
        elif format == "timestamp":
            return str(int(now.timestamp()))
        elif format == "iso":
            return now.isoformat()
        else:
            return str(now)


class GetDateInfoTool(Tool):
    """
    获取日期详细信息

    提供更详细的日期信息，包括：
- 星期几
- 年中第几天
- 月中第几天
- 是否闰年
    """

    def _get_description(self) -> str:
        return """获取详细的日期信息

提供当前日期的详细信息:
- 星期几
- 年中第几天
- 月中第几天
- 是否闰年
- 季度
"""

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "时区，默认 'Asia/Shanghai'",
                    "default": "Asia/Shanghai",
                }
            },
            "required": [],
        }

    async def execute_async(self, timezone: str = "Asia/Shanghai") -> str:
        """获取详细日期信息"""
        try:
            import pytz
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
        except:
            now = datetime.now()

        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

        info = [
            f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            f"星期: {weekdays[now.weekday()]}",
            f"年中第 {now.timetuple().tm_yday} 天",
            f"月中第 {now.day} 天",
            f"季度: 第 {(now.month - 1) // 3 + 1} 季度",
            f"是否闰年: {'是' if self._is_leap_year(now.year) else '否'}",
        ]

        return "\n".join(info)

    def _is_leap_year(self, year: int) -> bool:
        """判断是否闰年"""
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


class DateTimeCalcTool(Tool):
    """
    日期时间计算工具

    提供日期计算功能：
- 日期加减
- 计算日期差
- 格式化日期
    """

    def _get_description(self) -> str:
        return """日期时间计算

支持:
- 日期加减: 从今天起N天后的日期
- 计算日期差: 两个日期之间的天数
- 日期格式化: 转换日期格式
"""

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add_days", "subtract_days", "diff"],
                    "description": "操作类型: add_days(加天), subtract_days(减天), diff(日期差)",
                },
                "days": {
                    "type": "integer",
                    "description": "天数（用于add_days或subtract_days）",
                },
                "date1": {
                    "type": "string",
                    "description": "日期1（格式: YYYY-MM-DD）",
                },
                "date2": {
                    "type": "string",
                    "description": "日期2（格式: YYYY-MM-DD）",
                },
            },
            "required": ["operation"],
        }

    async def execute_async(
        self,
        operation: str,
        days: int = None,
        date1: str = None,
        date2: str = None
    ) -> str:
        """执行日期计算"""
        from datetime import timedelta

        today = datetime.now().date()

        if operation == "add_days":
            if days is None:
                return "错误: add_days 需要提供 days 参数"

            result_date = today + timedelta(days=days)
            return f"{days}天后是: {result_date.strftime('%Y-%m-%d')} ({self._get_weekday(result_date)})"

        elif operation == "subtract_days":
            if days is None:
                return "错误: subtract_days 需要提供 days 参数"

            result_date = today - timedelta(days=days)
            return f"{days}天前是: {result_date.strftime('%Y-%m-%d')} ({self._get_weekday(result_date)})"

        elif operation == "diff":
            if not date1 or not date2:
                return "错误: diff 需要提供 date1 和 date2 参数"

            try:
                d1 = datetime.strptime(date1, "%Y-%m-%d").date()
                d2 = datetime.strptime(date2, "%Y-%m-%d").date()
            except ValueError as e:
                return f"错误: 日期格式不正确，应为 YYYY-MM-DD"

            delta = abs((d2 - d1).days)
            return f"{date1} 和 {date2} 之间相隔 {delta} 天"

        else:
            return f"错误: 未知的操作 '{operation}'"

    def _get_weekday(self, date) -> str:
        """获取星期几"""
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        return weekdays[date.weekday()]
