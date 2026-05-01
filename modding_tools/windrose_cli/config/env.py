from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from windrose_cli.paths import DEFAULT_GAME_MODS_DIR, modding_tools_root, workspace_root


@dataclass(frozen=True)
class BuildConfig:
    input_dir: Path
    output_pak: Path
    mods_dir: Path
    mount_point: str = "../../../"
    version: str = "V11"
    compression: str = ""
    backup_dir: Path | None = None


def load_local_env(env_path: Path | None = None) -> None:
    """
    Load repo-local environment variables from .local/.env if present.
    Existing process env vars take precedence.
    """
    path = env_path or workspace_root() / ".local" / ".env"
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def token_values() -> dict[str, str]:
    return {
        "<REPO_ROOT>": str(workspace_root()),
        "<WORKSPACE_ROOT>": str(workspace_root()),
        "<MODDING_TOOLS_ROOT>": str(modding_tools_root()),
        "<WINDROSE_MODS_DIR>": os.environ.get("WINDROSE_MODS_DIR", str(DEFAULT_GAME_MODS_DIR)),
        "<WINDROSE_PAKS_DIR>": os.environ.get("WINDROSE_PAKS_DIR", ""),
    }


def resolve_config_string(raw: str, config_path: Path, field_name: str) -> str:
    value = raw
    for token, replacement in token_values().items():
        if token in value:
            if replacement == "":
                raise ValueError(
                    f"Config field '{field_name}' uses {token} but corresponding environment value is not set."
                )
            value = value.replace(token, replacement)
    return os.path.expandvars(value)


def resolve_config_path(raw: str, config_path: Path, field_name: str) -> Path:
    value = resolve_config_string(raw, config_path, field_name)
    path = Path(value)
    if not path.is_absolute():
        path = (config_path.parent / path).resolve()
    return path


def parse_build_config(raw: dict, config_path: Path) -> BuildConfig:
    mods_dir = (
        resolve_config_path(str(raw["mods_dir"]), config_path, "mods_dir")
        if "mods_dir" in raw
        else DEFAULT_GAME_MODS_DIR
    )
    backup_dir = (
        resolve_config_path(str(raw["backup_dir"]), config_path, "backup_dir")
        if "backup_dir" in raw
        else None
    )
    return BuildConfig(
        input_dir=resolve_config_path(str(raw["input_dir"]), config_path, "input_dir"),
        output_pak=resolve_config_path(str(raw["output_pak"]), config_path, "output_pak"),
        mods_dir=mods_dir,
        mount_point=resolve_config_string(str(raw.get("mount_point", "../../../")), config_path, "mount_point"),
        version=resolve_config_string(str(raw.get("version", "V11")), config_path, "version"),
        compression=resolve_config_string(str(raw.get("compression", "")), config_path, "compression"),
        backup_dir=backup_dir,
    )
