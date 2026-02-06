"""
Task Evaluator - Quality Assessment for Sprint 5

The Critic: Evaluates task execution results and determines if fixes are needed.

This is the "Test" phase in the TOTE (Test-Operate-Test-Exit) loop:
- Test: Evaluate execution result
- Operate: Execute task (done by Engine)
- Test: Evaluate again (this module)
- Exit: If passed, deliver result

Sprint 5: Operation Self-Correction
Phase 1: Hard metrics (exit codes, error patterns)
Phase 2: LLM-based reflection (future)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# Evaluation Result
# ============================================================================

class EvaluationOutcome(str, Enum):
    """Evaluation outcome categories"""
    SUCCESS = "success"  # Task completed successfully
    RETRY = "retry"  # Transient error, should retry
    FIX = "fix"  # Needs explicit fix
    FATAL = "fatal"  # Cannot recover, give up


@dataclass
class EvaluationResult:
    """
    Result of task evaluation

    Attributes:
        outcome: Evaluation outcome (success/retry/fix/fatal)
        success: True if task succeeded
        needs_retry: True if should retry without modification
        needs_fix: True if needs explicit fix instructions
        failure_reason: Human-readable explanation
        suggested_fix: Concrete fix suggestion
        confidence: Confidence in evaluation (0-1)
        metadata: Additional information
    """

    outcome: EvaluationOutcome
    success: bool
    needs_retry: bool
    needs_fix: bool
    failure_reason: Optional[str] = None
    suggested_fix: Optional[str] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "outcome": self.outcome.value,
            "success": self.success,
            "needs_retry": self.needs_retry,
            "needs_fix": self.needs_fix,
            "failure_reason": self.failure_reason,
            "suggested_fix": self.suggested_fix,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


# ============================================================================
# Task Evaluator
# ============================================================================

class TaskEvaluator:
    """
    Task execution quality evaluator

    Sprint 5: Operation Self-Correction

    Evaluates task results to determine:
    1. Did the task succeed? (success/fail)
    2. Should we retry? (transient errors)
    3. Does it need fixing? (requires intervention)

    Phase 1: Hard metrics
    - Exit codes
    - Error patterns in output
    - Exception keywords

    Phase 2: LLM reflection (future)
    - Semantic analysis
    - Context-aware evaluation

    Usage:
        evaluator = TaskEvaluator()
        result = await evaluator.evaluate(tool_result, context)

        if result.needs_retry:
            # Trigger retry
        elif result.needs_fix:
            # Generate fix task
    """

    def __init__(self, enable_llm_reflection: bool = False):
        """
        Initialize evaluator

        Args:
            enable_llm_reflection: Enable LLM-based reflection (Phase 2)
        """
        self.enable_llm_reflection = enable_llm_reflection

        # Error patterns for different tools
        self._error_patterns = {
            "python": [
                r"Traceback \(most recent call last\)",
                r"SyntaxError",
                r"IndentationError",
                r"NameError",
                r"TypeError",
                r"Exception:",
            ],
            "bash": [
                r"command not found",
                r"no such file or directory",
                r"permission denied",
                r"error:",
            ],
            "general": [
                r"\[ERROR\]",
                r"\[FAIL\]",
                r"\[FATAL\]",
            ],
        }

        # Patterns that require explicit fixes (not just retry)
        self._fix_patterns = [
            "no such file or directory",
            "permission denied",
            "command not found",
        ]

        # Statistics
        self._stats = {
            "total_evaluations": 0,
            "success_count": 0,
            "retry_count": 0,
            "fix_count": 0,
            "fatal_count": 0,
        }

    async def evaluate(
        self,
        tool_result: 'ToolResult',
        context: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        """
        Evaluate task execution result

        Args:
            tool_result: The tool execution result to evaluate
            context: Additional context (task, history, etc.)

        Returns:
            EvaluationResult with outcome and suggested actions

        Phase 1: Hard metrics check
        - Check explicit error flag
        - Check exit code (if available)
        - Check output for error patterns
        """

        self._stats["total_evaluations"] += 1

        # ====================================================================
        # Check 1: Explicit Error Flag
        # ====================================================================

        if hasattr(tool_result, 'is_error') and tool_result.is_error:
            error_msg = getattr(tool_result, 'error', 'Unknown error')
            logger.warning(f"[EVALUATOR] Tool execution failed: {error_msg}")

            return EvaluationResult(
                outcome=EvaluationOutcome.RETRY,
                success=False,
                needs_retry=True,
                needs_fix=False,
                failure_reason=f"Tool execution failed: {error_msg}",
                suggested_fix="Check the error message and correct the input or command.",
                confidence=1.0,
                metadata={"error_type": "tool_execution"}
            )

        # ====================================================================
        # Check 2: Exit Code (if available in metadata)
        # ====================================================================

        if hasattr(tool_result, 'metadata') and tool_result.metadata:
            exit_code = tool_result.metadata.get("exit_code")
            if exit_code is not None and exit_code != 0:
                logger.warning(f"[EVALUATOR] Non-zero exit code: {exit_code}")

                # Categorize error type based on exit code
                if exit_code == 1:
                    # Application error
                    return EvaluationResult(
                        outcome=EvaluationOutcome.FIX,
                        success=False,
                        needs_retry=False,
                        needs_fix=True,
                        failure_reason=f"Application error (exit code {exit_code})",
                        suggested_fix="Review the error output and fix the issue in the code.",
                        confidence=1.0,
                        metadata={"exit_code": exit_code}
                    )
                elif exit_code == 2:
                    # Misusage
                    return EvaluationResult(
                        outcome=EvaluationOutcome.FIX,
                        success=False,
                        needs_retry=False,
                        needs_fix=True,
                        failure_reason=f"Command misuse (exit code {exit_code})",
                        suggested_fix="Check the command syntax and arguments.",
                        confidence=1.0,
                        metadata={"exit_code": exit_code}
                    )
                else:
                    # Other error - retry
                    return EvaluationResult(
                        outcome=EvaluationOutcome.RETRY,
                        success=False,
                        needs_retry=True,
                        needs_fix=False,
                        failure_reason=f"Process failed with exit code {exit_code}",
                        suggested_fix="Check the error output and retry.",
                        confidence=1.0,
                        metadata={"exit_code": exit_code}
                    )

        # ====================================================================
        # Check 3: Error Patterns in Output
        # ====================================================================

        content = getattr(tool_result, 'result', '')
        if not isinstance(content, str):
            # Convert to string if possible
            content = str(content)

        content_lower = content.lower()

        # Check for error patterns
        for pattern_type, patterns in self._error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    logger.warning(f"[EVALUATOR] Detected error pattern: {pattern}")

                    # Determine if retry or fix based on pattern
                    pattern_lower = pattern.lower()
                    # Code syntax/traceback errors - need fix
                    if any(keyword in pattern_lower for keyword in [
                        "traceback", "syntaxerror", "indentationerror",
                        "nameerror", "typeerror", "exception"
                    ]):
                        return EvaluationResult(
                            outcome=EvaluationOutcome.FIX,
                            success=False,
                            needs_retry=False,
                            needs_fix=True,
                            failure_reason=f"Code error detected: {pattern}",
                            suggested_fix=self._generate_fix_suggestion(pattern, content),
                            confidence=0.9,
                            metadata={"error_pattern": pattern}
                        )
                    # Bash/general errors that need explicit fixes
                    elif any(keyword in pattern_lower for keyword in self._fix_patterns):
                        return EvaluationResult(
                            outcome=EvaluationOutcome.FIX,
                            success=False,
                            needs_retry=False,
                            needs_fix=True,
                            failure_reason=f"Command failed: {pattern}",
                            suggested_fix=self._generate_fix_suggestion(pattern, content),
                            confidence=0.85,
                            metadata={"error_pattern": pattern}
                        )
                    # Other bash/general errors - retry (might be transient)
                    elif pattern_type == "bash" or pattern_type == "general":
                        return EvaluationResult(
                            outcome=EvaluationOutcome.RETRY,
                            success=False,
                            needs_retry=True,
                            needs_fix=False,
                            failure_reason=f"Error pattern detected: {pattern}",
                            suggested_fix=f"Check the {pattern_type} output and retry.",
                            confidence=0.7,
                            metadata={"error_pattern": pattern}
                        )
                    else:
                        # Unknown - retry conservatively
                        return EvaluationResult(
                            outcome=EvaluationOutcome.RETRY,
                            success=False,
                            needs_retry=True,
                            needs_fix=False,
                            failure_reason=f"Error pattern detected: {pattern}",
                            suggested_fix=f"Check the {pattern_type} output and retry.",
                            confidence=0.6,
                            metadata={"error_pattern": pattern}
                        )

        # ====================================================================
        # Check 4: Empty Result (Suspicious)
        # ====================================================================

        if not content or content.strip() == "":
            logger.warning("[EVALUATOR] Empty tool result")

            return EvaluationResult(
                outcome=EvaluationOutcome.RETRY,
                success=False,
                needs_retry=True,
                needs_fix=False,
                failure_reason="Tool returned empty result",
                suggested_fix="The command produced no output. This might indicate an issue.",
                confidence=0.7,
                metadata={"error_type": "empty_result"}
            )

        # ====================================================================
        # Default: Success
        # ====================================================================

        logger.info("[EVALUATOR] Task evaluation: SUCCESS")
        self._stats["success_count"] += 1

        return EvaluationResult(
            outcome=EvaluationOutcome.SUCCESS,
            success=True,
            needs_retry=False,
            needs_fix=False,
            failure_reason=None,
            suggested_fix=None,
            confidence=1.0,
            metadata={}
        )

    def _generate_fix_suggestion(self, pattern: str, content: str) -> str:
        """
        Generate fix suggestion based on error pattern

        Args:
            pattern: Error pattern that was detected
            content: Tool output content

        Returns:
            Fix suggestion string
        """

        if "syntaxerror" in pattern.lower():
            return "Fix the syntax error shown in the traceback. Common issues include missing colons, incorrect indentation, or invalid Python syntax."
        elif "indentationerror" in pattern.lower():
            return "Fix the indentation error. Check for inconsistent mixing of tabs and spaces."
        elif "traceback" in pattern.lower():
            # Extract the actual error from traceback
            lines = content.split('\n')
            for line in lines:
                if 'Error:' in line or 'Exception:' in line:
                    return f"Fix this error: {line.strip()}"
            return "Review the traceback above to identify and fix the error."
        elif "command not found" in pattern.lower():
            return "Check if the command exists and is in the system PATH."
        elif "no such file" in pattern.lower():
            return "Check if the file path is correct and the file exists."
        elif "permission denied" in pattern.lower():
            return "Check file permissions or run with appropriate privileges."
        else:
            return f"Address the {pattern} error shown in the output."

    def get_stats(self) -> Dict[str, Any]:
        """Get evaluator statistics"""
        return dict(self._stats)


# ============================================================================
# Convenience Functions
# ============================================================================

def create_evaluator(enable_llm_reflection: bool = False) -> TaskEvaluator:
    """
    Create a task evaluator

    Args:
        enable_llm_reflection: Enable LLM-based reflection (Phase 2)

    Returns:
        TaskEvaluator instance
    """
    return TaskEvaluator(enable_llm_reflection=enable_llm_reflection)


async def quick_check(tool_result: 'ToolResult') -> bool:
    """
    Quick check if tool result indicates success

    Args:
        tool_result: Tool execution result

    Returns:
        True if successful, False otherwise
    """
    evaluator = TaskEvaluator()
    result = await evaluator.evaluate(tool_result)
    return result.success
