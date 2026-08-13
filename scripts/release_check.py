#!/usr/bin/env python3
"""Run release-facing checks for the current implementation milestone."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    commands = [
        [sys.executable, "scripts/verify_package.py"],
        [sys.executable, "-m", "pytest"],
    ]
    for example_type in ("architecture", "flowchart", "sequence", "sitemap", "gantt"):
        examples = ROOT / "skills/diagrammatical/assets/examples" / example_type
        commands.extend(
            [sys.executable, "skills/diagrammatical/scripts/self_check.py", str(path)]
            for path in sorted(examples.iterdir())
            if path.is_dir()
        )
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
