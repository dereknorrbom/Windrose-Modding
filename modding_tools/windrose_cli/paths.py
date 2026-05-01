from __future__ import annotations

from pathlib import Path


DEFAULT_GAME_MODS_DIR = Path(
    r"c:\Program Files (x86)\Steam\steamapps\common\Windrose\R5\Content\Paks\~mods"
)


def modding_tools_root() -> Path:
    return Path(__file__).resolve().parents[1]


def workspace_root() -> Path:
    return modding_tools_root().parent


def bin_dir() -> Path:
    return modding_tools_root() / "bin"
