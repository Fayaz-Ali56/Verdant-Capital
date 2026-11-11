"""Inventory tracked files and check common secret/debug markers without printing values."""

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    "Google API key": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    "provider token": re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{32,}"),
}


def main():
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    inventory, findings = [], []
    for name in sorted(filter(None, names)):
        file = ROOT / name
        if not file.is_file() or name == "docs/qa/source-inventory.json":
            continue
        content = file.read_bytes()
        entry = {"path": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            entry["kind"] = "binary artifact"
        else:
            entry["lines"] = len(text.splitlines())
            entry["kind"] = "text"
            if file.suffix == ".py":
                ast.parse(text, filename=name)
            if file.suffix == ".json":
                json.loads(text)
            for label, pattern in PATTERNS.items():
                if pattern.search(text):
                    findings.append({"path": name, "finding": label})
            if file.name.lower().startswith(".env") and file.name != ".env.example":
                findings.append({"path": name, "finding": "tracked environment file"})
            if file.suffix in {".py", ".cjs", ".js"} and name != "tools/audit_source.py":
                if re.search(r"\b(?:TODO|FIXME)\b|console\.log\s*\(", text):
                    findings.append({"path": name, "finding": "unfinished/debug marker"})
        inventory.append(entry)
    output = ROOT / "docs" / "qa" / "source-inventory.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    if findings:
        raise SystemExit(json.dumps(findings, indent=2))
    print(
        f"PASS: {len(inventory)} tracked files inventoried; Python ASTs and JSON parsed; no configured secret/debug patterns found"
    )


if __name__ == "__main__":
    main()
