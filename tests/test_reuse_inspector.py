"""Black-box, offline regression tests for the read-only reuse inspector.

Run from the package directory with:
    python -m unittest discover -s tests -v

Every invocation uses a fresh temporary project, a frozen baseline containing
real SHA-256 digests, and a separate current specification. No network, GPU,
third-party libraries, or user project files are involved.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "inspect_reuse.py"
ELIGIBLE = "eligible_for_reuse"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReuseInspectorTests(unittest.TestCase):
    """Exercise the public CLI rather than internal implementation helpers."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="reuse-inspector-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "project"
        self.root.mkdir()
        self.baseline_path = self.base / "baseline.json"
        self.current_path = self.base / "current.json"
        self.report_path = self.base / "report.json"
        self.current = {"project_id": "test-project", "tasks": []}
        for name, deps in (("A", []), ("B", ["A"]), ("C", ["B"])):
            self.current["tasks"].append(self.make_task(name, deps))
        self.baseline = self.freeze(self.current)
        self.save_specs()

    def make_task(self, name: str, dependencies: list[str]) -> dict:
        paths = {
            "inputs": f"inputs/{name}.dat",
            "code": f"code/{name}.py",
            "outputs": f"outputs/{name}.txt",
        }
        for role, relative in paths.items():
            target = self.root / relative
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(f"original {role} for {name}\n".encode())
        return {
            "task_id": name,
            "inputs": [paths["inputs"]],
            "code": [paths["code"]],
            "parameters": {"seed": 7, "nested": {"scale": 1, "mode": "test"}},
            "model_revision": "example-model@revision-001",
            "shard_id": "part-000",
            "dependencies": dependencies,
            "outputs": [paths["outputs"]],
        }

    def freeze(self, current: dict) -> dict:
        baseline = copy.deepcopy(current)
        for task in baseline["tasks"]:
            for role in ("inputs", "code", "outputs"):
                task[role] = [
                    {"path": relative, "sha256": digest(self.root / relative)}
                    for relative in task[role]
                ]
        return baseline

    def save_specs(self) -> None:
        self.baseline_path.write_text(json.dumps(self.baseline), encoding="utf-8")
        self.save_current()
        self.baseline_sha = digest(self.baseline_path)

    def save_current(self) -> None:
        self.current_path.write_text(json.dumps(self.current), encoding="utf-8")

    def task(self, name: str = "A", *, baseline: bool = False) -> dict:
        manifest = self.baseline if baseline else self.current
        return next(t for t in manifest["tasks"] if t["task_id"] == name)

    def invoke(
        self,
        *,
        trust: bool = True,
        pin: bool = True,
        sha: str | None = None,
        root: Path | None = None,
        baseline: Path | None = None,
        current: Path | None = None,
        report: Path | None = None,
    ) -> tuple[subprocess.CompletedProcess, dict | None]:
        report_path = report or self.report_path
        argv = [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(root or self.root),
            "--baseline",
            str(baseline or self.baseline_path),
            "--current",
            str(current or self.current_path),
            "--report",
            str(report_path),
        ]
        if pin:
            argv += ["--baseline-sha256", sha if sha is not None else self.baseline_sha]
        if trust:
            argv.append("--trust-baseline")
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        value = None
        if report_path.is_file():
            try:
                value = json.loads(report_path.read_text(encoding="utf-8"))
            except (UnicodeError, json.JSONDecodeError):
                pass
        return proc, value

    def task_reports(self, report: dict) -> dict[str, dict]:
        self.assertIsInstance(report, dict)
        self.assertIsInstance(report.get("tasks"), list)
        rows = {row["task_id"]: row for row in report["tasks"]}
        self.assertEqual(len(rows), len(report["tasks"]), "duplicate task report IDs")
        return rows

    def assert_all_eligible(self, proc: subprocess.CompletedProcess, report: dict) -> None:
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertEqual(report["overall_status"], ELIGIBLE)
        rows = self.task_reports(report)
        self.assertEqual(set(rows), {task["task_id"] for task in self.current["tasks"]})
        for task_id, row in rows.items():
            self.assertEqual(row["status"], ELIGIBLE, (task_id, row))

    def assert_not_eligible(
        self, proc: subprocess.CompletedProcess, report: dict | None
    ) -> None:
        self.assertIn(proc.returncode, (1, 2), proc.stderr + proc.stdout)
        if report is not None:
            self.assertNotEqual(report.get("overall_status"), ELIGIBLE)

    def assert_task_blocked(self, report: dict, task_id: str = "A") -> None:
        row = self.task_reports(report)[task_id]
        self.assertEqual(row["status"], "blocked", row)
        self.assertTrue(row.get("reasons"), row)

    def assert_invalid(self, proc: subprocess.CompletedProcess, report: dict | None) -> None:
        self.assertEqual(proc.returncode, 2, proc.stderr + proc.stdout)
        if report is not None:
            self.assertNotEqual(report.get("overall_status"), ELIGIBLE)
            for row in report.get("tasks", []):
                self.assertNotEqual(row["status"], ELIGIBLE)

    def change_file(self, role: str, name: str = "A") -> None:
        target = self.root / self.task(name)[role][0]
        target.write_bytes(b"changed bytes with unchanged manifest path\n")

    def test_unchanged_trusted_snapshot_is_eligible(self) -> None:
        self.assert_all_eligible(*self.invoke())

    def test_input_bytes_change_blocks_reuse(self) -> None:
        self.change_file("inputs")
        proc, report = self.invoke()
        self.assert_not_eligible(proc, report)
        self.assert_task_blocked(report)

    def test_code_bytes_change_blocks_reuse(self) -> None:
        self.change_file("code")
        proc, report = self.invoke()
        self.assert_not_eligible(proc, report)
        self.assert_task_blocked(report)

    def test_parameter_change_blocks_reuse(self) -> None:
        self.task()["parameters"]["seed"] = 8
        self.save_current()
        proc, report = self.invoke()
        self.assert_not_eligible(proc, report)
        self.assert_task_blocked(report)

    def test_nested_parameter_change_blocks_reuse(self) -> None:
        self.task()["parameters"]["nested"]["mode"] = "production"
        self.save_current()
        proc, report = self.invoke()
        self.assert_not_eligible(proc, report)
        self.assert_task_blocked(report)

    def test_parameter_object_key_order_is_not_a_change(self) -> None:
        self.task()["parameters"] = {"nested": {"mode": "test", "scale": 1}, "seed": 7}
        self.save_current()
        self.assert_all_eligible(*self.invoke())

    def test_model_revision_change_blocks_reuse(self) -> None:
        self.task()["model_revision"] = "example-model@revision-002"
        self.save_current()
        proc, report = self.invoke()
        self.assert_not_eligible(proc, report)
        self.assert_task_blocked(report)

    def test_shard_id_change_blocks_reuse(self) -> None:
        self.task()["shard_id"] = "part-001"
        self.save_current()
        proc, report = self.invoke()
        self.assert_not_eligible(proc, report)
        self.assert_task_blocked(report)

    def test_dependency_change_blocks_reuse(self) -> None:
        self.task("C")["dependencies"] = ["A"]
        self.save_current()
        proc, report = self.invoke()
        self.assert_not_eligible(proc, report)
        self.assert_task_blocked(report, "C")

    def test_output_tamper_blocks_reuse(self) -> None:
        self.change_file("outputs")
        proc, report = self.invoke()
        self.assert_not_eligible(proc, report)
        self.assert_task_blocked(report)

    def test_missing_output_blocks_reuse(self) -> None:
        (self.root / self.task()["outputs"][0]).unlink()
        proc, report = self.invoke()
        self.assert_not_eligible(proc, report)
        self.assert_task_blocked(report)

    def test_transitive_dependency_change_blocks_entire_chain(self) -> None:
        self.change_file("inputs", "A")
        proc, report = self.invoke()
        self.assert_not_eligible(proc, report)
        for name in ("A", "B", "C"):
            self.assert_task_blocked(report, name)

    def test_middle_dependency_change_does_not_block_ancestor(self) -> None:
        self.change_file("inputs", "B")
        proc, report = self.invoke()
        self.assert_not_eligible(proc, report)
        self.assertEqual(self.task_reports(report)["A"]["status"], ELIGIBLE)
        for name in ("B", "C"):
            self.assert_task_blocked(report, name)

    def test_new_task_is_never_eligible_without_baseline(self) -> None:
        self.current["tasks"].append(self.make_task("D", []))
        self.save_current()
        proc, report = self.invoke()
        self.assert_not_eligible(proc, report)
        self.assertNotEqual(self.task_reports(report)["D"]["status"], ELIGIBLE)

    def test_removed_task_is_reported_and_not_eligible(self) -> None:
        self.current["tasks"] = [t for t in self.current["tasks"] if t["task_id"] != "C"]
        self.save_current()
        proc, report = self.invoke()
        self.assert_not_eligible(proc, report)
        self.assertNotEqual(self.task_reports(report)["C"]["status"], ELIGIBLE)

    def test_project_identity_mismatch_cannot_reuse(self) -> None:
        self.current["project_id"] = "different-project"
        self.save_current()
        proc, report = self.invoke()
        self.assert_not_eligible(proc, report)
        if report:
            for row in report.get("tasks", []):
                self.assertNotEqual(row["status"], ELIGIBLE)

    def test_untrusted_baseline_is_unknown(self) -> None:
        proc, report = self.invoke(trust=False)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertEqual(report["overall_status"], "unknown")
        for row in self.task_reports(report).values():
            self.assertEqual(row["status"], "unknown")

    def test_trust_flag_alone_is_insufficient(self) -> None:
        proc, report = self.invoke(pin=False)
        self.assert_not_eligible(proc, report)
        if report:
            for row in report.get("tasks", []):
                self.assertNotEqual(row["status"], ELIGIBLE)

    def test_neither_trust_flag_nor_pin_is_insufficient(self) -> None:
        self.assert_not_eligible(*self.invoke(trust=False, pin=False))

    def test_wrong_baseline_hash_blocks_reuse(self) -> None:
        proc, report = self.invoke(sha="0" * 64)
        self.assert_not_eligible(proc, report)
        if report:
            self.assertEqual(report["overall_status"], "blocked")
            for row in report.get("tasks", []):
                self.assertEqual(row["status"], "blocked")

    def test_baseline_byte_change_breaks_pinned_trust(self) -> None:
        with self.baseline_path.open("ab") as stream:
            stream.write(b"\n")
        self.assert_not_eligible(*self.invoke())

    def test_invalid_baseline_pin_is_rejected(self) -> None:
        self.assert_invalid(*self.invoke(sha="not-a-sha256"))

    def test_actual_identity_changes_instead_of_comparing_current_to_itself(self) -> None:
        proc, report = self.invoke()
        self.assert_all_eligible(proc, report)
        old_identity = self.task_reports(report)["A"]["computed_identity_sha256"]
        self.assertRegex(old_identity, r"^[0-9a-f]{64}$")
        self.change_file("inputs")
        proc, changed_report = self.invoke(report=self.base / "changed-report.json")
        self.assert_not_eligible(proc, changed_report)
        row = self.task_reports(changed_report)["A"]
        self.assertNotEqual(row["computed_identity_sha256"], old_identity)
        self.assert_task_blocked(changed_report)

    def test_current_schema_cannot_supply_forged_file_hashes(self) -> None:
        self.change_file("inputs")
        self.task()["inputs"] = copy.deepcopy(self.task(baseline=True)["inputs"])
        self.save_current()
        self.assert_invalid(*self.invoke())

    def test_input_path_change_blocks_even_with_equal_bytes(self) -> None:
        old = self.root / self.task()["inputs"][0]
        new = self.root / "inputs/renamed.dat"
        new.write_bytes(old.read_bytes())
        self.task()["inputs"] = ["inputs/renamed.dat"]
        self.save_current()
        proc, report = self.invoke()
        self.assert_not_eligible(proc, report)
        self.assert_task_blocked(report)

    def test_output_path_change_blocks_even_with_equal_bytes(self) -> None:
        old = self.root / self.task()["outputs"][0]
        new = self.root / "outputs/renamed.txt"
        new.write_bytes(old.read_bytes())
        self.task()["outputs"] = ["outputs/renamed.txt"]
        self.save_current()
        proc, report = self.invoke()
        self.assert_not_eligible(proc, report)
        self.assert_task_blocked(report)

    def test_absolute_artifact_paths_are_rejected(self) -> None:
        for role in ("inputs", "code", "outputs"):
            with self.subTest(role=role):
                original = self.task()[role]
                self.task()[role] = [str(self.root / original[0])]
                self.save_current()
                self.assert_invalid(*self.invoke(report=self.base / f"absolute-{role}.json"))
                self.task()[role] = original

    def test_parent_traversal_artifact_paths_are_rejected(self) -> None:
        for relative in ("../outside.txt", "inputs/../inputs/A.dat", "a/../../outside"):
            with self.subTest(path=relative):
                self.task()["inputs"] = [relative]
                self.save_current()
                self.assert_invalid(*self.invoke(report=self.base / f"traversal-{len(relative)}.json"))

    def test_baseline_artifact_path_traversal_is_rejected(self) -> None:
        self.task(baseline=True)["inputs"][0]["path"] = "../outside.txt"
        self.save_specs()
        self.assert_invalid(*self.invoke())

    def test_symlink_artifacts_are_never_eligible(self) -> None:
        for role in ("inputs", "code", "outputs"):
            with self.subTest(role=role):
                target = self.root / self.task()[role][0]
                contents = target.read_bytes()
                outside = self.base / f"outside-{role}"
                outside.write_bytes(contents)
                target.unlink()
                target.symlink_to(outside)
                proc, report = self.invoke(report=self.base / f"symlink-{role}.json")
                self.assert_not_eligible(proc, report)
                if report and report.get("tasks"):
                    self.assertNotEqual(self.task_reports(report)["A"]["status"], ELIGIBLE)
                target.unlink()
                target.write_bytes(contents)

    def test_symlink_ancestor_within_artifact_path_is_rejected(self) -> None:
        real = self.root / "inputs"
        moved = self.base / "external-inputs"
        real.rename(moved)
        real.symlink_to(moved, target_is_directory=True)
        self.assert_not_eligible(*self.invoke())

    def test_symlink_root_is_rejected(self) -> None:
        link = self.base / "root-link"
        link.symlink_to(self.root, target_is_directory=True)
        self.assert_invalid(*self.invoke(root=link))

    def test_symlink_in_root_ancestor_is_rejected(self) -> None:
        link = self.base / "parent-link"
        link.symlink_to(self.base, target_is_directory=True)
        self.assert_invalid(*self.invoke(root=link / "project"))

    def test_directory_instead_of_artifact_is_rejected(self) -> None:
        target = self.root / self.task()["inputs"][0]
        target.unlink()
        target.mkdir()
        self.assert_not_eligible(*self.invoke())

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO test requires POSIX")
    def test_fifo_artifact_is_rejected_without_hanging(self) -> None:
        target = self.root / self.task()["inputs"][0]
        target.unlink()
        os.mkfifo(target)
        self.assert_not_eligible(*self.invoke())

    def test_missing_input_is_not_eligible(self) -> None:
        (self.root / self.task()["inputs"][0]).unlink()
        self.assert_not_eligible(*self.invoke())

    def test_missing_code_is_not_eligible(self) -> None:
        (self.root / self.task()["code"][0]).unlink()
        self.assert_not_eligible(*self.invoke())

    def test_missing_root_is_rejected(self) -> None:
        self.assert_invalid(*self.invoke(root=self.base / "missing-root"))

    def test_missing_manifest_is_rejected(self) -> None:
        self.assert_invalid(*self.invoke(current=self.base / "missing.json"))

    def test_symlink_manifest_is_rejected(self) -> None:
        link = self.base / "current-link.json"
        link.symlink_to(self.current_path)
        self.assert_invalid(*self.invoke(current=link))

    def test_nonregular_manifest_is_rejected(self) -> None:
        self.assert_invalid(*self.invoke(current=self.root))

    def test_duplicate_json_keys_are_rejected(self) -> None:
        raw = self.current_path.read_text()
        self.current_path.write_text(raw.replace('"project_id":', '"project_id":"shadow", "project_id":', 1))
        self.assert_invalid(*self.invoke())

    def test_duplicate_nested_json_keys_are_rejected(self) -> None:
        raw = self.current_path.read_text()
        self.current_path.write_text(raw.replace('"seed": 7', '"seed": 8, "seed": 7', 1))
        self.assert_invalid(*self.invoke())

    def test_nonfinite_json_numbers_are_rejected(self) -> None:
        original = self.current_path.read_text()
        for index, token in enumerate(("NaN", "Infinity", "-Infinity", "1e9999")):
            with self.subTest(token=token):
                self.current_path.write_text(original.replace('"seed": 7', f'"seed": {token}', 1))
                self.assert_invalid(*self.invoke(report=self.base / f"nonfinite-{index}.json"))

    def test_malformed_json_is_rejected(self) -> None:
        self.current_path.write_text('{"tasks": [')
        self.assert_invalid(*self.invoke())

    def test_invalid_utf8_json_is_rejected(self) -> None:
        self.current_path.write_bytes(b'{"project_id":"\xff"}')
        self.assert_invalid(*self.invoke())

    def test_bad_top_level_type_is_rejected(self) -> None:
        self.current_path.write_text("[]")
        self.assert_invalid(*self.invoke())

    def test_bad_task_field_types_are_rejected(self) -> None:
        bad_values = {
            "task_id": 1,
            "inputs": "inputs/A.dat",
            "code": None,
            "parameters": [],
            "model_revision": False,
            "shard_id": {},
            "dependencies": "A",
            "outputs": 12,
        }
        original = copy.deepcopy(self.task())
        for index, (field, value) in enumerate(bad_values.items()):
            with self.subTest(field=field):
                self.current["tasks"][0] = copy.deepcopy(original)
                self.task()[field] = value
                self.save_current()
                self.assert_invalid(*self.invoke(report=self.base / f"bad-type-{index}.json"))

    def test_missing_required_fields_are_rejected(self) -> None:
        original = copy.deepcopy(self.task())
        for index, field in enumerate(original):
            with self.subTest(field=field):
                self.current["tasks"][0] = copy.deepcopy(original)
                del self.current["tasks"][0][field]
                self.save_current()
                self.assert_invalid(*self.invoke(report=self.base / f"missing-field-{index}.json"))

    def test_unknown_fields_are_rejected(self) -> None:
        self.task()["trust_me"] = True
        self.save_current()
        self.assert_invalid(*self.invoke())

    def test_bad_baseline_file_hash_is_rejected(self) -> None:
        self.task(baseline=True)["inputs"][0]["sha256"] = "broken-hash"
        self.save_specs()
        self.assert_invalid(*self.invoke())

    def test_duplicate_task_ids_are_rejected(self) -> None:
        self.current["tasks"].append(copy.deepcopy(self.task()))
        self.save_current()
        self.assert_invalid(*self.invoke())

    def test_duplicate_artifact_paths_are_rejected(self) -> None:
        self.task()["inputs"] *= 2
        self.save_current()
        self.assert_invalid(*self.invoke())

    def test_duplicate_dependency_ids_are_rejected(self) -> None:
        self.task("B")["dependencies"] = ["A", "A"]
        self.save_current()
        self.assert_invalid(*self.invoke())

    def test_unknown_dependency_id_is_rejected(self) -> None:
        self.task("B")["dependencies"] = ["NOT_PRESENT"]
        self.save_current()
        self.assert_invalid(*self.invoke())

    def test_dependency_cycle_is_rejected(self) -> None:
        self.task()["dependencies"] = ["C"]
        self.save_current()
        self.assert_invalid(*self.invoke())

    def test_self_dependency_is_rejected(self) -> None:
        self.task()["dependencies"] = ["A"]
        self.save_current()
        self.assert_invalid(*self.invoke())

    def test_baseline_dependency_cycle_is_rejected(self) -> None:
        self.task(baseline=True)["dependencies"] = ["C"]
        self.save_specs()
        self.assert_invalid(*self.invoke())

    def test_existing_report_is_not_modified(self) -> None:
        sentinel = b"existing report must survive unchanged\n"
        self.report_path.write_bytes(sentinel)
        proc, _ = self.invoke()
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertEqual(self.report_path.read_bytes(), sentinel)

    def test_report_cannot_overwrite_baseline_manifest(self) -> None:
        before = self.baseline_path.read_bytes()
        proc, _ = self.invoke(report=self.baseline_path)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertEqual(self.baseline_path.read_bytes(), before)

    def test_report_cannot_overwrite_current_manifest(self) -> None:
        before = self.current_path.read_bytes()
        proc, _ = self.invoke(report=self.current_path)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertEqual(self.current_path.read_bytes(), before)

    def test_report_cannot_overwrite_any_project_artifact(self) -> None:
        for role in ("inputs", "code", "outputs"):
            with self.subTest(role=role):
                target = self.root / self.task()[role][0]
                before = target.read_bytes()
                proc, _ = self.invoke(report=target)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertEqual(target.read_bytes(), before)

    def test_report_hardlink_aliases_do_not_modify_original_files(self) -> None:
        targets = [self.baseline_path, self.current_path]
        targets.extend(self.root / self.task()[role][0] for role in ("inputs", "code", "outputs"))
        for index, target in enumerate(targets):
            with self.subTest(target=target.name):
                before = target.read_bytes()
                alias = self.base / f"hardlink-report-{index}.json"
                os.link(target, alias)
                proc, _ = self.invoke(report=alias)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertEqual(target.read_bytes(), before)
                self.assertEqual(alias.read_bytes(), before)

    def test_new_report_inside_project_root_is_rejected(self) -> None:
        target = self.root / "new-report.json"
        proc, _ = self.invoke(report=target)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertFalse(target.exists())

    def test_symlink_report_does_not_modify_target(self) -> None:
        target = self.base / "protected.txt"
        target.write_bytes(b"protected")
        self.report_path.symlink_to(target)
        proc, _ = self.invoke()
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertTrue(self.report_path.is_symlink())
        self.assertEqual(target.read_bytes(), b"protected")

    def test_dangling_symlink_report_does_not_create_target(self) -> None:
        target = self.base / "absent-target.txt"
        self.report_path.symlink_to(target)
        proc, _ = self.invoke()
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertTrue(self.report_path.is_symlink())
        self.assertFalse(target.exists())

    def test_symlink_report_parent_is_rejected(self) -> None:
        real = self.base / "reports"
        real.mkdir()
        link = self.base / "reports-link"
        link.symlink_to(real, target_is_directory=True)
        proc, _ = self.invoke(report=link / "new.json")
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertEqual(list(real.iterdir()), [])

    def test_successful_inspection_does_not_modify_inputs_or_manifests(self) -> None:
        paths = [self.baseline_path, self.current_path] + sorted(self.root.rglob("*"))
        before = {p: (digest(p), p.stat().st_mtime_ns) for p in paths if p.is_file()}
        files_before = {p.relative_to(self.root) for p in self.root.rglob("*")}
        self.assert_all_eligible(*self.invoke())
        after = {p: (digest(p), p.stat().st_mtime_ns) for p in before}
        self.assertEqual(after, before)
        self.assertEqual({p.relative_to(self.root) for p in self.root.rglob("*")}, files_before)

    def test_blocked_inspection_does_not_modify_inputs_or_manifests(self) -> None:
        self.change_file("inputs")
        paths = [self.baseline_path, self.current_path] + sorted(self.root.rglob("*"))
        before = {p: digest(p) for p in paths if p.is_file()}
        self.assert_not_eligible(*self.invoke())
        self.assertEqual({p: digest(p) for p in before}, before)

    def test_inspected_code_is_not_executed(self) -> None:
        sentinel = self.base / "code-was-executed"
        code_path = self.root / self.task()["code"][0]
        code_path.write_text(f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('unsafe')\n")
        self.baseline = self.freeze(self.current)
        self.save_specs()
        self.assert_all_eligible(*self.invoke())
        self.assertFalse(sentinel.exists())


if __name__ == "__main__":
    unittest.main()
