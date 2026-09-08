#!/usr/bin/env python3
"""
deploy.py — One-shot deployment script for the Library AI Agent.

Steps:
  1. Installs backend dependencies
  2. Imports the four Python tools into watsonx Orchestrate
  3. Imports the agent spec into watsonx Orchestrate

Usage:
    python deploy.py

Prerequisites:
    - `orchestrate env activate <your-env>` must have been run first
    - ibm-watsonx-orchestrate SDK installed: pip install ibm-watsonx-orchestrate
"""

import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))


def run(cmd: list[str], cwd: str = ROOT) -> None:
    print(f"\n▶  {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=False)
    if result.returncode != 0:
        print(f"✗ Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    print("✓ Done")


def main():
    print("=" * 60)
    print("  Library AI Agent — Deployment")
    print("=" * 60)

    # ── 1. Install backend requirements ──────────────────────────────
    print("\n[1/3] Installing backend dependencies…")
    run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=os.path.join(ROOT, "backend"))

    # ── 2. Import tools ───────────────────────────────────────────────
    print("\n[2/3] Importing tools into watsonx Orchestrate…")
    run([
        "orchestrate", "tools", "import",
        "-k", "python",
        "-f", os.path.join(ROOT, "tools", "library_tools.py"),
        "-r", os.path.join(ROOT, "tools", "requirements.txt"),
    ])

    # ── 3. Import agent ───────────────────────────────────────────────
    print("\n[3/3] Importing agent into watsonx Orchestrate…")
    run([
        "orchestrate", "agents", "import",
        "-f", os.path.join(ROOT, "agents", "library-ai-agent.yaml"),
    ])

    print("\n" + "=" * 60)
    print("  ✅ Deployment complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  • Start the backend:  cd backend && python app.py")
    print("  • Open the frontend:  frontend/index.html  (open in browser)")
    print("  • Chat with agent in watsonx Orchestrate UI")


if __name__ == "__main__":
    main()
