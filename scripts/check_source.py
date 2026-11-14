"""Compile tracked Python sources without executing application modules."""

from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
count = 0
for name in filter(None, paths):
    if name.endswith(".py"):
        compile((root / name).read_text(encoding="utf-8-sig"), name, "exec")
        count += 1
print("Compiled", count, "tracked Python files")
