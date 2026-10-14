"""Windows one-file bundle; never include user config or API keys."""
from pathlib import Path
from PyInstaller.utils.hooks import collect_dynamic_libs

root = Path(SPECPATH)
a = Analysis(
    [str(root / 'voice_sim.py')],
    pathex=[str(root)],
    binaries=collect_dynamic_libs('SimConnect'),
    datas=[(str(root / name), '.') for name in ('notification.wav', 'VoiceSim.sample.ini', 'aircraft_commands.json', 'THIRD_PARTY_NOTICES.md', 'SimConnect-LICENSE.txt')],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='VoiceSim',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
