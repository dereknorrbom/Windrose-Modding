from __future__ import annotations

from pathlib import Path

from windrose_cli.tools.common import resolve_tool
from windrose_cli.tools.process import ProcessResult, run


CUE4PARSE_CLI_NAME = "cue4parse.exe"


class Cue4ParseClient:
    def __init__(self, executable: Path | None = None):
        self.executable = executable or resolve_tool(CUE4PARSE_CLI_NAME)

    def export_asset(
        self,
        paks_dir: Path,
        output_dir: Path,
        package_patterns: list[str],
        aes_key: str,
        mappings: Path | None = None,
        game_version: str = "GAME_UE5_LATEST",
        export_format: str = "json",
        verbose: bool = False,
        check: bool = False,
    ) -> ProcessResult:
        cmd = [
            str(self.executable),
            "--input",
            str(paks_dir),
            "--output",
            str(output_dir),
            "--game",
            game_version,
            "--key",
            aes_key,
            "--format",
            export_format,
            "--yes",
        ]
        redacted_cmd = [*cmd]
        redacted_cmd[redacted_cmd.index("--key") + 1] = "<redacted>"
        if mappings:
            cmd.extend(["--mappings", str(mappings)])
            redacted_cmd.extend(["--mappings", str(mappings)])
        for pattern in package_patterns:
            cmd.extend(["--package", pattern])
            redacted_cmd.extend(["--package", pattern])
        if verbose:
            cmd.append("--verbose")
            redacted_cmd.append("--verbose")
        return run(cmd, redacted_cmd=redacted_cmd, check=check)
