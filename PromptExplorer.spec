# Сборка настольного приложения для текущей операционной системы.
from pathlib import Path
import sys

root = Path(SPECPATH)
a = Analysis(
    [str(root / 'run.py')],
    pathex=[str(root / 'src')],
    datas=[(str(root / 'src/promptexplorer/resources'), 'promptexplorer/resources')],
    binaries=[], hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtPdf'],
    noarchive=False,
)
if sys.platform == 'win32':
    # Qt использует системный ICU Windows. Одноимённые DLL из PATH (например,
    # из Poppler) имеют другой набор экспортов и ломают загрузку QtCore.
    a.binaries = [entry for entry in a.binaries
                  if not (Path(entry[0]).name.lower().startswith('icu')
                          and Path(entry[0]).suffix.lower() == '.dll')]
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name='PromptExplorer',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, icon=str(root / 'src/promptexplorer/resources/app.ico'),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='PromptExplorer')
