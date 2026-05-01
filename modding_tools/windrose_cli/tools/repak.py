from __future__ import annotations

from pathlib import Path

from windrose_cli.tools.common import resolve_tool
from windrose_cli.tools.process import run


class RepakClient:
    def __init__(self, executable: Path | None = None):
        self.executable = executable or resolve_tool("repak.exe")

    def list_entries(self, pak_path: Path, aes_key: str = "") -> list[str]:
        cmd = [str(self.executable)]
        if aes_key:
            cmd.extend(["--aes-key", aes_key])
        cmd.extend(["list", str(pak_path)])
        return [line.strip() for line in run(cmd).stdout.splitlines() if line.strip()]

    def get_text(self, pak_path: Path, asset_path: str, aes_key: str = "") -> str:
        cmd = [str(self.executable)]
        if aes_key:
            cmd.extend(["--aes-key", aes_key])
        cmd.extend(["get", str(pak_path), asset_path])
        return run(cmd).stdout

    def pack(
        self,
        input_dir: Path,
        output_pak: Path,
        mount_point: str = "../../../",
        version: str = "V11",
        compression: str = "",
    ) -> None:
        cmd = [
            str(self.executable),
            "pack",
            "--mount-point",
            mount_point,
            "--version",
            version,
        ]
        if compression:
            cmd.extend(["--compression", compression])
        cmd.extend([str(input_dir), str(output_pak)])
        run(cmd)
