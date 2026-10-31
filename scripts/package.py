"""Упаковать папку приложения, сохранив права запуска Linux, и вычислить SHA-256."""

import hashlib
import platform
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
system = platform.system()
archive = Path(
    shutil.make_archive(
        str(root / "dist" / f"PromptExplorer-{system}"),
        "zip" if system == "Windows" else "gztar",
        root_dir=root / "dist",
        base_dir="PromptExplorer",
    )
)
with archive.open("rb") as stream:
    checksum = hashlib.file_digest(stream, "sha256").hexdigest()
archive.with_suffix(archive.suffix + ".sha256").write_text(
    f"{checksum}  {archive.name}\n", encoding="utf-8"
)
print(archive)
