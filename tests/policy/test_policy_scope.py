"""Tests in this file validate `policy scope` located at `src/agentic_devkit/policies/policy_scope.py`.
`policy scope` is responsible for validating review folders and hashing their indexed files using current working-tree content.

Shared setup: _fixture creates a Git repository with indexed source and data-type files plus configured review folders. _git runs Git in that repository. Tests supply the file changes, links, and scope configurations relevant to their scenarios.
"""

from __future__ import annotations

import json
import unittest
from agentic_devkit.policies.policy_scope import hash_policy_scope
from tests.policy.test_harness.fixtures import _fixture, _git

class PolicyTests(unittest.TestCase):
    def test_hashes_only_git_index_files(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy scope` ignores new files until they are added to Git.
        New source files and skill files affect the code fingerprint only after they are staged.

        Verification Method: verify public function output

        Verification Detail:
        The policy check ignores files that Git ignores and new files that Git has not staged. The policy check notices each new code or skill file after Git stages it.

        Similar Coverage:
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_replaces_stale_data_type_digest`
          Explanation: This test ignores new files until Git stages them; the named test saves updated fingerprints after a tracked data-type file changes.
        - Happy/Failure Path Difference: `test_cli.py::test_explains_required_policy_reviews`
          Explanation: This test establishes which source files affect the digest. The named test emits the recovery diagnostic after the CLI detects a tracked-source change.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_clears_data_type_attestations`
          Explanation: This test establishes which source files affect the digest. The named test clears field-policy attestations after a data-type change.
        - Happy/Failure Path Difference: `test_cli.py::test_excludes_roots_from_cli_instructions`
          Explanation: This test establishes which source files affect the digest. The named test excludes root policy paths from CLI remediation output.
        - Scenario Difference: `test_policy_scope.py::test_hashes_newly_added_root`
          Explanation: This test ignores new files until Git stages them; the named test includes files after their folder is added to review scope.
        - Scenario Difference: `test_policy_scope.py::test_hashes_configured_folders_only`
          Explanation: This test ignores new files until Git stages them; the named test excludes file changes outside configured review folders.
        - Scenario Difference: `test_policy_scope.py::test_hashes_symlinked_scope_folders`
          Explanation: This test ignores new files until Git stages them; the named test hashes tracked files through linked folders.
        - Scenario Difference: `test_policy_scope.py::test_detects_retargeted_scope_link`
          Explanation: This test ignores new files until Git stages them; the named test changes the fingerprint when a reviewed link changes targets.
        """
        root = _fixture(self)
        initial = hash_policy_scope(root)
        (root / ".gitignore").write_text(".DS_Store\n")
        (root / "src/.DS_Store").write_text("local metadata\n")
        self.assertEqual(initial, hash_policy_scope(root))
        (root / "src/new-source.ts").write_text("export const added = true;\n")
        self.assertEqual(initial, hash_policy_scope(root))
        _git(root, "add", "src/new-source.ts")
        self.assertNotEqual(initial, hash_policy_scope(root))
        source_digest = hash_policy_scope(root)
        (root / "actions/technical-skills/example/SKILL.md").write_text("# Example skill\n")
        self.assertEqual(source_digest, hash_policy_scope(root))
        _git(root, "add", "actions/technical-skills/example/SKILL.md")
        self.assertNotEqual(source_digest, hash_policy_scope(root))


class ConfiguredScopeTests(unittest.TestCase):
    def test_hashes_newly_added_root(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy scope` includes files when their folder is added to the review list.
        Changes in that folder start affecting the code fingerprint once it is included.

        Verification Method: verify public function output

        Verification Detail:
        Changes outside scope preserve the digest; adding the root and later editing its indexed file each change the digest.

        Similar Coverage:
        - Scenario Difference: `test_policy_scope.py::test_hashes_only_git_index_files`
          Explanation: This test includes files after their folder is added to review scope; the named test ignores new files until Git stages them.
        - Scenario Difference: `test_policy_scope.py::test_hashes_configured_folders_only`
          Explanation: This test includes files after their folder is added to review scope; the named test excludes file changes outside configured review folders.
        - Scenario Difference: `test_policy_scope.py::test_hashes_symlinked_scope_folders`
          Explanation: This test includes files after their folder is added to review scope; the named test hashes tracked files through linked folders.
        - Scenario Difference: `test_policy_scope.py::test_detects_retargeted_scope_link`
          Explanation: This test includes files after their folder is added to review scope; the named test changes the fingerprint when a reviewed link changes targets.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_replaces_stale_data_type_digest`
          Explanation: This test includes files after their folder is added to review scope; the named test saves updated fingerprints after a tracked data-type file changes.
        """
        root = _fixture(self)
        (root / "app").mkdir()
        source = root / "app/main.py"
        source.write_text("length_m = 1\n")
        _git(root, "add", "app")
        before = hash_policy_scope(root)
        source.write_text("length_m = 2\n")
        self.assertEqual(before, hash_policy_scope(root))

        config = root / "policy/policy-scope-digest.json"
        document = json.loads(config.read_text())
        document["digests"].append({"root_folder": "app"})
        config.write_text(json.dumps(document))
        expanded = hash_policy_scope(root)
        self.assertNotEqual(before, expanded)

        source.write_text("length_m = 3\n")
        self.assertNotEqual(expanded, hash_policy_scope(root))

    def test_hashes_configured_folders_only(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy scope` detects changes only in folders selected for review.
        Specialized usage: A project selects app, so changes under src do not affect its code fingerprint.

        Verification Method: verify public function output

        Verification Detail:
        Changes outside app preserve the digest; changes to indexed app content change it.

        Similar Coverage:
        - Scenario Difference: `test_policy_scope.py::test_hashes_only_git_index_files`
          Explanation: This test excludes file changes outside configured review folders; the named test ignores new files until Git stages them.
        - Scenario Difference: `test_policy_scope.py::test_hashes_newly_added_root`
          Explanation: This test excludes file changes outside configured review folders; the named test includes files after their folder is added to review scope.
        - Scenario Difference: `test_policy_scope.py::test_hashes_symlinked_scope_folders`
          Explanation: This test excludes file changes outside configured review folders; the named test hashes tracked files through linked folders.
        - Scenario Difference: `test_policy_scope.py::test_detects_retargeted_scope_link`
          Explanation: This test excludes file changes outside configured review folders; the named test changes the fingerprint when a reviewed link changes targets.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_replaces_stale_data_type_digest`
          Explanation: This test excludes file changes outside configured review folders; the named test saves updated fingerprints after a tracked data-type file changes.
        """
        root = _fixture(self)
        (root / "app").mkdir()
        source = root / "app/main.py"
        source.write_text("length_m = 1\n")
        (root / "policy/policy-scope-digest.json").write_text(json.dumps({"digests": [{"root_folder": "app"}]}))
        _git(root, "add", "app")
        before = hash_policy_scope(root)
        (root / "src/example.ts").write_text("excluded change\n")
        self.assertEqual(before, hash_policy_scope(root))
        source.write_text("length_m = 2\n")
        self.assertNotEqual(before, hash_policy_scope(root))

    def test_requires_scope_configuration(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy scope` requires a file listing the folders to review.
        When that file is missing, the error tells the developer to create it.

        Verification Method: verify public function output

        Verification Detail:
        The error instructs the developer to create policy/policy-scope-digest.json.

        Similar Coverage:
        - Scenario Difference: `test_policy_scope.py::test_rejects_invalid_scope_configuration`
          Explanation: This test reports a missing scope file with creation instructions; the named test rejects malformed scope settings.
        """
        root = _fixture(self)
        (root / "policy/policy-scope-digest.json").unlink()
        with self.assertRaisesRegex(ValueError, "Create policy/policy-scope-digest.json"):
            hash_policy_scope(root)

    def test_rejects_invalid_scope_configuration(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy scope` rejects an invalid review configuration.
        Examples include broken JSON, repeated folders, missing folders, and paths outside the project.

        Verification Method: verify public function output

        Verification Detail:
        Invalid JSON, schemas, scope lists, and repository-relative paths each raise ValueError.

        Similar Coverage:
        - Scenario Difference: `test_policy_scope.py::test_requires_scope_configuration`
          Explanation: This test rejects malformed scope settings; the named test reports a missing scope file with creation instructions.
        """
        root = _fixture(self)
        (root / "outside-link").symlink_to(root.parent, target_is_directory=True)
        documents = ["{", "[]", '{}', '{"digests": "src"}', '{"digests": []}']
        for scope in ([None], [1], [""], ["../src"], [str(root / "src")],
                      ["src/../src"], [".git"], ["missing"], ["src/example.ts"],
                      ["src", "src"], ["src/"], ["src\\nested"], ["outside-link"]):
            documents.append(json.dumps({"digests": [{"root_folder": name} for name in scope]}))
        for document in documents:
            with self.subTest(config=document):
                (root / "policy/policy-scope-digest.json").write_text(document)
                with self.assertRaises(ValueError):  # Input check
                    hash_policy_scope(root)

    def test_hashes_symlinked_scope_folders(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy scope` detects changes to tracked files in linked review folders.
        Both a linked folder and a subfolder reached through it are supported.

        Verification Method: verify public function output

        Verification Detail:
        Each linked scope produces a fingerprint that changes when a tracked file in the target folder changes.

        Similar Coverage:
        - Scenario Difference: `test_policy_scope.py::test_hashes_only_git_index_files`
          Explanation: This test hashes tracked files through linked folders; the named test ignores new files until Git stages them.
        - Scenario Difference: `test_policy_scope.py::test_hashes_newly_added_root`
          Explanation: This test hashes tracked files through linked folders; the named test includes files after their folder is added to review scope.
        - Scenario Difference: `test_policy_scope.py::test_hashes_configured_folders_only`
          Explanation: This test hashes tracked files through linked folders; the named test excludes file changes outside configured review folders.
        - Scenario Difference: `test_policy_scope.py::test_detects_retargeted_scope_link`
          Explanation: This test hashes tracked files through linked folders; the named test changes the fingerprint when a reviewed link changes targets.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_replaces_stale_data_type_digest`
          Explanation: This test hashes tracked files through linked folders; the named test saves updated fingerprints after a tracked data-type file changes.
        """
        for folder in ("linked", "linked/data-types"):
            with self.subTest(scope=folder):
                root = _fixture(self)
                (root / "linked").symlink_to(root / "actions", target_is_directory=True)
                _git(root, "add", "linked")
                (root / "policy/policy-scope-digest.json").write_text(
                    json.dumps({"digests": [{"root_folder": folder}]}))
                target = root / "actions/data-types/example.ts"
                target.write_text("export type Example = string;\n")
                _git(root, "add", "actions/data-types/example.ts")
                before = hash_policy_scope(root)
                target.write_text("export type Example = number;\n")
                self.assertNotEqual(before, hash_policy_scope(root))

    def test_detects_retargeted_scope_link(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy scope` detects when a reviewed link points to a different folder.
        Redirecting the link changes the review scope even when both folders are empty.

        Verification Method: verify public function output

        Verification Detail:
        Switching the link between two empty project folders changes the fingerprint.

        Similar Coverage:
        - Scenario Difference: `test_policy_scope.py::test_hashes_only_git_index_files`
          Explanation: This test changes the fingerprint when a reviewed link changes targets; the named test ignores new files until Git stages them.
        - Scenario Difference: `test_policy_scope.py::test_hashes_newly_added_root`
          Explanation: This test changes the fingerprint when a reviewed link changes targets; the named test includes files after their folder is added to review scope.
        - Scenario Difference: `test_policy_scope.py::test_hashes_configured_folders_only`
          Explanation: This test changes the fingerprint when a reviewed link changes targets; the named test excludes file changes outside configured review folders.
        - Scenario Difference: `test_policy_scope.py::test_hashes_symlinked_scope_folders`
          Explanation: This test changes the fingerprint when a reviewed link changes targets; the named test hashes tracked files through linked folders.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_replaces_stale_data_type_digest`
          Explanation: This test changes the fingerprint when a reviewed link changes targets; the named test saves updated fingerprints after a tracked data-type file changes.
        """
        root = _fixture(self)
        (root / "first").mkdir()
        (root / "second").mkdir()
        link = root / "linked"
        link.symlink_to(root / "first", target_is_directory=True)
        (root / "policy/policy-scope-digest.json").write_text(
            json.dumps({"digests": [{"root_folder": "linked"}]}))
        before = hash_policy_scope(root)
        link.unlink()
        link.symlink_to(root / "second", target_is_directory=True)
        self.assertNotEqual(before, hash_policy_scope(root))


if __name__ == "__main__":
    unittest.main()
