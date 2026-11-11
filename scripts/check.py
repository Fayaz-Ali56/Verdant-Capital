"""Cross-platform submission gate. Run with the project's virtual-environment Python."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = [
    ["-m", "pip", "check"],
    ["-m", "ruff", "check", "."],
    ["-m", "ruff", "format", "--check", "."],
    ["-m", "pytest", "-q"],
    ["tools/ui_smoke_test.py"],
    [
        "-m",
        "compileall",
        "-q",
        "app.py",
        "config.py",
        "agents",
        "challenge",
        "data",
        "orchestrator",
        "ui",
        "tools",
        "scripts",
    ],
]

if __name__ == "__main__":
    for command in COMMANDS:
        subprocess.run([sys.executable, *command], cwd=ROOT, check=True)
    print("PASS: dependencies, lint, formatting, tests, real UI smoke and compilation")
