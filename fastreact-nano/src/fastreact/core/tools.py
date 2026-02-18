"""
Tool system for FastReAct Nano

Clean abstraction for agent tools with JSON Schema validation.
Based on Nanobot's simple pattern with FastReAct's type safety.
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass
from enum import Enum


class ValidationError(Exception):
    """Tool parameter validation error"""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Validation errors: {', '.join(errors)}")


class Tool(ABC):
    """
    Base class for all tools

    Tools are capabilities that the agent can use:
    - Read/write files
    - Execute shell commands
    - Search the web
    - etc.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (must be unique)"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM"""
        pass

    @property
    def parameters(self) -> dict[str, Any]:
        """
        JSON Schema for parameters

        Default: no parameters
        Override for custom parameters
        """
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    @abstractmethod
    async def execute(
        self,
        user_context: Optional["UserContext"] = None,
        **kwargs
    ) -> str:
        """
        Execute the tool

        Args:
            user_context: User context for multi-tenant isolation (optional)
            **kwargs: Tool parameters

        Returns:
            String result
        """
        pass

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        """
        Validate parameters against schema

        Args:
            params: Parameters to validate

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        schema = self.parameters
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # Check required params
        for field in required:
            if field not in params:
                errors.append(f"Missing required parameter: {field}")

        # Check type (basic validation)
        for field, value in params.items():
            if field in properties:
                prop_schema = properties[field]
                prop_type = prop_schema.get("type")

                if prop_type == "string" and not isinstance(value, str):
                    errors.append(f"{field} must be string")
                elif prop_type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"{field} must be number")
                elif prop_type == "integer" and not isinstance(value, int):
                    errors.append(f"{field} must be integer")
                elif prop_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"{field} must be boolean")
                elif prop_type == "array" and not isinstance(value, list):
                    errors.append(f"{field} must be array")

        return errors

    def to_schema(self) -> dict[str, Any]:
        """Convert to OpenAI tool format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """
    Registry for managing tools

    Provides registration, lookup, and execution.
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Register a tool"""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool

    def unregister(self, name: str):
        """Unregister a tool"""
        if name in self._tools:
            del self._tools[name]

    def get(self, name: str) -> Optional[Tool]:
        """Get tool by name"""
        return self._tools.get(name)

    def list_all(self) -> list[str]:
        """List all tool names"""
        return list(self._tools.keys())

    def schemas(self) -> list[dict[str, Any]]:
        """Get all tool schemas for LLM"""
        return [tool.to_schema() for tool in self._tools.values()]

    async def execute(
        self,
        name: str,
        params: dict[str, Any],
        user_context: Optional["UserContext"] = None,
    ) -> str:
        """
        Execute a tool

        Args:
            name: Tool name
            params: Tool parameters
            user_context: User context for multi-tenant isolation (optional)

        Returns:
            Result string

        Raises:
            ValueError: If tool not found or validation fails
        """
        tool = self.get(name)
        if not tool:
            return f"[ERROR] Tool '{name}' not found"

        # Validate parameters
        errors = tool.validate_params(params)
        if errors:
            raise ValidationError(errors)

        # Execute with user context
        try:
            return await tool.execute(
                user_context=user_context,
                **params
            )
        except Exception as e:
            return f"[ERROR] {type(e).__name__}: {str(e)}"


# Example tools


class EchoTool(Tool):
    """Example tool that echoes back input"""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echo back the input text"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to echo back",
                }
            },
            "required": ["text"],
        }

    async def execute(self, text: str, user_context: Optional["UserContext"] = None) -> str:
        _ = user_context  # Unused parameter for backward compatibility
        return f"[ECHO] {text}"


class AddTool(Tool):
    """Example tool that adds two numbers"""

    @property
    def name(self) -> str:
        return "add"

    @property
    def description(self) -> str:
        return "Add two numbers together"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "a": {
                    "type": "number",
                    "description": "First number",
                },
                "b": {
                    "type": "number",
                    "description": "Second number",
                }
            },
            "required": ["a", "b"],
        }

    async def execute(self, a: float, b: float, user_context: Optional["UserContext"] = None) -> str:
        _ = user_context  # Unused parameter for backward compatibility
        result = a + b
        return f"[ADD] {a} + {b} = {result}"
