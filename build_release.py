"""Build and smoke-test a portable Windows release."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import struct
import sys
import tempfile
import zipfile


def main():
    if sys.platform != 'win32':
        raise SystemExit('Build Windows releases on Windows.')
    if struct.calcsize('P') != 8:
        raise SystemExit('Use 64-bit Python to build the Windows x64 release.')
    root = Path(__file__).resolve().parent
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=root, check=True)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', 'VoiceSim.spec'], cwd=root, check=True)
    executable = root / 'dist' / 'VoiceSim.exe'
    # Exercise a copy with no source tree or existing configuration available.
    with tempfile.TemporaryDirectory(prefix='voicesim-release-') as directory:
        folder = Path(directory)
        portable = folder / executable.name
        shutil.copy2(executable, portable)
        environment = os.environ.copy()
        environment.pop('PYTHONHOME', None)
        environment.pop('PYTHONPATH', None)
        environment['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')
        for action in ('--help', '--self-test', '--setup'):
            subprocess.run([str(portable), action], cwd=folder, env=environment, check=True, timeout=60)
        config = folder / 'VoiceSim.ini'
        if not config.is_file():
            raise RuntimeError('Settings did not persist beside the executable.')
        if (folder / 'config.py').exists() or (folder / 'commands.txt').exists():
            raise RuntimeError('Setup must create only one configuration file.')
        custom_config = config.read_text(encoding='utf-8') + '\n# Preserve user settings\n'
        config.write_text(custom_config, encoding='utf-8')
        subprocess.run([str(portable), '--setup'], cwd=root, env=environment, check=True, timeout=60)
        if config.read_text(encoding='utf-8') != custom_config:
            raise RuntimeError('Setup overwrote user settings.')
    archive = root / 'dist' / 'VoiceSim-windows-x64.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(executable, executable.name)
        for name in ('README.md', 'LICENSE', 'logo.jpg', 'THIRD_PARTY_NOTICES.md', 'SimConnect-LICENSE.txt'):
            bundle.write(root / name, name)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (root / 'dist' / 'SHA256SUMS.txt').write_text(f'{checksum}  {archive.name}\n', encoding='utf-8')
    print(f'Release ready: {archive}')


if __name__ == '__main__':
    main()
