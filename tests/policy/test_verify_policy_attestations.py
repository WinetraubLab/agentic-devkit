"""Tests in this file validate `policy attestation verifier` located at `src/agentic_devkit/policies/verify_policy_attestations.py`.
`policy attestation verifier` is responsible for digest freshness, exception baselines, and stale-policy review instructions.

Shared setup: _fixture creates and commits two generated policies with the supplied security and privacy finding lists. _complete writes the supplied finding list, or NONE for an empty list. _commit stages and commits the current project files.
"""

from __future__ import annotations

import json
import unittest
from agentic_devkit.policies.render_policy_documents import render_policy_documents
from agentic_devkit.policies.verify_policy_attestations import verify_policy_attestations
from tests.policy.test_harness.fixtures import _fixture, _complete, _commit, _run_cli

class PolicyTests(unittest.TestCase):
    def test_scope_changes_reset_attestations(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy attestation verifier` clears previous review results when a folder is added to the review list.
        Even adding an empty folder requires another review.

        Verification Method: verify public function output

        Verification Detail:
        Verification requests another review and clears the previous finding list after an empty root is added.

        Similar Coverage:
        - Happy/Failure Path Difference: `test_cli.py::test_render_resets_attestations_and_digest`
          Explanation: This test resets reviews after a root is added; the named test clears completed reviews through the render command.
        - Happy/Failure Path Difference: `test_render_policy_documents.py::test_resets_editable_attestation`
          Explanation: This test resets reviews after a root is added; the named test clears the review after YAML changes while retaining exemptions.
        - Scenario Difference: `test_verify_policy_attestations.py::test_removing_root_resets_attestations`
          Explanation: This test resets reviews after a root is added; the named test resets reviews after a root is removed.
        - Scenario Difference: `test_verify_policy_attestations.py::test_clears_data_type_attestations`
          Explanation: This test resets reviews after a root is added; the named test resets reviews after a tracked data-type file changes.
        - Happy/Failure Path Difference: `test_cli.py::test_document_check_preserves_review_results`
          Explanation: This test resets completed attestations after a review root is added; the named test preserves completed attestations during a document check.
        """
        root = _fixture(self, security_exceptions=["src/example.ts"], privacy_exceptions=[])
        (root / "extra").mkdir()
        config = root / "policy/policy-scope-digest.json"
        document = json.loads(config.read_text())
        document["digests"].append({"root_folder": "extra", "digest": None})
        config.write_text(json.dumps(document))
        with self.assertRaisesRegex(ValueError, "Policy scope changed"):
            verify_policy_attestations(root=root, baseline_revision="HEAD")
        self.assertTrue((root / "policy/access/security.md").read_text().endswith("Noncompliant Files:\n"))

    def test_removing_root_resets_attestations(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy attestation verifier` clears previous review results when a folder is removed from the review list.
        The remaining folders must be reviewed again.

        Verification Method: verify public function output

        Verification Detail:
        Verification raises the scope-change error and leaves the previous finding list empty after the configured root is removed.

        Similar Coverage:
        - Happy/Failure Path Difference: `test_cli.py::test_render_resets_attestations_and_digest`
          Explanation: This test resets reviews after a root is removed; the named test clears completed reviews through the render command.
        - Happy/Failure Path Difference: `test_render_policy_documents.py::test_resets_editable_attestation`
          Explanation: This test resets reviews after a root is removed; the named test clears the review after YAML changes while retaining exemptions.
        - Scenario Difference: `test_verify_policy_attestations.py::test_scope_changes_reset_attestations`
          Explanation: This test resets reviews after a root is removed; the named test resets reviews after a root is added.
        - Scenario Difference: `test_verify_policy_attestations.py::test_clears_data_type_attestations`
          Explanation: This test resets reviews after a root is removed; the named test resets reviews after a tracked data-type file changes.
        - Happy/Failure Path Difference: `test_cli.py::test_document_check_preserves_review_results`
          Explanation: This test resets completed attestations after a review root is removed; the named test preserves completed attestations during a document check.
        """
        root = _fixture(self, security_exceptions=["src/example.ts"], privacy_exceptions=[])
        policy = root / "policy/access/security.md"
        self.assertIn("Noncompliant Files:\n- src/example.ts", policy.read_text())  # Input check
        # The JSON's root_folder entries are the configured review list.
        path = root / "policy/policy-scope-digest.json"
        document = json.loads(path.read_text())
        document["digests"] = [entry for entry in document["digests"]
                               if entry["root_folder"] != "actions/data-types"]
        path.write_text(json.dumps(document))
        with self.assertRaisesRegex(ValueError, "Policy scope changed"):
            verify_policy_attestations(root=root, baseline_revision="HEAD")
        self.assertTrue(policy.read_text().endswith("Noncompliant Files:\n"))

    def test_accepts_same_or_fewer_violations(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy attestation verifier` accepts reviews reporting no more violating files than the committed review.
        A review previously listed one file; its next review lists one or none.

        Verification Method: verify public function output

        Verification Detail:
        Verification succeeds with one reported file and with no reported files against a committed review listing one file.

        Similar Coverage:
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_rejects_exception_count_above_baseline`
          Explanation: This test accepts the same or fewer findings than a committed review; the named test rejects more findings than a committed review allows.
        - Scenario Difference: `test_verify_policy_attestations.py::test_accepts_new_policy_without_violations`
          Explanation: This test accepts the same or fewer findings than a committed review; the named test accepts a new policy whose first review reports no findings.
        - Scenario Difference: `test_cli.py::test_verify_accepts_explicit_baseline`
          Explanation: This test accepts the same or fewer findings than a committed review; the named test selects an older committed finding allowance.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_rejects_new_policy_violations`
          Explanation: This test accepts the same or fewer findings than a committed review; the named test rejects findings when a policy has no completed committed review.
        """
        root = _fixture(self, security_exceptions=["src/example.ts"])
        for files in (["src/example.ts"], []):
            with self.subTest(reported_files=files):
                _complete(root / "policy/access/security.md", files)
                result = verify_policy_attestations(root=root, baseline_revision="HEAD")
                self.assertIn(root / "policy/access/security.md", result.policy_paths)

    def test_rejects_new_policy_violations(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy attestation verifier` rejects a new policy's attestation if it reports any violations.
        When introducing a policy, existing violations must be fixed before its first attestation passes.

        Verification Method: verify public function output

        Verification Detail:
        Verification rejects a violation whether the new policy is uncommitted or was committed with a blank review.

        Similar Coverage:
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_accepts_new_policy_without_violations`
          Explanation: This test rejects findings when a policy has no completed committed review; the named test accepts a new policy whose first review reports no findings.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_accepts_same_or_fewer_violations`
          Explanation: This test rejects findings when a policy has no completed committed review; the named test accepts the same or fewer findings than a committed review.
        - Scenario Difference: `test_verify_policy_attestations.py::test_rejects_exception_count_above_baseline`
          Explanation: This test rejects findings when a policy has no completed committed review; the named test rejects more findings than a committed review allows.
        """
        for committed_without_review in (False, True):
            with self.subTest(committed_without_review=committed_without_review):
                root = _fixture(self, security_exceptions=["src/example.ts"], privacy_exceptions=[])
                source = root / "policy/access/new-policy.policy.yaml"
                source.write_text("title: New policy\nobjective: Enforce a new rule.\npolicy_content: Follow the new rule.\n")
                render_policy_documents(root=root)
                _complete(root / "policy/access/security.md", ["src/example.ts"])
                _complete(root / "policy/privacy/privacy.md", [])
                if committed_without_review:
                    _commit(root, "Add new policy before its first review")
                _complete(root / "policy/access/new-policy.md", ["src/example.ts"])
                with self.assertRaisesRegex(ValueError, r"- policy/access/new-policy\.md"):
                    verify_policy_attestations(root=root, baseline_revision="HEAD")

    def test_accepts_new_policy_without_violations(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy attestation verifier` accepts a new policy when its first review finds no files breaking the rule.
        A developer introduces a rule and finds no files that break it.

        Verification Method: verify public function output

        Verification Detail:
        Verification accepts NONE whether the new policy is uncommitted or was committed with a blank review.

        Similar Coverage:
        - Scenario Difference: `test_verify_policy_attestations.py::test_accepts_same_or_fewer_violations`
          Explanation: This test accepts a new policy whose first review reports no findings; the named test accepts the same or fewer findings than a committed review.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_rejects_exception_count_above_baseline`
          Explanation: This test accepts a new policy whose first review reports no findings; the named test rejects more findings than a committed review allows.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_rejects_new_policy_violations`
          Explanation: This test accepts a new policy whose first review reports no findings; the named test rejects findings when a policy has no completed committed review.
        """
        for committed_without_review in (False, True):
            with self.subTest(committed_without_review=committed_without_review):
                root = _fixture(self, security_exceptions=["src/example.ts"], privacy_exceptions=[])
                source = root / "policy/access/new-policy.policy.yaml"
                source.write_text("title: New policy\nobjective: Enforce a new rule.\npolicy_content: Follow the new rule.\n")
                render_policy_documents(root=root)
                _complete(root / "policy/access/security.md", ["src/example.ts"])
                _complete(root / "policy/privacy/privacy.md", [])
                if committed_without_review:
                    _commit(root, "Add new policy before its first review")
                _complete(root / "policy/access/new-policy.md", [])
                result = verify_policy_attestations(root=root, baseline_revision="HEAD")
                self.assertIn(root / "policy/access/new-policy.md", result.policy_paths)

    def test_replaces_stale_data_type_digest(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy attestation verifier` saves updated fingerprints when reviewed code changes.
        A tracked data-type file changes after its previous review.

        Verification Method: verify public function output

        Verification Detail:
        The saved fingerprints match those computed from the changed working-tree content.

        Similar Coverage:
        - Happy/Failure Path Difference: `test_cli.py::test_render_resets_attestations_and_digest`
          Explanation: This test saves updated fingerprints after a tracked data-type file changes; the named test saves the current code fingerprint through the render command.
        - Happy/Failure Path Difference: `test_policy_scope.py::test_hashes_only_git_index_files`
          Explanation: This test saves updated fingerprints after a tracked data-type file changes; the named test ignores new files until Git stages them.
        - Happy/Failure Path Difference: `test_policy_scope.py::test_hashes_newly_added_root`
          Explanation: This test saves updated fingerprints after a tracked data-type file changes; the named test includes files after their folder is added to review scope.
        - Happy/Failure Path Difference: `test_policy_scope.py::test_hashes_configured_folders_only`
          Explanation: This test saves updated fingerprints after a tracked data-type file changes; the named test excludes file changes outside configured review folders.
        - Happy/Failure Path Difference: `test_policy_scope.py::test_hashes_symlinked_scope_folders`
          Explanation: This test saves updated fingerprints after a tracked data-type file changes; the named test hashes tracked files through linked folders.
        - Happy/Failure Path Difference: `test_policy_scope.py::test_detects_retargeted_scope_link`
          Explanation: This test saves updated fingerprints after a tracked data-type file changes; the named test changes the fingerprint when a reviewed link changes targets.
        """
        from agentic_devkit.policies.policy_scope import _hash_policy_roots

        root = _fixture(self, security_exceptions=["src/example.ts"], privacy_exceptions=[])
        (root / "actions/data-types/example.ts").write_text("export type Example = number;\n")
        expected = _hash_policy_roots(root)
        try:
            verify_policy_attestations(root=root, baseline_revision="HEAD")
        except ValueError:
            pass
        stored = json.loads((root / "policy/policy-scope-digest.json").read_text())["digests"]
        self.assertEqual(expected, {entry["root_folder"]: entry["digest"] for entry in stored})

    def test_clears_data_type_attestations(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy attestation verifier` clears previous review results after reviewed code changes.
        Changing a tracked data-type file starts fresh reviews for every policy.

        Verification Method: verify public function output

        Verification Detail:
        Before the reset, both field policies contain attested files in their Noncompliant Files sections. After the reset, both generated field policies contain an empty Noncompliant Files section at the end.

        Similar Coverage:
        - Scenario Difference: `test_cli.py::test_explains_required_policy_reviews`
          Explanation: This test observes reset field policies. The named test emits the recovery diagnostic for those policies.
        - Happy/Failure Path Difference: `test_policy_scope.py::test_hashes_only_git_index_files`
          Explanation: This test clears attestations after a data-type change. The named test establishes the Git-index boundary that determines digest inputs.
        - Scenario Difference: `test_verify_policy_attestations.py::test_replaces_stale_data_type_digest`
          Explanation: This test clears field-policy attestations after a data-type change. The named test synchronizes the stored digest after that change.
        - Scenario Difference: `test_cli.py::test_excludes_roots_from_cli_instructions`
          Explanation: This test verifies regenerated field-policy attestations. The named test excludes root policy paths from the related CLI output.
        - Happy/Failure Path Difference: `test_cli.py::test_render_resets_attestations_and_digest`
          Explanation: This test resets reviews after a tracked data-type file changes; the named test clears completed reviews through the render command.
        - Happy/Failure Path Difference: `test_render_policy_documents.py::test_resets_editable_attestation`
          Explanation: This test resets reviews after a tracked data-type file changes; the named test clears the review after YAML changes while retaining exemptions.
        - Scenario Difference: `test_verify_policy_attestations.py::test_scope_changes_reset_attestations`
          Explanation: This test resets reviews after a tracked data-type file changes; the named test resets reviews after a root is added.
        - Scenario Difference: `test_verify_policy_attestations.py::test_removing_root_resets_attestations`
          Explanation: This test resets reviews after a tracked data-type file changes; the named test resets reviews after a root is removed.
        - Happy/Failure Path Difference: `test_cli.py::test_document_check_preserves_review_results`
          Explanation: This test resets completed attestations after a tracked data-type file changes; the named test preserves completed attestations during a document check.
        """
        root = _fixture(self, security_exceptions=["src/example.ts"], privacy_exceptions=["actions/data-types/example.ts"])
        policies = list((root / "policy").glob("*/*.md"))
        for policy in policies:
            self.assertRegex(policy.read_text(), r"Noncompliant Files:\n- .+")  # Input check
        (root / "actions/data-types/example.ts").write_text("export type Example = number;\n")
        try:
            verify_policy_attestations(root=root, baseline_revision="HEAD")
        except ValueError:
            pass
        for policy in policies:
            self.assertTrue(policy.read_text().endswith("Noncompliant Files:\n"))

    def test_rejects_exception_count_above_baseline(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy attestation verifier` rejects reviews reporting more violating files than the last committed review.
        The current review reports more files with violations than the review committed at HEAD.

        Verification Method: verify public function output

        Verification Detail:
        The public verifier invocation throws an error.

        Similar Coverage:
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_accepts_same_or_fewer_violations`
          Explanation: This test rejects more findings than a committed review allows; the named test accepts the same or fewer findings than a committed review.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_accepts_new_policy_without_violations`
          Explanation: This test rejects more findings than a committed review allows; the named test accepts a new policy whose first review reports no findings.
        - Happy/Failure Path Difference: `test_cli.py::test_verify_accepts_explicit_baseline`
          Explanation: This test rejects more findings than a committed review allows; the named test selects an older committed finding allowance.
        - Scenario Difference: `test_verify_policy_attestations.py::test_rejects_new_policy_violations`
          Explanation: This test rejects more findings than a committed review allows; the named test rejects findings when a policy has no completed committed review.
        """
        root = _fixture(self, security_exceptions=["src/example.ts"])
        _complete(root / "policy/access/security.md", ["src/example.ts", "actions/data-types/example.ts"])
        with self.assertRaises(ValueError):
            verify_policy_attestations(root=root, baseline_revision="HEAD")




if __name__ == "__main__":
    unittest.main()
