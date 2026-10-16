#!/usr/bin/env python3
"""Run offline behavioral tests in a new, explicitly chosen proof workspace."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import select
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / 'cpu_checkpoint_demo.py'
VALIDATOR = HERE.parent.parent / 'scripts' / 'validate_manifest.py'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def obj(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path, help='New nonexistent proof directory; parent must exist')
    args = parser.parse_args()
    root = args.workspace.resolve()
    root.mkdir(exist_ok=False)
    checks = []
    transcript = []

    def call(command, workspace, *extra, expected=0, script=SCRIPT):
        argv = [sys.executable, str(script), command, '--workspace', str(workspace), *extra]
        result = subprocess.run(argv, text=True, capture_output=True, timeout=20)
        transcript.append({'command': [str(script.name), command, '--workspace', str(workspace.relative_to(root)), *extra],
                           'returncode': result.returncode, 'stdout': result.stdout.strip().replace(str(root), '<test-workspace>'), 'stderr': result.stderr.strip().replace(str(root), '<test-workspace>')})
        assert result.returncode == expected, (argv, result.returncode, result.stdout, result.stderr)
        return result

    def check(name, **evidence):
        checks.append({'test': name, 'status': 'PASS', **evidence})
        print('PASS ' + name, flush=True)

    def manifest(path):
        return obj(path / 'manifest.json')

    def attempts(path):
        return {t['task_id']: t['attempts'] for t in manifest(path)['tasks']}

    baseline = root / 'uninterrupted'
    call('new', baseline)
    call('verify', baseline)
    final_hash = digest(baseline / 'outputs' / 'aggregate.json')
    assert final_hash == '480d53766e520a3cd3a7072228a9c21c8a91af2cd31f617b13db163da1fe78c2'
    expected = obj(baseline / 'outputs' / 'aggregate.json')
    assert expected['records'] == 9 and expected['tokens'] == 54 and expected['counts']['work'] == 4
    assert attempts(baseline) == {'count-0': 1, 'count-1': 1, 'count-2': 1, 'aggregate': 1}
    check('uninterrupted_run_and_backup_restore', final_sha256=final_hash, records=9)

    resumed = root / 'checkpoint-interrupted'
    call('new', resumed, '--interrupt-after', '1', expected=75)
    assert manifest(resumed)['tasks'][0]['status'] == 'done'
    shard = resumed / 'outputs' / 'count-0.json'
    before = (digest(shard), shard.stat().st_mtime_ns)
    call('resume', resumed)
    assert (digest(shard), shard.stat().st_mtime_ns) == before
    assert attempts(resumed) == attempts(baseline)
    assert digest(resumed / 'outputs' / 'aggregate.json') == final_hash
    assert 'skip_verified_done' in (resumed / 'events.jsonl').read_text()
    check('checkpoint_resume_skips_completed_shard', attempts=attempts(resumed), unchanged_shard_hash=before[0], unchanged_mtime=True)

    in_flight = root / 'in-flight-interrupted'
    call('new', in_flight, '--interrupt-before-work', 'count-1', expected=75)
    assert manifest(in_flight)['tasks'][1]['status'] == 'running'
    assert not (in_flight / 'outputs' / 'count-1.json').exists()
    call('resume', in_flight)
    assert attempts(in_flight) == {'count-0': 1, 'count-1': 2, 'count-2': 1, 'aggregate': 1}
    assert digest(in_flight / 'outputs' / 'aggregate.json') == final_hash
    check('write_ahead_running_checkpoint_reconciled', attempts=attempts(in_flight))

    killed = root / 'hard-killed'
    proc = subprocess.Popen([sys.executable, str(SCRIPT), 'new', '--workspace', str(killed), '--pause-before-work', 'count-1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert select.select([proc.stdout], [], [], 10)[0], 'Child did not reach pause'
        pause = json.loads(proc.stdout.readline())
        assert pause == {'status': 'paused_before_work', 'task_id': 'count-1'}, pause
        assert manifest(killed)['tasks'][1]['status'] == 'running'
        proc.kill()
        proc.wait(timeout=10)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=10)
        proc.stdin.close()
        proc.stdout.close()
        proc.stderr.close()
    transcript.append({'command': ['cpu_checkpoint_demo.py', 'new', '--workspace', 'hard-killed', '--pause-before-work', 'count-1'], 'returncode': proc.returncode, 'intervention': 'Test sent SIGKILL after observing durable running checkpoint'})
    assert proc.returncode == -9
    call('resume', killed)
    assert attempts(killed) == {'count-0': 1, 'count-1': 2, 'count-2': 1, 'aggregate': 1}
    assert digest(killed / 'outputs' / 'aggregate.json') == final_hash
    check('actual_sigkill_releases_lock_and_resumes', killed_returncode=proc.returncode, attempts=attempts(killed))

    receipt = root / 'receipt-interrupted'
    call('new', receipt, '--interrupt-after-output', 'count-1', expected=75)
    assert manifest(receipt)['tasks'][1]['status'] == 'validating'
    path = receipt / 'outputs' / 'count-1.json'
    before = (digest(path), path.stat().st_mtime_ns)
    call('resume', receipt)
    assert (digest(path), path.stat().st_mtime_ns) == before
    assert attempts(receipt) == attempts(baseline)
    assert 'adopt_verified_output' in (receipt / 'events.jsonl').read_text()
    check('durable_receipt_adopted_without_worker_restart', attempts=attempts(receipt), unchanged_mtime=True)

    before_attempts = attempts(resumed)
    before_backups = digest(resumed / 'backups' / 'result.zip')
    call('resume', resumed)
    call('verify', resumed)
    assert attempts(resumed) == before_attempts
    assert digest(resumed / 'backups' / 'result.zip') == before_backups
    check('completed_workspace_repeat_is_idempotent', attempts=attempts(resumed))

    corrupt = root / 'corrupt-completed'
    call('new', corrupt, '--interrupt-after', '1', expected=75)
    path = corrupt / 'outputs' / 'count-0.json'
    path.write_bytes(b'INTENTIONALLY CORRUPT TEST OUTPUT\n')
    corrupt_hash = digest(path)
    call('resume', corrupt, expected=3)
    assert digest(path) == corrupt_hash
    assert manifest(corrupt)['state'] == 'blocked'
    assert manifest(corrupt)['tasks'][0]['status'] == 'blocked'
    assert not (corrupt / 'outputs' / 'count-1.json').exists()
    call('resume', corrupt, expected=3)
    assert digest(path) == corrupt_hash
    check('corrupt_completed_output_blocks_and_is_preserved', preserved_sha256=corrupt_hash)

    complete_corrupt = root / 'corrupt-after-all-done'
    call('new', complete_corrupt)
    path = complete_corrupt / 'outputs' / 'count-0.json'
    path.write_bytes(b'CORRUPTION AFTER AGGREGATION\n')
    before = digest(path)
    call('resume', complete_corrupt, expected=3)
    assert digest(path) == before
    assert manifest(complete_corrupt)['tasks'][-1]['status'] == 'blocked'
    check('corrupt_completed_dependency_blocks_downstream_done_task')

    orphan = root / 'orphan-output'
    call('new', orphan, '--interrupt-before-work', 'count-0', expected=75)
    path = orphan / 'outputs' / 'count-0.json'
    path.write_bytes(b'UNCOMMITTED OUTPUT WITHOUT HASH RECEIPT\n')
    before = digest(path)
    call('resume', orphan, expected=3)
    assert digest(path) == before
    check('unreceipted_orphan_output_blocks_and_is_preserved')

    bad_backup = root / 'corrupt-backup'
    call('new', bad_backup)
    path = bad_backup / 'backups' / 'result.zip'
    path.write_bytes(b'INTENTIONALLY CORRUPT BACKUP\n')
    before = digest(path)
    call('verify', bad_backup, expected=3)
    call('resume', bad_backup, expected=3)
    assert digest(path) == before and manifest(bad_backup)['state'] == 'blocked'
    check('corrupt_backup_detected_and_preserved')

    bad_restore = root / 'corrupt-restored-copy'
    call('new', bad_restore)
    path = bad_restore / 'restored' / 'outputs' / 'aggregate.json'
    path.write_bytes(b'INTENTIONALLY CORRUPT RESTORED COPY\n')
    before = digest(path)
    call('verify', bad_restore, expected=3)
    call('resume', bad_restore, expected=3)
    assert digest(path) == before and manifest(bad_restore)['state'] == 'blocked'
    check('corrupt_restored_copy_detected_and_preserved')

    changed_input = root / 'changed-input'
    call('new', changed_input, '--interrupt-after', '1', expected=75)
    path = changed_input / 'input.json'
    path.write_text('[]\n', encoding='utf-8')
    call('resume', changed_input, expected=3)
    assert manifest(changed_input)['state'] == 'blocked'
    check('input_identity_change_blocks_resume')

    before = digest(baseline / 'manifest.json')
    call('new', baseline, expected=3)
    assert digest(baseline / 'manifest.json') == before
    empty = root / 'already-existing-empty'
    empty.mkdir()
    call('new', empty, expected=3)
    assert not list(empty.iterdir())
    check('new_refuses_existing_workspaces_without_modification')

    with (baseline / '.lock').open('a+b') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        call('resume', baseline, expected=3)
        fcntl.flock(handle, fcntl.LOCK_UN)
    check('concurrent_workspace_owner_is_rejected')

    recovered = root / 'rebuild-from-restored-source'
    call('new', recovered, script=baseline / 'restored' / 'source' / 'cpu_checkpoint_demo.py')
    assert digest(recovered / 'outputs' / 'aggregate.json') == final_hash
    check('restored_source_and_input_rebuild_same_final_output', final_sha256=final_hash)

    sys.dont_write_bytecode = True
    specification = importlib.util.spec_from_file_location('validate_manifest', VALIDATOR)
    validator = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(validator)
    validated = []
    for path in root.iterdir():
        if (path / 'manifest.json').is_file():
            errors = validator.validate(manifest(path))
            assert not errors, (str(path), errors)
            validated.append(path.name)
    check('all_manifests_pass_repository_validator', workspace_count=len(validated))

    report = {'status': 'PASS', 'test_count': len(checks),
              'run_utc': datetime.now(timezone.utc).isoformat(),
              'path_normalization': 'The selected proof workspace is replaced with <test-workspace> in captured output.',
              'validator_sha256': digest(VALIDATOR),
              'python': sys.version.split()[0], 'platform': sys.platform,
              'script_sha256': digest(SCRIPT), 'test_script_sha256': digest(Path(__file__)), 'sample_sha256': digest(HERE / 'sample_input.json'),
              'final_sha256': final_hash,
              'scope': 'Small deterministic offline CPU fixture; fault-injected exits and actual SIGKILL recovery; not a benchmark or hardware failure test.',
              'checks': checks, 'commands': transcript}
    (root / 'run-proof.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'PASS', 'test_count': len(checks), 'final_sha256': final_hash, 'proof': str(root / 'run-proof.json')}))


if __name__ == '__main__':
    main()
