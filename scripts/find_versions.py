import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

exclude_dirs = {'.git', '.venv', '__pycache__', '.pytest_cache', '.idea', '.vscode', 'node_modules', '.agents', 'dist', 'build'}

for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    for file in files:
        if file.endswith(('.py', '.toml', '.json', '.md', '.yml', '.yaml')):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_no, line in enumerate(f, 1):
                        if re.search(r'v?9\.\d+\.\d+', line, re.IGNORECASE):
                            print(f"{path}:{line_no} -> {line.strip()[:140]}")
            except Exception:
                pass
