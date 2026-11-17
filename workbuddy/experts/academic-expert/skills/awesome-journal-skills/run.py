#!/usr/bin/env python3
"""run.py — 入口（转发至 scripts/main.py）"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
import main as _impl

if __name__ == "__main__":
    sys.exit(_impl.main())
