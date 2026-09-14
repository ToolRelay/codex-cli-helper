"""Give a PyInstaller output its release name and write a SHA-256 sidecar."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-name", required=True)
    args = parser.parse_args()

    source = Path("dist") / ("codex-cli-helper.exe" if os.name == "nt" else "codex-cli-helper")
    target = Path("dist") / args.asset_name
    if source != target:
        shutil.move(source, target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    Path(f"{target}.sha256").write_text(
        f"{digest}  {target.name}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
