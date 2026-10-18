"""Tests in this file validate `policy document renderer` located at `src/agentic_devkit/policies/render_policy_documents.py`.
`policy document renderer` is responsible for generation, strict body checking, and regeneration with empty attestations.
"""

from __future__ import annotations

import json
import unittest
from agentic_devkit.policies.render_policy_documents import render_policy_documents
from tests.policy.test_harness.fixtures import _renderer_fixture, _run_cli, TEMPLATE

class PolicyTests(unittest.TestCase):
    def test_all_expands_configured_roots(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy document renderer` lists every configured root when a policy applies to all folders.
        Adding another root also adds it to that policy on the next render.

        Verification Method: verify public function output

        Verification Detail:
        The applicable-folder section lists every configured root and incorporates a newly added root.
        """
        root = _renderer_fixture(self)
        (root / "app").mkdir()
        config = root / "policy/policy-scope-digest.json"
        config.write_text(json.dumps({"digests": [{"root_folder": folder} for folder in ("app", "src")]}))
        source = root / "policy/user-interface/back-navigation.policy.yaml"
        source.write_text(source.read_text() + "applicable_folders: all\n")
        (root / "policy/policy-template.md.j2").unlink()
        render_policy_documents(root=root)
        output = root / "policy/user-interface/back-navigation.md"
        section = output.read_text().split("## Applicable folders\n", 1)[1].split("## Instructions", 1)[0]
        self.assertEqual(["- `app/`", "- `src/`"], section.strip().splitlines())
        (root / "lib").mkdir()
        document = json.loads(config.read_text())
        document["digests"].append({"root_folder": "lib", "digest": None})
        config.write_text(json.dumps(document))
        render_policy_documents(root=root)
        section = output.read_text().split("## Applicable folders\n", 1)[1].split("## Instructions", 1)[0]
        self.assertEqual(["- `app/`", "- `lib/`", "- `src/`"], section.strip().splitlines())

    def test_renders_policy_specific_folders(self) -> None:
    def test_rejects_invalid_applicable_folders(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy document renderer` rejects invalid folder selections in a policy.
        Examples include repeated folders, missing folders, and folders outside the configured roots.

        Verification Method: verify public function output

        Verification Detail:
        Each invalid selection raises ValueError without generating the policy document.
        """
        root = _renderer_fixture(self)
        (root / "outside").mkdir()
        source = root / "policy/user-interface/back-navigation.policy.yaml"
        original = source.read_text()
        selections = (None, "everything", [], [1], ["../src"], [str(root / "src")],
                      ["outside"], ["src/missing"], ["src/example.ts"], ["src", "src"])
        for folders in selections:
            with self.subTest(folders=folders):
                source.write_text(original + "applicable_folders: " + json.dumps(folders) + "\n")
                with self.assertRaisesRegex(ValueError, "applicable"):
                    render_policy_documents(root=root)
                self.assertFalse((root / "policy/user-interface/back-navigation.md").exists())

