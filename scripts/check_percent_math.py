import os
import re
import sys

# Ensure UTF-8 output even in Windows cmd/powershell
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

exclude_dirs = {'.git', '.venv', '__pycache__', '.pytest_cache', '.idea', '.vscode', 'node_modules', '.agents', 'dist', 'build'}
matches_by_file = {}

for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    for file in files:
        if file.endswith('.md') or (file.endswith('.py') and not root.startswith('.' + os.sep + 'scripts')):
            fpath = os.path.normpath(os.path.join(root, file))
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue

            lines = content.splitlines()
            file_matches = []
            for i, line in enumerate(lines, 1):
                # Look for single dollar expressions with %
                items = re.findall(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', line)
                for item in items:
                    if '%' in item:
                        file_matches.append((i, item, line))
            if file_matches:
                matches_by_file[fpath] = file_matches

total = 0
for fpath, items in sorted(matches_by_file.items()):
    print(f"=== {fpath} ({len(items)} matches) ===")
    for ln, math_content, full_line in items:
        print(f"  Line {ln}: ${math_content}$")
    total += len(items)

print(f"\nTotal matches across repo (excluding dist/build): {total}")
