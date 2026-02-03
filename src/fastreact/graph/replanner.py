"""
Replanner - Dynamic planning and reflection for Interactive Execution Loop

Handles:
- Analyzing failures and deciding between retry vs replan
- Generating GraphPatch objects (not direct modifications)
- Replanning from user interrupts
- Reflection using execution history context
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .iel_context import IELExecutionContext
from .iel_types import StepResult, Status, FailureType

logger = logging.getLogger(__name__)


# ============================================================================
# Patch Operations
# ============================================================================

class PatchOp(str, Enum):
    """Graph patch operation types"""
    ADD_NODE = "add_node"
    REMOVE_NODE = "remove_node"
    REPLACE_NODE = "replace_node"
    RECONNECT = "reconnect"
    INSERT_BEFORE = "insert_before"
    INSERT_AFTER = "insert_after"
    RETRY = "retry"  # Special: Retry same node without modification


# ============================================================================
# Graph Patch
# ============================================================================

@dataclass
class NodeInstruction:
    """
    Instruction for node creation/replacement

    Attributes:
        node_id: Target node ID
        tool_name: Tool to use
        inputs: Input parameters
        dependencies: Node dependencies
    """
    node_id: str
    tool_name: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "tool_name": self.tool_name,
            "inputs": self.inputs,
            "dependencies": self.dependencies,
        }


@dataclass
class GraphPatch:
    """
    Immutable patch description for graph modification

    Replanner outputs GraphPatch; IELExecutionContext.apply_patch() executes it.
    This separation ensures traceability and auditability.

    Attributes:
        patch_id: Unique patch identifier
        operation: Patch operation type
        reason: Human-readable explanation
        instructions: Operation-specific data
        metadata: Additional context
        timestamp: When patch was created
    """
    patch_id: str
    operation: PatchOp
    reason: str
    instructions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "patch_id": self.patch_id,
            "operation": self.operation.value,
            "reason": self.reason,
            "instructions": self.instructions,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }

    def is_retry(self) -> bool:
        """Check if this is a retry operation (no graph change)"""
        return self.operation == PatchOp.RETRY


# ============================================================================
# Reflection Result
# ============================================================================

@dataclass
class ReflectionResult:
    """
    Result of reflection analysis

    Attributes:
        should_retry: True if transient error (retry without modification)
        should_replan: True if logic error (need to modify graph)
        failure_category: Type of failure (environment, logic, data)
        root_cause: Underlying cause analysis
        confidence: Confidence in analysis (0-1)
        suggested_patch: Optional GraphPatch to apply
    """
    should_retry: bool
    should_replan: bool
    failure_category: str
    root_cause: str
    confidence: float
    suggested_patch: Optional[GraphPatch] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Replanner
# ============================================================================

class Replanner:
    """
    Dynamic replanner with reflection capabilities

    Responsibilities:
    1. Analyze failures using execution history (last 3 steps)
    2. Decide between retry vs replan
    3. Generate GraphPatch objects (not direct modifications)
    4. Handle user interrupts with replanning

    Usage:
        replanner = Replanner(llm_client=client, tool_registry=tools)

        # On failure
        patch = await replanner.reflect_and_patch(context, failed_result)
        if patch:
            context.apply_patch(patch)

        # On user interrupt
        patch = await replanner.replan_from_user(context, user_input)
        if patch:
            context.apply_patch(patch)
    """

    def __init__(
        self,
        llm_client,
        tool_registry: Dict[str, Any],
        model: str = "gpt-4",
    ):
        """
        Initialize Replanner

        Args:
            llm_client: LLM client for reflection and planning
            tool_registry: Available tools dictionary
            model: Model name
        """
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.model = model

        # Replanning stats
        self._replan_count = 0
        self._retry_count = 0

        logger.debug("Replanner initialized")

    # ========================================================================
    # Reflection and Patching
    # ========================================================================

    async def reflect_and_patch(
        self,
        context: IELExecutionContext,
        failure: StepResult,
    ) -> Optional[GraphPatch]:
        """
        Reflect on failure and generate patch

        Args:
            context: Current execution context
            failure: Failed step result

        Returns:
            GraphPatch to apply, or None if should just retry
        """
        logger.info(f"Reflecting on failure: {failure.node_id}")

        # Get last 3 steps for context (IEL requirement)
        recent_history = self._get_recent_history(context, n=3)

        # Analyze failure
        reflection = await self._analyze_failure(context, failure, recent_history)

        if reflection.should_retry:
            self._retry_count += 1
            logger.info(f"Decision: RETRY (transient error)")
            logger.info(f"  Reason: {reflection.root_cause}")

            # Return retry patch
            return GraphPatch(
                patch_id=f"retry_{failure.node_id}_{self._retry_count}",
                operation=PatchOp.RETRY,
                reason=f"Retry after transient error: {reflection.root_cause}",
                instructions={"node_id": failure.node_id},
                metadata={
                    "failure_category": reflection.failure_category,
                    "confidence": reflection.confidence,
                }
            )

        elif reflection.should_replan:
            self._replan_count += 1
            logger.info(f"Decision: REPLAN (logic error)")
            logger.info(f"  Reason: {reflection.root_cause}")

            if reflection.suggested_patch:
                return reflection.suggested_patch

            # Generate patch based on failure type
            patch = await self._generate_patch(context, failure, reflection)
            return patch

        else:
            logger.warning(f"Reflection inconclusive (confidence: {reflection.confidence})")
            # Default to retry for safety
            return GraphPatch(
                patch_id=f"default_retry_{failure.node_id}",
                operation=PatchOp.RETRY,
                reason="Default retry (reflection inconclusive)",
                instructions={"node_id": failure.node_id},
            )

    async def replan_from_user(
        self,
        context: IELExecutionContext,
        user_input: str,
    ) -> Optional[GraphPatch]:
        """
        Replan based on user interrupt/input

        Args:
            context: Current execution context
            user_input: User's feedback or new direction

        Returns:
            GraphPatch to apply, or None if no changes needed
        """
        logger.info(f"Replanning from user input: {user_input[:50]}...")

        # Generate new plan incorporating user feedback
        patch = await self._generate_user_patch(context, user_input)

        return patch

    # ========================================================================
    # Failure Analysis
    # ========================================================================

    async def _analyze_failure(
        self,
        context: IELExecutionContext,
        failure: StepResult,
        recent_history: List[StepResult],
    ) -> ReflectionResult:
        """
        Analyze failure using LLM reflection

        Key: Pass last 3 steps of history for context (IEL requirement)
        """
        # Build reflection prompt
        prompt = self._build_reflection_prompt(
            context, failure, recent_history
        )

        try:
            # Call LLM for reflection
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing execution failures and determining the best recovery strategy."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for consistent analysis
                max_tokens=1000,
            )

            analysis = response.choices[0].message.content or ""

            # Parse analysis
            return self._parse_reflection(analysis, failure)

        except Exception as e:
            logger.error(f"Reflection LLM call failed: {e}")
            # Default: retry for safety
            return ReflectionResult(
                should_retry=True,
                should_replan=False,
                failure_category="unknown",
                root_cause=f"Reflection failed: {str(e)}",
                confidence=0.0,
            )

    def _build_reflection_prompt(
        self,
        context: IELExecutionContext,
        failure: StepResult,
        recent_history: List[StepResult],
    ) -> str:
        """
        Build reflection prompt with execution context

        IEL Requirement: Must include last 3 steps of history
        """

        # Format recent history
        history_text = self._format_history_for_prompt(recent_history)

        # Format failure info
        failure_text = f"""
