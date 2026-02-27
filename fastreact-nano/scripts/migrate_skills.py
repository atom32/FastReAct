#!/usr/bin/env python3
"""
Migration script to convert openclaw skills to FastReAct format

openclaw skill format:
- TypeScript/JavaScript files
- Inline skill definitions

FastReAct skill format:
- YAML frontmatter + markdown (SKILL.md)
- Organized in skill directories

Usage:
    python3 scripts/migrate_skills.py \\
        --openclaw-dir /path/to/openclaw \\
        --output-dir skills/builtin \\
        --dry-run

Author: FastReAct Team
Version: 1.0.0
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# Mapping of openclaw tools to FastReAct MCP servers
TOOL_TO_MCP_MAP: Dict[str, str] = {
    "read_file": "filesystem",
    "write_file": "filesystem",
    "edit_file": "filesystem",
    "list_dir": "filesystem",
    "exec": "shell",
    "bash": "shell",
    "web_search": "brave_search",
    "git": "git_ops",
    "git_commit": "git_ops",
    "git_push": "git_ops",
    "git_log": "git_ops",
}


def parse_openclaw_skill(skill_path: Path) -> Optional[Dict[str, Any]]:
    """
    Parse openclaw skill definition

    This function handles the openclaw skill format which may be:
    - TypeScript .skill files
    - JSON skill definitions
    - Markdown skill files

    Args:
        skill_path: Path to the openclaw skill file

    Returns:
        Dictionary with skill data or None if parsing fails
    """
    if not skill_path.exists():
        return None

    content = skill_path.read_text(encoding='utf-8')

    # Try JSON format first
    if skill_path.suffix in ['.json', '.skill']:
        try:
            # Try parsing as JSON
            data = json.loads(content)
            return normalize_openclaw_skill(data)
        except json.JSONDecodeError:
            pass

    # Try TypeScript-style skill definition
    # Format: export const skill = { name: "...", ... }
    ts_match = re.search(r'export\s+(const|let|var)\s+\w+\s*=\s*({[^}]+})', content, re.DOTALL)
    if ts_match:
        try:
            # Extract JSON object from TS syntax
            json_str = ts_match.group(2)
            # Clean up TS syntax
            json_str = re.sub(r'(\w+)\s*:', r'"\1":', json_str)  # Quote keys
            json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas
            data = json.loads(json_str)
            return normalize_openclaw_skill(data)
        except (json.JSONDecodeError, ValueError):
            pass

    # Try markdown with frontmatter
    if skill_path.suffix == '.md':
        return parse_markdown_skill(content)

    # Fallback: extract basic info from filename
    return {
        'name': skill_path.stem,
        'description': f"Skill migrated from {skill_path.name}",
        'tags': [],
        'tools': [],
        'content': content[:1000]  # Truncate if too long
    }


def normalize_openclaw_skill(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize openclaw skill data to standard format"""
    return {
        'name': data.get('name') or data.get('skill_name', 'unknown'),
        'description': data.get('description') or data.get('desc', ''),
        'tags': data.get('tags', []),
        'tools': data.get('tools', data.get('required_tools', [])),
        'content': data.get('content', data.get('instructions', '')),
        'author': data.get('author', 'Migrated from openclaw'),
        'version': data.get('version', '1.0.0')
    }


def parse_markdown_skill(content: str) -> Optional[Dict[str, Any]]:
    """Parse markdown skill with YAML frontmatter"""
    # Extract YAML frontmatter
    frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
    if not frontmatter_match:
        return None

    try:
        import yaml
        frontmatter = yaml.safe_load(frontmatter_match.group(1))
        body = frontmatter_match.group(2)

        return {
            'name': frontmatter.get('name', 'unknown'),
            'description': frontmatter.get('description', ''),
            'tags': frontmatter.get('tags', []),
            'tools': frontmatter.get('tools', []),
            'content': body,
            'author': frontmatter.get('author', 'Migrated from openclaw'),
            'version': frontmatter.get('version', '1.0.0')
        }
    except ImportError:
        # PyYAML not available, do basic parsing
        return {
            'name': 'unknown',
            'description': '',
            'tags': [],
            'tools': [],
            'content': frontmatter_match.group(2),
        }


