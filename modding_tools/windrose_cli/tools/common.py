from __future__ import annotations

from pathlib import Path

from windrose_cli.paths import bin_dir


def resolve_tool(name: str, explicit_path: str | None = None) -> Path:
    if explicit_path:
        path = Path(explicit_path)
        if not path.exists():
            raise FileNotFoundError(f"Tool not found: {path}")
        return path
    candidate = bin_dir() / name
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"Could not resolve '{name}'. Put it in '{bin_dir()}' or pass an explicit tool path.")
