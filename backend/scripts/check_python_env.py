#!/usr/bin/env python3
"""Detect mixed Conda + Homebrew Python (causes segfault on import sqlalchemy)."""
from __future__ import annotations

import importlib.util
import sys


def main() -> int:
    exe = sys.executable.lower()
    spec = importlib.util.find_spec("_pickle")
    origin = (spec.origin or "").lower() if spec else ""

    print("Python executable:", sys.executable)
    print("_pickle module file:  ", spec.origin if spec else "(not found)")

    bad = False
    if "homebrew" in exe and "anaconda" in origin:
        bad = True
        print()
        print("PROBLEM: Homebrew Python is loading Anaconda's _pickle (stdlib).")
        print("That mix crashes with SIGSEGV when SQLAlchemy imports pickle.")
    elif "conda" in exe and "homebrew" in origin:
        bad = True
        print()
        print("PROBLEM: Mixed Conda interpreter with non-Conda extension modules.")

    if bad:
        print()
        print("Fix: fully deactivate conda, remove backend/.venv, recreate venv with ONE Python:")
        print('  conda deactivate   # until prompt has no "(base)"')
        print("  unset PYTHONHOME")
        print("  cd backend && rm -rf .venv")
        print("  /opt/homebrew/bin/python3 -m venv .venv   # adjust path if needed")
        print("  source .venv/bin/activate && pip install -r requirements.txt")
        print()
        print("Do not run `import sqlalchemy` until the mix above is fixed (it may segfault).")
        return 1

    try:
        import sqlalchemy  # noqa: F401
    except Exception as e:
        print("import sqlalchemy failed:", e)
        return 1

    print("import sqlalchemy: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