def convert_to_skill_md(skill_data: Dict[str, Any]) -> str:
    """
    Convert skill data to FastReAct SKILL.md format

    Args:
        skill_data: Normalized skill data dictionary

    Returns:
        Complete SKILL.md content as string
    """
    name = skill_data['name']
    description = skill_data.get('description', f"Skill: {name}")
    tags = skill_data.get('tags', [])
    tools = skill_data.get('tools', [])
    content = skill_data.get('content', '')
    author = skill_data.get('author', 'Migrated from openclaw')
    version = skill_data.get('version', '1.0.0')

    # Convert tools to MCP servers
    mcp_servers = convert_tools_to_mcp(tools)

    # Build YAML frontmatter
    frontmatter = f"""---
name: {name}
description: {description}
version: {version}
tags: {json.dumps(tags, ensure_ascii=False)}
author: {author}
mcp_servers: {json.dumps(mcp_servers, ensure_ascii=False)}
recommended_tools: {json.dumps(tools, ensure_ascii=False)}
---

# {name.replace('_', ' ').title()}

{description}

## When to Use

Use this skill when you need to:
{generate_use_cases(content)}

## How It Works

{content if content else "See instructions below for usage details."}

## Examples

Coming soon - add examples as you use this skill.

---

*Migrated from openclaw to FastReAct*
"""

    return frontmatter


def convert_tools_to_mcp(tools: List[str]) -> List[str]:
    """
    Map tool names to MCP server names

    Args:
        tools: List of tool names from openclaw

    Returns:
        List of MCP server names
    """
    mcps: Set[str] = set()
    for tool in tools:
        if tool in TOOL_TO_MCP_MAP:
            mcps.add(TOOL_TO_MCP_MAP[tool])
    return sorted(list(mcps))


def generate_use_cases(content: str) -> str:
    """Generate use case bullets from content"""
    if not content:
        return "- Use this skill for related tasks"

    # Try to extract use cases from content
    use_cases = []

    # Look for bullet points or numbered lists
    bullet_matches = re.findall(r'^[\s]*[-*]\s*(.+)$', content, re.MULTILINE)
    if bullet_matches:
        use_cases.extend([f"- {match.strip()}" for match in bullet_matches[:3]])

    # If no bullets found, provide generic
    if not use_cases:
        use_cases = [
            f"- Handle tasks related to this skill",
            f"- Apply best practices for this domain",
        ]

    return '\n'.join(use_cases)


def migrate_skill(
    openclaw_skill_path: Path,
    fastreact_skills_dir: Path,
    dry_run: bool = False
) -> Optional[Path]:
    """
    Migrate a single skill from openclaw to FastReAct format

    Args:
        openclaw_skill_path: Path to openclaw skill file
        fastreact_skills_dir: Target directory for FastReAct skills
        dry_run: If True, show what would be done without making changes

    Returns:
        Path to created SKILL.md file, or None if dry_run or failed
    """
    # Parse openclaw skill
    skill_data = parse_openclaw_skill(openclaw_skill_path)
    if not skill_data:
        print(f"[WARNING] Failed to parse: {openclaw_skill_path}")
        return None

    skill_name = skill_data['name']
    if not skill_name or skill_name == 'unknown':
        print(f"[WARNING] Skipping skill with no name: {openclaw_skill_path}")
        return None

    # Convert to SKILL.md format
    skill_md = convert_to_skill_md(skill_data)

    # Create output path
    output_dir = fastreact_skills_dir / skill_name
    output_path = output_dir / "SKILL.md"

    if dry_run:
        print(f"[DRY RUN] Would create: {output_path}")
        print(f"           Name: {skill_name}")
        print(f"           Description: {skill_data.get('description', '')[:50]}...")
        return None

    # Create directory and write file
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(skill_md, encoding='utf-8')

    print(f"[OK] Migrated skill: {skill_name} -> {output_path}")
    return output_path


