import os
import re
from datetime import datetime

def count_lines(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return sum(1 for _ in f)

def extract_imports(filepath):
    imports = set()
    stdlib = {'os', 'sys', 're', 'datetime', 'time', 'json', 'math', 'collections'}
    pattern = re.compile(r'^import\s+([\w\.]+)|^from\s+([\w\.]+)\s+import')
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith('#'):
                continue
            match = pattern.match(line)
            if match:
                module = match.group(1) or match.group(2)
                base_module = module.split('.')[0]
                if base_module not in stdlib:
                    imports.add(base_module)
    return imports

def comment_ratio(filepath):
    code_lines = 0
    comment_lines = 0
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith('#'):
                comment_lines += 1
            else:
                code_lines += 1
    
    return round(comment_lines / (code_lines + comment_lines) * 100, 2) if (code_lines + comment_lines) > 0 else 0

def main():
    start_time = datetime.now()
    root_dir = r'D:\FastReAct'
    total_lines = 0
    all_imports = set()
    total_files = 0
    comment_ratios = []
    
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    total_lines += count_lines(filepath)
                    all_imports.update(extract_imports(filepath))
                    comment_ratios.append(comment_ratio(filepath))
                    total_files += 1
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")
    
    avg_comment_ratio = round(sum(comment_ratios) / len(comment_ratios), 2) if comment_ratios else 0
    
    # Generate AUDIT_REPORT.md
    with open('AUDIT_REPORT.md', 'w', encoding='utf-8') as f:
        f.write(f"# FastReAct Code Audit Report\n")
        f.write(f"- **Total Python Files**: {total_files}\n")
        f.write(f"- **Total Lines of Code**: {total_lines}\n")
        f.write(f"- **Third-party Dependencies**: {', '.join(sorted(all_imports)) or 'None'}\n")
        f.write(f"- **Average Comment Ratio**: {avg_comment_ratio}%\n")
    
    # Generate SUCCESS.txt
    with open('SUCCESS.txt', 'w', encoding='utf-8') as f:
        f.write(f"Audit completed successfully at {datetime.now()}\n")
        f.write(f"Execution time: {datetime.now() - start_time}\n")

if __name__ == '__main__':
    main()