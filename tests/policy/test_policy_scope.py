"""Tests in this file validate `policy scope` located at `src/agentic_devkit/policies/policy_scope.py`.
`policy scope` is responsible for hashing only indexed paths and their current working-tree content.
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
          Explanation: This test establishes the Git-index boundary for digest inputs. The named test records a recomputed digest after indexed data-type content changes.
        - Happy/Failure Path Difference: `test_cli.py::test_explains_required_policy_reviews`
          Explanation: This test establishes which source files affect the digest. The named test emits the recovery diagnostic after the CLI detects a tracked-source change.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_clears_data_type_attestations`
          Explanation: This test establishes which source files affect the digest. The named test clears field-policy attestations after a data-type change.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_excludes_roots_from_cli_instructions`
          Explanation: This test establishes which source files affect the digest. The named test excludes root policy paths from CLI remediation output.
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
        The public hash function raises an error naming policy/policy-scope-digest.json.
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
        """
        root = _fixture(self)
        documents = ["{", "[]", '{}', '{"digests": "src"}', '{"digests": []}']
        for scope in ([None], [1], [""], ["../src"], [str(root / "src")],
                      ["src/../src"], [".git"], ["missing"], ["src/example.ts"],
                      ["src", "src"], ["src/"], ["src\\nested"]):
            documents.append(json.dumps({"digests": [{"root_folder": name} for name in scope]}))
        for document in documents:
            with self.subTest(config=document):
                (root / "policy/policy-scope-digest.json").write_text(document)
                with self.assertRaises(ValueError):
                    hash_policy_scope(root)