def find_openclaw_skills(openclaw_dir: Path) -> List[Path]:
    """
    Find all skill files in openclaw directory

    Args:
        openclaw_dir: Path to openclaw repository

    Returns:
        List of skill file paths
    """
    skill_files: List[Path] = []

    # Common skill directories in openclaw
    search_patterns = [
        "skills/**/*.skill",
        "skills/**/*.json",
        "skills/**/*.md",
        "src/skills/**/*.ts",
        "src/skills/**/*.js",
        "agents/skills/**/*.ts",
    ]

    for pattern in search_patterns:
        skill_files.extend(openclaw_dir.glob(pattern))

    # Also check for flat skill directories
    for skill_dir in ["skills", "src/skills", "agents/skills"]:
        skill_path = openclaw_dir / skill_dir
        if skill_path.is_dir():
            for item in skill_path.iterdir():
                if item.is_file() and item.suffix in ['.skill', '.json', '.md', '.ts', '.js']:
                    skill_files.append(item)

    # Remove duplicates while preserving order
    seen = set()
    unique_files = []
    for f in skill_files:
        if f not in seen:
            seen.add(f)
            unique_files.append(f)

    return unique_files


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Migrate openclaw skills to FastReAct format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be migrated
  python3 scripts/migrate_skills.py --openclaw-dir /path/to/openclaw --dry-run

  # Migrate all skills
  python3 scripts/migrate_skills.py --openclaw-dir /path/to/openclaw

  # Migrate to custom output directory
  python3 scripts/migrate_skills.py --openclaw-dir /path/to/openclaw --output-dir skills/community
        """
    )

    parser.add_argument(
        '--openclaw-dir',
        required=True,
        type=Path,
        help='Path to openclaw repository'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('skills/builtin'),
        help='Output directory for migrated skills (default: skills/builtin)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--pattern',
        default=None,
        help='Only migrate skills matching this pattern (e.g., "code_*")'
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.openclaw_dir.exists():
        print(f"[ERROR] Openclaw directory not found: {args.openclaw_dir}", file=sys.stderr)
        sys.exit(1)

    # Find all skill files
    print(f"[INFO] Searching for skill files in: {args.openclaw_dir}")
    skill_files = find_openclaw_skills(args.openclaw_dir)

    if not skill_files:
        print(f"[WARNING] No skill files found in {args.openclaw_dir}")
        print("[INFO] Checked locations:")
        print("  - skills/**/*.skill")
        print("  - skills/**/*.json")
        print("  - skills/**/*.md")
        print("  - src/skills/**/*.ts")
        print("  - agents/skills/**/*.ts")
        sys.exit(0)

    print(f"[INFO] Found {len(skill_files)} skill files")

    # Filter by pattern if specified
    if args.pattern:
        import fnmatch
        filtered = [f for f in skill_files if fnmatch.fnmatch(f.stem, args.pattern)]
        print(f"[INFO] Filtered to {len(filtered)} files matching pattern: {args.pattern}")
        skill_files = filtered

    # Migrate skills
    success_count = 0
    failure_count = 0

    for skill_file in skill_files:
        result = migrate_skill(skill_file, args.output_dir, args.dry_run)
        if result:
            success_count += 1
        else:
            failure_count += 1

    # Print summary
    print()
    print("=" * 60)
    print("Migration Summary:")
    print(f"  Total files: {len(skill_files)}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {failure_count}")
    print("=" * 60)

    if failure_count > 0:
        print("[WARNING] Some skills failed to migrate. Check warnings above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
