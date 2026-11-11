"""Atomic report writes: readers see either the old file or the complete new one."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            file.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_json(path, value):
    write_text(path, json.dumps(value, indent=2, allow_nan=False))
