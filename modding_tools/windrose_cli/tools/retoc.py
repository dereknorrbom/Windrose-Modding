from __future__ import annotations

import shutil
from pathlib import Path

from windrose_cli.tools.common import resolve_tool
from windrose_cli.tools.process import run


class RetocClient:
    def __init__(self, executable: Path | None = None):
        self.executable = executable or resolve_tool("retoc.exe")

    def to_legacy(self, paks_dir: Path, output_dir: Path, asset_filter: str, version: str = "UE5_6") -> None:
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        run(
            [
                str(self.executable),
                "to-legacy",
                str(paks_dir),
                str(output_dir),
                "--filter",
                asset_filter,
                "--version",
                version,
                "--no-shaders",
            ]
        )

    def to_zen(self, input_pak: Path, output_utoc: Path, version: str = "UE5_6") -> None:
        run([str(self.executable), "to-zen", str(input_pak), str(output_utoc), "--version", version])
