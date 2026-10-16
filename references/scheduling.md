# Scheduling and Recovery

## Inspect resources

Record observed_at, authentication state, running jobs and owners, CPU, RAM, free disk, each GPU and VRAM, quota_seen, and evidence location. Use null for unknown values. Reserve capacity for model caches and temporary files. If free quota is insufficient, defer affected GPU work; do not purchase or change accounts to bypass it.

Two GPUs may run separate independent inputs if a model fits each card and CPU/RAM/disk and provider concurrency limits permit. A second provider receives only unclaimed shards. Three 15 GiB cards are not a single 45 GiB device. Cloud storage is separate from runtime disk and may be paid even when compute is free.

## Record before submitting

For each task store task_id, revision, input_sha256, script_sha256, parameters, model_revision, shard_id, dependencies, owner, resource, status, lease_until, checkpoint, outputs, and submission_ref. Persist the record before dispatch. One dispatcher controls allocation, or use an actual atomic claim mechanism; a JSON file alone is not a lock.

Compute an equivalence key from canonical JSON containing input hash, script hash, parameters, model revision, and shard ID. A different task_id does not make equivalent work independent. Check active and already verified completed outputs before a new submission. The validator rejects equivalent active work even when a rerun reason is present. When an equivalent completed task exists, reuse its verified output without creating a new active job. If new computation is genuinely needed, give the new task a nonempty `recompute_reason` describing why; this records intent, not execution permission. Changing task ID, revision number, or resource does not change work identity. A changed input, script, parameters, model revision, or shard does.

States: planned → claimed → submitted → running → validating → done. Exception states: failed, unknown, blocked, cancelled. A submission with no receipt is unknown, not failed. Record platform job references and shard output manifests.

## Recover without duplication

1. Reload the project record. Inspect the original provider job and output before resubmitting. Browser disconnection does not prove termination.
2. An expired lease or missing worker triggers reconciliation, not immediate reassignment. Confirm the old job ended or never submitted, and identify completed shards. If uncertain, retain unknown and hold that shard.
3. Compare a trusted completion baseline with the current requested input files, code, parameters, model revision, shard, dependency list, and actual output hashes. Check dependency outputs and their identities transitively, not only the final artifact. Reuse only when every check passes. Mere file existence, an old verified flag, or matching output bytes cannot show that current inputs remain compatible. Keep mismatches blocked; do not move or delete files as part of inspection. Do not combine changed narration with stale audio or captions.
4. Checkpoint the last verified output and next action after expensive operations. Transfer through authorized private storage only.
5. Reproduce a fix on a small sample before retrying a batch. Repeated identical failures require diagnosis; denied permission, unexpected cost, or unresolved previous-job state stops the affected action.

Estimate time from measured unit duration × remaining units / effective parallelism, plus transfer, assembly, and validation. State queue/quota uncertainty. Two cards do not justify an automatic twofold speed claim.

## Completed records and compatibility

Every `done` task must have a nonempty outputs array. Each output needs `location` (a nonempty path or URI string), `sha256` (64 lowercase hexadecimal characters), and `verified: true`. A location records where to find the artifact; the offline validator does not open it or prove it accessible. Only set verified after checking the actual file. All dependencies of active or done tasks must be done too; the referenced done records must independently pass their own output checks.

Use strict JSON: duplicate property names and non-finite numbers are rejected. Task IDs, shard IDs, resource names, and project IDs must not be blank. Deep dependency graphs are checked iteratively.

Existing manifests without `recompute_reason` remain valid unless they activate work equivalent to a completed task. Older done outputs lacking `location` now fail validation: find and check the actual artifact, then record its path or URI. Do not invent a locator or set verified merely to pass. `recompute_reason` may be absent or null for ordinary work; if provided it must be a nonempty string. A legitimate rerun must still satisfy dependency, lease, receipt, permission, and resource checks.

For a local example of checkpointing, verified reuse, blocked corruption, and restored backups, see [the CPU demo](../examples/cpu-recovery/README.md). This is a single-process local demonstration, not a platform adapter or distributed lock.

## Local executable reuse check

Use [the local reuse inspector](local-reuse.md) to check actual files against a separate, trusted historical baseline and current plan. Save the resulting new report with the project recovery records. This complements the JSON manifest validator: it reads local files and checks content identity, but does not contact providers, claim leases, schedule work, or authorize cleanup. If baseline provenance or current inputs cannot be established, report unknown/blocked and investigate rather than reconstructing a baseline from today's files.
