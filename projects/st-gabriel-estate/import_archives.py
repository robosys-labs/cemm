#!/usr/bin/env python3
"""Import only the named game packages; never execute downloaded content."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = Path('projects/st-gabriel-estate')
BRANCH = 'assets/st-gabriel-estate'
PLAN = json.loads((ROOT / 'IMPORT_PLAN.json').read_text())
SOURCES = {item['id']: item for item in PLAN['archives']}
ISSUE_URL = 'https://api.github.com/repos/robosys-labs/cemm/issues/102'
MARKER = 'ST_GABRIEL_SOURCE_URLS'


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def install(source_id, archive_path):
    spec = SOURCES[source_id]
    data = archive_path.read_bytes()
    if len(data) != spec['bytes'] or sha(data) != spec['sha256']:
        raise ValueError('Archive verification failed')
    writes = []
    if source_id == 'repository':
        with zipfile.ZipFile(archive_path) as archive:
            entries = [item for item in archive.infolist() if not item.is_dir()]
            if len(entries) != 574 or sum(item.file_size for item in entries) > 64 * 1024 * 1024:
                raise ValueError('Unexpected archive file count or size')
            seen = set()
            for item in entries:
                path = PurePosixPath(item.filename)
                if (path.is_absolute() or not path.parts or path.parts[0] != 'st-gabriel-estate'
                    or any(part in ('..', '.git') for part in path.parts)
                    or '\\' in item.filename or ':' in item.filename
                    or stat.S_ISLNK(item.external_attr >> 16) or str(path).casefold() in seen):
                    raise ValueError('Unsafe archive member')
                seen.add(str(path).casefold())
                writes.append((ROOT / 'game' / Path(*path.parts[1:]), archive.read(item)))
        original = next(blob for path, blob in writes if path.name == 'St_Gabriel_Estate_Individual_Assets.zip')
        if sha(original) != 'aa1f156ff5b0bb13da883713fc679035d50f34c0df1bb78afc3d60c72077f969':
            raise ValueError('Original package verification failed')
        writes.append((ROOT / 'downloads' / 'St_Gabriel_Estate_Individual_Assets.zip', original))
    category = 'concepts' if source_id.startswith('concept_') else 'downloads'
    writes.append((ROOT / category / spec['name'], data))
    for path, blob in writes:
        if any(parent.is_symlink() for parent in [path, *path.parents]):
            raise ValueError('Symbolic-link destination rejected')
        if path.exists() and path.read_bytes() != blob:
            raise ValueError('Existing differing file would be overwritten')
    records = []
    for path, blob in writes:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
        records.append({'path': path.as_posix(), 'bytes': len(blob), 'sha256': sha(blob),
            'git_blob_sha1': hashlib.sha1(b'blob ' + str(len(blob)).encode() + b'\0' + blob).hexdigest()})
    return records


def download(source_id, url, directory):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or not (parsed.hostname or '').endswith('.oaiusercontent.com'):
        raise ValueError('Unapproved file delivery host')
    spec = SOURCES[source_id]
    path = directory / spec['name']
    total = 0
    with urllib.request.urlopen(url, timeout=120) as response, path.open('wb') as stream:
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > spec['bytes']:
                raise ValueError('Download exceeds pinned size')
            stream.write(chunk)
    return path


def publish(records, completed):
    receipt = {'files': records, 'file_count': len(records), 'sources_imported': sorted(completed),
               'sources_remaining': sorted(set(SOURCES) - completed),
               'total_bytes': sum(item['bytes'] for item in records),
               'status': 'complete' if completed == set(SOURCES) else 'partial'}
    (ROOT / 'GIT_UPLOAD_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    git('add', '--', str(ROOT))
    names = git('diff', '--cached', '--name-only').splitlines()
    if not all(name.startswith(ROOT.as_posix() + '/') for name in names):
        raise ValueError('Change outside authorized game directory')
    index = {}
    for line in git('ls-files', '--stage', '--', str(ROOT)).splitlines():
        meta, path = line.split('\t', 1)
        index[path] = meta.split()[1]
    if any(index.get(item['path']) != item['git_blob_sha1'] for item in records):
        raise ValueError('Git index changed original bytes')
    if names:
        git('commit', '-m', 'assets: upload ' + str(len(records)) + ' verified game files')
        git('push', 'origin', 'HEAD:refs/heads/' + BRANCH)
    head = git('rev-parse', 'HEAD')
    if git('ls-remote', 'origin', 'refs/heads/' + BRANCH).split()[0] != head:
        raise ValueError('Remote commit verification failed')
    print('Remote commit verified:', head, 'Files:', len(records), flush=True)


def resume():
    receipt_path = ROOT / 'GIT_UPLOAD_RECEIPT.json'
    if not receipt_path.exists():
        return [], set()
    receipt = json.loads(receipt_path.read_text())
    records = receipt['files']
    for item in records:
        path = Path(item['path'])
        if not path.is_relative_to(ROOT) or '..' in path.parts or path.is_symlink():
            raise ValueError('Unsafe resume path')
        data = path.read_bytes()
        if len(data) != item['bytes'] or sha(data) != item['sha256']:
            raise ValueError('Previously imported file changed')
    completed = set(receipt['sources_imported'])
    if not completed <= set(SOURCES):
        raise ValueError('Unknown resume source')
    print('Resuming after verification of', len(records), 'existing files', flush=True)
    return records, completed


def main():
    if git('branch', '--show-current') != BRANCH:
        raise ValueError('Unexpected branch')
    git('config', 'user.name', 'St Gabriel Asset Import')
    git('config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    git('config', 'core.autocrlf', 'false')
    records, completed = resume()
    processed = set()
    deadline = time.monotonic() + 1800
    with tempfile.TemporaryDirectory(prefix='estate-files-') as directory:
        while time.monotonic() < deadline and completed != set(SOURCES):
            try:
                request = urllib.request.Request(ISSUE_URL, headers={'User-Agent': 'St-Gabriel-Asset-Import'})
                with urllib.request.urlopen(request, timeout=30) as response:
                    body = json.load(response).get('body') or ''
            except urllib.error.HTTPError as exc:
                print('Source index temporarily unavailable:', exc.code, flush=True)
                time.sleep(60)
                continue
            if MARKER not in body:
                time.sleep(30)
                continue
            payload = json.loads(body.split(MARKER, 1)[1].split('```json', 1)[1].split('```', 1)[0])
            old_count = len(completed)
            for source_id, url in payload.items():
                if source_id not in SOURCES or source_id in completed or (source_id, url) in processed:
                    continue
                processed.add((source_id, url))
                try:
                    archive_path = download(source_id, url, Path(directory))
                except Exception as exc:
                    print('Source requires refresh:', source_id, type(exc).__name__, flush=True)
                    continue
                records.extend(install(source_id, archive_path))
                completed.add(source_id)
            if len(completed) > old_count:
                publish(records, completed)
            if completed != set(SOURCES):
                time.sleep(30)
        if completed != set(SOURCES):
            raise TimeoutError('Some source files remain; earlier verified commits are preserved')
        if len(records) != PLAN['expected_total_files']:
            raise ValueError('Final file count mismatch')
        print('ALL PINNED SOURCES COMMITTED', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Stopped safely:', type(exc).__name__, flush=True)
        raise SystemExit(1)
