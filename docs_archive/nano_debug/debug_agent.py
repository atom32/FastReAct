#!/usr/bin/env python3
"""带调试输出的 Agent"""
import sys
import asyncio
from pathlib import Path

src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))
sys.path = [p for p in sys.path if not ('FastReAct/src' in p and 'fastreact-nano' not in p)]

from fastreact import Agent, Config, EventType

# Patch the agent to add debug output
from fastreact.agent import Agent as OriginalAgent

class DebugAgent(OriginalAgent):
    async def run_event_stream(self, query, skills=None, session_id=None, history=None):
        from fastreact.core.events import AgentEvent, EventType
        import uuid

        session_id = session_id or str(uuid.uuid4())
        self._session_queues[session_id] = self._react.core.messages.MessageQueue()

        try:
            yield AgentEvent.session_start(query, session_id)
            messages = list(history or [])
            messages.append(self._react.core.messages.Message.user(query).to_llm_format())

            outer_iter = 0
            while True:
                outer_iter += 1
                print(f"\n[DEBUG] Outer iteration {outer_iter} started")

                has_more_tool_calls = True
                executed_tools_this_iteration = False

                inner_iter = 0
                while has_more_tool_calls:
                    inner_iter += 1
                    print(f"[DEBUG]   Inner iteration {inner_iter}")

                    # Core logic (simplified - call original)
                    async for event in self._core.run_step_stream(messages, session_id):
                        if event.type == EventType.THINK:
                            yield event
                        elif event.type == EventType.TOOL_CALL:
                            yield event
                        elif event.type == EventType.STEP_END:
                            print(f"[DEBUG]     STEP_END: has_tool_calls={event.metadata.get('has_tool_calls')}")
                            if event.content:
                                messages.append({"role": "assistant", "content": event.content})
                            break

                    # Execute tools
                    step_end_events = []
                    tool_calls = []
                    async for event in self._core.run_step_stream(messages, session_id):
                        if event.type == EventType.TOOL_CALL:
                            tool_calls.append(event)
                        elif event.type == EventType.STEP_END:
                            step_end_events.append(event)
                            break

                    if step_end_events and step_end_events[0].metadata.get("has_tool_calls") and tool_calls:
                        print(f"[DEBUG]     Executing {len(tool_calls)} tools")
                        for tool_call in tool_calls:
                            # Execute tool
                            result = await self._tools.execute(tool_call.tool_name, tool_call.tool_args)
                            yield AgentEvent.tool_result(tool_call.tool_name, result, session_id)
                            messages.append(self._react.core.messages.Message.tool(
                                name=tool_call.tool_name,
                                result=result,
                                call_id="",
                            ).to_llm_format())

                        executed_tools_this_iteration = True
                        has_more_tool_calls = False
                        print(f"[DEBUG]     executed_tools_this_iteration = True")
                    else:
                        has_more_tool_calls = False
                        print(f"[DEBUG]     No tool calls")

                # After inner loop
                has_followup = bool(self._session_queues.get(session_id))
                print(f"[DEBUG] After inner loop: executed_tools_this_iteration={executed_tools_this_iteration}, has_followup={has_followup}")

                if executed_tools_this_iteration and not has_followup:
                    print(f"[DEBUG] Continuing to next iteration (tools executed)")
                    continue

                if has_followup:
                    print(f"[DEBUG] Continuing (has follow-up)")
                    continue

                print(f"[DEBUG] Breaking outer loop")
                break

            # Extract final answer
            final_answer = ""
            for msg in reversed(messages):
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    if content and not content.startswith("["):
                        final_answer = content
                        break

            yield AgentEvent.session_end(session_id, final_answer)

        except Exception as e:
            yield AgentEvent.error(str(e), session_id)
            import traceback
            traceback.print_exc()

async def main():
    config = Config.load()
    agent = DebugAgent(config=config)

    query = "读取 config.json 并总结"
    print(f"Query: {query}\n")

    async for event in agent.run_event_stream(query):
        pass  # Events already printed in debug output

if __name__ == "__main__":
    asyncio.run(main())
