"""Build the CLI and bundle its packaged skill with PyInstaller."""

from __future__ import annotations

import os
from pathlib import Path

import PyInstaller.__main__


def main() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    source_root = repository_root / "src"
    entrypoint = source_root / "codex_cli_helper" / "__main__.py"
    skill_root = source_root / "codex_cli_helper" / "skill"
    PyInstaller.__main__.run(
        [
            "--clean",
            "--noconfirm",
            "--onefile",
            "--name",
            "codex-cli-helper",
            "--paths",
            str(source_root),
            "--add-data",
            f"{skill_root}{os.pathsep}codex_cli_helper/skill",
            str(entrypoint),
        ]
    )


if __name__ == "__main__":
    main()
