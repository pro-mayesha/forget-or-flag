"""Load KEY=value lines from the project's .env into os.environ (no extra dependency).

Values already set in the environment win, so `export ANTHROPIC_API_KEY=...` still works.
"""
from __future__ import annotations

import os
from pathlib import Path


def load_env(path: str | Path = Path(__file__).resolve().parent.parent / ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip("\"'")
        if value and not os.environ.get(key.strip()):
            os.environ[key.strip()] = value
