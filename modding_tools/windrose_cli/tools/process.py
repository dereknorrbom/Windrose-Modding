from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


class ToolError(RuntimeError):
    pass


def run(cmd: list[str], cwd: Path | None = None, check: bool = True, redacted_cmd: list[str] | None = None) -> ProcessResult:
    completed = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    result = ProcessResult(completed.returncode, completed.stdout, completed.stderr)
    if check and result.returncode != 0:
        shown = redacted_cmd or cmd
        raise ToolError(f"Command failed ({result.returncode}): {' '.join(shown)}\n{result.stderr}")
    return result


def run_no_capture(cmd: list[str], cwd: Path | None = None, check: bool = True) -> ProcessResult:
    completed = subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=False)
    result = ProcessResult(completed.returncode, "", "")
    if check and result.returncode != 0:
        raise ToolError(f"Command failed ({result.returncode}): {' '.join(cmd)}")
    return result


def run_shell(command: str, cwd: Path | None = None, check: bool = True) -> ProcessResult:
    completed = subprocess.run(command, cwd=str(cwd) if cwd else None, check=False, shell=True)
    result = ProcessResult(completed.returncode, "", "")
    if check and result.returncode != 0:
        raise ToolError(f"Shell command failed ({result.returncode}): {command}")
    return result
