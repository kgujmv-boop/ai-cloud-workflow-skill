#!/usr/bin/env python3
"""Conservative, local-CPU-only reuse inspection against a retained baseline.

This program reads files and creates exactly one NEW report. It never runs tasks,
modifies artifacts, obtains leases, deletes files, or accesses the network.

Exit codes: 0 = every task eligible; 1 = blocked/unknown tasks; 2 = invalid input,
operational error, or report creation failure. Eligibility is byte/snapshot
consistency, not proof of correct computation, historical provenance, or authority.
"""
from __future__ import annotations

import argparse
import datetime as dt
import errno
import hashlib
import json
import math
import os
import re
import stat
import sys
from typing import Any

VERSION = "1.0.0"
REPORT_SCHEMA = "local-reuse-inspection-v1"
IDENTITY_SCHEMA = "task-snapshot-v1"
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_TASKS = 10000
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
REQUIRED_TASK_KEYS = {
    "task_id", "inputs", "code", "parameters", "model_revision", "shard_id",
    "dependencies", "outputs",
}
LIMITATIONS = [
    "The baseline digest checks retained bytes only; it does not authenticate their origin.",
    "Trust acknowledgment assumes a separately retained historical baseline captured after independently verified successful execution, not a baseline reconstructed from present artifacts.",
    "Matching bytes and declared metadata do not prove computation correctness or that undeclared inputs, environment, or dependencies are unchanged.",
    "File descriptors, no-follow traversal, and metadata checks reduce races but do not provide an atomic or adversarial-filesystem-proof snapshot.",
    "Eligibility does not grant execution, deletion, upload, publishing, access, permission, or lease ownership.",
    "External model revisions are compared as declared strings; no remote model or service is contacted or authenticated.",
]


class InspectionError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def reason(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **details}


def diagnostic(message: str, *, error: bool = False) -> None:
    # Valid JSON can contain unpaired surrogate escapes. Never let diagnostic
    # encoding turn an otherwise handled failure into an uncaught traceback.
    stream = sys.stderr if error else sys.stdout
    print(message.encode("ascii", "backslashreplace").decode("ascii"), file=stream)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def absolute_path(value: str) -> str:
    if (not isinstance(value, str) or not value or
            any(ord(char) < 32 or ord(char) == 127 or 0xD800 <= ord(char) <= 0xDFFF for char in value)):
        raise InspectionError("invalid_path", "CLI paths must be nonempty and contain no control characters or surrogate code points.")
    full = value if value.startswith("/") else os.path.join(os.getcwd(), value)
    parts = full.split("/")
    if ".." in parts:
        raise InspectionError("invalid_path", "Parent traversal ('..') is forbidden in CLI paths.")
    return "/" + "/".join(part for part in parts if part not in ("", "."))


def relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise InspectionError("invalid_path", f"{label} must be a nonempty relative POSIX path.")
    if (value.startswith("/") or "\\" in value or ":" in value or
            any(ord(char) < 32 or ord(char) == 127 or 0xD800 <= ord(char) <= 0xDFFF for char in value) or
            any(part in ("", ".", "..") for part in value.split("/"))):
        raise InspectionError("invalid_path", f"{label} must be a normalized relative POSIX path without traversal, backslashes, colons, or control characters.")
    return value


def nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise InspectionError("invalid_schema", f"{label} must be a nonempty string without NUL bytes.")
    return value


def exact_keys(value: Any, keys: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        raise InspectionError("invalid_schema", f"{label} must have exactly these fields: {', '.join(sorted(keys))}.")


def no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InspectionError("duplicate_json_key", f"Duplicate JSON key: {key!r}.")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise InspectionError("nonfinite_json", f"Nonfinite JSON number is forbidden: {value}.")


def validate_finite(value: Any) -> None:
    # Iterative walk avoids adding a recursion failure after successful parsing.
    queue = [value]
    while queue:
        item = queue.pop()
        if isinstance(item, float) and not math.isfinite(item):
            raise InspectionError("nonfinite_json", "All JSON numbers must be finite.")
        if isinstance(item, dict):
            queue.extend(item.values())
        elif isinstance(item, list):
            queue.extend(item)


def parse_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicate_keys,
                           parse_constant=reject_constant)
        validate_finite(value)
        return value
    except InspectionError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise InspectionError("invalid_json", f"{label} is not supported strict UTF-8 JSON: {exc}") from None


