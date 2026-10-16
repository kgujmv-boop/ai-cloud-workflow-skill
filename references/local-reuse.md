# Local Reuse Inspection

Use this check before reusing local completed work after an interruption or a change request. It compares a historical completion baseline with the current requested plan and hashes the actual files. It does not run tasks, change files, contact providers, claim leases, or grant permissions.

## Keep expected and current separate

The **baseline** is a snapshot saved after a successful execution and separate output-quality verification. Retain its SHA-256 in a trusted earlier completion receipt, separately from the snapshot. The **current plan** describes today's requested inputs, code, parameters, model revision, shard, dependencies, and output locations. Prepare it from the current request, not by blindly copying the old plan.

Do not create a baseline from today's files merely to make the check pass. A supplied digest checks consistency with that chosen reference, not who created it: if an attacker or mistaken process changes both the baseline and its reference digest, this tool cannot establish authenticity. Explicit trust acknowledgment records the caller's established provenance assumption; it is not a substitute for establishing it.

Record all relevant files and dependencies. Omitting a true input can hide a change. Pin model revisions and include runtime/package/configuration changes in the recorded code files or parameters when they affect results. A label such as “latest” does not establish a fixed model version. Use the explicit string `none` when no model is involved.

## Records

Both JSON files contain `project_id` and a nonempty `tasks` list. Every task contains:

- `task_id`: stable nonempty identifier.
- `inputs`, `code`, `outputs`: baseline entries are `{ "path": "relative/file", "sha256": "64 hexadecimal characters" }`; current entries are relative path strings. Outputs must be nonempty. Explicit empty inputs/code arrays mean there are deliberately no files in that role, not that they were forgotten.
- `parameters`: a finite JSON object.
- `model_revision`, `shard_id`: explicit nonempty strings.
- `dependencies`: task IDs in the same record, forming an acyclic graph.

See the [small fixture](../examples/local-reuse/README.md). This inspection format is separate from the dispatch task manifest; it does not alter that manifest's schema or scheduling state.

## Decision

For each task, compare input and code paths and their freshly computed file hashes, parameters, model revision, shard, dependency IDs, and output paths/hashes. Dependency eligibility propagates through the complete graph. An unchanged output cannot be reused if an upstream task no longer matches its trusted baseline. Missing or additional tasks and incomplete records require investigation.

Only a complete match against an acknowledged trusted baseline permits `eligible_for_reuse`. Missing, changed, unsafe, or incompatible evidence blocks reuse; lack of established trust leaves it unknown. Neither result initiates recomputation. Save the new report with the project's recovery records and use its reasons to plan only the affected work.

Reports include observation time, tool version, input-record digests, computed identities/hashes, and per-task decisions. Do not hand-edit a report to make work eligible. Re-run to a new report path after resolving the cause.

## Boundaries

Task file paths must stay beneath the explicit workspace root. Absolute paths, parent traversal, symlinks and nonregular files are rejected. Baseline and current records are explicitly selected files; the new report lives outside the inspected workspace and is created exclusively, never overwritten. The tool does not quarantine, delete, or repair any input.

This is a local observation, not an atomic filesystem snapshot or a distributed lock. Stop relevant writers while inspecting. Checks around file reads reduce obvious concurrent-change errors but cannot prove consistency against a malicious process rewriting files during inspection. Revalidate before later use if files may have changed. An eligible report says nothing about a provider's running jobs, access authorization, scientific correctness, or a backup at another location.

The inspector uses Python's standard library and requires POSIX no-follow filesystem support. Linux is tested; macOS and other platforms are not validated here. Unsupported filesystem/platform capabilities must fail closed rather than silently weaken checks. No cloud credentials or GPU are required.

Run the command in [the example](../examples/local-reuse/README.md), using actual project paths and a separately retained expected baseline digest. Exit 0 means all tasks eligible, 1 means blocked/unknown tasks, and 2 means invalid input or operational/report failure. An explicit digest mismatch blocks reuse; an unacknowledged baseline leaves matching work unknown.
