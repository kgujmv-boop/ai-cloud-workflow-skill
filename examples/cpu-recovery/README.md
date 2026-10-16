# Reproducible CPU checkpoint and recovery demo

This original, deliberately small example counts words in nine bundled text records. Three independent CPU shards produce separate files; a dependent aggregation task produces the final count. It requires no cloud account, network request, GPU, package installation, credential, or paid resource.

**Requirements:** Python 3.9 or later on Linux/macOS and a normal local filesystem with atomic rename, hard links, `fsync`, and `flock`. Only the Python standard library is used. Windows and network filesystems are not supported by this demo.

This is a recovery example, not a benchmark, scheduler, cloud dispatcher, or authorization system. Its timing and tiny input say nothing about production throughput or hardware capacity.

## Run in a directory you choose

Run these commands from this example directory. Replace `/your/existing-parent/...` with paths you choose. The parent must already exist; the new workspace itself must **not** exist, even as an empty directory. There is no default output location, automatic cleanup, or overwrite flag.

```sh
python3 cpu_checkpoint_demo.py new --workspace /your/existing-parent/cpu-demo-run
python3 cpu_checkpoint_demo.py verify --workspace /your/existing-parent/cpu-demo-run
```

A successful run prints `status: complete`, a final SHA-256, per-task attempt counts, and `backup_restored_and_hash_checked: true`. `verify` checks final/shard output hashes, the backup, all restored files, and the original files listed in the delivery receipt. Relative output locations in the manifest are resolved against the workspace.

Expected final result: **9 records, 54 tokens**. The exact `outputs/aggregate.json` SHA-256 is:

```text
480d53766e520a3cd3a7072228a9c21c8a91af2cd31f617b13db163da1fe78c2
```

The final aggregate is byte-for-byte reproducible. Runtime manifest fields such as PID, attempts, and lease timestamps can differ, so archives containing those fields are not promised to be identical across fresh runs.

## Interrupt, then resume

```sh
python3 cpu_checkpoint_demo.py new --workspace /your/existing-parent/cpu-demo-interrupted --interrupt-after 1
# Expected exit code: 75. count-0 is already done and verified.
python3 cpu_checkpoint_demo.py resume --workspace /your/existing-parent/cpu-demo-interrupted
python3 cpu_checkpoint_demo.py verify --workspace /your/existing-parent/cpu-demo-interrupted
```

The completed shard's hash and file modification time stay unchanged. Its attempt count remains 1. `events.jsonl` records `skip_verified_done`; only unfinished tasks start. Repeating `resume` after completion verifies and reuses all four tasks.

Other deliberate fault-injection points:

- `--interrupt-before-work count-1`: exit after saving a `running` checkpoint, before computation. Resume reconciles the interrupted task and starts a second attempt; `count-0` is reused.
- `--interrupt-after-output count-1`: exit after saving the durable output hash receipt, before the `done` transition. Resume verifies and adopts the output without restarting that worker.
- `--pause-before-work count-1`: save the `running` checkpoint and wait for a line on standard input. The test runner uses this controlled pause to send an actual SIGKILL, then verifies recovery and automatic release of the OS lock.

Do not use a shell `set -e` sequence without allowing the intentional exit code 75.

## What is durable and when

1. The manifest records input/code identity, parameters, dependencies, task state, and CPU placement before any computation.
2. A single local process takes an OS-backed workspace lock. The OS releases it even after SIGKILL. This permits local reconciliation; it does **not** justify reclaiming a remote or distributed job's lease.
3. Before each task, its `running` checkpoint and attempt number are saved using `fsync` and atomic replacement.
4. Each output is written separately and published exclusively. Existing different bytes are never replaced.
5. The output hash is verified; its receipt is persisted in `validating` state before `done` is recorded.
6. On resume, every completed/receipted output is checked before new work. A completed task is reused under the same identity. Aggregation starts only after all dependencies are `done`.
7. The input, source, manifest, and outputs are put in a ZIP backup. Every entry is restored into a separate directory and hash-checked before the delivery receipt reports success.

`events.jsonl` is an audit aid, not the recovery authority; an abrupt termination can truncate its last line. The manifest and verified bytes drive recovery. Abrupt termination can also leave an unused `.pending-*` temporary file; it is not treated as an output and is not deleted automatically.

