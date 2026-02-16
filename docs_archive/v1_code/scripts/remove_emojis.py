"""
Remove all emojis from Python source files

Replaces emojis with text markers for cross-platform compatibility
"""

import os
from pathlib import Path
from typing import Dict, List


# Emoji to text replacements (use actual emojis as keys)
EMOJI_REPLACEMENTS = {
    # Checkmarks
    '\u2705': '[OK]',           # [OK]
    '\u274c': '[ERROR]',        # [ERROR]
    '\u26a0': '[WARNING]',      # [WARNING]
    '\u274e': '[DENIED]',       # 🚮

    # Celebration
    '\U0001f389': '[SUCCESS]',   # [SUCCESS]
    '\U0001f680': '[START]',     # [START]
    '\U0001f4a1': '[INFO]',      # [INFO]
    '\U0001f4dd': '[NOTE]',      # [NOTE]
    '\U0001f527': '[CONFIG]',    # [CONFIG]

    # Objects
    '\U0001f4ca': '[STATS]',     # [STATS]
    '\u26a1': '[FAST]',          # [FAST]
    '\U00002728': '[STAR]',      # [STAR]
    '\U0001f3af': '[TARGET]',    # [TARGET]
    '\U0001f6e0': '[TOOLS]',     # [TOOLS]
    '\U0001f4e6': '[PACKAGE]',    # [PACKAGE]
    '\U0001f50d': '[SEARCH]',     # [SEARCH]

    # Communication
    '\u2754': '[QUESTION]',      # ❓
    '\U0001f4ac': '[CHAT]',       # [CHAT]
    '\u2699': '[SETTINGS]',      # [SETTINGS]
    '\U0001f3a8': '[STYLE]',      # [STYLE]
    '\U0001f4cc': '[PIN]',        # [PIN]

    # Building
    '\U0001f3d7': '[BUILD]',      # [BUILD]
    '\U0001f525': '[HOT]',        # [HOT]
    '\U0001f4bb': '[CODE]',       # [CODE]
    '\U0001f31f': '[STAR]',       # [STAR]
    '\U0001f4da': '[DOCS]',       # [DOCS]
    '\U0001f393': '[LEARN]',      # [LEARN]
    '\U0001f916': '[BOT]',        # [BOT]

    # Security
    '\U0001f512': '[LOCK]',       # 🔐
    '\U0001f310': '[WEB]',        # [WEB]
    '\U0001f3ad': '[MASK]',       # [MASK]
}


def remove_emojis_from_text(text: str) -> tuple:
    """Remove emojis from text, return (cleaned_text, replacements_count)"""
    cleaned = text
    replacements = 0

    for emoji, replacement in EMOJI_REPLACEMENTS.items():
        if emoji in cleaned:
            count = cleaned.count(emoji)
            cleaned = cleaned.replace(emoji, replacement)
            replacements += count

    return cleaned, replacements


def remove_emojis_from_file(filepath: Path) -> int:
    """Remove emojis from a file, return number of replacements"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return 0

    cleaned_content, replacements = remove_emojis_from_text(content)

    # Only write if changes were made
    if replacements > 0:
        try:
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                f.write(cleaned_content)
            return replacements
        except Exception as e:
            print(f"Error writing {filepath}: {e}")
            return 0

    return 0


def scan_directory(directory: Path, extensions: List[str] = ['.py']) -> Dict:
    """Scan and fix all Python files"""
    results = {
        'scanned': 0,
        'fixed': 0,
        'replacements': 0,
        'files_fixed': [],
    }

    for ext in extensions:
        for filepath in directory.rglob(f'*{ext}'):
            # Skip virtual environments and cache
            skip_patterns = ['venv', '.tox', '__pycache__', '.git', 'node_modules', '.pytest_cache']
            if any(skip in str(filepath) for skip in skip_patterns):
                continue

            results['scanned'] += 1
            replacements = remove_emojis_from_file(filepath)

            if replacements > 0:
                results['fixed'] += 1
                results['replacements'] += replacements
                results['files_fixed'].append({
                    'file': str(filepath.relative_to(directory)),
                    'replacements': replacements
                })

    return results


def main():
    """Main entry point"""
    import sys

    print("\n" + "="*70)
    print("FastReAct Emoji Removal Tool")
    print("="*70)
    print("\nScanning entire project for emojis...")
    print()

    # Scan project root directory
    root_dir = Path(__file__).parent.parent
    if not root_dir.exists():
        print(f"Error: Root directory not found: {root_dir}")
        return 1

    results = scan_directory(root_dir)

    # Print results
    print(f"Scanned: {results['scanned']} files")
    print(f"Fixed: {results['fixed']} files")
    print(f"Total replacements: {results['replacements']}")

    if results['files_fixed']:
        print("\nFiles fixed:")
        for item in results['files_fixed'][:20]:
            print(f"  {item['file']} ({item['replacements']} replacements)")

        if len(results['files_fixed']) > 20:
            print(f"\n  ... and {len(results['files_fixed']) - 20} more files")

    print("\n" + "="*70)
    if results['replacements'] > 0:
        print("[SUCCESS] Emoji removal completed!")
    else:
        print("[OK] No emojis found - Code is already clean!")
    print("="*70)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
