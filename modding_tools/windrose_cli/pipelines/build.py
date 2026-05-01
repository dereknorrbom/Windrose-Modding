from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PackageRequest:
    package_mode: str
    staged_dir: Path
    output_base: Path
    install_dir: Path | None = None


def validate_package_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized not in {"pak", "iostore"}:
        raise ValueError(f"Unsupported package mode: {mode}")
    return normalized


def install_outputs(paths: list[Path], install_dir: Path) -> list[Path]:
    install_dir.mkdir(parents=True, exist_ok=True)
    installed = []
    for path in paths:
        target = install_dir / path.name
        shutil.copy2(path, target)
        installed.append(target)
    return installed
