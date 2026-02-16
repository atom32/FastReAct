"""
Check and clean hardcoded values and emoji from the codebase

Ensures cross-platform compatibility (Windows/Mac/Linux)
"""

import os
import re
from pathlib import Path
from typing import List, Tuple


# Emoji ranges
EMOJI_PATTERNS = [
    re.compile(r'[\u2600-\u27BF]'),  # Misc symbols
    re.compile(r'[\u2B00-\u2BFF]'),  # Arrow/Geometric
    re.compile(r'[\u1F300-\u1F9FF]'),  # Misc symbols and pictographs
    re.compile(r'[\u1F600-\u1F64F]'),  # Emoticons
    re.compile(r'[\u1F680-\u1F6FF]'),  # Transport and map
]

# Common emojis to check (fallback for systems with limited unicode support)
COMMON_EMOJIS = [
    '[OK]', '[ERROR]', '[WARNING]', '[SUCCESS]', '[START]', '[INFO]', '[NOTE]', '[CONFIG]', '[STATS]', '[FAST]',
    '[NEW]', '[TARGET]', '[TOOLS]', '[PACKAGE]', '[SEARCH]', '[QUESTION]', '[CHAT]', '[SETTINGS]', '[STYLE]', '[PIN]',
    '[BUILD]', '[HOT]', '[CODE]', '[STAR]', '[DOCS]', '[LEARN]', '[BOT]', '[LOCK]', '[WEB]', '[MASK]',
    '[CIRCUS]', '[MASK]', '[GAME]', '[AUDIO]', '[TROPHY]', '[FIRST]', '[BELL]', '[ANNOUNCE]', '[SPEAKER]', '[VOLUME]',
    '[GIFT]', '[CART]', '[SHOP]', '[OFFICE]', '[HOUSE]', '[HOME]', '[BUILD]', '[CONSTRUCTION]', '[SIREN]', '[TRAFFIC]',
]

# Hardcoded patterns to check
HARDCODED_PATTERNS = [
    # Windows paths
    (r'D:\\\\[^"\']*', 'Windows path (D:\\)'),
    (r'C:\\\\[^"\']*', 'Windows path (C:\\)'),
    (r'C:\\Users\\[^"\']*', 'User profile path'),
    # Mac paths
    (r'/Users/[^"\']*', 'Mac user path'),
    (r'/Volumes/[^"\']*', 'Mac volume path'),
    # Linux paths
    (r'/home/[^"\']*', 'Linux home path'),
    # Absolute paths that look like development machines
    (r'[A-Z]:\\\\[^"\'\\s]*\\fastreact', 'FastReAct project path'),
]


def find_emojis(text: str) -> List[str]:
    """Find emoji characters in text"""
    found = []

    # Check for common emojis (fast)
    for emoji in COMMON_EMOJIS:
        if emoji in text:
            found.append(emoji)

    # Check unicode ranges (slower but more complete)
    for pattern in EMOJI_PATTERNS:
        matches = pattern.findall(text)
        found.extend(matches)

    return list(set(found))  # Deduplicate


def find_hardcoded_values(text: str, filename: str) -> List[Tuple[str, str, int]]:
    """Find hardcoded paths and values"""
    issues = []
    lines = text.split('\n')

    for line_num, line in enumerate(lines, 1):
        # Skip comments
        if '#' in line:
            code_part = line[:line.index('#')]
        else:
            code_part = line

        # Check each pattern
        for pattern, description in HARDCODED_PATTERNS:
            matches = re.finditer(pattern, code_part)
            for match in matches:
                issues.append((match.group(), description, line_num))

    return issues


def check_file(filepath: Path) -> dict:
    """Check a single file for emojis and hardcoded values"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return {'error': 'Could not read file'}

    result = {
        'file': str(filepath.relative_to(Path.cwd())),
        'emojis': [],
        'hardcoded': [],
    }

    # Find emojis
    emojis = find_emojis(content)
    if emojis:
        result['emojis'] = emojis

    # Find hardcoded values
    hardcoded = find_hardcoded_values(content, str(filepath))
    if hardcoded:
        result['hardcoded'] = hardcoded

    return result


def scan_directory(directory: Path, extensions: List[str] = ['.py']) -> dict:
    """Scan directory for issues"""
    results = {
        'files_with_emojis': [],
        'files_with_hardcoded': [],
        'summary': {}
    }

    for ext in extensions:
        for filepath in directory.rglob(f'*{ext}'):
            # Skip virtual environments and cache
            if 'venv' in str(filepath) or '.tox' in str(filepath):
                continue
            if '__pycache__' in str(filepath):
                continue

            result = check_file(filepath)

            if result.get('emojis'):
                results['files_with_emojis'].append(result)

            if result.get('hardcoded'):
                results['files_with_hardcoded'].append(result)

    return results


def print_results(results: dict):
    """Print scan results"""
    print("\n" + "="*70)
    print("FastReAct Code Quality Check")
    print("="*70)

    # Summary
    emoji_count = len(results['files_with_emojis'])
    hardcoded_count = len(results['files_with_hardcoded'])

    print(f"\nFiles with emojis: {emoji_count}")
    print(f"Files with hardcoded values: {hardcoded_count}")

    # Emoji details
    if results['files_with_emojis']:
        print("\n" + "="*70)
        print("EMOJI FOUND")
        print("="*70)
        print("\nRecommendation: Replace emojis with text markers")
        print("Examples:")
        print("  [OK] → [OK]")
        print("  [ERROR] → [ERROR]")
        print("  [WARNING] → [WARNING]")
        print("  [SUCCESS] → [SUCCESS]")
        print()

        for result in results['files_with_emojis'][:20]:  # Show first 20
            print(f"  {result['file']}")
            print(f"    Emojis: {', '.join(result['emojis'])}")

        if len(results['files_with_emojis']) > 20:
            print(f"\n  ... and {len(results['files_with_emojis']) - 20} more files")

    # Hardcoded values details
    if results['files_with_hardcoded']:
        print("\n" + "="*70)
        print("HARDCODED VALUES FOUND")
        print("="*70)
        print("\nRecommendation: Use config files or environment variables")
        print()

        for result in results['files_with_hardcoded'][:10]:  # Show first 10
            print(f"  {result['file']}")
            for value, desc, line in result['hardcoded'][:3]:  # Show first 3
                print(f"    Line {line}: {desc}")
                print(f"      {value[:60]}...")

        if len(results['files_with_hardcoded']) > 10:
            print(f"\n  ... and {len(results['files_with_hardcoded']) - 10} more files")

    # Final status
    print("\n" + "="*70)
    if emoji_count == 0 and hardcoded_count == 0:
        print("[OK] No issues found - Code is clean!")
    else:
        print(f"[WARNING] Found {emoji_count} files with emojis")
        print(f"[WARNING] Found {hardcoded_count} files with hardcoded values")
        print("\nReview and fix common issues manually")
    print("="*70)


def main():
    """Main entry point"""
    import sys

    # Scan current directory
    results = scan_directory(Path.cwd())

    # Print results
    print_results(results)

    # Exit code
    if results['files_with_emojis'] or results['files_with_hardcoded']:
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