Failed Node: {failure.node_id}
Error: {failure.error}
Failure Type: {failure.failure_type.value if failure.failure_type else 'UNKNOWN'}
Payload: {failure.payload}
"""

        # Get graph context
        graph_info = f"""
Graph: {context.graph.name}
Total Nodes: {len(context.graph.nodes)}
Completed: {len(context.get_completed_nodes())}
Failed: {len(context.get_failed_nodes())}
Pending: {len(context.get_pending_nodes())}
"""

        prompt = f"""Analyze this execution failure and determine the best recovery strategy.

## Recent Execution History (Last 3 Steps)
{history_text}

## Current Failure
{failure_text}

## Graph Context
{graph_info}

## Available Tools
{self._format_tools_for_prompt()}

## Your Task
Analyze the failure and provide:

1. **Failure Category**: Choose one:
   - `transient`: Temporary issues (network timeout, rate limit, service unavailable)
   - `environment`: Missing dependencies, wrong paths, configuration issues
   - `logic`: Wrong tool choice, invalid parameters, incorrect plan
   - `data`: Invalid input data, missing required fields

2. **Root Cause**: Brief explanation of why this failed

3. **Recovery Strategy**: Choose one:
   - `retry`: Just retry the same node (for transient errors)
   - `replan`: Modify the graph to fix the issue (for environment/logic/data errors)

4. **Suggested Fix** (if replan):
   What change is needed? (e.g., "add node to install dependency", "change file path", "add validation")

