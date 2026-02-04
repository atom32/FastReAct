"""
FastReAct MCP Demo Server

A minimal MCP server to verify FastReAct's MCP integration works.

This server provides 3 simple tools:
1. get_secret_code - Returns a secret verification code
2. calculate_power - Calculates base^exponent
3. reverse_text - Reverses a string

Run with: python my_server.py
"""
from mcp.server.fastmcp import FastMCP
import datetime

# Create the MCP server
mcp = FastMCP("FastReAct-Demo")


@mcp.tool()
def get_secret_code(name: str) -> str:
    """
    Get a secret verification code (MCP demo tool).

    This tool is ONLY available through MCP connection.
    It proves that FastReAct successfully connected to an external tool server.

    Args:
        name: Your name to personalize the code

    Returns:
        A personalized secret verification code
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"SECRET-{name.upper()}-{timestamp}"


@mcp.tool()
def calculate_power(base: float, exponent: float) -> str:
    """
    Calculate the power of a number (MCP demo tool).

    Args:
        base: The base number
        exponent: The exponent

    Returns:
        The result of base^exponent
    """
    result = base ** exponent
    return f"{base}^{exponent} = {result}"


@mcp.tool()
def reverse_text(text: str) -> str:
    """
    Reverse a string (MCP demo tool).

    Args:
        text: The text to reverse

    Returns:
        The reversed text
    """
    return text[::-1]


@mcp.tool()
def get_server_info() -> str:
    """
    Get information about this MCP server.

    Returns:
        Server information
    """
    return """This is the FastReAct Demo MCP Server!
It proves that FastReAct can connect to external tool servers.
Tools provided:
- get_secret_code: Get a secret verification code
- calculate_power: Calculate powers
- reverse_text: Reverse strings
- get_server_info: Show this message"""


if __name__ == "__main__":
    # Run the server
    mcp.run()
