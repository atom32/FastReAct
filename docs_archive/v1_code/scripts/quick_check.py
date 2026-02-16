"""
Quick check for cross-platform compatibility

Verifies:
- No emojis in source code
- No hardcoded paths
- UTF-8 encoding used
"""

import sys
from pathlib import Path


def check_file(filepath: Path) -> dict:
    """Check a single file"""
    issues = {
        'file': str(filepath),
        'emojis': [],
        'hardcoded_paths': [],
        'encoding_issues': False,
    }

    try:
        # Check file encoding
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        issues['encoding_issues'] = True
        # Try with latin-1 to detect issues
        try:
            with open(filepath, 'r', encoding='latin-1') as f:
                content = f.read()
        except:
            return issues
    except Exception as e:
        return issues

    # Check for emojis (common ones)
    emoji_patterns = [
        '\u2705', '\u274c', '\u26a0',  # ✅❌⚠
        '\U0001f389', '\U0001f680',     # 🎉🚀
        '\U0001f4a1', '\U0001f4dd',     # 💡📝
        '\U0001f527', '\U0001f4ca',     # 🔧📊
    ]

    for emoji in emoji_patterns:
        if emoji in content:
            issues['emojis'].append(emoji)

    # Check for hardcoded paths
    hardcoded_patterns = [
        (r'D:\\\\[^"\']*\s', 'Windows D: drive path'),
        (r'C:\\\\[^"\']*\s', 'Windows C: drive path'),
        (r'C:\\Users\\[^"\']*\s', 'Windows user profile'),
        (r'/Users/[^"\']*\s', 'Mac user profile'),
        (r'/home/[^"\']*\s', 'Linux home directory'),
    ]

    import re
    for pattern, desc in hardcoded_patterns:
        if re.search(pattern, content):
            issues['hardcoded_paths'].append(desc)

    return issues


def main():
    """Main check"""
    import sys

    print("\n" + "="*70)
    print("FastReAct Cross-Platform Quick Check")
    print("="*70)

    # Check src directory
    src_dir = Path(__file__).parent.parent / "src"

    if not src_dir.exists():
        print(f"[ERROR] src directory not found: {src_dir}")
        return 1

    # Scan all Python files
    files_with_issues = []

    for py_file in src_dir.rglob('*.py'):
        # Skip cache
        if '__pycache__' in str(py_file):
            continue

        issues = check_file(py_file)

        if any([issues['emojis'], issues['hardcoded_paths'], issues['encoding_issues']]):
            files_with_issues.append(issues)

    # Print results
    print(f"\nScanned: {len(list(src_dir.rglob('*.py')))} files")
    print(f"Issues found: {len(files_with_issues)} files")

    if files_with_issues:
        print("\nFiles with issues:")
        for issues in files_with_issues[:10]:
            print(f"\n  {issues['file']}")
            if issues['emojis']:
                print(f"    Emojis: {len(issues['emojis'])} found")
            if issues['hardcoded_paths']:
                print(f"    Hardcoded paths: {issues['hardcoded_paths']}")
            if issues['encoding_issues']:
                print(f"    [ERROR] Encoding issues detected")

        if len(files_with_issues) > 10:
            print(f"\n  ... and {len(files_with_issues) - 10} more")

        print("\n" + "="*70)
        print("[FAILED] Cross-platform compatibility issues found")
        print("Run: python scripts/remove_emojis.py")
        print("="*70)
        return 1
    else:
        print("\n" + "="*70)
        print("[SUCCESS] No issues found!")
        print("Code is clean and cross-platform compatible")
        print("="*70)
        return 0


if __name__ == "__main__":
    sys.exit(main())
