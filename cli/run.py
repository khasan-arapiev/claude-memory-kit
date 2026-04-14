#!/usr/bin/env python3
"""Standalone runner so `python run.py <args>` works without package install.

Usage:
    python run.py audit [path] [--json]
"""
import sys
from pathlib import Path

# Make `brain` importable when this file is run directly.
sys.path.insert(0, str(Path(__file__).parent))

from brain.cli import main

if __name__ == "__main__":
    sys.exit(main() or 0)
