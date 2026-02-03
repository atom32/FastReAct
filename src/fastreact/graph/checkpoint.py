"""
CheckpointManager - Git-native snapshot and rollback system

Handles workspace snapshots with git integration:
- Auto-detects git repositories
- Uses git stash for snapshots (when in git repo)
- Falls back to filesystem snapshots (when not in git)
- Clean rollback via git reset
"""

import os
import subprocess
import logging
import shutil
import tempfile
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================================
# Git Utils
# ============================================================================

def is_git_repo(path: str = ".") -> bool:
    """Check if directory is a git repository"""
    git_dir = os.path.join(path, ".git")
    return os.path.exists(git_dir)


def run_git_command(
    args: List[str],
    cwd: str = ".",
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    """
    Run git command safely

    Args:
        args: Git command arguments (e.g., ["status", "--short"])
        cwd: Working directory
        capture_output: Whether to capture stdout/stderr

    Returns:
        CompletedProcess result
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            check=False,  # Don't raise on non-zero exit
        )
        return result
    except FileNotFoundError:
        logger.warning("Git not found in PATH")
        raise


def get_git_status(cwd: str = ".") -> Dict[str, Any]:
    """Get git repository status"""
    if not is_git_repo(cwd):
        return {"in_git": False}

    try:
        # Get branch
        branch_result = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"

        # Get status
        status_result = run_git_command(["status", "--short"], cwd=cwd)
        has_changes = bool(status_result.stdout.strip()) if status_result.returncode == 0 else False

        # Get untracked files
        untracked_result = run_git_command(["ls-files", "--others", "--exclude-standard"], cwd=cwd)
        untracked_files = untracked_result.stdout.strip().split("\n") if untracked_result.returncode == 0 else []

        return {
            "in_git": True,
            "branch": branch,
            "has_changes": has_changes,
            "untracked_files": [f for f in untracked_files if f],
        }
    except Exception as e:
        logger.error(f"Failed to get git status: {e}")
        return {"in_git": False, "error": str(e)}


# ============================================================================
# Checkpoint Types
# ============================================================================

class CheckpointType(str):
    """Checkpoint storage type"""
    GIT_STASH = "git_stash"      # Use git stash (best for git repos)
    GIT_COMMIT = "git_commit"    # Use temporary git commit
    FILESYSTEM = "filesystem"     # Copy files to temp directory


# ============================================================================
# Git Checkpoint
# ============================================================================

@dataclass
class GitCheckpoint:
    """
    Git-based checkpoint using git stash or commit

    Advantages:
    - Fast (no file copying)
    - Space-efficient (git compression)
    - Clean rollback (git reset)
    - Preserves full history
    """
    checkpoint_id: str
    timestamp: datetime
    checkpoint_type: str  # "stash" or "commit"
    git_ref: str  # Stash ref or commit hash
    branch: str
    has_untracked: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "timestamp": self.timestamp.isoformat(),
            "checkpoint_type": self.checkpoint_type,
            "git_ref": self.git_ref,
            "branch": self.branch,
            "has_untracked": self.has_untracked,
            "metadata": self.metadata,
        }


# ============================================================================
# Filesystem Checkpoint
# ============================================================================

@dataclass
class FilesystemCheckpoint:
    """
    Filesystem-based checkpoint (fallback when not in git)

    Copies changed files to temporary directory.
    """
    checkpoint_id: str
    timestamp: datetime
    temp_dir: str
    changed_files: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def cleanup(self):
        """Remove temporary directory"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.debug(f"Cleaned up checkpoint: {self.checkpoint_id}")
        except Exception as e:
            logger.error(f"Failed to cleanup checkpoint {self.checkpoint_id}: {e}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "timestamp": self.timestamp.isoformat(),
            "checkpoint_type": "filesystem",
            "temp_dir": self.temp_dir,
            "changed_files": self.changed_files,
            "metadata": self.metadata,
        }


# ============================================================================
# Checkpoint Manager
# ============================================================================

class CheckpointManager:
    """
    Git-native checkpoint and rollback manager

    Auto-detects git repository and uses appropriate strategy:
    - Git repo: Use git stash or commit
    - No git: Use filesystem snapshots

    Usage:
        manager = CheckpointManager(workspace_path="/path/to/project")

        # Create checkpoint
        checkpoint_id = manager.create_checkpoint(
            label="Before risky operation",
            include_untracked=True
        )

        # Rollback
        success = manager.rollback(checkpoint_id)

        # Cleanup
        manager.cleanup_all()
    """

    def __init__(
        self,
        workspace_path: str = ".",
        prefer_stash: bool = True,
    ):
        """
        Initialize CheckpointManager

        Args:
            workspace_path: Path to workspace directory
            prefer_stash: Prefer git stash over commits (default: True)
        """
        self.workspace_path = os.path.abspath(workspace_path)
        self.prefer_stash = prefer_stash

        # Storage
        self._git_checkpoints: Dict[str, GitCheckpoint] = {}
        self._fs_checkpoints: Dict[str, FilesystemCheckpoint] = {}

        # Detect git
        self._in_git = is_git_repo(self.workspace_path)
        self._git_status = get_git_status(self.workspace_path) if self._in_git else {}

        logger.info(f"CheckpointManager initialized for: {self.workspace_path}")
        logger.info(f"  Git detected: {self._in_git}")

        if self._in_git:
            logger.info(f"  Branch: {self._git_status.get('branch', 'unknown')}")
            logger.info(f"  Has changes: {self._git_status.get('has_changes', False)}")

    # ========================================================================
    # Checkpoint Creation
    # ========================================================================

    def create_checkpoint(
        self,
        label: str = None,
        include_untracked: bool = True,
    ) -> str:
        """
        Create checkpoint of current workspace state

        Args:
            label: Optional label for checkpoint
            include_untracked: Include untracked files (git only)

        Returns:
            Checkpoint ID
        """
        checkpoint_id = f"ckpt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if self._in_git:
            checkpoint = self._create_git_checkpoint(
                checkpoint_id,
                label,
                include_untracked
            )
            self._git_checkpoints[checkpoint_id] = checkpoint
        else:
            checkpoint = self._create_fs_checkpoint(checkpoint_id, label)
            self._fs_checkpoints[checkpoint_id] = checkpoint

        logger.info(f"Created checkpoint: {checkpoint_id} ({label})")
        return checkpoint_id

    def _create_git_checkpoint(
        self,
        checkpoint_id: str,
        label: str = None,
        include_untracked: bool = True,
    ) -> GitCheckpoint:
        """Create git-based checkpoint using stash or commit"""

        # Prepare stash message
        stash_msg = f"checkpoint:{checkpoint_id}"
        if label:
            stash_msg += f" - {label}"

        if self.prefer_stash:
            # Use git stash
            return self._stash_checkpoint(checkpoint_id, stash_msg, include_untracked)
        else:
            # Use git commit
            return self._commit_checkpoint(checkpoint_id, stash_msg)

    def _stash_checkpoint(
        self,
        checkpoint_id: str,
        stash_msg: str,
        include_untracked: bool,
    ) -> GitCheckpoint:
        """Create checkpoint using git stash"""

        args = ["stash", "push", "-m", stash_msg]

        if include_untracked:
            args.append("-u")  # Include untracked files

        result = run_git_command(args, cwd=self.workspace_path)

        if result.returncode != 0:
            logger.warning(f"Git stash failed: {result.stderr}")
            # Fallback to commit
            return self._commit_checkpoint(checkpoint_id, stash_msg)

        # Get stash ref
        # Stash is created as stash@{0}, stash@{1}, etc.
        # We need to get the reference to this specific stash
        ref_result = run_git_command(["stash", "list", "--format=%H"], cwd=self.workspace_path)
        stash_hash = ref_result.stdout.split("\n")[0] if ref_result.returncode == 0 else "unknown"

        return GitCheckpoint(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.now(),
            checkpoint_type="stash",
            git_ref=f"stash@{{0}}",  # Most recent stash
            branch=self._git_status.get("branch", "unknown"),
            has_untracked=include_untracked,
            metadata={"label": stash_msg}
        )

    def _commit_checkpoint(
        self,
        checkpoint_id: str,
        commit_msg: str,
    ) -> GitCheckpoint:
        """Create checkpoint using temporary git commit"""

        # Create temporary branch for checkpoint
        temp_branch = f"checkpoint/{checkpoint_id}"

        # Create orphan branch (no history)
        run_git_command(["checkout", "--orphan", temp_branch], cwd=self.workspace_path)

        # Add all files
        run_git_command(["add", "-A"], cwd=self.workspace_path)

        # Commit
        result = run_git_command(["commit", "-m", commit_msg], cwd=self.workspace_path)

        if result.returncode != 0:
            logger.error(f"Git commit failed: {result.stderr}")
            # Return to original branch
            run_git_command(["checkout", "-"], cwd=self.workspace_path)
            raise RuntimeError("Failed to create git checkpoint")

        # Get commit hash
        hash_result = run_git_command(["rev-parse", "HEAD"], cwd=self.workspace_path)
        commit_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else "unknown"

        # Return to original branch
        run_git_command(["checkout", "-"], cwd=self.workspace_path)

        return GitCheckpoint(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.now(),
            checkpoint_type="commit",
            git_ref=commit_hash,
            branch=temp_branch,
            has_untracked=True,
            metadata={"label": commit_msg}
        )

    def _create_fs_checkpoint(
        self,
        checkpoint_id: str,
        label: str = None,
    ) -> FilesystemCheckpoint:
        """Create filesystem-based checkpoint"""

        # Create temp directory
        temp_dir = tempfile.mkdtemp(prefix=f"ckpt_{checkpoint_id}_")

        # Copy workspace files
        changed_files = []
        for root, dirs, files in os.walk(self.workspace_path):
            # Skip .git directory
            dirs[:] = [d for d in dirs if d != ".git"]

            for file in files:
                src_file = os.path.join(root, file)
                rel_path = os.path.relpath(src_file, self.workspace_path)
                dst_file = os.path.join(temp_dir, rel_path)

                # Create directory structure
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)

                # Copy file
                shutil.copy2(src_file, dst_file)
                changed_files.append(rel_path)

        logger.info(f"Filesystem checkpoint: {len(changed_files)} files copied to {temp_dir}")

        return FilesystemCheckpoint(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.now(),
            temp_dir=temp_dir,
            changed_files=changed_files,
            metadata={"label": label}
        )

    # ========================================================================
    # Rollback
    # ========================================================================

    def rollback(self, checkpoint_id: str) -> bool:
        """
        Rollback workspace to checkpoint state

        Args:
            checkpoint_id: Checkpoint to rollback to

        Returns:
            True if successful
        """
        logger.info(f"Rolling back to checkpoint: {checkpoint_id}")

        # Check git checkpoints first
        if checkpoint_id in self._git_checkpoints:
            return self._rollback_git(checkpoint_id)

        # Check filesystem checkpoints
        elif checkpoint_id in self._fs_checkpoints:
            return self._rollback_fs(checkpoint_id)

        else:
            logger.error(f"Checkpoint not found: {checkpoint_id}")
            return False

    def _rollback_git(self, checkpoint_id: str) -> bool:
        """Rollback using git"""

        checkpoint = self._git_checkpoints[checkpoint_id]

        if checkpoint.checkpoint_type == "stash":
            return self._rollback_stash(checkpoint)
        elif checkpoint.checkpoint_type == "commit":
            return self._rollback_commit(checkpoint)
        else:
            logger.error(f"Unknown git checkpoint type: {checkpoint.checkpoint_type}")
            return False

    def _rollback_stash(self, checkpoint: GitCheckpoint) -> bool:
        """Rollback using git stash pop"""

        # Stash pop applies the stash and removes it from stash list
        result = run_git_command(
            ["stash", "pop"],
            cwd=self.workspace_path
        )

        if result.returncode != 0:
            logger.error(f"Git stash pop failed: {result.stderr}")

            # Try reset instead
            logger.info("Attempting git reset instead")
            return self._rollback_git_reset(checkpoint)

        logger.info("Git stash pop successful")
        return True

    def _rollback_commit(self, checkpoint: GitCheckpoint) -> bool:
        """Rollback using git reset"""

        # Checkout the commit
        result = run_git_command(
            ["checkout", checkpoint.git_ref],
            cwd=self.workspace_path
        )

        if result.returncode != 0:
            logger.error(f"Git checkout failed: {result.stderr}")
            return False

        logger.info(f"Git checkout to {checkpoint.git_ref[:8]} successful")
        return True

    def _rollback_git_reset(self, checkpoint: GitCheckpoint) -> bool:
        """Rollback using git reset --hard"""

        # Hard reset to the stash state
        # First, try to find the stash
        result = run_git_command(
            ["stash", "list"],
            cwd=self.workspace_path
        )

        if result.returncode != 0:
            logger.error("Cannot list git stashes")
            return False

        # Apply the stash
        apply_result = run_git_command(
            ["stash", "apply"],
            cwd=self.workspace_path
        )

        if apply_result.returncode != 0:
            logger.error(f"Git stash apply failed: {apply_result.stderr}")
            return False

        # Drop the stash
        run_git_command(["stash", "drop"], cwd=self.workspace_path)

        logger.info("Git reset via stash apply successful")
        return True

    def _rollback_fs(self, checkpoint_id: str) -> bool:
        """Rollback using filesystem checkpoint"""

        checkpoint = self._fs_checkpoints[checkpoint_id]

        # Restore files from temp directory
        for file_path in checkpoint.changed_files:
            src_file = os.path.join(checkpoint.temp_dir, file_path)
            dst_file = os.path.join(self.workspace_path, file_path)

            # Create directory structure
            os.makedirs(os.path.dirname(dst_file), exist_ok=True)

            # Copy file back
            shutil.copy2(src_file, dst_file)

        logger.info(f"Restored {len(checkpoint.changed_files)} files from checkpoint")
        return True

    # ========================================================================
    # Cleanup
    # ========================================================================

    def cleanup(self, checkpoint_id: str):
        """Clean up a specific checkpoint"""
        if checkpoint_id in self._fs_checkpoints:
            self._fs_checkpoints[checkpoint_id].cleanup()
            del self._fs_checkpoints[checkpoint_id]

        if checkpoint_id in self._git_checkpoints:
            # Git checkpoints don't need cleanup
            # But we can remove from tracking
            del self._git_checkpoints[checkpoint_id]

    def cleanup_all(self):
        """Clean up all checkpoints"""
        for checkpoint_id in list(self._fs_checkpoints.keys()):
            self.cleanup(checkpoint_id)

        self._git_checkpoints.clear()

    # ========================================================================
    # Status
    # ========================================================================

    def get_checkpoint_info(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a checkpoint"""
        if checkpoint_id in self._git_checkpoints:
            return self._git_checkpoints[checkpoint_id].to_dict()
        elif checkpoint_id in self._fs_checkpoints:
            return self._fs_checkpoints[checkpoint_id].to_dict()
        else:
            return None

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all checkpoints"""
        checkpoints = []

        for ckpt in self._git_checkpoints.values():
            checkpoints.append(ckpt.to_dict())

        for ckpt in self._fs_checkpoints.values():
            checkpoints.append(ckpt.to_dict())

        return sorted(checkpoints, key=lambda x: x["timestamp"])

    def get_status(self) -> Dict[str, Any]:
        """Get checkpoint manager status"""
        return {
            "workspace_path": self.workspace_path,
            "in_git": self._in_git,
            "git_status": self._git_status,
            "git_checkpoints": len(self._git_checkpoints),
            "fs_checkpoints": len(self._fs_checkpoints),
            "prefer_stash": self.prefer_stash,
        }


# ============================================================================
# Convenience Function
# ============================================================================

def create_checkpoint_manager(
    workspace_path: str = ".",
    prefer_stash: bool = True,
) -> CheckpointManager:
    """
    Create checkpoint manager for workspace

    Args:
        workspace_path: Path to workspace directory
        prefer_stash: Prefer git stash over commits

    Returns:
        CheckpointManager instance
    """
    return CheckpointManager(
        workspace_path=workspace_path,
        prefer_stash=prefer_stash,
    )
