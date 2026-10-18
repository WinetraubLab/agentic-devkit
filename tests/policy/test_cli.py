"""Tests in this file validate `policy CLI` located at `src/agentic_devkit/policies/cli.py`.
`policy CLI` is responsible for exposing policy operations through agentic-devkit.
"""

import json
import unittest

from tests.policy.test_harness.fixtures import _fixture, _run_cli, _complete, _commit, _git, _renderer_fixture


class PolicyCliTests(unittest.TestCase):
    def test_render_resets_attestations_and_digest(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy CLI` regenerates policies with empty attestations and stores the current digest.
        Standard usage: A project renders policies before beginning a fresh review.

        Verification Method: verify public function output

        Verification Detail:
        The command succeeds, clears the completed attestation, and writes the scope digest.
        """
        root = _fixture(self)
        (root / "src/example.ts").write_text("export const value = 2;\n")
        result = _run_cli(root, "render")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue((root / "policy/access/security.md").read_text().endswith("Noncompliant Files:\n"))
        entries = json.loads((root / "policy/policy-scope-digest.json").read_text())["digests"]
        self.assertEqual({"src", "actions/data-types", "actions/technical-skills"},
                         {entry["root_folder"] for entry in entries})
        for entry in entries:
            self.assertRegex(entry["digest"], r"^[a-f0-9]{64}$")
        _complete(root / "policy/access/security.md")
        _complete(root / "policy/privacy/privacy.md")
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
        """
        root = _fixture(self)
        path = root / "policy/access/security.md"
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
        The diagnostic contains the reset explanation, stored and current digest labels, the no-violation clarification, the affected-policy list, and the rerun instruction in one message.

        Similar Coverage:
        - Happy/Failure Path Difference: `test_policy_scope.py::test_hashes_only_git_index_files`
          Explanation: This test emits the review instructions after a scope mismatch. The named test establishes the Git-index boundary that creates that mismatch.
        - Scenario Difference: `test_verify_policy_attestations.py::test_replaces_stale_data_type_digest`
          Explanation: This test verifies the review instructions. The named test verifies the synchronized digest stored on disk.
        - Scenario Difference: `test_verify_policy_attestations.py::test_clears_data_type_attestations`
          Explanation: This test verifies the review instructions. The named test verifies that the reset clears field-policy reviews.
        - Scenario Difference: `test_verify_policy_attestations.py::test_excludes_roots_from_cli_instructions`
          Explanation: This test verifies the complete review instructions. The named test verifies exclusion of root policy paths from that diagnostic.
        """
        root = _fixture(self)
        (root / "src/example.ts").write_text("export const value = 2;\n")
        result = _run_cli(root, "verify")
        output = result.stdout + result.stderr
        self.assertRegex(output, r"(?s)Policy scope changed; all policy attestations were reset\..*Stored policy scope digest: [a-f0-9]{64}.*Current policy scope digest: [a-f0-9]{64}.*This does not mean every listed policy has a violation\..*Policies requiring re-attestation:\n- policy/access/security\.md\n- policy/privacy/privacy\.md.*complete its Noncompliant Files attestation, and rerun agentic-devkit policy verify\.")

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
