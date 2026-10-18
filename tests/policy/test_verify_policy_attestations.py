"""Tests in this file validate `policy attestation verifier` located at `src/agentic_devkit/policies/verify_policy_attestations.py`.
`policy attestation verifier` is responsible for digest freshness, exception baselines, and stale-policy review instructions.
"""

from __future__ import annotations

import json
import re
import unittest
from agentic_devkit.policies.policy_scope import hash_policy_scope
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
        Verification fails, replaces the digest, and clears attestations despite unchanged indexed content.
        """
        root = _fixture(self)
        before = (root / "policy/policy-scope-digest.json").read_bytes()
        (root / "extra").mkdir()
        config = root / "policy/policy-scope-digest.json"
        document = json.loads(config.read_text())
        document["digests"].append({"root_folder": "extra", "digest": None})
        config.write_text(json.dumps(document))
        with self.assertRaisesRegex(ValueError, "Policy scope changed"):
            verify_policy_attestations(root=root, baseline_revision="HEAD")
        self.assertNotEqual(before, (root / "policy/policy-scope-digest.json").read_bytes())
        self.assertTrue((root / "policy/access/security.md").read_text().endswith("Noncompliant Files:\n"))
        entries = json.loads(config.read_text())["digests"]
        added = next(entry for entry in entries if entry["root_folder"] == "extra")
        self.assertRegex(added["digest"], r"^[a-f0-9]{64}$")

    def test_removing_root_resets_attestations(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy attestation verifier` clears previous review results when a folder is removed from the review list.
        The remaining folders must be reviewed again.

        Verification Method: verify public function output

        Verification Detail:
        Verification resets attestations after root removal, then accepts a completed review without resetting it again.
        """
        root = _fixture(self)
        path = root / "policy/policy-scope-digest.json"
        document = json.loads(path.read_text())
        document["digests"] = [entry for entry in document["digests"]
                               if entry["root_folder"] != "actions/data-types"]
        path.write_text(json.dumps(document))
        with self.assertRaisesRegex(ValueError, "Policy scope changed"):
            verify_policy_attestations(root=root, baseline_revision="HEAD")
        self.assertTrue((root / "policy/access/security.md").read_text().endswith("Noncompliant Files:\n"))
        _complete(root / "policy/access/security.md")
        _complete(root / "policy/privacy/privacy.md")
        verified = verify_policy_attestations(root=root, baseline_revision="HEAD")
        self.assertEqual(hash_policy_scope(root), verified.digest)

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
          Explanation: This test accepts unchanged or lower counts; the named test rejects an increase.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_rejects_violations_without_prior_results`
          Explanation: This test has valid committed results to compare against; the named test has no usable previous results.
        - Scenario Difference: `test_verify_policy_attestations.py::test_accepts_new_policy_without_violations`
          Explanation: This test covers an existing policy with a committed violation; the named test introduces a new policy with no violations.
        """
        root = _fixture(self, security_exceptions=["src/example.ts"])
        for files in (["src/example.ts"], []):
            with self.subTest(reported_files=files):
                _complete(root / "policy/access/security.md", files)
                result = verify_policy_attestations(root=root, baseline_revision="HEAD")
                self.assertEqual("HEAD", result.baseline_revision)

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
          Explanation: Both cover a new policy before its first completed review; this test reports a violation, while the named test reports none.
        """
        for committed_without_review in (False, True):
            with self.subTest(committed_without_review=committed_without_review):
                root = _fixture(self)
                source = root / "policy/access/new-policy.policy.yaml"
                source.write_text("title: New policy\nobjective: Enforce a new rule.\npolicy_content: Follow the new rule.\n")
                render_policy_documents(root=root)
                _complete(root / "policy/access/security.md", ["src/example.ts"])
                _complete(root / "policy/privacy/privacy.md")
                if committed_without_review:
                    _commit(root, "Add new policy before its first review")
                _complete(root / "policy/access/new-policy.md", ["src/example.ts"])
                with self.assertRaisesRegex(ValueError, r"- policy/access/new-policy\.md"):
                    verify_policy_attestations(root=root, baseline_revision="HEAD")

    def test_replaces_stale_data_type_digest(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy attestation verifier` updates saved code fingerprints after reviewed files change.
        Changing a tracked data-type file causes the stored fingerprints to be replaced.

        Verification Method: verify public function output

        Verification Detail:
        Before the reset, the stored central digest differs from the digest derived from the changed policy-scope content. After the reset, the stored central digest has the same value as that digest.

        Similar Coverage:
        - Happy/Failure Path Difference: `test_policy_scope.py::test_hashes_only_git_index_files`
          Explanation: This test records a recomputed digest after indexed data-type content changes. The named test establishes the Git-index boundary for digest inputs.
        - Scenario Difference: `test_verify_policy_attestations.py::test_clears_data_type_attestations`
          Explanation: This test synchronizes the stored digest after a data-type change. The named test clears field-policy attestations after the same kind of change.
        - Scenario Difference: `test_verify_policy_attestations.py::test_regenerates_malformed_policy`
          Explanation: This test synchronizes a stale digest. The named test recreates malformed field-policy Markdown during stale-digest regeneration.
        - Scenario Difference: `test_cli.py::test_explains_required_policy_reviews`
          Explanation: This test verifies the stored digest state. The named test emits the recovery diagnostic for the same mismatch.
        - Scenario Difference: `test_verify_policy_attestations.py::test_excludes_roots_from_cli_instructions`
          Explanation: This test synchronizes a stale digest. The named test excludes root policy paths from CLI remediation output.
        """
        root = _fixture(self)
        stored = (root / "policy/policy-scope-digest.json").read_bytes()
        (root / "actions/data-types/example.ts").write_text("export type Example = number;\n")
        changed = hash_policy_scope(root)
        with self.assertRaisesRegex(ValueError, "Policy scope changed"):
            verify_policy_attestations(root=root, baseline_revision="HEAD")
        self.assertNotEqual(stored, (root / "policy/policy-scope-digest.json").read_bytes())
        _complete(root / "policy/access/security.md")
        _complete(root / "policy/privacy/privacy.md")
        verified = verify_policy_attestations(root=root, baseline_revision="HEAD")
        self.assertEqual(changed, verified.digest)

    def test_clears_data_type_attestations(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy attestation verifier` clears previous review results after reviewed code changes.
        Changing a tracked data-type file starts fresh reviews for every policy.

        Verification Method: verify public function output

        Verification Detail:
        Before the reset, both field policies contain attested files in their Noncompliant Files sections. After the reset, both generated field policies contain an empty Noncompliant Files section at the end.

        Similar Coverage:
        - Scenario Difference: `test_verify_policy_attestations.py::test_regenerates_malformed_policy`
          Explanation: This test clears every generated field-policy attestation after a data-type change. The named test specifically recreates one malformed field policy with an empty attestation.
        - Scenario Difference: `test_cli.py::test_explains_required_policy_reviews`
          Explanation: This test observes reset field policies. The named test emits the recovery diagnostic for those policies.
        - Happy/Failure Path Difference: `test_policy_scope.py::test_hashes_only_git_index_files`
          Explanation: This test clears attestations after a data-type change. The named test establishes the Git-index boundary that determines digest inputs.
        - Scenario Difference: `test_verify_policy_attestations.py::test_replaces_stale_data_type_digest`
          Explanation: This test clears field-policy attestations after a data-type change. The named test synchronizes the stored digest after that change.
        - Scenario Difference: `test_verify_policy_attestations.py::test_excludes_roots_from_cli_instructions`
          Explanation: This test verifies regenerated field-policy attestations. The named test excludes root policy paths from the related CLI output.
        """
        root = _fixture(self, security_exceptions=["src/example.ts"], privacy_exceptions=["actions/data-types/example.ts"])
        (root / "actions/data-types/example.ts").write_text("export type Example = number;\n")
        try:
            verify_policy_attestations(root=root, baseline_revision="HEAD")
        except ValueError:
            pass
        for name in ("policy/access/security.md", "policy/privacy/privacy.md"):
            self.assertTrue((root / name).read_text().endswith("Noncompliant Files:\n"))

    def test_regenerates_malformed_policy(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy attestation verifier` repairs broken policy documents when changed code triggers fresh reviews.
        A damaged policy document is rebuilt from its YAML with an empty review section.

        Verification Method: verify public function output

        Verification Detail:
        The regenerated field policy contains its generated heading and an empty Noncompliant Files section. The regenerated field policy excludes the original malformed heading.

        Similar Coverage:
        - Happy/Failure Path Difference: `test_policy_scope.py::test_hashes_only_git_index_files`
          Explanation: This test uses a tracked-source digest change to recreate malformed field-policy Markdown. The named test proves which source files affect that digest.
        - Scenario Difference: `test_verify_policy_attestations.py::test_clears_data_type_attestations`
          Explanation: This test recreates one malformed field policy with an empty attestation. The named test clears every generated field-policy attestation after a data-type change.
        - Scenario Difference: `test_cli.py::test_explains_required_policy_reviews`
          Explanation: This test recreates malformed Markdown after a tracked-source change. The named test emits the recovery diagnostic through npm.
        - Scenario Difference: `test_verify_policy_attestations.py::test_replaces_stale_data_type_digest`
          Explanation: This test recreates malformed field-policy Markdown. The named test synchronizes the stored digest after a data-type change.
        - Scenario Difference: `test_verify_policy_attestations.py::test_excludes_roots_from_cli_instructions`
          Explanation: This test recreates malformed field-policy Markdown. The named test excludes root policy paths from CLI remediation output.
        """
        root = _fixture(self)
        policy = root / "policy/access/security.md"
        policy.write_text("# Malformed policy\n")
        (root / "src/example.ts").write_text("export const value = 2;\n")
        try:
            verify_policy_attestations(root=root, baseline_revision="HEAD")
        except ValueError:
            pass
        regenerated = policy.read_text()
        self.assertTrue(regenerated.startswith("# Security policy\n"))
        self.assertTrue(regenerated.endswith("Noncompliant Files:\n"))
        self.assertNotIn("# Malformed policy", regenerated)

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
          Explanation: This test rejects regression from one exception to two. The named test accepts improvement from one exception to zero.
        - Scenario Difference: `test_verify_policy_attestations.py::test_rejects_violations_without_prior_results`
          Explanation: This test rejects a working count above a present committed count. The named test rejects a committed policy that supplies no count.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_accepts_new_policy_without_violations`
          Explanation: This test verifies that `policy attestation verifier` refuses a policy when its exception count exceeds its HEAD baseline. When a policy has two exceptions against a committed baseline of one, `policy attestation verifier` refuses that policy; the named test instead verifies that `policy attestation verifier` accepts each newly added policy whose attestation has an empty noncompliant-file list.
        """
        root = _fixture(self, security_exceptions=["src/example.ts"])
        _complete(root / "policy/access/security.md", ["src/example.ts", "actions/data-types/example.ts"])
        with self.assertRaises(ValueError):
            verify_policy_attestations(root=root, baseline_revision="HEAD")

    def test_excludes_roots_from_cli_instructions(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy attestation verifier` excludes project notes from the list of policies needing review.
        A code change must not request reviews of the README or TODO file.

        Verification Method: verify public function output

        Verification Detail:
        The CLI diagnostic contains neither root policy artifact path.

        Similar Coverage:
        - Happy/Failure Path Difference: `test_policy_scope.py::test_hashes_only_git_index_files`
          Explanation: This test excludes root paths from CLI output. The named test establishes the Git-index boundary for digest inputs.
        - Scenario Difference: `test_verify_policy_attestations.py::test_replaces_stale_data_type_digest`
          Explanation: This test excludes root paths from CLI remediation output. The named test verifies the synchronized digest stored after a mismatch.
        - Scenario Difference: `test_verify_policy_attestations.py::test_clears_data_type_attestations`
          Explanation: This test excludes root policy paths from CLI output. The named test verifies cleared field-policy attestations.
        - Scenario Difference: `test_verify_policy_attestations.py::test_regenerates_malformed_policy`
          Explanation: This test excludes root paths from CLI remediation output. The named test recreates malformed field-policy Markdown.
        - Scenario Difference: `test_cli.py::test_explains_required_policy_reviews`
          Explanation: This test verifies root-path exclusion. The named test verifies the complete recovery diagnostic.
        """
        root = _fixture(self)
        (root / "src/example.ts").write_text("export const value = 2;\n")
        result = _run_cli(root, "verify")
        output = result.stdout + result.stderr
        self.assertNotIn("policy/README.md", output)
        self.assertNotIn("policy/TODO-SECURITY.md", output)



if __name__ == "__main__":
    unittest.main()