## Corruption is a stop condition

If a completed shard is missing or its hash differs, `resume` exits 3, marks the workspace and affected tasks blocked, and preserves the bytes. Completed dependents are blocked too. No new shard is started. A later resume remains blocked rather than silently recomputing or overwriting evidence.

An output present without a persisted hash receipt also blocks recovery: the demo does not guess whether it is trustworthy. Changed input/source, a damaged backup, or damaged restored files are rejected as well. Inspect or preserve the affected workspace; choose a **different new workspace** for a fresh run. There is deliberately no automatic repair or force-overwrite command.

## Files and recovery scope

```text
input.json                      Frozen fixture input
source/                         Frozen script and companion input
manifest.json                   Task identity, dependencies, states, attempts, output receipts
outputs/count-0.json             First shard
outputs/count-1.json             Second shard
outputs/count-2.json             Third shard
outputs/aggregate.json           Final result
backups/result.zip              Input, source, manifest, outputs, and backup-index.json
restored/                       Extracted backup, verified against expected file hashes
delivery.json                   Final hash and verification receipts (at workspace root)
events.jsonl                    Local audit log
.lock                           Kernel-backed local lock file
```


The verified restored final output is `restored/outputs/aggregate.json`. You can reproduce it from restored code and input in a new chosen workspace:

```sh
python3 /your/existing-parent/cpu-demo-run/restored/source/cpu_checkpoint_demo.py new --workspace /your/existing-parent/cpu-demo-rebuilt
```

The restored snapshot is for recovering the result and rebuilding from source; it is not a second live workspace. Do not run `resume` inside `restored/`.

**The ZIP and restored copy are on the same filesystem as the workspace.** This proves the included files can be restored and hash-checked locally; it does not protect against loss of that filesystem, power failure, malicious edits to both receipts and data, or every possible crash point. Nothing is uploaded. Separate durable storage requires a separately authorized step.

## Reproduce the tests and inspect actual run proof

From this example directory:

```sh
python3 test_cpu_checkpoint_demo.py --workspace /your/existing-parent/cpu-demo-proof
```

The test runner also requires a new explicitly chosen directory. It retains its generated workspaces and writes `run-proof.json`; it does not remove anything. It checks:

- Uninterrupted completion, exact expected final hash, backup extraction, and verification
- Checkpoint interruption and unchanged completed-shard hash, mtime, and attempt count
- Interrupted `running` task reconciliation and actual SIGKILL recovery
- Durable output receipt adoption and idempotent repeated resume
- Corrupt completed shard preservation, including blocked completed dependents
- Unreceipted orphan output and corrupt ZIP preservation
- Input identity changes, existing-workspace rejection, and concurrent-owner rejection
- Rebuilding the same final output using the restored source/input
- Every generated manifest against the repository's offline manifest validator

`proof/run-proof.json` is captured from an actual successful run of this version. It records source/input/validator hashes, Python version, test outcomes, command exit codes, normalized output, and the final result hash. `proof/aggregate.json` is the actual final output from that run. Re-running the tests produces new evidence for your environment; the bundled proof is not a claim that every platform was tested.

## 中文简要说明

这是仅用 CPU 和 Python 标准库的断点恢复小示例，不联网、不调用 GPU、不登录账号、不购买算力。请明确选择一个尚不存在的新工作目录。

- 首次运行：`python3 cpu_checkpoint_demo.py new --workspace 你选择的新目录`
- 模拟中断：在首次运行命令末尾加 `--interrupt-after 1`，返回码 75 属于预期
- 继续运行：`python3 cpu_checkpoint_demo.py resume --workspace 同一目录`
- 核验结果：`python3 cpu_checkpoint_demo.py verify --workspace 同一目录`
- 复现测试：`python3 test_cpu_checkpoint_demo.py --workspace 另一个新目录`

已完成的分片会先校验再复用，不重复计算；损坏文件会保留并阻止继续，不会静默覆盖。测试还实际终止一个子进程并验证恢复。备份会另行解包、逐个核验哈希，但仍保存在同一工作目录内，不等于异地备份。此例不提供性能或算力基准结论。