def validate_manifest(value: Any, baseline: bool) -> dict[str, Any]:
    label = "baseline" if baseline else "current"
    exact_keys(value, {"project_id", "tasks"}, label)
    nonempty_string(value["project_id"], f"{label}.project_id")
    tasks = value["tasks"]
    if not isinstance(tasks, list) or not (1 <= len(tasks) <= MAX_TASKS):
        raise InspectionError("invalid_schema", f"{label}.tasks must contain 1 through {MAX_TASKS} tasks.")
    task_ids: set[str] = set()
    output_owners: dict[str, str] = {}
    for index, task in enumerate(tasks):
        where = f"{label}.tasks[{index}]"
        exact_keys(task, REQUIRED_TASK_KEYS, where)
        task_id = nonempty_string(task["task_id"], f"{where}.task_id")
        if task_id in task_ids:
            raise InspectionError("duplicate_task", f"Duplicate task_id in {label}: {task_id!r}.")
        task_ids.add(task_id)
        nonempty_string(task["model_revision"], f"{where}.model_revision")
        nonempty_string(task["shard_id"], f"{where}.shard_id")
        if not isinstance(task["parameters"], dict):
            raise InspectionError("invalid_schema", f"{where}.parameters must be an object.")
        dependencies = task["dependencies"]
        if not isinstance(dependencies, list):
            raise InspectionError("invalid_schema", f"{where}.dependencies must be an array of task IDs.")
        for dependency in dependencies:
            nonempty_string(dependency, f"{where}.dependencies entry")
        if len(set(dependencies)) != len(dependencies):
            raise InspectionError("duplicate_dependency", f"{where}.dependencies contains duplicate IDs.")
        role_paths: dict[str, set[str]] = {}
        for role in ("inputs", "code", "outputs"):
            entries = task[role]
            if not isinstance(entries, list) or (role == "outputs" and not entries):
                raise InspectionError("invalid_schema", f"{where}.{role} must be an array; outputs cannot be empty.")
            seen: set[str] = set()
            for file_index, entry in enumerate(entries):
                file_label = f"{where}.{role}[{file_index}]"
                if baseline:
                    exact_keys(entry, {"path", "sha256"}, file_label)
                    path = relative_path(entry["path"], file_label + ".path")
                    if not isinstance(entry["sha256"], str) or not SHA256_RE.fullmatch(entry["sha256"]):
                        raise InspectionError("invalid_schema", f"{file_label}.sha256 must be exactly 64 hexadecimal characters.")
                    entry["sha256"] = entry["sha256"].lower()
                else:
                    path = relative_path(entry, file_label)
                if path in seen:
                    raise InspectionError("duplicate_path", f"Duplicate path in {where}.{role}: {path!r}.")
                seen.add(path)
                if role == "outputs":
                    if path in output_owners:
                        raise InspectionError("duplicate_output_owner", f"{label} output {path!r} is owned by more than one task.")
                    output_owners[path] = task_id
            role_paths[role] = seen
        if role_paths["outputs"] & (role_paths["inputs"] | role_paths["code"]):
            raise InspectionError("self_overlapping_output", f"{where} declares an output as its own input or code.")
    task_map = {task["task_id"]: task for task in tasks}
    for task in tasks:
        for dependency in task["dependencies"]:
            if dependency not in task_map:
                raise InspectionError("unknown_dependency", f"{label} task {task['task_id']!r} has unknown dependency {dependency!r}.")
    # Kahn's algorithm: dependencies first, with no Python recursion depth limit.
    indegree = {task_id: len(task["dependencies"]) for task_id, task in task_map.items()}
    dependents = {task_id: [] for task_id in task_map}
    for task_id, task in task_map.items():
        for dependency in task["dependencies"]:
            dependents[dependency].append(task_id)
    ready = sorted(task_id for task_id, count in indegree.items() if count == 0)
    order: list[str] = []
    while ready:
        task_id = ready.pop()
        order.append(task_id)
        for child in dependents[task_id]:
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
    if len(order) != len(tasks):
        raise InspectionError("dependency_cycle", f"{label} dependency graph contains a cycle.")
    return {"project_id": value["project_id"], "tasks": task_map, "order": order}


