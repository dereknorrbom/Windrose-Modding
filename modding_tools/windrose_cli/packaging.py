from __future__ import annotations

import zipfile
from pathlib import Path


def package_pak_variant(pak_path: Path, zip_path: Path | None = None) -> Path:
    if not pak_path.exists():
        raise FileNotFoundError(f"Pak not found: {pak_path}")
    target = zip_path or pak_path.with_suffix(".zip")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(pak_path, pak_path.name)
    return target


def package_iostore_variant(pak_path: Path, zip_path: Path | None = None) -> Path:
    files = [pak_path, pak_path.with_suffix(".ucas"), pak_path.with_suffix(".utoc")]
    missing = [path for path in files if not path.exists()]
    if missing:
        raise FileNotFoundError(f"IoStore output file(s) missing: {', '.join(str(path) for path in missing)}")
    target = zip_path or pak_path.with_suffix(".zip")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.name)
    return target

