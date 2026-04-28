#!/usr/bin/env python3
"""
One-command setup: creates venv, installs deps, runs pre-auth.
Usage: python setup.py
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def main():
    root = Path(__file__).parent
    venv = root / "venv"
    is_win = platform.system() == "Windows"
    pip = str(venv / ("Scripts" if is_win else "bin") / "pip")
    python = str(venv / ("Scripts" if is_win else "bin") / "python")

    print("=" * 60)
    print("  Kusto AI Assistant - Setup")
    print("=" * 60)

    # 1. Create venv
    if not venv.exists():
        print("\n[1/3] Creating virtual environment...")
        subprocess.check_call([sys.executable, "-m", "venv", str(venv)])
        print("  Done.")
    else:
        print("\n[1/3] Virtual environment already exists.")

    # 2. Install deps
    print("\n[2/3] Installing dependencies...")
    req = root / "requirements.txt"
    subprocess.check_call([pip, "install", "-r", str(req), "--quiet"])
    print("  Done.")

    # 3. Pre-auth
    print("\n[3/3] Starting authentication...")
    subprocess.check_call([python, str(root / "pre_auth.py")])

    print("\n" + "=" * 60)
    print("  Setup complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Copy config/config.json.template -> config/config.json")
    print("  2. Fill in your cluster URLs and database names")
    print("  3. Configure VS Code MCP settings (see README.md)")
    print("  4. Start chatting with Copilot about your data!")


if __name__ == "__main__":
    main()
