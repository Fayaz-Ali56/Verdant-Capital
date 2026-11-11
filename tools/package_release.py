"""Package tracked source only. Commit intended files before building the release."""

import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

SOURCE = Path(__file__).resolve().parents[1]
OUTPUT = SOURCE / "dist" / "Verdant-Capital-Submission.zip"


def package():
    files = subprocess.check_output(["git", "ls-files", "-z"], cwd=SOURCE).decode().split("\0")
    OUTPUT.parent.mkdir(exist_ok=True)
    count = 0
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED, compresslevel=7) as archive:
        for name in sorted(filter(None, files)):
            file = SOURCE / name
            if file.is_symlink() or not file.is_file():
                continue
            if file.name.lower().startswith(".env") and file.name != ".env.example":
                continue
            if file.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".pyc", ".log"}:
                continue
            archive.write(file, Path("Verdant-Capital") / name)
            count += 1
    print(
        f"Created {OUTPUT.name}: {count} tracked source files; local caches, secrets and Git metadata excluded"
    )
    return OUTPUT


if __name__ == "__main__":
    package()
