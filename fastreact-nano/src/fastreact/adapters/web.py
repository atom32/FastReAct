"""
Web Adapter for FastReAct Nano

Provides Streamlit-based web UI with ChatGPT-like interface.
Install with: pip install fastreact-nano[web]

Usage:
    streamlit run src/fastreact/adapters/web.py
"""

import asyncio
import uuid
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

try:
    import streamlit as st

    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

from fastreact import Agent, Config
from fastreact.core.events import EventType, AgentEvent


class WebSession:
    """Web session manager for Streamlit"""

    def __init__(self):
        self.agent: Optional[Agent] = None
        self.session_id: str = str(uuid.uuid4())
        self.message_history: List[Dict] = []
        self.event_buffer: List[Dict] = []
        self.config: Config = Config.load()

    def initialize(self):
        """Initialize agent with config"""
        if self.agent is None:
            self.agent = Agent(config=self.config)

    def add_message(self, role: str, content: str, events: Optional[List[Dict]] = None):
        """Add message to history"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if events:
            message["events"] = events
        self.message_history.append(message)

    def clear_history(self):
        """Clear message history"""
        self.message_history = []
        self.event_buffer = []


def event_stream_generator(session: WebSession, query: str):
    """
    Generator that yields events one by one for Streamlit streaming display

    Args:
        session: Web session instance
        query: User query to process

    Yields:
        str: Formatted event strings for real-time display
    """
    async def collect_events():
        try:
            # Convert message_history to OpenAI format (exclude timestamp)
            history = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in session.message_history[:-1]  # Exclude current user message
            ] if len(session.message_history) > 1 else []

            events_collected = []

            async for event in session.agent.run_event_stream(
                query,
                session_id=session.session_id,
                history=history,
            ):
                event_dict = {
                    "type": event.type,
                    "content": event.content,
                    "tool_name": event.tool_name,
                    "tool_args": event.tool_args,
                    "session_id": event.session_id,
                    "metadata": event.metadata,
                }
                events_collected.append(event_dict)

                # Yield formatted string for streaming display
                yield format_event_for_streaming(event_dict)

            # Save all events to session for history
            session.event_buffer = events_collected

        except Exception as e:
            error_event = {
                "type": EventType.ERROR,
                "content": str(e),
            }
            session.event_buffer.append(error_event)
            yield f"[ERROR] {str(e)}"

    # Simple and reliable: collect all events first, then yield
    try:
        async def run_all():
            async_gen = collect_events()
            results = []
            async for item in async_gen:
                results.append(item)
            return results

        results = asyncio.run(run_all())
        for result in results:
            yield result
    except Exception as e:
        yield f"[ERROR] Stream execution failed: {str(e)}"


def format_event_for_streaming(event_dict: Dict) -> str:
    """Format event for streaming display"""
    event_type = event_dict.get("type")
    content = event_dict.get("content", "")
    tool_name = event_dict.get("tool_name", "")

    if event_type == EventType.THINK:
        return f"[Thinking] {content}\n"
    elif event_type == EventType.TOOL_CALL:
        tool_args = event_dict.get("tool_args", {})
        args_str = ", ".join(f"{k}={v}" for k, v in tool_args.items())
        return f"\n[Tool Call] `{tool_name}({args_str})`\n\n"
    elif event_type == EventType.TOOL_RESULT:
        truncated = content[:500] + "..." if len(content) > 500 else content
        return f"[Result]\n```\n{truncated}\n```\n"
    elif event_type == EventType.ERROR:
        return f"[ERROR] {content}\n"
    elif event_type == EventType.SESSION_START:
        return f"[Start] {content[:100]}...\n"
    elif event_type == EventType.SESSION_END:
        if content:
            return f"\n{content}\n"
        return ""
    return ""


def render_event(event_dict: Dict):
    """
    Render agent event to UI

    Args:
        event_dict: Event dictionary to render
    """
    event_type = event_dict.get("type")
    content = event_dict.get("content", "")
    tool_name = event_dict.get("tool_name", "")

    if event_type == EventType.THINK:
        # Render thinking in blue
        st.markdown(
            f"<div style='color: #0066cc; font-style: italic;'>{content}</div>",
            unsafe_allow_html=True
        )

    elif event_type == EventType.TOOL_CALL:
        # Render tool call with emphasis
        tool_args = event_dict.get("tool_args", {})
        args_str = ", ".join(f"{k}={v}" for k, v in tool_args.items())
        st.markdown(f"**[Tool Call]** `{tool_name}({args_str})`")

    elif event_type == EventType.TOOL_RESULT:
        # Render tool result in expandable section
        with st.expander(f"[Tool Result] {tool_name}", expanded=False):
            # Truncate long output
            display_content = content[:1000] + "..." if len(content) > 1000 else content
            st.code(display_content, language="text")

    elif event_type == EventType.ERROR:
        # Render error in red
        st.error(f"[ERROR] {content}")

    elif event_type == EventType.SESSION_START:
        st.info(f"[Session Start] {content[:100]}...")

    elif event_type == EventType.SESSION_END:
        if content:
            st.success(f"[DONE] {content}")

    elif event_type == EventType.STEP_END:
        # Step end is internal, don't render
        pass


def render_sidebar(session: WebSession):
    """
    Render sidebar with configuration and controls

    Args:
        session: Web session instance
    """
    with st.sidebar:
        st.title("FastReAct Nano")

        # Configuration section
        st.subheader("Configuration")

        # Model selection
        model = st.text_input("Model", value=session.config.llm.model)
        if model != session.config.llm.model:
            session.config.llm.model = model

        # API Base
        api_base = st.text_input("API Base", value=session.config.llm.api_base)
        if api_base != session.config.llm.api_base:
            session.config.llm.api_base = api_base

        # API Key
        api_key = st.text_input("API Key", type="password")
        if api_key:
            session.config.llm.api_key = api_key

        # Temperature
        temp = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=session.config.llm.temperature,
            step=0.1
        )
        if temp != session.config.llm.temperature:
            session.config.llm.temperature = temp

        st.divider()

        # Session controls
        st.subheader("Session Controls")

        # Session info
        st.caption(f"Session ID: {session.session_id[:8]}...")

        # Message count
        st.caption(f"Messages: {len(session.message_history)}")

        # Clear history button
        if st.button("Clear History"):
            session.clear_history()
            st.rerun()

        st.divider()

        # Help section
        st.subheader("Help")
        st.markdown("""
        **Usage Tips:**

        - Ask questions in natural language
        - Agent can read and write files
        - Agent can execute shell commands
        - Use 'Clear History' to start fresh

        **Example Queries:**

        - "What files are in the current directory?"
        - "Read the README file"
        - "Create a Python script that..."
        - "Execute: ls -la"
        """)


def render_chat_interface():
    """Render main chat interface"""
    # Check Streamlit availability
    if not STREAMLIT_AVAILABLE:
        st.error("Streamlit not available. Install with: pip install fastreact-nano[web]")
        return

    # Page config
    st.set_page_config(
        page_title="FastReAct Nano",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize session
    if "web_session" not in st.session_state:
        st.session_state.web_session = WebSession()

    session = st.session_state.web_session
    session.initialize()

    # Render sidebar
    render_sidebar(session)

    # Main chat area
    st.title("Chat with FastReAct")

    # Render message history
    for msg in session.message_history:
        with st.chat_message(msg["role"]):
            # If message has events, show both final answer and events
            if "events" in msg and msg["events"]:
                # Show final answer if exists
                if msg.get("content"):
                    st.markdown(msg["content"])

                # Show expandable section for detailed events
                # expanded=True so events are visible by default
                with st.expander("Show detailed events", expanded=True):
                    for event_dict in msg["events"]:
                        # Render formatted event
                        st.markdown(format_event_for_streaming(event_dict))
            else:
                # No events, just show content
                st.markdown(msg["content"])

    # Event streaming container
    if session.event_buffer:
        with st.chat_message("assistant"):
            for event_dict in session.event_buffer:
                render_event(event_dict)
        session.event_buffer = []

    # Chat input
    if prompt := st.chat_input("Ask FastReAct anything..."):
        # Add user message to history
        session.add_message("user", prompt)

        # Render user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Execute agent with TRUE real-time streaming
        with st.chat_message("assistant"):
            try:
                # Use Streamlit's write_stream for TRUE real-time display
                st.write_stream(event_stream_generator(session, prompt))

            except Exception as e:
                st.error(f"[ERROR] {str(e)}")
                import traceback
                st.code(traceback.format_exc())

        # Save to history
        if session.event_buffer:
            final_events = [e for e in session.event_buffer
                          if e["type"] == EventType.SESSION_END]
            final_answer = ""
            if final_events:
                final_answer = final_events[-1].get("content", "")

            session.add_message("assistant", final_answer, events=session.event_buffer)
            session.event_buffer = []

        # Rerun to show in history
        st.rerun()


def main():
    """Main entry point"""
    render_chat_interface()


if __name__ == "__main__":
    main()
