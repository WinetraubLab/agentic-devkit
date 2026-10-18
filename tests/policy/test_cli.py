"""Tests in this file validate `policy CLI` located at `src/agentic_devkit/policies/cli.py`.
`policy CLI` is responsible for exposing policy operations through agentic-devkit.

Shared setup: _fixture creates and commits two generated policies; security_exceptions sets the committed security finding list. _complete writes the supplied finding list, or NONE for an empty list. _run_cli executes the public policy command with --root pointing to the supplied repository.
"""

import unittest

from tests.policy.test_harness.fixtures import _fixture, _run_cli, _complete, _commit, _git, _renderer_fixture


class PolicyCliTests(unittest.TestCase):
    def test_render_clears_completed_attestations(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy CLI` regenerates policies with empty attestations and stores the current digest.
        Standard usage: A project renders policies before beginning a fresh review.

        Verification Method: verify public function output

        Verification Detail:
        The render command returns zero and replaces the previous finding list with an empty attestation.

        Similar Coverage:
        - Scenario Difference: `test_cli.py::test_document_check_preserves_review_results`
          Explanation: This test clears completed reviews through the render command; the named test preserves recorded findings during document checks.
        - Scenario Difference: `test_render_policy_documents.py::test_renders_policy_document`
          Explanation: This test clears completed reviews through the render command; the named test creates a document from YAML using the provided template.
        - Scenario Difference: `test_render_policy_documents.py::test_resets_editable_attestation`
          Explanation: This test clears completed reviews through the render command; the named test clears the review after YAML changes while retaining exemptions.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_scope_changes_reset_attestations`
          Explanation: This test clears completed reviews through the render command; the named test resets reviews after a root is added.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_removing_root_resets_attestations`
          Explanation: This test clears completed reviews through the render command; the named test resets reviews after a root is removed.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_clears_data_type_attestations`
          Explanation: This test clears completed reviews through the render command; the named test resets reviews after a tracked data-type file changes.
        - Scenario Difference: `test_cli.py::test_render_updates_scope_digest`
          Explanation: This test clears completed reviews through the render command; the named test saves the current code fingerprint through the render command.
        """
        root = _fixture(self, security_exceptions=["src/example.ts"])
        policy = root / "policy/access/security.md"
        self.assertIn("Noncompliant Files:\n- src/example.ts", policy.read_text())  # Input check
        (root / "src/example.ts").write_text("export const value = 2;\n")
        result = _run_cli(root, "render")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(policy.read_text().endswith("Noncompliant Files:\n"))

        verified = _run_cli(root, "verify")
        self.assertEqual(0, verified.returncode, verified.stderr)

    def test_verify_accepts_explicit_baseline(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy CLI` uses the selected commit when checking reported violations.
        A developer selects an older review allowing one violating file instead of the latest review allowing none.

        Verification Method: verify public function output

        Verification Detail:
        The current review fails against HEAD but passes when --baseline-ref selects the older commit.

        Similar Coverage:
        - Scenario Difference: `test_verify_policy_attestations.py::test_accepts_same_or_fewer_violations`
          Explanation: This test selects an older committed finding allowance; the named test accepts the same or fewer findings than a committed review.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_rejects_exception_count_above_baseline`
          Explanation: This test selects an older committed finding allowance; the named test rejects more findings than a committed review allows.
        """
        root = _fixture(self)
        baseline = _git(root, "rev-parse", "HEAD").strip()
        policy = root / "policy/access/security.md"
        _complete(policy)
        _commit(root, "Record a review without violations")
        _complete(policy, ["src/example.ts"])
        default = _run_cli(root, "verify")
        self.assertEqual(1, default.returncode, default.stdout + default.stderr)
        result = _run_cli(root, "verify", "--baseline-ref", baseline)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn(f"Policy attestations do not exceed {baseline}", result.stdout)

    def test_document_check_preserves_review_results(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy CLI` must not erase the agent's recorded violations when checking that a policy document is up to date.
        Standard usage: A developer runs check-documents after an agent has recorded policy violations.

        Verification Method: verify public function output

        Verification Detail:
        The check-documents command succeeds and leaves the policy file, including its list of violations, unchanged.

        Similar Coverage:
        - Scenario Difference: `test_cli.py::test_render_clears_completed_attestations`
          Explanation: This test preserves recorded findings during document checks; the named test clears completed reviews through the render command.
        - Happy/Failure Path Difference: `test_cli.py::test_reports_missing_policy_documents`
          Explanation: This test preserves recorded findings during document checks; the named test reports missing policy documents with generation instructions.
        - Scenario Difference: `test_render_policy_documents.py::test_resets_editable_attestation`
          Explanation: This test preserves recorded findings during document checks; the named test clears the review after YAML changes while retaining exemptions.
        - Happy/Failure Path Difference: `test_render_policy_documents.py::test_rejects_manual_body_edits`
          Explanation: This test preserves recorded findings during document checks; the named test rejects direct edits to generated policy text.
        """
        root = _fixture(self)
        path = root / "policy/access/security.md"
        _complete(path, ["src/example.ts"])
        before = path.read_bytes()
        result = _run_cli(root, "check-documents")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(before, path.read_bytes())


    def test_explains_required_policy_reviews(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy CLI` explains which policies need another review and what to do next.
        After code changes, the error lists those policies and the command to rerun.

        Verification Method: verify public function output

        Verification Detail:
        The error lists the affected policies and instructs the agent to complete their attestations before running verification again.

        Similar Coverage:
        - Happy/Failure Path Difference: `test_policy_scope.py::test_hashes_only_git_index_files`
          Explanation: This test emits the review instructions after a scope mismatch. The named test establishes the Git-index boundary that creates that mismatch.
        - Scenario Difference: `test_verify_policy_attestations.py::test_replaces_stale_data_type_digest`
          Explanation: This test verifies the review instructions. The named test verifies the synchronized digest stored on disk.
        - Scenario Difference: `test_verify_policy_attestations.py::test_clears_data_type_attestations`
          Explanation: This test verifies the review instructions. The named test verifies that the reset clears field-policy reviews.
        - Scenario Difference: `test_cli.py::test_excludes_roots_from_cli_instructions`
          Explanation: This test verifies the complete review instructions. The named test verifies exclusion of root policy paths from that diagnostic.
        """
        root = _fixture(self)
        (root / "src/example.ts").write_text("export const value = 2;\n")
        result = _run_cli(root, "verify")
        output = result.stdout + result.stderr
        self.assertEqual(1, result.returncode, output)
        self.assertRegex(output, r"Policies requiring re-attestation:\n- policy/access/security\.md\n- policy/privacy/privacy\.md")
        self.assertIn("complete its Noncompliant Files attestation", output)
        self.assertIn("rerun agentic-devkit policy verify", output)

    def test_reports_missing_policy_documents(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy CLI` rejects missing policy documents and explains how to generate them.
        A developer checks policy documents before they have been generated.

        Verification Method: verify public function output

        Verification Detail:
        The command fails, explains that generated documents are stale or missing, and gives the command for generating fresh review documents.
        """
        root = _renderer_fixture(self)
        result = _run_cli(root, "check-documents")
        output = result.stdout + result.stderr
        self.assertEqual(1, result.returncode, output)
        self.assertIn("Generated policy documents are stale or were edited manually", output)
        self.assertIn("Run agentic-devkit policy render to regenerate them with empty attestations", output)


    def test_excludes_roots_from_cli_instructions(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy CLI` excludes project notes from the list of policies needing review.
        A code change must not request reviews of the README or TODO file.

        Verification Method: verify public function output

        Verification Detail:
        The failed verification lists field policies needing review and omits the project README and TODO paths.

        Similar Coverage:
        - Happy/Failure Path Difference: `test_policy_scope.py::test_hashes_only_git_index_files`
          Explanation: This test excludes root paths from CLI output. The named test establishes the Git-index boundary for digest inputs.
        - Scenario Difference: `test_verify_policy_attestations.py::test_replaces_stale_data_type_digest`
          Explanation: This test excludes root paths from CLI remediation output. The named test verifies the synchronized digest stored after a mismatch.
        - Scenario Difference: `test_verify_policy_attestations.py::test_clears_data_type_attestations`
          Explanation: This test excludes root policy paths from CLI output. The named test verifies cleared field-policy attestations.
        - Scenario Difference: `test_cli.py::test_explains_required_policy_reviews`
          Explanation: This test verifies root-path exclusion. The named test verifies the complete recovery diagnostic.
        """
        root = _fixture(self)
        (root / "src/example.ts").write_text("export const value = 2;\n")
        result = _run_cli(root, "verify")
        output = result.stdout + result.stderr
        self.assertEqual(1, result.returncode, output)
        self.assertIn("Policies requiring re-attestation:", output)
        self.assertIn("policy/access/security.md", output)
        self.assertNotIn("policy/README.md", output)
        self.assertNotIn("policy/TODO-SECURITY.md", output)



if __name__ == "__main__":
    unittest.main()
