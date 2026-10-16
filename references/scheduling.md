# Scheduling and Recovery

## Inspect resources

Record observed_at, authentication state, running jobs and owners, CPU, RAM, free disk, each GPU and VRAM, quota_seen, and evidence location. Use null for unknown values. Reserve capacity for model caches and temporary files. If free quota is insufficient, defer affected GPU work; do not purchase or change accounts to bypass it.

Two GPUs may run separate independent inputs if a model fits each card and CPU/RAM/disk and provider concurrency limits permit. A second provider receives only unclaimed shards. Three 15 GiB cards are not a single 45 GiB device. Cloud storage is separate from runtime disk and may be paid even when compute is free.

## Record before submitting

For each task store task_id, revision, input_sha256, script_sha256, parameters, model_revision, shard_id, dependencies, owner, resource, status, lease_until, checkpoint, outputs, and submission_ref. Persist the record before dispatch. One dispatcher controls allocation, or use an actual atomic claim mechanism; a JSON file alone is not a lock.

Compute an equivalence key from canonical JSON containing input hash, script hash, parameters, model revision, and shard ID. A different task_id does not make equivalent work independent. Check active and already verified completed outputs before a new submission.

States: planned → claimed → submitted → running → validating → done. Exception states: failed, unknown, blocked, cancelled. A submission with no receipt is unknown, not failed. Record platform job references and shard output manifests.

## Recover without duplication

1. Reload the project record. Inspect the original provider job and output before resubmitting. Browser disconnection does not prove termination.
2. An expired lease or missing worker triggers reconciliation, not immediate reassignment. Confirm the old job ended or never submitted, and identify completed shards. If uncertain, retain unknown and hold that shard.
3. Match recovered results to input, script, model, parameter and output hashes. Reuse only matching validated shards; quarantine mismatches. Do not combine changed narration with stale audio or captions.
4. Checkpoint the last verified output and next action after expensive operations. Transfer through authorized private storage only.
5. Reproduce a fix on a small sample before retrying a batch. Repeated identical failures require diagnosis; denied permission, unexpected cost, or unresolved previous-job state stops the affected action.

Estimate time from measured unit duration × remaining units / effective parallelism, plus transfer, assembly, and validation. State queue/quota uncertainty. Two cards do not justify an automatic twofold speed claim.
