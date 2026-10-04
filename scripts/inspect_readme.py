import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open('README.md', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.splitlines()

print(f"Total lines in README.md: {len(lines)}")

print("\n--- Sections mentioning versions or tests ---")
for i, line in enumerate(lines, 1):
    if re.search(r'v?9\.\d+|test|passed|badge|endpoint|architettura|struttura', line, re.IGNORECASE):
        print(f"L{i}: {line[:120]}")
