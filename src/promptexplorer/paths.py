"""Расположение данных и время без зависимости от Qt."""

import os
from datetime import datetime
from pathlib import Path

from .constants import APP_NAME


def app_data_dir() -> str:
    override = os.getenv("PROMPTEXPLORER_DATA_DIR")
    if override:
        path = Path(override).expanduser().resolve()
    elif os.name == "nt":
        path = Path(os.getenv("APPDATA") or Path.home() / "AppData" / "Roaming") / APP_NAME
    else:
        # Сохраняем прежний путь, чтобы обнаружить существующие коллекции.
        path = Path.home() / f".{APP_NAME.lower()}"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
