#!/usr/bin/env python3
"""Run the full build pipeline."""
import subprocess
import sys
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
STEPS = ["build_admin.py", "build_mapping.py", "build_tdp.py", "build_nested.py", "build_sqlite.py"]

for s in STEPS:
    print(f"\n=== {s} ===")
    r = subprocess.run([sys.executable, str(HERE / s)])
    if r.returncode != 0:
        sys.exit(r.returncode)
print("\nDONE")
