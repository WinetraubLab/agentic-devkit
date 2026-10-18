"""Tests in this file validate `policy document renderer` located at `src/agentic_devkit/policies/render_policy_documents.py`.
`policy document renderer` is responsible for generation, strict body checking, and regeneration with empty attestations.
"""

from __future__ import annotations

import json
import unittest
from agentic_devkit.policies.render_policy_documents import render_policy_documents
from tests.policy.test_harness.fixtures import _renderer_fixture, _run_cli, _complete

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
        """Test Path: happy path

        Requirement Tested:
        `policy document renderer` tells the agent to review selected folders and all their subfolders.
        A policy names src/vehicles, which contains nested folders.

        Verification Method: verify public function output

        Verification Detail:
        The Markdown lists src/vehicles and explicitly includes all subfolders in the review instructions, while omitting other configured roots.
        """
        root = _renderer_fixture(self)
        (root / "src/vehicles/parts").mkdir(parents=True)
        source = root / "policy/user-interface/back-navigation.policy.yaml"
        source.write_text(source.read_text() + "applicable_folders:\n  - src/vehicles\n")
        render_policy_documents(root=root)
        markdown = (root / "policy/user-interface/back-navigation.md").read_text()
        section = markdown.split("## Applicable folders\n", 1)[1].split("## Instructions", 1)[0]
        self.assertEqual("- `src/vehicles/`", section.strip())
        self.assertIn("Review every file under `src/vehicles/`, including all subfolders", markdown)
        self.assertNotIn("actions/data-types", markdown)

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

    def test_renders_policy_document(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy document renderer` fills the provided Jinja template with policy content from YAML.
        Project files with template-like names do not replace the provided template.

        Verification Method: verify public function output

        Verification Detail:
        The document contains the YAML content, shared review instructions, and an empty review section despite unrelated project templates.

        Similar Coverage:
        - Scenario Difference: `test_render_policy_documents.py::test_resets_editable_attestation`
          Explanation: This test verifies that `policy document renderer` creates Markdown from a YAML policy source and the shared template; the named test instead verifies that `policy document renderer` replaces an existing attestation with an empty attestation during regeneration.
        """
        root = _renderer_fixture(self)
        (root / "policy/policy-template.md.j2").write_text("Unrelated project template")
        (root / "policy/policy-template.md.njk").write_text("Unrelated legacy template")
        render_policy_documents(root=root)
        markdown = (root / "policy/user-interface/back-navigation.md").read_text()
        self.assertTrue(markdown.startswith("# Back navigation policy\n"))
        self.assertIn("Keep navigation safe.", markdown)
        self.assertIn("Use the shared back hook.", markdown)
        self.assertIn("## Instructions\n", markdown)
        self.assertIn("including all subfolders", markdown)
        self.assertTrue(markdown.endswith("Noncompliant Files:\n"))

    def test_reports_changed_policy_document_path(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy document renderer` returns the path of each policy document it creates.
        Standard usage: Generating one document returns that document's path.

        Verification Method: verify public function output

        Verification Detail:
        The changed-path result contains exactly the generated policy-document path.
        """
        root = _renderer_fixture(self)
        result = render_policy_documents(root=root)
        self.assertEqual([root / "policy/user-interface/back-navigation.md"], result.changed_paths)

    def test_rejects_manual_body_edits(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy document renderer` rejects policy text changed directly in generated Markdown.
        A developer edits the generated policy instead of its YAML source.

        Verification Method: verify public function output

        Verification Detail:
        A changed generated sentence produces an error that instructs the caller to regenerate policy documents.

        Similar Coverage:
        - Scenario Difference: `test_render_policy_documents.py::test_detects_stale_policy`
          Explanation: This test verifies that `policy document renderer` rejects manual edits to generated policy content in check mode; the named test verifies that the policy verifier CLI rejects a missing generated document.
        - Scenario Difference: `test_render_policy_documents.py::test_preserves_manual_edits_during_checks`
          Explanation: This test verifies that check mode rejects manually edited generated content with a regeneration error; the named test instead verifies that the same rejected check leaves the manually edited document unchanged.
        - Scenario Difference: `test_render_policy_documents.py::test_reports_stale_policy_diagnostic`
          Explanation: This test verifies that renderer check mode rejects a manually edited generated document; the named test instead verifies that the verifier CLI reports a missing generated document with the stale-or-manually-edited diagnostic.
        - Scenario Difference: `test_render_policy_documents.py::test_recommends_policy_regeneration`
          Explanation: This test verifies that renderer check mode rejects a manually edited generated document and requests regeneration; the named test instead verifies that the verifier CLI gives the complete regeneration command and empty-attestation instruction when a generated document is missing.
        """
        root = _renderer_fixture(self)
        render_policy_documents(root=root)
        output = root / "policy/user-interface/back-navigation.md"
        output.write_text(output.read_text().replace("Use the shared back hook.", "Use a custom back function."))
        with self.assertRaisesRegex(ValueError, "Run agentic-devkit policy render to regenerate them with empty attestations"):
            render_policy_documents(root=root, check=True)

