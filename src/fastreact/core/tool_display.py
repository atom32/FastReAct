"""
Tool Display System

Provides user-friendly formatting for tool calls and results with icons,
colors, and enhanced information.

Key features:
- Formatted tool call display
- Clear error messages
- Execution information (time, status, risk)
- Tool categorization with icons
- Multiple display modes
"""

import logging
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Any, Optional, TextIO
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DisplayMode(IntEnum):
    """Display verbosity modes"""

    # Minimal output (tool name + status)
    MINIMAL = 1

    # Normal output (tool + params + result summary)
    NORMAL = 2

    # Verbose output (all details + timing + metadata)
    VERBOSE = 3


class ToolCategory(IntEnum):
    """Tool categories for icon assignment"""

    # Shell/execution tools
    EXECUTION = 1

    # Search/retrieval tools
    SEARCH = 2

    # File/edit tools
    EDIT = 3

    # Data/analysis tools
    DATA = 4

    # Network/API tools
    NETWORK = 5

    # System/tools
    SYSTEM = 6

    # Unknown category
    UNKNOWN = 99


# Tool icons mapping
TOOL_ICONS = {
    ToolCategory.EXECUTION: "🔧",
    ToolCategory.SEARCH: "🔍",
    ToolCategory.EDIT: "📝",
    ToolCategory.DATA: "📊",
    ToolCategory.NETWORK: "🌐",
    ToolCategory.SYSTEM: "⚙️",
    ToolCategory.UNKNOWN: "🔹",
}

# Status icons
STATUS_ICONS = {
    "success": "✅",
    "error": "❌",
    "running": "⏳",
    "warning": "⚠️",
}


@dataclass
class ToolCallInfo:
    """Information about a tool call"""

    # Tool name
    tool_name: str

    # Tool parameters
    parameters: Dict[str, Any]

    # Tool category
    category: ToolCategory = ToolCategory.UNKNOWN

    # Risk level
    risk_level: str = "UNKNOWN"

    # Start time
    start_time: float = field(default_factory=time.time)

    # End time (0 if still running)
    end_time: float = 0.0

    # Status (running, success, error)
    status: str = "running"

    # Result or error message
    result: Any = None

    # Error message if status is error
    error: Optional[str] = None

    # Execution time in seconds
    @property
    def execution_time(self) -> float:
        """Get execution time in seconds"""
        if self.end_time > 0:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "category": self.category.name,
            "risk_level": self.risk_level,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
            "result": self.result if self.status == "success" else None,
            "error": self.error,
            "execution_time": self.execution_time,
        }


@dataclass
class DisplayConfig:
    """Configuration for tool display"""

    # Display mode
    mode: DisplayMode = DisplayMode.NORMAL

    # Use colors/emoji (disable for non-interactive terminals)
    use_colors: bool = True

    # Show execution time
    show_time: bool = True

    # Show risk level
    show_risk: bool = True

    # Maximum lines to show for results
    max_result_lines: int = 50

    # Truncate long results
    truncate_results: bool = True

    # Output stream
    output: TextIO = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "mode": self.mode.name,
            "use_colors": self.use_colors,
            "show_time": self.show_time,
            "show_risk": self.show_risk,
            "max_result_lines": self.max_result_lines,
            "truncate_results": self.truncate_results,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DisplayConfig":
        """Create from dictionary"""
        mode_map = {
            "minimal": DisplayMode.MINIMAL,
            "normal": DisplayMode.NORMAL,
            "verbose": DisplayMode.VERBOSE,
        }

        return cls(
            mode=mode_map.get(data.get("mode", "normal"), DisplayMode.NORMAL),
            use_colors=data.get("use_colors", True),
            show_time=data.get("show_time", True),
            show_risk=data.get("show_risk", True),
            max_result_lines=data.get("max_result_lines", 50),
            truncate_results=data.get("truncate_results", True),
        )


