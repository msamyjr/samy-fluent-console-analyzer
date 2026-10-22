#!/usr/bin/env python3
"""Update an existing Samy Home folder without reading/copying TV credentials."""
import hashlib
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

ARCHIVE_URL = 'https://github.com/msamyjr/samy-fluent-console-analyzer/raw/refs/heads/download/samy-vizio-modern-home/downloads/Samy_Vizio_Modern_Home.zip'
EXPECTED_SHA256 = '6c044d12338b9157b325176375bf07efae06cf3da645c353302e63134b3b833e'
ROOT_FILES = {'README.md', 'COMPATIBILITY.md', 'REAL_DEVICE_TESTS.md', 'TEST_RESULTS.md', 'main.py', '.gitignore', 'CODEX_PROMPT.md', 'README_AR.md', 'COMPATIBILITY_AR.md', 'REAL_DEVICE_TESTS_AR.md', 'TEST_RESULTS_AR.md'}


def apply_update(archive, root):
    root = Path(root).resolve()
    if not (root / 'main.py').is_file() or not (root / 'site').is_dir():
        raise RuntimeError('Run this updater from the existing project directory containing main.py and site/.')
    with zipfile.ZipFile(archive) as z:
        entries = []
        seen = set()
        total = 0
        for info in z.infolist():
            if info.is_dir():
                continue
            path = PurePosixPath(info.filename)
            if len(path.parts) < 2 or path.parts[0] != 'Samy_Vizio_Modern_Home' or '..' in path.parts or path.is_absolute():
                raise RuntimeError('Unsafe archive path; no update applied.')
            relative = Path(*path.parts[1:])
            if str(relative) in seen:
                raise RuntimeError('Duplicate archive entry.')
            seen.add(str(relative))
            if relative.as_posix() not in ROOT_FILES and relative.parts[0] not in ('site', 'tests', 'artifacts'):
                raise RuntimeError('Unexpected archive file; private configuration must never be replaced.')
            target = root / relative
            if target.is_symlink() or not target.resolve().is_relative_to(root):
                raise RuntimeError('Refusing update through a symbolic link.')
            total += info.file_size
            if total > 40 * 1024 * 1024:
                raise RuntimeError('Archive is too large.')
            entries.append((info, relative))
        if not {'main.py', 'site/index.html', 'site/controller.html', 'site/styles.css', 'site/app.js', 'site/catalog.json'}.issubset(seen):
            raise RuntimeError('Incomplete application archive.')
        # Read all data and CRCs before touching existing application files.
        content = [(relative, z.read(info)) for info, relative in entries]
    if (root / 'backups').is_symlink():
        raise RuntimeError('Refusing a symbolic link backup directory.')
    backup = root / 'backups' / ('samy_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(parents=True, mode=0o700)
    for relative, body in content:
        target = root / relative
        if target.exists():
            destination = backup / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, destination)
    written = []
    try:
        for relative, body in content:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            # Include target before writing so even a partial write is rolled back.
            written.append(relative)
            target.write_bytes(body)
    except Exception:
        for relative in reversed(written):
            target, previous = root / relative, backup / relative
            if previous.exists():
                shutil.copy2(previous, target)
            elif target.exists():
                target.unlink()
        raise
    return backup


def main():
    root = Path.cwd()
    if not (root / 'main.py').is_file() or not (root / 'site').is_dir():
        raise RuntimeError('Open Terminal in your existing Samy project directory first.')
    with tempfile.TemporaryDirectory(prefix='samy-update-') as directory:
        archive = Path(directory) / 'project.zip'
        subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error', '--proto', '=https', '--proto-redir', '=https', ARCHIVE_URL, '-o', str(archive)], check=True)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != EXPECTED_SHA256:
            raise RuntimeError('Checksum mismatch. Nothing updated. Download the current updater and retry.')
        backup = apply_update(archive, root)
    print('Update installed. Your .vizio_local.json was not read or changed.')
    print('Previous application files:', backup)
    print('Next: python3 main.py preview  (Mac dashboard)')
    print('Or:   python3 main.py launch   (also requests Conjure on TV)')
    print('WatchFree test: python3 main.py watchfree')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        print('Update failed:', str(exc))
        raise SystemExit(1)
