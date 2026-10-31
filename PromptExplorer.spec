# Сборка настольного приложения для текущей операционной системы.
from pathlib import Path

root = Path(SPECPATH)
a = Analysis(
    [str(root / 'run.py')],
    pathex=[str(root / 'src')],
    datas=[(str(root / 'src/promptexplorer/resources'), 'promptexplorer/resources')],
    binaries=[], hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtPdf'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name='PromptExplorer',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, icon=str(root / 'src/promptexplorer/resources/app.ico'),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='PromptExplorer')
