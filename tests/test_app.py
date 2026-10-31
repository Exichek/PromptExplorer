"""Проверка полного запуска в отдельном процессе без пользовательских данных."""

import os
import subprocess
import sys


def test_smoke_launch_isolated_from_selected_library(tmp_path):
    directory = tmp_path / "не трогать"
    directory.mkdir()
    marker = directory / "marker.txt"
    marker.write_text("Исходные данные", encoding="utf-8")
    env = {
        **os.environ,
        "PROMPTEXPLORER_DATA_DIR": str(directory),
        "TEMP": str(tmp_path),
        "TMP": str(tmp_path),
        "TMPDIR": str(tmp_path),
        "QT_QPA_PLATFORM": "offscreen",
    }
    result = subprocess.run(
        [sys.executable, "-m", "promptexplorer", "--smoke-test"],
        env=env,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert list(directory.iterdir()) == [marker]


def test_version_does_not_create_data(tmp_path):
    directory = tmp_path / "не создавать"
    result = subprocess.run(
        [sys.executable, "-m", "promptexplorer", "--version"],
        env={**os.environ, "PROMPTEXPLORER_DATA_DIR": str(directory)},
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 0
    assert b"0.10.0" in result.stdout
    assert not directory.exists()
