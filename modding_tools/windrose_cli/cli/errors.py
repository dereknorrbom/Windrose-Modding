from __future__ import annotations

import argparse
import json
import sys
from typing import Callable

from windrose_cli.tools.process import ToolError


class UserFacingError(RuntimeError):
    pass


def emit_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2))


def run_with_error_handling(parser: argparse.ArgumentParser, action: Callable[[], int], debug: bool = False) -> int:
    try:
        return action()
    except (FileNotFoundError, ValueError, RuntimeError, ToolError) as exc:
        if debug:
            raise
        print(f"error: {exc}", file=sys.stderr)
        return 1