## Response Format
```json{{
  "failure_category": "transient|environment|logic|data",
  "root_cause": "Brief explanation",
  "recovery_strategy": "retry|replan",
  "suggested_fix": "Description of fix (if replan)",
  "confidence": 0.8
}}
```

IMPORTANT:
- Consider the recent history - is this a recurring issue or first occurrence?
- Check if previous steps succeeded or failed
- Be conservative: if unsure, recommend retry
"""

        return prompt

    def _format_history_for_prompt(
        self,
        history: List[StepResult],
    ) -> str:
        """Format execution history for prompt"""
        if not history:
            return "No recent history"

        lines = []
        for i, result in enumerate(history, 1):
            status_icon = "[OK]" if result.is_success() else "[FAIL]"
            lines.append(f"{i}. {status_icon} {result.node_id}: {result.status.value}")

            if result.error:
                lines.append(f"   Error: {result.error}")

            if result.payload:
                payload_preview = str(result.payload)[:100]
                lines.append(f"   Payload: {payload_preview}...")

        return "\n".join(lines)

    def _format_tools_for_prompt(self) -> str:
        """Format available tools for prompt"""
        tool_names = list(self.tool_registry.keys())
        return ", ".join(tool_names[:20])  # Limit to avoid token overflow

    def _parse_reflection(
        self,
        analysis: str,
        failure: StepResult,
    ) -> ReflectionResult:
        """Parse LLM reflection response"""
        import json
        import re

        try:
            # Extract JSON from response
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', analysis, re.DOTALL)
            if not json_match:
                json_match = re.search(r'\{.*\}', analysis, re.DOTALL)

            if json_match:
                data = json.loads(json_match.group(1) if json_match.lastindex else json_match.group(0))

                failure_category = data.get("failure_category", "unknown")
                root_cause = data.get("root_cause", "Unknown cause")
                strategy = data.get("recovery_strategy", "retry")
                confidence = data.get("confidence", 0.5)

                should_retry = strategy == "retry"
                should_replan = strategy == "replan"

                suggested_patch = None
                if should_replan:
                    # Generate patch from suggestion
                    suggested_fix = data.get("suggested_fix", "")
                    suggested_patch = self._create_patch_from_suggestion(
                        failure, suggested_fix
                    )

                return ReflectionResult(
                    should_retry=should_retry,
                    should_replan=should_replan,
                    failure_category=failure_category,
                    root_cause=root_cause,
                    confidence=confidence,
                    suggested_patch=suggested_patch,
                )

        except Exception as e:
            logger.error(f"Failed to parse reflection: {e}")

        # Fallback: Default to retry
        return ReflectionResult(
            should_retry=True,
            should_replan=False,
            failure_category="unknown",
            root_cause="Parse error",
            confidence=0.0,
        )

    # ========================================================================
    # Patch Generation
    # ========================================================================

    async def _generate_patch(
        self,
        context: IELExecutionContext,
        failure: StepResult,
        reflection: ReflectionResult,
    ) -> GraphPatch:
        """Generate GraphPatch based on failure and reflection"""

        # Common failure patterns and their patches
        error_lower = failure.error.lower() if failure.error else ""

        # File not found -> Add check/creation node
        if "not found" in error_lower or "no such file" in error_lower:
            return self._create_file_not_found_patch(failure)

        # Permission denied -> Add fix permission node
        if "permission" in error_lower or "access denied" in error_lower:
            return self._create_permission_patch(failure)

        # Missing dependency -> Add install node
        if "not found" in error_lower or "no module named" in error_lower:
            return self._create_dependency_patch(failure)

        # Timeout -> Retry with backoff
        if "timeout" in error_lower:
            return GraphPatch(
                patch_id=f"retry_timeout_{failure.node_id}",
                operation=PatchOp.RETRY,
                reason="Retry after timeout with backoff",
                instructions={"node_id": failure.node_id, "backoff": True},
            )

        # Default: Request new plan from LLM
        return await self._request_new_plan(context, failure)

    async def _generate_user_patch(
        self,
        context: IELExecutionContext,
        user_input: str,
    ) -> Optional[GraphPatch]:
        """Generate patch based on user input"""

        prompt = f"""User has provided feedback during execution:

## Current Graph State
Graph: {context.graph.name}
Completed Nodes: {context.get_completed_nodes()}
Pending Nodes: {context.get_pending_nodes()}
Recent History:
{self._format_history_for_prompt(context.history[-3:])}

## User Feedback
{user_input}

## Your Task
Generate a patch to modify the graph based on user feedback.

Options:
1. Add new nodes to address user request
2. Remove nodes user wants to skip
3. Modify existing node parameters
4. Reorder execution

