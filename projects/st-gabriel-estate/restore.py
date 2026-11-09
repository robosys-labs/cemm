#!/usr/bin/env python3
"""Verify and restore the original St Gabriel Estate repository archive.

Download the archive from the linked Space first. This script uses only the
standard library, makes no network requests, and never executes archive code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


def verify_archive(archive: Path, expected: dict) -> None:
    if archive.stat().st_size != expected['bytes']:
        raise ValueError('Archive size mismatch; use the complete repository ZIP.')
    digest = hashlib.sha256()
    with archive.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != expected['sha256']:
        raise ValueError('SHA-256 mismatch. No files were extracted.')


def restore(archive: Path, destination: Path) -> int:
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f'Refusing to overwrite: {destination}')
    with zipfile.ZipFile(archive) as source:
        entries = source.infolist()
        if sum(item.file_size for item in entries) > 256 * 1024 * 1024:
            raise ValueError('Unexpected unpacked size.')
        seen: set[str] = set()
        for item in entries:
            path = PurePosixPath(item.filename)
            if (path.is_absolute() or '..' in path.parts or '\\' in item.filename
                    or ':' in item.filename or not path.parts
                    or path.parts[0] != 'st-gabriel-estate'
                    or stat.S_ISLNK(item.external_attr >> 16)):
                raise ValueError(f'Unsafe archive entry: {item.filename}')
            normalized = str(path).casefold()
            if normalized in seen:
                raise ValueError(f'Duplicate archive entry: {item.filename}')
            seen.add(normalized)
        corrupt = source.testzip()
        if corrupt is not None:
            raise ValueError(f'CRC mismatch: {corrupt}')
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix='.estate-restore-', dir=destination.parent))
        try:
            source.extractall(temporary)
            project = temporary / 'st-gabriel-estate'
            if not (project / 'index.html').is_file():
                raise ValueError('The archive is missing the asset catalog.')
            if destination.exists() or destination.is_symlink():
                raise FileExistsError(f'Destination appeared during restore: {destination}')
            project.rename(destination)
        finally:
            shutil.rmtree(temporary, ignore_errors=True)
    return sum(not item.is_dir() for item in entries)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--destination', type=Path,
                        default=Path(__file__).resolve().parent / 'restored')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    try:
        manifest_path = Path(__file__).resolve().with_name('archives.json')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        expected = next(item for item in manifest['archives'] if item['id'] == 'repository')
        verify_archive(args.archive, expected)
        if args.verify_only:
            print('Repository archive size and SHA-256 verified.')
            return
        count = restore(args.archive, args.destination.absolute())
        print(f'Restored {count} files to {args.destination.absolute()}')
        print('Open index.html for the catalog; demo/index.html for the integration preview.')
    except (OSError, ValueError, KeyError, StopIteration, zipfile.BadZipFile) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
