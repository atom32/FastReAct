"""
FastReAct Nano v2.0 - Minimal Tool Set

Pi's philosophy: Don't create tools for every function.
The AI can use Bash for complex operations.

Core tools (4):
- ReadFileTool: Read file contents
- WriteFileTool: Write files
- ExecTool: Execute bash commands
- EditFileTool: Text replacement editing
"""

from fastreact.tools.read_file import ReadFileTool
from fastreact.tools.write_file import WriteFileTool
from fastreact.tools.exec_tool import ExecTool
from fastreact.tools.edit_file import EditFileTool

__all__ = [
    "ReadFileTool",
    "WriteFileTool",
    "ExecTool",
    "EditFileTool",
]
