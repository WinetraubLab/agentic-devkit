"""Tests in this file validate `policy document renderer` located at `src/agentic_devkit/policies/render_policy_documents.py`.
`policy document renderer` is responsible for generation, strict body checking, and regeneration with empty attestations.
"""

from __future__ import annotations

import json
import unittest
from agentic_devkit.policies.render_policy_documents import render_policy_documents
from tests.policy.test_harness.fixtures import _renderer_fixture, _complete

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

    def test_renders_linked_applicable_folders(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy document renderer` accepts applicable folders reached through symbolic links.
        A policy names a linked folder whose target is inside the configured review roots.

        Verification Method: verify public function output

        Verification Detail:
        The document lists the linked path and instructs the agent to review it and all subfolders.
        """
        root = _renderer_fixture(self)
        (root / "linked").symlink_to(root / "actions", target_is_directory=True)
        source = root / "policy/user-interface/back-navigation.policy.yaml"
        source.write_text(source.read_text() + "applicable_folders: [linked/data-types]\n")
        render_policy_documents(root=root)
        markdown = (root / "policy/user-interface/back-navigation.md").read_text()
        self.assertIn("- `linked/data-types/`", markdown)
        self.assertIn("Review every file under `linked/data-types/`, including all subfolders", markdown)

    def test_rejects_invalid_policy_fields(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy document renderer` rejects policy fields with invalid values.
        Bad folder selections or accepted exceptions written as numbers or lists prevent generation.

        Verification Method: verify public function output

        Verification Detail:
        Each invalid folder selection or non-text exemption raises ValueError without generating a policy document.
        """
        root = _renderer_fixture(self)
        (root / "outside").mkdir()
        source = root / "policy/user-interface/back-navigation.policy.yaml"
        original = source.read_text()
        selections = (None, "everything", [], [1], ["../src"], [str(root / "src")],
                      ["outside"], ["src/missing"], ["src/example.ts"], ["src", "src"])
        cases = [("applicable_folders", value) for value in selections]
        cases += [("exemptions", value) for value in (None, {}, [], ["src/example.ts"], 15, True)]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                source.write_text(original + field + ": " + json.dumps(value) + "\n")
                with self.assertRaises(ValueError):
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
        self.assertNotIn("## Accepted exemptions", markdown)

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

    def test_resets_editable_attestation(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy document renderer` clears old review results when generating a policy document again.
        A policy change needs a fresh review, even when the previous review reported no violations.

        Verification Method: verify public function output

        Verification Detail:
        The regenerated policy document contains changed policy text.
        The regenerated policy document contains an empty attestation.

        Similar Coverage:
        - Scenario Difference: `test_render_policy_documents.py::test_renders_policy_document`
          Explanation: This test verifies that `policy document renderer` replaces an existing attestation with an empty attestation during regeneration; the named test instead verifies that `policy document renderer` creates Markdown from a YAML policy source and the shared template.
        - Happy/Failure Path Difference: `test_cli.py::test_reports_missing_policy_documents`
          Explanation: This test verifies that successful regeneration replaces an existing completed attestation with an empty attestation after the YAML source changes; the named test instead verifies that the failure-path verifier CLI instructs the caller to regenerate a missing policy document with empty attestations.
        """
        root = _renderer_fixture(self)
        render_policy_documents(root=root)
        output = root / "policy/user-interface/back-navigation.md"
        _complete(output)
        source = root / "policy/user-interface/back-navigation.policy.yaml"
        source.write_text(source.read_text().replace("Keep navigation safe.", "Keep navigation consistent."))
        render_policy_documents(root=root)
        regenerated = output.read_text()
        self.assertIn("Keep navigation consistent.", regenerated)
        self.assertTrue(regenerated.endswith("Noncompliant Files:\n"))
        self.assertNotIn("Noncompliant Files: NONE", regenerated.split("# Attestation", 1)[1])

    def test_rejects_manual_body_edits(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy document renderer` rejects policy text changed directly in generated Markdown.
        A developer edits the generated policy instead of its YAML source.

        Verification Method: verify public function output

        Verification Detail:
        A changed generated sentence produces an error that instructs the caller to regenerate policy documents.

        Similar Coverage:
        - Scenario Difference: `test_cli.py::test_reports_missing_policy_documents`
          Explanation: This test verifies that `policy document renderer` rejects manual edits to generated policy content in check mode; the named test verifies that the policy verifier CLI rejects a missing generated document.
        """
        root = _renderer_fixture(self)
        render_policy_documents(root=root)
        output = root / "policy/user-interface/back-navigation.md"
        output.write_text(output.read_text().replace("Use the shared back hook.", "Use a custom back function."))
        with self.assertRaisesRegex(ValueError, "Run agentic-devkit policy render to regenerate them with empty attestations"):
            render_policy_documents(root=root, check=True)

if __name__ == "__main__":
    unittest.main()
