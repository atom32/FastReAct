"""
FastReAct 异常体系

提供分类的异常类型，支持智能重试和错误处理
"""

from typing import Optional, Dict, Any


class FastReActError(Exception):
    """FastReAct 基础异常类"""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化异常

        Args:
            message: 错误消息
            details: 额外的错误详情（如工具名、参数等）
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于日志和序列化）"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details
        }


class ToolError(FastReActError):
    """工具执行错误的基类"""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化工具错误

        Args:
            message: 错误消息
            tool_name: 工具名称
            parameters: 工具调用参数
            details: 额外详情
        """
        details = details or {}
        if tool_name:
            details["tool_name"] = tool_name
        if parameters:
            details["parameters"] = parameters

        super().__init__(message, details)
        self.tool_name = tool_name
        self.parameters = parameters


class RetryableError(ToolError):
    """
    可重试的工具错误

    用于临时性错误，如网络超时、服务暂时不可用等
    """

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        retry_after: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化可重试错误

        Args:
            message: 错误消息
            tool_name: 工具名称
            parameters: 工具调用参数
            retry_after: 建议的等待时间（秒）
            details: 额外详情
        """
        details = details or {}
        if retry_after is not None:
            details["retry_after"] = retry_after

        super().__init__(message, tool_name, parameters, details)
        self.retry_after = retry_after


class NonRetryableError(ToolError):
    """
    不可重试的工具错误

    用于永久性错误，如参数错误、权限问题、工具不存在等
    """

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化不可重试错误

        Args:
            message: 错误消息
            tool_name: 工具名称
            parameters: 工具调用参数
            details: 额外详情
        """
        super().__init__(message, tool_name, parameters, details)


class NetworkError(RetryableError):
    """网络错误（超时、连接失败等）"""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
        retry_after: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if status_code is not None:
            details["status_code"] = status_code

        # 默认重试延迟 2 秒
        if retry_after is None:
            retry_after = 2.0

        super().__init__(message, tool_name, parameters, retry_after=retry_after, details=details)
        self.status_code = status_code


class TimeoutError(RetryableError):
    """超时错误"""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if timeout is not None:
            details["timeout"] = timeout

        super().__init__(message, tool_name, parameters, retry_after=1.0, details=details)
        self.timeout = timeout


class ValidationError(NonRetryableError):
    """参数验证错误"""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        validation_errors: Optional[Dict[str, str]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if validation_errors:
            details["validation_errors"] = validation_errors

        super().__init__(message, tool_name, parameters, details)
        self.validation_errors = validation_errors or {}


class ToolNotFoundError(NonRetryableError):
    """工具不存在错误"""

    def __init__(
        self,
        tool_name: str,
        available_tools: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if available_tools:
            details["available_tools"] = available_tools

        message = f"Tool '{tool_name}' not found"
        super().__init__(message, tool_name=tool_name, details=details)
        self.available_tools = available_tools or []


class PermissionError(NonRetryableError):
    """权限错误"""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        required_permission: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if required_permission:
            details["required_permission"] = required_permission

        super().__init__(message, tool_name, details=details)
        self.required_permission = required_permission


class RateLimitError(RetryableError):
    """速率限制错误"""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        retry_after: Optional[float] = None,
        limit: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if limit is not None:
            details["rate_limit"] = limit

        # 默认等待时间
        if retry_after is None:
            retry_after = 5.0

        super().__init__(message, tool_name, retry_after=retry_after, details=details)
        self.limit = limit


class LLMError(FastReActError):
    """LLM 调用错误"""

    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if model:
            details["model"] = model
        if error_code:
            details["error_code"] = error_code

        super().__init__(message, details)
        self.model = model
        self.error_code = error_code


class MaxRetriesExceededError(FastReActError):
    """超过最大重试次数错误"""

    def __init__(
        self,
        message: str,
        original_error: Exception,
        retry_count: int,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details["retry_count"] = retry_count
        details["original_error"] = str(original_error)
        details["original_error_type"] = type(original_error).__name__

        super().__init__(message, details)
        self.original_error = original_error
        self.retry_count = retry_count


# 辅助函数
def is_retryable_error(error: Exception) -> bool:
    """
    判断错误是否可重试

    Args:
        error: 异常对象

    Returns:
        True 如果错误可重试
    """
    # 检查是否是可重试错误的实例
    if isinstance(error, RetryableError):
        return True

    # 检查常见的可重试错误类型
    error_type_name = type(error).__name__

    # 网络相关错误
    if "timeout" in error_type_name.lower():
        return True
    if "connection" in error_type_name.lower():
        return True
    if "network" in error_type_name.lower():
        return True

    # HTTP 错误（5xx 可重试，4xx 不可重试）
    if hasattr(error, 'status'):
        status = getattr(error, 'status', None) or getattr(error, 'status_code', None)
        if status and isinstance(status, int):
            return 500 <= status < 600

    return False


def get_suggested_retry_delay(error: Exception, attempt: int) -> float:
    """
    获取建议的重试延迟时间（指数退避）

    Args:
        error: 异常对象
        attempt: 当前重试次数（从 0 开始）

    Returns:
        建议的延迟时间（秒）
    """
    # 如果错误本身包含建议的等待时间
    if isinstance(error, RetryableError) and error.retry_after is not None:
        return error.retry_after

    # 指数退避：2^attempt 秒，最多 30 秒
    base_delay = min(2 ** attempt, 30)

    # 添加随机抖动（±25%）避免雷鸣羊群效应
    import random
    jitter = base_delay * 0.25 * (random.random() * 2 - 1)

    return base_delay + jitter
