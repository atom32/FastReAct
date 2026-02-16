"""
Session detection module for CLI startup

Detects and prompts user about existing sessions before starting REPL.
Similar to Claude Code's behavior.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime


def find_session_files(start_dir: Optional[Path] = None) -> List[Path]:
    """Find all session files in the given directory

    Args:
        start_dir: Directory to search (default: current working directory)

    Returns:
        List of session file paths
    """
    if start_dir is None:
        start_dir = Path.cwd()

    session_files = []

    # Check for .fastreact/sessions directory
    sessions_dir = start_dir / ".fastreact" / "sessions"
    if sessions_dir.exists():
        for file in sessions_dir.glob("*.json"):
            session_files.append(file)

    # Check for autosave files in .fastreact
    autosave_dir = start_dir / ".fastreact"
    if autosave_dir.exists():
        for file in autosave_dir.glob("autosave_*.json"):
            session_files.append(file)

    # Sort by modification time (newest first)
    session_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    return session_files


def get_session_info(session_file: Path) -> Dict[str, Any]:
    """Get session information from file

    Args:
        session_file: Path to session file

    Returns:
        Dictionary with session information
    """
    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract relevant information
        info = {
            "file": session_file,
            "filename": session_file.name,
            "modified": datetime.fromtimestamp(session_file.stat().st_mtime),
            "message_count": len(data.get("messages", [])),
            "title": data.get("title", "Untitled"),
            "created_at": data.get("timestamp"),
            "has_variables": bool(data.get("variables")),
        }

        return info
    except Exception as e:
        return {
            "file": session_file,
            "filename": session_file.name,
            "error": str(e),
        }


def format_session_info(info: Dict[str, Any]) -> str:
    """Format session information for display

    Args:
        info: Session information dictionary

    Returns:
        Formatted string
    """
    if "error" in info:
        return f"  [ERROR] {info['filename']}: {info['error']}"

    lines = [
        f"  Title: {info['title']}",
        f"  Messages: {info['message_count']}",
        f"  Modified: {info['modified'].strftime('%Y-%m-%d %H:%M:%S')}",
        f"  File: {info['filename']}",
    ]

    if info['has_variables']:
        lines.append(f"  Variables: Yes")

    return "\n".join(lines)


def prompt_user_to_resume() -> bool:
    """Prompt user whether to resume session

    Returns:
        True to resume, False to exit
    """
    import sys

    while True:
        try:
            response = input("\nContinue? [Y/n] ").strip().lower()
            if response in ('', 'y', 'yes'):
                return True
            elif response in ('n', 'no', 'q', 'quit', 'exit'):
                return False
            else:
                print("Please enter 'y' or 'n'")
        except (EOFError, KeyboardInterrupt):
            print("\n")
            return False


def check_and_prompt(
    start_dir: Optional[Path] = None,
    auto_resume: bool = False
) -> Optional[Path]:
    """Check for existing sessions and prompt user

    Args:
        start_dir: Directory to check (default: current working directory)
        auto_resume: If True, automatically resume latest session without prompting

    Returns:
        Path to session file if user chooses to resume, None otherwise
    """
    session_files = find_session_files(start_dir)

    if not session_files:
        return None

    # Get information about the most recent session
    latest = get_session_info(session_files[0])

    if "error" in latest:
        # Session file is corrupted, skip prompt
        return None

    # Display session information
    print("\n" + "=" * 70)
    print("Previous session detected:")
    print("=" * 70)
    print(format_session_info(latest))
    print("=" * 70)

    # Auto-resume or prompt user
    if auto_resume:
        print("\nAuto-resuming latest session...")
        return latest['file']
    else:
        if prompt_user_to_resume():
            return latest['file']
        else:
            return None


def get_latest_session(start_dir: Optional[Path] = None) -> Optional[Path]:
    """Get the latest session file without prompting

    Args:
        start_dir: Directory to check (default: current working directory)

    Returns:
        Path to latest session file, or None if no sessions found
    """
    session_files = find_session_files(start_dir)
    return session_files[0] if session_files else None


def should_resume_session(
    start_dir: Optional[Path] = None,
    force_prompt: bool = True
) -> tuple[bool, Optional[Path]]:
    """Determine whether to resume existing session

    This is the main entry point for session detection.
    Should be called before starting the REPL.

    Args:
        start_dir: Directory to check (default: current working directory)
        force_prompt: If True, always prompt user. If False, check env var.

    Returns:
        Tuple of (should_resume: bool, session_file: Optional[Path])
    """
    # Check environment variable
    if not force_prompt:
        auto_resume = os.environ.get("FASTREACT_AUTO_RESUME", "").lower() in ('1', 'true', 'yes')
        if auto_resume:
            session_file = get_latest_session(start_dir)
            return (session_file is not None, session_file)

    # Prompt user
    session_file = check_and_prompt(start_dir)
    return (session_file is not None, session_file)
