"""
Context Monitor - Token Usage Tracker for LLMDriver

Real-time token consumption monitoring with warnings
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ContextMetrics:
    """Context usage metrics"""
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    context_window: int = 128000  # Default for DeepSeek-V3
    usage_percentage: float = 0.0

    def update_usage(self, input_tokens: int, output_tokens: int = 0):
        """Update metrics with new token usage"""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens = self.input_tokens + self.output_tokens
        self.usage_percentage = (self.total_tokens / self.context_window) * 100


class ContextMonitor:
    """
    Monitor context usage and provide warnings

    Features:
    - Real-time token tracking
    - Warning at 80% usage
    - Alert at 90% usage
    - Critical at 95% usage
    """

    WARNING_THRESHOLD = 80.0
    ALERT_THRESHOLD = 90.0
    CRITICAL_THRESHOLD = 95.0

    def __init__(self, context_window: int = 128000):
        """
        Initialize ContextMonitor

        Args:
            context_window: Maximum token limit for the model
        """
        self.context_window = context_window
        self.metrics = ContextMetrics(context_window=context_window)
        self._last_warning_level = None

    def track_request(self, input_tokens: int, output_tokens: int = 0) -> Dict[str, Any]:
        """
        Track a request and update metrics

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Status dict with warnings if needed
        """
        self.metrics.update_usage(input_tokens, output_tokens)

        status = {
            "total_tokens": self.metrics.total_tokens,
            "usage_percentage": self.metrics.usage_percentage,
            "input_tokens": self.metrics.input_tokens,
            "output_tokens": self.metrics.output_tokens,
            "remaining_tokens": self.context_window - self.metrics.total_tokens,
        }

        # Check thresholds and log warnings
        warning_level = self._check_thresholds()

        if warning_level:
            status["warning"] = warning_level
            self._log_warning(warning_level, status)

        return status

    def _check_thresholds(self) -> Optional[str]:
        """Check if any threshold is crossed"""
        usage = self.metrics.usage_percentage

        if usage >= self.CRITICAL_THRESHOLD:
            return "CRITICAL"
        elif usage >= self.ALERT_THRESHOLD:
            return "ALERT"
        elif usage >= self.WARNING_THRESHOLD:
            return "WARNING"
        return None

    def _log_warning(self, level: str, status: Dict[str, Any]):
        """Log warning message"""
        usage = status["usage_percentage"]
        remaining = status["remaining_tokens"]

        if level == "WARNING":
            logger.warning(
                f"[ContextMonitor] Context usage at {usage:.1f}% "
                f"({status['total_tokens']} tokens used, {remaining} remaining)"
            )
        elif level == "ALERT":
            logger.error(
                f"[ContextMonitor] ALERT: Context usage at {usage:.1f}%! "
                f"({status['total_tokens']} tokens used, {remaining} remaining)"
            )
        elif level == "CRITICAL":
            logger.critical(
                f"[ContextMonitor] CRITICAL: Context usage at {usage:.1f}%! "
                f"({status['total_tokens']} tokens used, {remaining} remaining) "
                f"System may trigger Memory Flush or truncation!"
            )

    def get_progress_bar(self, width: int = 40) -> str:
        """
        Generate text-based progress bar

        Args:
            width: Width of the progress bar in characters

        Returns:
            Progress bar string
        """
        usage = self.metrics.usage_percentage / 100.0
        filled = int(width * usage)
        bar = "=" * filled + "-" * (width - filled)

        # Color indicators
        if usage >= 0.95:
            indicator = "[CRITICAL]"
        elif usage >= 0.90:
            indicator = "[ALERT]   "
        elif usage >= 0.80:
            indicator = "[WARNING] "
        else:
            indicator = "[OK]      "

        return f"{indicator} [{bar}] {self.metrics.usage_percentage:.1f}%"

    def get_status_text(self) -> str:
        """Get human-readable status text"""
        return (
            f"Token Usage: {self.metrics.total_tokens:,} / {self.context_window:,} "
            f"({self.metrics.usage_percentage:.1f}%)"
        )

    def reset(self):
        """Reset metrics (for new conversation)"""
        self.metrics = ContextMetrics(context_window=self.context_window)
        self._last_warning_level = None
        logger.debug("[ContextMonitor] Metrics reset")


# Singleton instance for global use
_global_monitor: Optional[ContextMonitor] = None


def get_context_monitor(context_window: int = 128000) -> ContextMonitor:
    """
    Get global context monitor instance

    Args:
        context_window: Maximum token limit

    Returns:
        ContextMonitor instance
    """
    global _global_monitor

    if _global_monitor is None:
        _global_monitor = ContextMonitor(context_window)

    return _global_monitor


def reset_context_monitor():
    """Reset global context monitor"""
    global _global_monitor
    _global_monitor = None