class ToolDisplay:
    """
    Formats and displays tool calls and results with user-friendly output
    """

    def __init__(self, config: Optional[DisplayConfig] = None):
        """Initialize tool display

        Args:
            config: Display configuration
        """
        self.config = config or DisplayConfig()
        self.active_calls: Dict[str, ToolCallInfo] = {}
        self.call_counter = 0

        logger.debug(
            f"ToolDisplay initialized: mode={self.config.mode.name}, "
            f"colors={self.config.use_colors}"
        )

    def get_tool_category(self, tool_name: str) -> ToolCategory:
        """Determine tool category from name

        Args:
            tool_name: Name of the tool

        Returns:
            Tool category
        """
        name_lower = tool_name.lower()

        # Execution tools
        if any(keyword in name_lower for keyword in ["bash", "shell", "exec", "run", "sandbox"]):
            return ToolCategory.EXECUTION

        # Search tools
        elif any(keyword in name_lower for keyword in ["search", "grep", "find", "tavily"]):
            return ToolCategory.SEARCH

        # Edit tools
        elif any(keyword in name_lower for keyword in ["edit", "write", "save", "modify"]):
            return ToolCategory.EDIT

        # Data tools
        elif any(keyword in name_lower for keyword in ["data", "analyze", "parse", "json"]):
            return ToolCategory.DATA

        # Network tools
        elif any(keyword in name_lower for keyword in ["http", "fetch", "api", "request"]):
            return ToolCategory.NETWORK

        # System tools
        elif any(keyword in name_lower for keyword in ["system", "config", "settings"]):
            return ToolCategory.SYSTEM

        return ToolCategory.UNKNOWN

    def format_tool_call(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        risk_level: str = "MEDIUM"
    ) -> str:
        """Format a tool call for display

        Args:
            tool_name: Name of the tool
            parameters: Tool parameters
            risk_level: Risk level

        Returns:
            Formatted string
        """
        if self.config.mode == DisplayMode.MINIMAL:
            return self._format_minimal(tool_name)
        elif self.config.mode == DisplayMode.VERBOSE:
            return self._format_verbose(tool_name, parameters, risk_level)
        else:  # NORMAL
            return self._format_normal(tool_name, parameters, risk_level)

    def _format_minimal(self, tool_name: str) -> str:
        """Format in minimal mode"""
        category = self.get_tool_category(tool_name)
        icon = TOOL_ICONS.get(category, TOOL_ICONS[ToolCategory.UNKNOWN])

        if self.config.use_colors:
            return f"{icon} {tool_name}"
        else:
            return f"[{tool_name}]"

    def _format_normal(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        risk_level: str
    ) -> str:
        """Format in normal mode"""
        lines = []

        category = self.get_tool_category(tool_name)
        icon = TOOL_ICONS.get(category, TOOL_ICONS[ToolCategory.UNKNOWN])

        # Header
        if self.config.use_colors:
            lines.append(f"{icon} {tool_name}")
        else:
            lines.append(f"Tool: {tool_name}")

        # Parameters
        if parameters and self.config.mode >= DisplayMode.NORMAL:
            for key, value in list(parameters.items())[:5]:  # Limit to 5 params
                # Truncate long values
                value_str = str(value)
                if len(value_str) > 50:
                    value_str = value_str[:47] + "..."
                lines.append(f"  ├─ {key}: {value_str}")
            if len(parameters) > 5:
                lines.append(f"  └─ ... and {len(parameters) - 5} more")

        # Risk level
        if self.config.show_risk and risk_level != "UNKNOWN":
            lines.append(f"  ├─ Risk: {risk_level}")

        return "\n".join(lines)

    def _format_verbose(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        risk_level: str
    ) -> str:
        """Format in verbose mode"""
        lines = self._format_normal(tool_name, parameters, risk_level).split("\n")

        # Add category info
        category = self.get_tool_category(tool_name)
        lines.append(f"  ├─ Category: {category.name}")

        return "\n".join(lines)

    def format_result(
        self,
        tool_name: str,
        result: Any,
        error: Optional[str] = None,
        execution_time: float = 0.0
    ) -> str:
        """Format tool execution result

        Args:
            tool_name: Name of the tool
            result: Result value
            error: Error message if failed
            execution_time: Execution time in seconds

        Returns:
            Formatted string
        """
        if error:
            return self._format_error(tool_name, error, execution_time)
        else:
            return self._format_success(tool_name, result, execution_time)

    def _format_success(
        self,
        tool_name: str,
        result: Any,
        execution_time: float
    ) -> str:
        """Format successful result"""
        lines = []

        icon = STATUS_ICONS["success"] if self.config.use_colors else "[OK]"

        # Status line
        time_str = f" ({execution_time:.2f}s)" if self.config.show_time and execution_time > 0 else ""
        lines.append(f"{icon} Status: Success{time_str}")

        # Result
        if result is not None and self.config.mode >= DisplayMode.NORMAL:
            result_str = str(result)

            if self.config.truncate_results and len(result_str) > 500:
                lines.append("├─ Result:")
                lines.append("│ " + result_str[:200])
                lines.append("│ ... " + str(len(result_str) - 400) + " bytes omitted ...")
                lines.append("│ " + result_str[-200:])
            else:
                # Split into lines and limit
                result_lines = result_str.split("\n")
                if len(result_lines) > self.config.max_result_lines:
                    result_lines = (
                        result_lines[:25] +
                        [f"... {len(result_lines) - 50} lines omitted ..."] +
                        result_lines[-25:]
                    )
                lines.append("└─ Result:")
                for line in result_lines[:self.config.max_result_lines]:
                    lines.append("  " + line)

        return "\n".join(lines)

    def _format_error(
        self,
        tool_name: str,
        error: str,
        execution_time: float
    ) -> str:
        """Format error result"""
        lines = []

        icon = STATUS_ICONS["error"] if self.config.use_colors else "[ERROR]"

        # Status line
        time_str = f" ({execution_time:.2f}s)" if self.config.show_time and execution_time > 0 else ""
        lines.append(f"{icon} Status: Error{time_str}")

        # Error message
        if error:
            lines.append(f"└─ Error: {error}")

        return "\n".join(lines)

    @contextmanager
    def track_call(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        risk_level: str = "MEDIUM"
    ):
        """Context manager for tracking a tool call

        Args:
            tool_name: Name of the tool
            parameters: Tool parameters
            risk_level: Risk level

        Yields:
            ToolCallInfo object
        """
        # Create call info
        self.call_counter += 1
        call_id = f"call_{self.call_counter:04d}"

        info = ToolCallInfo(
            tool_name=tool_name,
            parameters=parameters,
            category=self.get_tool_category(tool_name),
            risk_level=risk_level,
        )

        self.active_calls[call_id] = info

        # Display call start
        print(self.format_tool_call(tool_name, parameters, risk_level))

        try:
            yield info
        finally:
            # Mark as completed
            info.end_time = time.time()

            # Display result
            if info.status == "error":
                print(self.format_result(tool_name, None, info.error, info.execution_time))
            else:
                print(self.format_result(tool_name, info.result, None, info.execution_time))

            # Remove from active
            del self.active_calls[call_id]

    def get_statistics(self) -> Dict[str, Any]:
        """Get tool call statistics

        Returns:
            Dictionary with statistics
        """
        return {
            "total_calls": self.call_counter,
            "active_calls": len(self.active_calls),
        }


def create_default_display() -> ToolDisplay:
    """Create tool display with default configuration

    Returns:
        ToolDisplay with NORMAL mode
    """
    return ToolDisplay(DisplayConfig(mode=DisplayMode.NORMAL))


def format_tool_call_minimal(tool_name: str) -> str:
    """Convenience function for minimal formatting

    Args:
        tool_name: Name of the tool

    Returns:
        Formatted string
    """
    display = ToolDisplay(DisplayConfig(mode=DisplayMode.MINIMAL))
    return display.format_tool_call(tool_name, {})