Respond in JSON:
```json{{
  "operation": "add_node|remove_node|replace_node|reconnect",
  "reason": "Explanation of change",
  "instructions": {{
    "node_id": "...",
    "tool_name": "...",
    "inputs": {{...}},
    "dependencies": [...]
  }}
}}
```
"""

        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at modifying execution plans based on user feedback."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1500,
            )

            content = response.choices[0].message.content or ""
            return self._parse_patch_response(content)

        except Exception as e:
            logger.error(f"Failed to generate user patch: {e}")
            return None

    async def _request_new_plan(
        self,
        context: IELExecutionContext,
        failure: StepResult,
    ) -> GraphPatch:
        """Request completely new plan from LLM"""

        # This would use the full planning system
        # For now, create a generic patch
        return GraphPatch(
            patch_id=f"replan_{failure.node_id}",
            operation=PatchOp.REPLACE_NODE,
            reason=f"Requesting new plan after failure: {failure.error}",
            instructions={
                "node_id": failure.node_id,
                "reason": "Original approach failed, need alternative"
            }
        )

    # ========================================================================
    # Patch Creation Helpers
    # ========================================================================

    def _create_file_not_found_patch(self, failure: StepResult) -> GraphPatch:
        """Create patch for file not found error"""
        return GraphPatch(
            patch_id=f"fix_file_{failure.node_id}",
            operation=PatchOp.INSERT_BEFORE,
            reason="Add file check/creation node before failed node",
            instructions={
                "target_node": failure.node_id,
                "new_node": NodeInstruction(
                    node_id=f"check_file_{failure.node_id}",
                    tool_name="read_file",
                    inputs={"path": "@context.file_path"},
                    dependencies=[]
                ).to_dict()
            }
        )

    def _create_permission_patch(self, failure: StepResult) -> GraphPatch:
        """Create patch for permission denied error"""
        return GraphPatch(
            patch_id=f"fix_permission_{failure.node_id}",
            operation=PatchOp.INSERT_BEFORE,
            reason="Add permission fix node",
            instructions={
                "target_node": failure.node_id,
                "new_node": NodeInstruction(
                    node_id=f"fix_perms_{failure.node_id}",
                    tool_name="bash",
                    inputs={"command": "chmod +x @context.target_path"},
                    dependencies=[]
                ).to_dict()
            }
        )

    def _create_dependency_patch(self, failure: StepResult) -> GraphPatch:
        """Create patch for missing dependency"""
        return GraphPatch(
            patch_id=f"install_dep_{failure.node_id}",
            operation=PatchOp.INSERT_BEFORE,
            reason="Install missing dependency before failed node",
            instructions={
                "target_node": failure.node_id,
                "new_node": NodeInstruction(
                    node_id=f"install_{failure.node_id}",
                    tool_name="bash",
                    inputs={"command": "pip install @context.missing_package"},
                    dependencies=[]
                ).to_dict()
            }
        )

    def _create_patch_from_suggestion(
        self,
        failure: StepResult,
        suggestion: str,
    ) -> Optional[GraphPatch]:
        """Create patch from LLM suggestion"""
        # Parse suggestion and create appropriate patch
        # This is a simplified version
        return GraphPatch(
            patch_id=f"suggested_{failure.node_id}",
            operation=PatchOp.REPLACE_NODE,
            reason=f"LLM suggestion: {suggestion}",
            instructions={
                "node_id": failure.node_id,
                "suggestion": suggestion
            }
        )

    def _parse_patch_response(self, response: str) -> Optional[GraphPatch]:
        """Parse LLM patch response"""
        import json
        import re

        try:
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if not json_match:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)

            if json_match:
                data = json.loads(json_match.group(1) if json_match.lastindex else json_match.group(0))

                return GraphPatch(
                    patch_id=f"user_patch_{datetime.now().strftime('%H%M%S')}",
                    operation=PatchOp(data.get("operation", "add_node")),
                    reason=data.get("reason", "User requested change"),
                    instructions=data.get("instructions", {}),
                )

        except Exception as e:
            logger.error(f"Failed to parse patch response: {e}")

        return None

    # ========================================================================
    # Utility
    # ========================================================================

    def _get_recent_history(
        self,
        context: IELExecutionContext,
        n: int = 3,
    ) -> List[StepResult]:
        """Get last N steps from history"""
        return context.history[-n:] if len(context.history) >= n else context.history.copy()

    def get_stats(self) -> Dict[str, Any]:
        """Get replanning statistics"""
        return {
            "replan_count": self._replan_count,
            "retry_count": self._retry_count,
            "total_decisions": self._replan_count + self._retry_count,
        }
