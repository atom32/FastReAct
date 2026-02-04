"""
Clean up documentation files

Organizes docs into KEEP, ARCHIVE, and DELETE categories
"""

import os
import shutil
from pathlib import Path
from datetime import datetime


# Categories
KEEP_CORE = [
    "README.md",
    "CLAUDE.md",
]

KEEP_FEATURES = [
    "VERSION_MANAGEMENT.md",
    "MULTI_TENANT_WORKSPACE.md",
    "SESSION_RESUME.md",
    "WORKSPACE_ISOLATION.md",
    "CROSS_PLATFORM_SUMMARY.md",
    "MCP_INTEGRATION_SUCCESS.md",
]

KEEP_TECHNICAL = [
    "CHANGELOG.md",
    "IEL.md",
    "SECURITY.md",
    "CONFIG.md",
    "INSTALLATION.md",
]

KEEP_DOCKER = [
    "DOCKER_DEPLOYMENT.md",
]

ARCHIVE = [
    "TEST_REPORT.md",
    "TEST_SUITE_SUMMARY.md",
    "INTEGRATION_TESTS.md",
    "FEATURES_SUMMARY.md",
    "MCP_NATIVE_SUCCESS.md",
    "SESSION_CONTEXT.md",
    "V0_DEV_PROMPT.md",
    "WSL_QUICKSTART.md",
    "IEL_ANALYSIS.md",
    "IEL_COMPLETE_GUIDE.md",
    "IEL_PHASE1_PHASE2.md",
    "IEL_PHASE3.md",
    "IEL_PHASE4_PHASE5.md",
]

DELETE = [
    "TODO.md",
    "FEATURES.md",
    "CROSS_PLATFORM_CHECK.md",
    "README_DOCKER.md",
    "MCP_VERIFICATION.md",
    "SECURITY_AUDIT.md",
    "EXAMPLES.md",
    "QUICKSTART_FRONTEND.md",
    "FEATURES_SUMMARY.md",  # Duplicate in archive
    "MCP_NATIVE_SUCCESS.md",  # Duplicate in archive
    "VERSION_UNIFIED.md",  # Consolidate into VERSION_MANAGEMENT
]


def cleanup_docs():
    """Clean up documentation files"""
    root = Path.cwd()

    # Create archive directory
    archive_dir = root / "docs_archive"
    if not archive_dir.exists():
        archive_dir.mkdir()
        print(f"Created archive directory: {archive_dir}")

    # Get all markdown files
    md_files = list(root.glob('*.md'))

    kept = []
    archived = []
    deleted = []

    for md_file in md_files:
        filename = md_file.name

        # Skip if already processed
        if not md_file.exists():
            continue

        if filename in KEEP_CORE:
        filename = md_file.name

        if filename in KEEP_CORE:
            kept.append(filename)
        elif filename in KEEP_FEATURES:
            kept.append(filename)
        elif filename in KEEP_TECHNICAL:
            kept.append(filename)
        elif filename in KEEP_DOCKER:
            kept.append(filename)
        elif filename in ARCHIVE:
            # Move to archive
            target = archive_dir / filename
            shutil.move(str(md_file), str(target))
            archived.append(filename)
        elif filename in DELETE:
            # Delete file
            md_file.unlink()
            deleted.append(filename)
        else:
            # Uncategorized - keep for now
            kept.append(f"(review) {filename}")

    # Print summary
    print("\n" + "="*70)
    print("Documentation Cleanup Summary")
    print("="*70)

    print(f"\nTotal files: {len(md_files)}")
    print(f"Kept:      {len(kept)}")
    print(f"Archived:  {len(archived)}")
    print(f"Deleted:   {len(deleted)}")

    if archived:
        print(f"\nArchived files (moved to docs_archive/):")
        for f in archived:
            print(f"  - {f}")

    if deleted:
        print(f"\nDeleted files:")
        for f in deleted:
            print(f"  - {f}")

    # Create archive index
    index_file = archive_dir / "INDEX.md"
    with open(str(index_file), 'w', encoding='utf-8') as f:
        f.write("# Documentation Archive\n\n")
        f.write(f"Archived on: {datetime.now().isoformat()}\n\n")
        f.write("This directory contains historical and development-process documentation.\n\n")
        f.write("## Archived Files\n\n")
        for f in sorted(archived):
            f.write(f"- {f}\n")

    print(f"\nCreated archive index: {index_file}")

    print("\n" + "="*70)
    print("Cleanup completed!")
    print("="*70)


if __name__ == "__main__":
    cleanup_docs()
