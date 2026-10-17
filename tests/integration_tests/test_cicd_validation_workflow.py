"""Tests in this file validate `CI/CD linter` located at `src/agentic_devkit/tdd_lint/cli/run_lint_pipeline.py`.
`CI/CD linter` is responsible for validating committed review proof without creating review packets.

Terms:
- `CI/CD linter`: CI/CD linter runs `agentic-devkit tdd lint` in an automated pipeline against committed manifest proof. For example, it validates current proof without generating `.agent.md` files.
- `.agent.md`: An .agent.md file contains a review scorecard that create-agent-md generates for a test. For example, CI validates committed manifest proof without recreating these files.
"""

from __future__ import annotations

import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from tests.integration_tests.test_harness.usage_scenarios import (
    packet_paths as _packet_paths,
    record_approved_manifest as _record_approved_manifest,
    remove_packet_directory as _remove_packet_directory,
    run_cli as _run_cli,
    write_source as _write_source,
)


class CicdValidationWorkflowTests(unittest.TestCase):
    def test_outdated_version_remains_valid(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `CI/CD linter` accepts current test-content proof with outdated linter-version metadata.
        Specialized usage: The manifest records a historical linter version instead of the installed baseline version while its test-content hash remains current.

        Verification Method: verify public function output

        Verification Detail:
        1. Harness creates a temporary repository containing one valid test.
        2. Harness completes its review.
        3. Harness persists passing manifest proof before invoking `CI/CD linter`.
        4. Harness replaces the manifest linter-version metadata with 0.1.0.
        5. Harness removes the existing '.agent.md' files to reproduce `CI/CD linter` input.
        6. Harness invokes `CI/CD linter` using `agentic-devkit tdd lint --repo-root <temporary-repository>`.
        7. `CI/CD linter` succeeds without requiring a new review.

        Similar Coverage:
        - Scenario Difference: `test_build_manifest_from_agent_md_files.py::test_manifest_accepts_old_review_contract`
          Explanation: The current test verifies historical linter-version metadata remains valid for unchanged tests. The named test verifies historical review-contract metadata remains valid for unchanged tests; these scenarios distinguish the two contracts.
        - Scenario Difference: `test_cicd_validation_workflow.py::test_cicd_accepts_current_proof`
          Explanation: The current test verifies `CI/CD linter` accepts current proof with outdated version metadata. The named test verifies `CI/CD linter` accepts proof from the current release; both use happy path, but exercise materially different scenarios.
        - Scenario Difference: `test_cicd_validation_workflow.py::test_cicd_creates_no_packets`
          Explanation: The current test verifies `CI/CD linter` accepts current proof with outdated version metadata. The named test verifies `CI/CD linter` creates no `.agent.md` files when valid proof exists; both use happy path, but exercise materially different scenarios.
        - Happy/Failure Path Difference: `test_build_manifest_from_agent_md_files.py::test_deleted_file_proof_removed`
          Explanation: The current test verifies unchanged proof remains valid with historical linter metadata. The named test verifies proof for a deleted test file is removed; the current test is happy path, while the named test is failure path.
        - Happy/Failure Path Difference: `test_build_manifest_from_agent_md_files.py::test_deleted_function_proof_removed`
          Explanation: The current test verifies unchanged proof remains valid with historical linter metadata. The named test verifies proof for a deleted test function is removed; the current test is happy path, while the named test is failure path.
        - Scenario Difference: `test_build_manifest_from_agent_md_files.py::test_recording_keeps_current_proof`
          Explanation: The current test verifies unchanged proof remains valid with historical linter metadata. The named test verifies a manifest update retains current proof; both use happy path, but exercise materially different scenarios.
        - Happy/Failure Path Difference: `test_pre_commit_review_workflow.py::test_incomplete_review_preserves_manifest`
          Explanation: The current test verifies unchanged proof remains valid with historical linter metadata. The named test verifies an incomplete replacement review preserves existing manifest records; the current test is happy path, while the named test is failure path.
        - Scenario Difference: `test_pre_commit_review_workflow.py::test_lint_ignores_obsolete_pending_packets`
          Explanation: The current test verifies unchanged proof remains valid with historical linter metadata. The named test verifies lint ignores obsolete pending packets when manifest proof is current; both use happy path, but exercise materially different scenarios.
        - Scenario Difference: `test_pre_commit_review_workflow.py::test_repeated_generation_preserves_manifest`
          Explanation: The current test verifies unchanged proof remains valid with historical linter metadata. The named test verifies repeated ordinary generation preserves manifest bytes; both use happy path, but exercise materially different scenarios.
        - Happy/Failure Path Difference: `test_pre_commit_review_workflow.py::test_stale_test_requires_review`
          Explanation: The current test verifies unchanged proof remains valid with historical linter metadata. The named test verifies an edited test creates only its packet and related relationship rows; the current test is happy path, while the named test is failure path.
        - Scenario Difference: `test_agent_review_examples.py::test_current_jsonl_attestation_skips_evaluation`
          Explanation: The current test verifies CI accepts unchanged test proof with outdated version metadata; the named test verifies matching YAML-case proof skips evaluation.
        - Happy/Failure Path Difference: `test_agent_review_examples.py::test_stale_attestation_reports_pending_packet`
          Explanation: The current test verifies CI accepts current test-content proof with outdated version metadata; the named test verifies a changed YAML-case digest requires review.
        - Scenario Difference: `test_render_cross_test_agent_md_file.py::test_completed_classification_remains_valid`
          Explanation: The current test verifies CI accepts current test-content proof with outdated version metadata; the named test verifies unchanged files preserve completed pair classifications.
        - Scenario Difference: `test_pre_commit_review_workflow.py::test_current_manifest_generates_zero_packets`
          Explanation: The current test verifies CI accepts unchanged test proof with outdated version metadata; the named test verifies current passing proof suppresses packet generation.
        - Happy/Failure Path Difference: `test_build_manifest_from_agent_md_files.py::test_added_function_preserves_existing_proof`
          Explanation: The current test verifies CI accepts unchanged test proof with outdated version metadata; the named test verifies adding an unreviewed sibling preserves existing proof.
        """

        test_source = textwrap.dedent(
            '''\
            """Tests in this file validate `current review proof` located at `src/review_proof.py`.
            `current review proof` is responsible for recording the linter version that approved a test.
            """

            def test_version_sensitive_behavior() -> None:
                """Test Path: happy path

                Requirement Tested:
                `current review proof` remains valid for the linter release that recorded it.
                Standard usage: The installed linter records the completed review.

                Verification Method: verify public function output

                Verification Detail:
                The reviewed expression equals true.
                """

                assert True
            '''
        )

        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            _write_source(
                repo_root / "src" / "review_proof.py",
                "PROOF = 'current'\n",
            )
            _write_source(repo_root / "tests" / "test_version.py", test_source)
            _record_approved_manifest(
                repo_root,
                review_status="pass",
                review_evidence="approved version fixture",
            )
            manifest_path = repo_root / "tests" / "agentic_review_manifest.jsonl"
            record = json.loads(manifest_path.read_text(encoding="utf-8"))
            record["linter_version"] = "0.1.0"
            manifest_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            _remove_packet_directory(repo_root)

            lint = _run_cli(repo_root, "lint")

        self.assertEqual(0, lint.returncode)
        self.assertNotIn("missing_required_agent_md", lint.stdout)

    def test_cicd_accepts_current_proof(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `CI/CD linter` exits successfully when the manifest contains a passing review for the test's current content.
        Standard usage: CI reuses committed proof for an unchanged reviewed test.

        Verification Method: verify public function output

        Verification Detail:
        1. Harness creates a temporary repository containing one valid test.
        2. Harness completes its review.
        3. Harness persists passing proof whose source hash identifies the current test content.
        4. Harness invokes `CI/CD linter` using `agentic-devkit tdd lint --repo-root <temporary-repository>`.
        5. `CI/CD linter` accepts current manifest proof, demonstrated by exit code `0`.

        Similar Coverage:
        - Scenario Difference: `test_build_manifest_from_agent_md_files.py::test_recording_keeps_current_proof`
          Explanation: The current test verifies `CI/CD linter` accepts current manifest proof. The named test verifies `build_manifest_from_agent_md_files` retains passing `manifest proof` during `orphaned record` cleanup when its source SHA256 matches the current test content; both use happy path, but exercise materially different scenarios.
        - Scenario Difference: `test_cicd_validation_workflow.py::test_cicd_creates_no_packets`
          Explanation: The current test verifies `CI/CD linter` accepts current manifest proof. The named test verifies `CI/CD linter` creates no `.agent.md` files when current manifest proof exists; both use happy path, but exercise materially different scenarios.
        - Scenario Difference: `test_cicd_validation_workflow.py::test_outdated_version_remains_valid`
          Explanation: The current test verifies `CI/CD linter` accepts current manifest proof. The named test verifies `CI/CD linter` accepts proof created under an earlier version; both use happy path, but exercise materially different scenarios.
        - Scenario Difference: `test_review_documentation.py::test_github_actions_shows_ci`
          Explanation: The current test verifies CI accepts committed current proof. The named test verifies documentation describes CI validating committed proof; these scenarios distinguish the two contracts.
        - Scenario Difference: `test_build_manifest_from_agent_md_files.py::test_manifest_accepts_old_review_contract`
          Explanation: The current test verifies CI accepts current passing proof. The named test verifies unchanged proof remains valid with historical review-contract metadata; both use happy path, but exercise materially different scenarios.
        - Scenario Difference: `test_pre_commit_review_workflow.py::test_current_manifest_generates_zero_packets`
          Explanation: The current test verifies CI accepts current passing proof. The named test verifies ordinary generation creates no packets for current proof; both use happy path, but exercise materially different scenarios.
        - Happy/Failure Path Difference: `test_pre_commit_review_workflow.py::test_incomplete_review_preserves_manifest`
          Explanation: The current test verifies CI accepts current passing proof. The named test verifies an incomplete replacement review preserves existing manifest records; the current test is happy path, while the named test is failure path.
        - Scenario Difference: `test_pre_commit_review_workflow.py::test_lint_ignores_obsolete_pending_packets`
          Explanation: The current test verifies CI accepts current passing proof. The named test verifies lint ignores obsolete pending packets when manifest proof is current; both use happy path, but exercise materially different scenarios.
        - Scenario Difference: `test_pre_commit_review_workflow.py::test_repeated_generation_preserves_manifest`
          Explanation: The current test verifies CI accepts current passing proof. The named test verifies repeated ordinary generation preserves manifest bytes; both use happy path, but exercise materially different scenarios.
        - Happy/Failure Path Difference: `test_pre_commit_review_workflow.py::test_stale_test_requires_review`
          Explanation: The current test verifies CI accepts current passing proof. The named test verifies an edited test creates only its packet and related relationship rows; the current test is happy path, while the named test is failure path.
        - Scenario Difference: `test_agent_review_examples.py::test_current_jsonl_attestation_skips_evaluation`
          Explanation: The current test verifies CI accepts a passing manifest for unchanged test content; the named test verifies matching YAML-case proof bypasses evaluation and produces no pending packet paths.
        - Happy/Failure Path Difference: `test_agent_review_examples.py::test_stale_attestation_reports_pending_packet`
          Explanation: The current test verifies CI accepts a passing manifest for unchanged test content; the named test verifies an outdated YAML-case digest produces a pending-packet error.
        - Module Difference: `test_render_cross_test_agent_md_file.py::test_completed_classification_remains_valid`
          Explanation: The current test verifies CI accepts a passing manifest for unchanged test content; the named test verifies completed pair classifications remain valid when reviewed test files are unchanged.
        """

        test_source = textwrap.dedent(
            '''\
            """Tests in this file validate `approved behavior` located at `src/approved.py`.
            `approved behavior` is responsible for evaluating an approved boolean expression.
            """

            def test_approved_packet_behavior() -> None:
                """Test Path: happy path

                Requirement Tested:
                `approved behavior` evaluates to true.
                Standard usage: The scenario demonstrates baseline behavior.

                Verification Method: verify public function output

                Verification Detail:
                The expression equals true.
                """

                assert True
            '''
        )

        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            _write_source(repo_root / "src" / "approved.py", "VALUE = True\n")
            _write_source(repo_root / "tests" / "test_approved.py", test_source)
            _record_approved_manifest(
                repo_root,
                review_status="pass",
                review_evidence="approved packetless CI fixture",
            )
            lint = _run_cli(repo_root, "lint")

        self.assertEqual(0, lint.returncode, lint.stdout + lint.stderr)

    def test_cicd_creates_no_packets(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `CI/CD linter` creates no `.agent.md` files when current manifest proof exists.
        Standard usage: The scenario demonstrates baseline behavior.

        Verification Method: verify public function output

        Verification Detail:
        1. Harness creates a temporary repository containing one valid test.
        2. Harness completes its review.
        3. Harness persists current passing proof in the manifest.
        4. Harness removes the existing '.agent.md' directory before invoking `CI/CD linter`.
        5. Harness invokes `CI/CD linter` using `agentic-devkit tdd lint --repo-root <temporary-repository>`.
        6. Packet list contains zero paths after lint.

        Similar Coverage:
        - Scenario Difference: `test_cicd_validation_workflow.py::test_cicd_accepts_current_proof`
          Explanation: The current test verifies `CI/CD linter` creates no `.agent.md` files when current manifest proof exists. The named test verifies `CI/CD linter` accepts current manifest proof; both use happy path, but exercise materially different scenarios.
        - Scenario Difference: `test_cicd_validation_workflow.py::test_outdated_version_remains_valid`
          Explanation: The current test verifies `CI/CD linter` creates no `.agent.md` files when current proof exists. The named test verifies `CI/CD linter` accepts proof created under an earlier version; both use happy path, but exercise materially different scenarios.
        - Scenario Difference: `test_review_documentation.py::test_github_actions_omits_packet_creation`
          Explanation: The current test verifies CI lint creates no packets. The named test verifies documentation excludes the packet-creation command from CI guidance; these scenarios distinguish the two contracts.
        - Module Difference: `test_pre_commit_review_workflow.py::test_current_manifest_generates_zero_packets`
          Explanation: The current test verifies CI lint creates no review packets. The named test verifies ordinary generation creates no packets for current proof; both exercise materially the same scenario through different named modules or contract subjects.
        - Scenario Difference: `test_pre_commit_review_workflow.py::test_lint_ignores_obsolete_pending_packets`
          Explanation: The current test verifies CI lint creates no review packets. The named test verifies lint ignores obsolete pending packets when manifest proof is current; both use happy path, but exercise materially different scenarios.
        - Scenario Difference: `test_pre_commit_review_workflow.py::test_refresh_scenario`
          Explanation: The current test verifies CI lint creates no review packets. The named test verifies fresh generation recreates every individual and relationship packet; both use happy path, but exercise materially different scenarios.
        - Scenario Difference: `test_pre_commit_review_workflow.py::test_repeated_generation_preserves_manifest`
          Explanation: The current test verifies CI lint creates no review packets. The named test verifies repeated ordinary generation preserves manifest bytes; both use happy path, but exercise materially different scenarios.
        - Happy/Failure Path Difference: `test_pre_commit_review_workflow.py::test_stale_test_requires_review`
          Explanation: The current test verifies CI lint creates no review packets. The named test verifies an edited test creates only its packet and related relationship rows; the current test is happy path, while the named test is failure path.
        - Scenario Difference: `test_agent_review_examples.py::test_current_jsonl_attestation_skips_evaluation`
          Explanation: The current test verifies CI writes no review packets when the manifest already proves the tests; the named test verifies matching YAML-case proof bypasses evaluation and produces no pending packet paths.
        """

        test_source = textwrap.dedent(
            '''\
            """Tests in this file validate `approved behavior` located at `src/approved.py`.
            `approved behavior` is responsible for evaluating an approved boolean expression.
            """

            def test_approved_packet_behavior() -> None:
                """Test Path: happy path

                Requirement Tested:
                `approved behavior` evaluates to true.
                Standard usage: The scenario demonstrates baseline behavior.

                Verification Method: verify public function output

                Verification Detail:
                The expression equals true.
                """

                assert True
            '''
        )

        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            _write_source(repo_root / "src" / "approved.py", "VALUE = True\n")
            _write_source(repo_root / "tests" / "test_approved.py", test_source)
            _record_approved_manifest(
                repo_root,
                review_status="pass",
                review_evidence="approved packetless CI fixture",
            )
            _remove_packet_directory(repo_root)

            _run_cli(
                repo_root,
                "lint",
            )
            packets = _packet_paths(repo_root)

        self.assertEqual([], packets)


if __name__ == "__main__":
    unittest.main()
