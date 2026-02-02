"""
FastReAct CLI - 命令行工具

提供便捷的命令行界面，让用户无需编程即可使用 FastReAct。
"""

# Lazy import to avoid RuntimeWarning when running as module
def __getattr__(name):
    if name == 'cli':
        from .main import cli
        return cli
    elif name == 'main':
        from .main import main
        return main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ['cli', 'main']
