#!/usr/bin/env python3
"""Small offline CPU checkpoint demo. Python 3.9+, Linux/macOS, standard library."""
import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import zipfile

VERSION = 1
SCRIPT = Path(__file__).resolve()
SAMPLE = SCRIPT.with_name('sample_input.json')
EXIT_INTERRUPTED = 75


class Blocked(Exception):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def fsync_dir(directory):
    fd = os.open(str(directory), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_replace(path, data):
    """For mutable metadata only. Durable temp file then atomic replacement."""
    fd, name = tempfile.mkstemp(prefix='.pending-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
        fsync_dir(path.parent)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def immutable_write(path, data):
    """Never replace output bytes, even when they are corrupt."""
    if path.is_symlink():
        raise Blocked('Refusing symlink output: ' + str(path))
    if path.exists():
        if path.read_bytes() != data:
            raise Blocked('Existing output differs; preserved without overwrite: ' + str(path))
        return
    fd, name = tempfile.mkstemp(prefix='.pending-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(name, path)  # Exclusive publication: fails rather than replacing.
        fsync_dir(path.parent)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def safe_path(root, relative):
    p = Path(relative)
    if p.is_absolute() or '..' in p.parts:
        raise Blocked('Manifest location must stay inside the chosen workspace')
    target = root / p
    if any(part.is_symlink() for part in (target, *target.parents) if part != root.parent):
        raise Blocked('Refusing symlink in workspace output path: ' + relative)
    if root not in target.resolve().parents:
        raise Blocked('Output path escapes workspace: ' + relative)
    return target


def save(root, manifest):
    atomic_replace(root / 'manifest.json', encoded(manifest))


def event(root, action, **fields):
    with (root / 'events.jsonl').open('a', encoding='utf-8') as handle:
        handle.write(json.dumps({'event': action, **fields}, sort_keys=True) + '\n')
        handle.flush()
        os.fsync(handle.fileno())


@contextmanager
def locked(root):
    # flock is released by the OS even if the process is killed. No stale-lease steal.
    path = root / '.lock'
    if path.is_symlink():
        raise Blocked('Refusing symlink lock')
    with path.open('a+b') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Blocked('Another process holds this local workspace lock')
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def task(task_id, shard_id, input_hash, script_hash, dependencies):
    return {'task_id': task_id, 'shard_id': shard_id, 'revision': 1,
            'status': 'planned', 'resource': 'cpu-local-offline',
            'input_sha256': input_hash, 'script_sha256': script_hash,
            'parameters': {'shards': 3, 'algorithm': 'unicode-word-count-v1'},
            'model_revision': None, 'dependencies': dependencies,
            'outputs': [], 'attempts': 0, 'owner': None, 'lease_until': None}


def initialize(root):
    # mkdir without exist_ok deliberately rejects existing, empty, and symlink dirs.
    root.mkdir(parents=False, exist_ok=False)
    for name in ('outputs', 'backups', 'restored', 'source'):
        (root / name).mkdir()
    sample, source = SAMPLE.read_bytes(), SCRIPT.read_bytes()
    immutable_write(root / 'input.json', sample)
    immutable_write(root / 'source' / 'cpu_checkpoint_demo.py', source)
    immutable_write(root / 'source' / 'sample_input.json', sample)
    tasks = [task('count-' + str(n), str(n), sha(sample), sha(source), []) for n in range(3)]
    tasks.append(task('aggregate', 'aggregate', sha(sample), sha(source), [t['task_id'] for t in tasks]))
    manifest = {'project_id': 'offline-cpu-checkpoint-demo', 'demo_version': VERSION,
                'state': 'running', 'tasks': tasks}
    save(root, manifest)
    event(root, 'initialized', task_count=len(tasks))


def load(root):
    manifest = read_json(root / 'manifest.json')
    if manifest.get('project_id') != 'offline-cpu-checkpoint-demo' or manifest.get('demo_version') != VERSION:
        raise Blocked('Not a supported demo workspace')
    return manifest


def block(root, manifest, message, current=None):
    manifest['state'] = 'blocked'
    manifest['blocked_reason'] = message
    if current is not None:
        current['status'] = 'blocked'
        current['blocked_reason'] = message
        for output in current['outputs']:
            output['verified'] = False
        blocked_ids = {current['task_id']}
        changed = True
        while changed:
            changed = False
            for dependent in manifest['tasks']:
                if dependent['task_id'] not in blocked_ids and any(dep in blocked_ids for dep in dependent['dependencies']):
                    dependent.update(status='blocked', blocked_reason='A required dependency is blocked')
                    for output in dependent['outputs']:
                        output['verified'] = False
                    blocked_ids.add(dependent['task_id'])
                    changed = True
    save(root, manifest)
    event(root, 'blocked', reason=message)
    raise Blocked(message)


def verify_output(root, output):
    path = safe_path(root, output['location'])
    if not path.is_file() or sha(path.read_bytes()) != output['sha256']:
        raise Blocked('Missing or corrupt output; preserved without overwrite: ' + output['location'])


def reconcile(root, manifest):
    if manifest.get('state') == 'blocked':
        raise Blocked('Workspace remains blocked: ' + manifest.get('blocked_reason', 'unknown'))
    current_input = sha((root / 'input.json').read_bytes())
    current_script = sha(SCRIPT.read_bytes())
    if sha((root / 'source' / 'cpu_checkpoint_demo.py').read_bytes()) != current_script or sha((root / 'source' / 'sample_input.json').read_bytes()) != current_input:
        block(root, manifest, 'Saved source/input copy changed; preserve it and inspect')
    for current in manifest['tasks']:
        if current['input_sha256'] != current_input or current['script_sha256'] != current_script:
            block(root, manifest, 'Input/script changed; create a new chosen workspace')
        if current['status'] in ('done', 'validating'):
            if len(current['outputs']) != 1:
                block(root, manifest, 'Checkpoint has no unique output receipt', current)
            try:
                verify_output(root, current['outputs'][0])
            except Blocked as error:
                block(root, manifest, str(error), current)
            if current['status'] == 'validating':
                current.update(status='done', owner=None, lease_until=None)
                save(root, manifest)
                event(root, 'adopt_verified_output', task_id=current['task_id'])
            else:
                event(root, 'skip_verified_done', task_id=current['task_id'])
        elif current['status'] == 'running':
            # This process owns flock, so no local worker remains in this demo.
            destination = root / 'outputs' / (current['task_id'] + '.json')
            if destination.exists() or destination.is_symlink():
                block(root, manifest, 'Uncommitted output has no hash receipt; preserve and inspect: ' + str(destination), current)
            current.update(status='planned', owner=None, lease_until=None)
            save(root, manifest)
            event(root, 'reconcile_unfinished', task_id=current['task_id'])
        elif current['status'] != 'planned':
            block(root, manifest, 'Unexpected task state: ' + current['status'])


def compute(root, current):
    if current['task_id'] == 'aggregate':
        counts = Counter()
        records = 0
        for n in range(3):
            shard = read_json(root / 'outputs' / ('count-' + str(n) + '.json'))
            counts.update(shard['counts'])
            records += len(shard['record_ids'])
        return {'records': records, 'tokens': sum(counts.values()), 'counts': dict(sorted(counts.items()))}
    rows = read_json(root / 'input.json')
    rows = [row for i, row in enumerate(rows) if i % 3 == int(current['shard_id'])]
    words = Counter(word for row in rows for word in re.findall(r'\w+', row['text'].casefold()))
    return {'shard_id': current['shard_id'], 'record_ids': [r['id'] for r in rows], 'counts': dict(sorted(words.items()))}


def interrupt(root, stage, task_id):
    event(root, 'injected_interruption', stage=stage, task_id=task_id)
    print(json.dumps({'status': 'interrupted', 'stage': stage, 'task_id': task_id}))
    raise SystemExit(EXIT_INTERRUPTED)


def zip_bytes(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.external_attr = 0o600 << 16
            archive.writestr(info, data)
    return buffer.getvalue()


def verify_delivery(root):
    receipt = read_json(root / 'delivery.json')
    for output in receipt['verified_files']:
        verify_output(root, output)
    return receipt


def make_delivery(root, manifest):
    if (root / 'delivery.json').exists():
        return verify_delivery(root)
    names = ['input.json', 'source/cpu_checkpoint_demo.py', 'source/sample_input.json', 'manifest.json']
    names.extend(t['outputs'][0]['location'] for t in manifest['tasks'])
    files = {name: safe_path(root, name).read_bytes() for name in names}
    expected = {name: sha(data) for name, data in files.items()}
    files['backup-index.json'] = encoded({'files': expected})
    backup = zip_bytes(files)
    immutable_write(root / 'backups' / 'result.zip', backup)
    with zipfile.ZipFile(io.BytesIO((root / 'backups' / 'result.zip').read_bytes())) as archive:
        if set(archive.namelist()) != set(files):
            raise Blocked('Unexpected archive members')
        for name in sorted(files):
            restored = safe_path(root, 'restored/' + name)
            restored.parent.mkdir(parents=True, exist_ok=True)
            immutable_write(restored, archive.read(name))
            if sha(restored.read_bytes()) != sha(files[name]):
                raise Blocked('Restored backup hash mismatch: ' + name)
    verified = [{'location': 'backups/result.zip', 'sha256': sha(backup), 'verified': True}]
    verified += [{'location': name, 'sha256': sha(data), 'verified': True} for name, data in sorted(files.items()) if name != 'backup-index.json']
    verified += [{'location': 'restored/' + name, 'sha256': sha(data), 'verified': True} for name, data in sorted(files.items())]
    receipt = {'status': 'complete', 'backup_scope': 'same workspace; not disaster recovery',
               'final_output': 'outputs/aggregate.json',
               'final_sha256': sha(files['outputs/aggregate.json']),
               'backup_restored_and_hash_checked': True, 'verified_files': verified}
    atomic_replace(root / 'delivery.json', encoded(receipt))
    event(root, 'backup_restored_verified', final_sha256=receipt['final_sha256'])
    return verify_delivery(root)


def run(root, args):
    with locked(root):
        manifest = load(root)
        reconcile(root, manifest)
        completed_now = 0
        for current in manifest['tasks']:
            if current['status'] == 'done':
                continue
            by_id = {t['task_id']: t for t in manifest['tasks']}
            if any(by_id[dep]['status'] != 'done' for dep in current['dependencies']):
                block(root, manifest, 'Dependencies are not done', current)
            current.update(status='running', owner='local-pid-' + str(os.getpid()),
                           lease_until=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                           submission_ref='local://' + str(os.getpid()) + '/' + current['task_id'])
            current['attempts'] += 1
            save(root, manifest)  # Write-ahead checkpoint precedes computation.
            event(root, 'start', task_id=current['task_id'], attempt=current['attempts'])
            if args.pause_before_work == current['task_id']:
                print(json.dumps({'status': 'paused_before_work', 'task_id': current['task_id']}), flush=True)
                sys.stdin.readline()
            if args.interrupt_before_work == current['task_id']:
                interrupt(root, 'before_work', current['task_id'])
            value = encoded(compute(root, current))
            relative = 'outputs/' + current['task_id'] + '.json'
            try:
                immutable_write(safe_path(root, relative), value)
                output = {'location': relative, 'sha256': sha(value), 'verified': True}
                verify_output(root, output)
            except Blocked as error:
                block(root, manifest, str(error), current)
            current.update(status='validating', outputs=[output])
            save(root, manifest)  # Durable output receipt allows safe adoption.
            if args.interrupt_after_output == current['task_id']:
                interrupt(root, 'after_output_receipt', current['task_id'])
            current.update(status='done', owner=None, lease_until=None)
            save(root, manifest)
            event(root, 'done', task_id=current['task_id'])
            completed_now += 1
            if args.interrupt_after == completed_now:
                interrupt(root, 'after_done', current['task_id'])
        manifest['state'] = 'complete'
        save(root, manifest)
        try:
            receipt = make_delivery(root, manifest)
        except (Blocked, OSError, ValueError, zipfile.BadZipFile) as error:
            block(root, manifest, str(error))
        print(json.dumps({'status': 'complete', 'final_sha256': receipt['final_sha256'],
                          'backup_restored_and_hash_checked': True,
                          'attempts': {t['task_id']: t['attempts'] for t in manifest['tasks']}}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('new', 'resume', 'verify'))
    parser.add_argument('--workspace', type=Path, required=True, help='Explicit directory; new requires it not to exist. Parent must exist.')
    parser.add_argument('--interrupt-after', type=int, help='Testing only: exit 75 after N newly completed tasks')
    parser.add_argument('--interrupt-before-work', choices=('count-0', 'count-1', 'count-2', 'aggregate'))
    parser.add_argument('--pause-before-work', choices=('count-0', 'count-1', 'count-2', 'aggregate'), help='Testing only: wait for a stdin line after saving running state')
    parser.add_argument('--interrupt-after-output', choices=('count-0', 'count-1', 'count-2', 'aggregate'))
    args = parser.parse_args()
    if args.interrupt_after is not None and not 1 <= args.interrupt_after <= 4:
        parser.error('--interrupt-after must be 1..4')
    if args.workspace.is_symlink():
        parser.error('workspace must not be a symlink')
    root = args.workspace.resolve()
    try:
        if args.command == 'new':
            initialize(root)
        elif not root.is_dir():
            raise Blocked('Workspace does not exist; choose a new path with new')
        if args.command == 'verify':
            with locked(root):
                manifest = load(root)
                if manifest['state'] != 'complete' or any(t['status'] != 'done' for t in manifest['tasks']):
                    raise Blocked('Workspace is not complete')
                for current in manifest['tasks']:
                    verify_output(root, current['outputs'][0])
                receipt = verify_delivery(root)
                print(json.dumps({'status': 'verified', 'final_sha256': receipt['final_sha256']}))
        else:
            run(root, args)
        return 0
    except (Blocked, OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'status': 'blocked', 'error': str(error)}), file=sys.stderr)
        return 3


if __name__ == '__main__':
    sys.exit(main())