def os_error(exc: OSError, label: str) -> InspectionError:
    if exc.errno == errno.ENOENT:
        code = "missing_file"
    elif exc.errno in (errno.ELOOP, errno.ENOTDIR):
        code = "unsafe_path"
    elif exc.errno in (errno.EACCES, errno.EPERM):
        code = "unreadable_file"
    else:
        code = "file_error"
    return InspectionError(code, f"{label}: {exc.strerror or type(exc).__name__}.")


def directory_flags() -> int:
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def open_absolute_directory(path: str) -> int:
    fd = os.open("/", directory_flags())
    try:
        for component in path.split("/"):
            if not component:
                continue
            next_fd = os.open(component, directory_flags(), dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except OSError as exc:
        os.close(fd)
        raise os_error(exc, f"Directory {path!r}") from None


def open_relative_file(root_fd: int, path: str) -> tuple[int, int, str]:
    parent_fd = os.dup(root_fd)
    parts = path.split("/")
    try:
        for component in parts[:-1]:
            next_fd = os.open(component, directory_flags(), dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                     dir_fd=parent_fd)
        return fd, parent_fd, parts[-1]
    except OSError as exc:
        os.close(parent_fd)
        raise os_error(exc, f"File {path!r}") from None


def stat_signature(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_nlink)


def inspect_file(root_fd: int, path: str, capture: bool = False) -> dict[str, Any]:
    fd, parent_fd, filename = open_relative_file(root_fd, path)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise InspectionError("nonregular_file", f"File {path!r} is not a regular file.")
        if capture and before.st_size > MAX_MANIFEST_BYTES:
            raise InspectionError("manifest_too_large", f"Manifest exceeds {MAX_MANIFEST_BYTES} bytes.")
        digest = hashlib.sha256()
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if capture and size > MAX_MANIFEST_BYTES:
                raise InspectionError("manifest_too_large", f"Manifest exceeds {MAX_MANIFEST_BYTES} bytes.")
            digest.update(chunk)
            if capture:
                chunks.append(chunk)
        after = os.fstat(fd)
        named = os.stat(filename, dir_fd=parent_fd, follow_symlinks=False)
        signature = stat_signature(before)
        if signature != stat_signature(after) or signature != stat_signature(named) or size != before.st_size:
            raise InspectionError("file_changed", f"File {path!r} changed while it was being hashed.")
        result = {"path": path, "sha256": digest.hexdigest(), "size_bytes": size,
                  "_signature": signature}
        if capture:
            result["_raw"] = b"".join(chunks)
        return result
    except OSError as exc:
        raise os_error(exc, f"File {path!r}") from None
    finally:
        os.close(fd)
        os.close(parent_fd)


def verify_unchanged(root_fd: int, observation: dict[str, Any]) -> None:
    fd, parent_fd, filename = open_relative_file(root_fd, observation["path"])
    try:
        opened = os.fstat(fd)
        named = os.stat(filename, dir_fd=parent_fd, follow_symlinks=False)
        if (stat_signature(opened) != observation["_signature"] or
                stat_signature(named) != observation["_signature"]):
            raise InspectionError("file_changed", f"File {observation['path']!r} changed after hashing.")
    except OSError as exc:
        raise os_error(exc, f"File {observation['path']!r}") from None
    finally:
        os.close(fd)
        os.close(parent_fd)


def read_manifest(path: str) -> dict[str, Any]:
    parent, filename = os.path.split(path)
    fd = open_absolute_directory(parent)
    try:
        result = inspect_file(fd, filename, capture=True)
        result["_absolute"] = path
        return result
    finally:
        os.close(fd)


def verify_manifest_unchanged(observation: dict[str, Any]) -> None:
    parent, _ = os.path.split(observation["_absolute"])
    fd = open_absolute_directory(parent)
    try:
        verify_unchanged(fd, observation)
    finally:
        os.close(fd)


def normalized_identity(project_id: str, task: dict[str, Any]) -> dict[str, Any]:
    return {
        "identity_schema": IDENTITY_SCHEMA,
        "project_id": project_id,
        "task_id": task["task_id"],
        "inputs": sorted(task["inputs"], key=lambda entry: entry["path"]),
        "code": sorted(task["code"], key=lambda entry: entry["path"]),
        "parameters": task["parameters"],
        "model_revision": task["model_revision"],
        "shard_id": task["shard_id"],
        "dependencies": sorted(task["dependencies"]),
        "outputs": sorted(task["outputs"], key=lambda entry: entry["path"]),
    }


def public_observation(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if not key.startswith("_")}


def evaluate(baseline: dict[str, Any], current: dict[str, Any], observations: dict[str, dict[str, Any]],
             trusted: bool, trust_reasons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for task_id in sorted(set(baseline["tasks"]) | set(current["tasks"])):
        old = baseline["tasks"].get(task_id)
        new = current["tasks"].get(task_id)
        record = {"task_id": task_id, "status": "eligible_for_reuse", "reasons": [],
                  "expected_identity_sha256": None, "computed_identity_sha256": None,
                  "current_files": {"inputs": [], "code": [], "outputs": []},
                  "dependencies": sorted(new["dependencies"] if new else old["dependencies"])}
        reasons = record["reasons"]
        if old:
            record["expected_identity_sha256"] = fingerprint(normalized_identity(baseline["project_id"], old))
        if new:
            actual = {**new}
            all_readable = True
            for role in ("inputs", "code", "outputs"):
                record["current_files"][role] = [public_observation(observations[path]) for path in sorted(new[role])]
                actual[role] = []
                for path in new[role]:
                    observation = observations[path]
                    if "error" in observation:
                        all_readable = False
                        reasons.append(reason(observation["error"]["code"], observation["error"]["message"], role=role, path=path))
                    else:
                        actual[role].append({"path": path, "sha256": observation["sha256"]})
            if all_readable:
                record["computed_identity_sha256"] = fingerprint(normalized_identity(current["project_id"], actual))
        if old is None:
            reasons.append(reason("new_task", "Task has no retained baseline entry."))
        elif new is None:
            reasons.append(reason("missing_task", "Retained baseline task is absent from the current task manifest."))
        elif trusted:
            if baseline["project_id"] != current["project_id"]:
                reasons.append(reason("project_mismatch", "Current project_id differs from the retained baseline."))
            for field in ("parameters", "model_revision", "shard_id"):
                if canonical(old[field]) != canonical(new[field]):
                    reasons.append(reason(field + "_mismatch", f"Current {field} differs from the retained baseline."))
            if set(old["dependencies"]) != set(new["dependencies"]):
                reasons.append(reason("dependencies_mismatch", "Current dependency set differs from the retained baseline."))
            for role in ("inputs", "code", "outputs"):
                expected = {entry["path"]: entry["sha256"] for entry in old[role]}
                if set(expected) != set(new[role]):
                    reasons.append(reason(role + "_paths_mismatch", f"Current {role} path set differs from the retained baseline.",
                                          missing_paths=sorted(set(expected) - set(new[role])),
                                          additional_paths=sorted(set(new[role]) - set(expected))))
                for path in sorted(set(expected) & set(new[role])):
                    observed = observations[path]
                    if "sha256" in observed and observed["sha256"] != expected[path]:
                        reasons.append(reason(role + "_hash_mismatch", f"Current {role} file bytes differ from the retained baseline.", path=path,
                                              expected_sha256=expected[path], actual_sha256=observed["sha256"]))
        if old is None or new is None:
            record["status"] = "blocked"
        elif not trusted:
            # A known digest integrity failure blocks reuse. Missing provenance
            # acknowledgment alone leaves the reference trust unknown.
            record["status"] = ("blocked" if any(item["code"] == "baseline_digest_mismatch"
                                                   for item in trust_reasons) else "unknown")
            reasons.extend(trust_reasons)
        elif reasons:
            record["status"] = "blocked"
        results[task_id] = record
    # Every current dependency must be eligible, transitively. Current DAG order
    # ensures the direct dependency's final decision already includes its ancestors.
    for task_id in current["order"]:
        record = results[task_id]
        for dependency in current["tasks"][task_id]["dependencies"]:
            dependency_status = results[dependency]["status"]
            if dependency_status != "eligible_for_reuse":
                record["reasons"].append(reason("dependency_not_eligible", "A transitive dependency is not eligible for reuse.",
                                                dependency_task_id=dependency, dependency_status=dependency_status))
                if trusted or dependency_status == "blocked":
                    record["status"] = "blocked"
                elif record["status"] == "eligible_for_reuse":
                    record["status"] = "unknown"
    return [results[task_id] for task_id in sorted(results)]


def write_report(path: str, report: dict[str, Any]) -> None:
    parent, filename = os.path.split(path)
    if not filename:
        raise InspectionError("invalid_report_path", "Report path must name a new file.")
    parent_fd = open_absolute_directory(parent)
    fd: int | None = None
    try:
        # Encode before opening; serialization errors must not create an empty report.
        payload = (json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
        fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=parent_fd)
        offset = 0
        while offset < len(payload):
            written = os.write(fd, payload[offset:])
            if written <= 0:
                raise InspectionError("report_write_failed", "Report write made no progress; a partial new report may remain.")
            offset += written
        os.fsync(fd)
        os.fsync(parent_fd)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            raise InspectionError("report_exists", "Report path already exists; it was not overwritten.") from None
        raise InspectionError("report_write_failed", f"Unable to create/write report: {exc.strerror}; a partial new report may remain.") from None
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent_fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", required=True, help="Explicit workspace root; all manifest artifact paths are relative to it.")
    parser.add_argument("--baseline", required=True, help="Separately retained historical expected-state JSON file.")
    parser.add_argument("--current", required=True, help="Current task-declaration JSON file; artifacts are hashed by this inspector.")
    parser.add_argument("--baseline-sha256", required=True, help="Expected SHA256 supplied independently of the baseline being inspected.")
    parser.add_argument("--trust-baseline", action="store_true", help="Acknowledge a trustworthy historical baseline after independently verified successful execution; never reconstructed from current artifacts.")
    parser.add_argument("--report", required=True, help="NEW report file outside the workspace root; existing files are never overwritten.")
    args = parser.parse_args(argv)
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA, "inspector_version": VERSION,
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "identity_schema": IDENTITY_SCHEMA, "overall_status": "unknown", "exit_code": 2,
        "workspace_root": None, "baseline": {"trust_acknowledged": args.trust_baseline,
            "supplied_sha256": args.baseline_sha256, "actual_sha256": None,
            "digest_matches": False, "trusted_for_comparison": False},
        "current": {"actual_sha256": None}, "tasks": [], "errors": [],
        "limitations": LIMITATIONS,
    }
    report_path: str | None = None
    root_fd: int | None = None
    try:
        if os.name != "posix" or not all(hasattr(os, name) for name in ("O_NOFOLLOW", "O_DIRECTORY", "O_CLOEXEC")):
            raise InspectionError("unsupported_platform", "This inspector requires POSIX no-follow directory-relative file operations (tested on Linux).")
        root = absolute_path(args.root)
        report["workspace_root"] = root
        candidate_report = absolute_path(args.report)
        if os.path.commonpath((root, candidate_report)) == root:
            raise InspectionError("unsafe_report_path", "Report must be outside the workspace root to avoid modifying inspected artifacts.")
        report_path = candidate_report
        baseline_path = absolute_path(args.baseline)
        current_path = absolute_path(args.current)
        report["baseline"]["path"] = baseline_path
        report["current"]["path"] = current_path
        if baseline_path == current_path:
            raise InspectionError("same_manifest", "Baseline and current must be separate files, not the same pathname.")
        if not SHA256_RE.fullmatch(args.baseline_sha256):
            raise InspectionError("invalid_baseline_digest", "--baseline-sha256 must contain exactly 64 hexadecimal characters.")
        report["baseline"]["supplied_sha256"] = args.baseline_sha256.lower()
        root_fd = open_absolute_directory(root)
        expected_observation = read_manifest(baseline_path)
        report["baseline"]["actual_sha256"] = expected_observation["sha256"]
        report["baseline"]["digest_matches"] = expected_observation["sha256"] == args.baseline_sha256.lower()
        current_observation = read_manifest(current_path)
        report["current"]["actual_sha256"] = current_observation["sha256"]
        if expected_observation["_signature"][:2] == current_observation["_signature"][:2]:
            raise InspectionError("same_manifest", "Baseline and current must not be hard links to the same file.")
        baseline = validate_manifest(parse_json(expected_observation["_raw"], "baseline"), baseline=True)
        current = validate_manifest(parse_json(current_observation["_raw"], "current"), baseline=False)
        report["baseline"]["project_id"] = baseline["project_id"]
        report["current"]["project_id"] = current["project_id"]
        trust_reasons = []
        if not args.trust_baseline:
            trust_reasons.append(reason("baseline_not_acknowledged", "Historical baseline trust was not explicitly acknowledged."))
        if not report["baseline"]["digest_matches"]:
            trust_reasons.append(reason("baseline_digest_mismatch", "Baseline bytes do not match the independently supplied digest."))
        trusted = not trust_reasons
        paths = sorted({path for task in current["tasks"].values() for role in ("inputs", "code", "outputs") for path in task[role]})
        observations: dict[str, dict[str, Any]] = {}
        for path in paths:
            try:
                observations[path] = inspect_file(root_fd, path)
            except InspectionError as exc:
                observations[path] = {"path": path, "error": reason(exc.code, exc.message)}
        # Best-effort final metadata validation catches changes after individual reads.
        for path, observation in observations.items():
            if "error" not in observation:
                try:
                    verify_unchanged(root_fd, observation)
                except InspectionError as exc:
                    observations[path] = {"path": path, "error": reason(exc.code, exc.message)}
        verify_manifest_unchanged(expected_observation)
        verify_manifest_unchanged(current_observation)
        report["baseline"]["trusted_for_comparison"] = trusted
        report["tasks"] = evaluate(baseline, current, observations, trusted, trust_reasons)
        statuses = {task["status"] for task in report["tasks"]}
        report["overall_status"] = "blocked" if "blocked" in statuses else "unknown" if "unknown" in statuses else "eligible_for_reuse"
        report["exit_code"] = 0 if report["overall_status"] == "eligible_for_reuse" else 1
    except InspectionError as exc:
        report["errors"].append(reason(exc.code, exc.message))
    except (OSError, ValueError, TypeError, OverflowError, RecursionError) as exc:
        report["errors"].append(reason("inspection_failed", f"Inspection could not complete: {type(exc).__name__}: {exc}"))
    finally:
        if root_fd is not None:
            os.close(root_fd)
    if report_path is None:
        diagnostic("Inspection failed: " + report["errors"][0]["message"], error=True)
        return 2
    try:
        write_report(report_path, report)
    except (InspectionError, OSError, ValueError, RecursionError) as exc:
        message = exc.message if isinstance(exc, InspectionError) else str(exc)
        diagnostic("Report not completed: " + message, error=True)
        return 2
    counts = {status: sum(task["status"] == status for task in report["tasks"])
              for status in ("eligible_for_reuse", "blocked", "unknown")}
    diagnostic(f"{report['overall_status']}: {counts['eligible_for_reuse']} eligible, {counts['blocked']} blocked, {counts['unknown']} unknown; report: {report_path}")
    if report["errors"]:
        diagnostic("Inspection error: " + report["errors"][0]["message"], error=True)
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
