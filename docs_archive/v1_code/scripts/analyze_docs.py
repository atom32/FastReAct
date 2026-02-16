"""
Analyze and categorize project documentation files

Proposes which to keep, archive, or delete
"""

from pathlib import Path
from typing import Dict, List
import re


# Documentation categories
CORE_DOCS = [
    "README.md",
    "CLAUDE.md",
    "QUICKSTART.md",
    "CONFIG.md",
    "INSTALLATION.md",
]

FEATURE_DOCS = [
    "VERSION_MANAGEMENT.md",
    "MULTI_TENANT_WORKSPACE.md",
    "SESSION_RESUME.md",
    "WORKSPACE_ISOLATION.md",
    "CROSS_PLATFORM_SUMMARY.md",
    "MCP_INTEGRATION_SUCCESS.md",
]

TECHNICAL_DOCS = [
    "IEL.md",  # If it's the main IEL guide
    "SECURITY.md",
    "CHANGELOG.md",
]

DOCKER_DOCS = [
    "DOCKER_DEPLOYMENT.md",
]

# Docs to archive (historical/development process)
ARCHIVE_DOCS = [
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

# Docs to delete (duplicates or obsolete)
DELETE_DOCS = [
    "TODO.md",
    "FEATURES.md",
    "CROSS_PLATFORM_CHECK.md",
    "README_DOCKER.md",
    "MCP_VERIFICATION.md",
    "SECURITY_AUDIT.md",
    "EXAMPLES.md",
    "QUICKSTART_FRONTEND.md",
    "FEATURES_SUMMARY.md",
    "MCP_NATIVE_SUCCESS.md",
]


def analyze_md_file(filepath: Path) -> Dict:
    """Analyze a markdown file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.count('\n')

        # Extract title from first heading
        title = "No title"
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()

        return {
            'file': filepath.name,
            'title': title,
            'lines': lines,
            'size': filepath.stat().st_size,
        }
    except:
        return {
            'file': filepath.name,
            'title': 'Error reading',
            'lines': 0,
            'size': 0,
        }


def main():
    """Main analysis"""
    root = Path.cwd()
    md_files = list(root.glob('*.md'))

    print("\n" + "="*70)
    print("FastReAct Documentation Analysis")
    print("="*70)
    print(f"\nTotal markdown files: {len(md_files)}")

    # Analyze all files
    files_info = []
    for md_file in md_files:
        info = analyze_md_file(md_file)
        files_info.append(info)

    # Sort by name
    files_info.sort(key=lambda x: x['file'])

    # Categorize
    print("\n" + "-"*70)
    print("SUGGESTED ACTIONS:")
    print("-"*70)

    categories = {
        'KEEP (Core)': [f for f in files_info if f['file'] in CORE_DOCS],
        'KEEP (Features)': [f for f in files_info if f['file'] in FEATURE_DOCS],
        'KEEP (Technical)': [f for f in files_info if f['file'] in TECHNICAL_DOCS],
        'KEEP (Docker)': [f for f in files_info if f['file'] in DOCKER_DOCS],
        'ARCHIVE': [f for f in files_info if f['file'] in ARCHIVE_DOCS],
        'DELETE': [f for f in files_info if f['file'] in DELETE_DOCS],
        'UNCATEGORIZED': [f for f in files_info
                          if f['file'] not in CORE_DOCS
                          and f['file'] not in FEATURE_DOCS
                          and f['file'] not in TECHNICAL_DOCS
                          and f['file'] not in DOCKER_DOCS
                          and f['file'] not in ARCHIVE_DOCS
                          and f['file'] not in DELETE_DOCS],
    }

    for category, files in categories.items():
        if files:
            print(f"\n{category} ({len(files)} files):")
            for f in files:
                # Simple ASCII-only output
                title_clean = f['title'].encode('ascii', 'ignore').decode('ascii')[:40]
                print(f"  - {f['file']:<40} ({f['lines']:4} lines) {title_clean}")

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    total_keep = sum(len(files) for files in categories.values() if 'KEEP' in str(files))
    total_archive = len(categories['ARCHIVE'])
    total_delete = len(categories['DELETE'])
    total_unknown = len(categories['UNCATEGORIZED'])

    print(f"Keep:   {total_keep} files")
    print(f"Archive: {total_archive} files")
    print(f"Delete: {total_delete} files")
    print(f"Review: {total_unknown} files")

    return categories


if __name__ == "__main__":
    main()
