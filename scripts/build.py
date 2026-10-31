"""Собрать приложение из проверенной спецификации PyInstaller."""

import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
subprocess.run(
    [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        str(root / "PromptExplorer.spec"),
    ],
    cwd=root,
    check=True,
)
