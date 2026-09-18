#!/usr/bin/env python3
"""
Entry point for the life-ops dashboard.

Usage:
    python web/run.py --local
"""

import os
import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path and we run from there
_ROOT = str(Path(__file__).resolve().parent.parent)
os.chdir(_ROOT)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dotenv import load_dotenv
load_dotenv()

from web import create_app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a loopback-only Life Ops demo.")
    parser.add_argument("--local", action="store_true", required=True,
                        help="Allow this computer to open the dashboard without login")
    parser.parse_args()
    app = create_app(local_only=True)
    port = int(os.getenv("WEB_PORT", "5050"))
    print(f"Starting ops dashboard at http://localhost:{port}")
    app.run(host="127.0.0.1", debug=False, port=port, use_reloader=False)
