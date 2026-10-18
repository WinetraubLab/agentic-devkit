"""Tests in this file validate `policy document renderer` located at `src/agentic_devkit/policies/render_policy_documents.py`.
`policy document renderer` is responsible for generation, strict body checking, and regeneration with empty attestations.

Shared setup: _renderer_fixture creates an unrendered YAML policy, a source folder, and configured review roots. policy_source supplies the YAML when a test needs specific content. _complete writes the supplied finding list, or NONE for an empty list.
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

        Similar Coverage:
        - Scenario Difference: `test_render_policy_documents.py::test_renders_policy_specific_folders`
          Explanation: This test expands all to every configured root; the named test restricts recursive review to one selected subfolder.
        - Scenario Difference: `test_render_policy_documents.py::test_renders_linked_applicable_folders`
          Explanation: This test expands all to every configured root; the named test lists a linked folder for recursive review.
        - Happy/Failure Path Difference: `test_render_policy_documents.py::test_rejects_invalid_policy_fields`
          Explanation: This test expands all to every configured root; the named test rejects invalid YAML field values.
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
        `policy document renderer` limits the review to selected folders and all their subfolders.
        A policy names src/vehicles, which contains nested folders.

        Verification Method: verify public function output

        Verification Detail:
        The Markdown lists src/vehicles and explicitly includes all subfolders in the review instructions, while omitting other configured roots.

        Similar Coverage:
        - Scenario Difference: `test_render_policy_documents.py::test_all_expands_configured_roots`
          Explanation: This test restricts recursive review to one selected subfolder; the named test expands all to every configured root.
        - Scenario Difference: `test_render_policy_documents.py::test_renders_linked_applicable_folders`
          Explanation: This test restricts recursive review to one selected subfolder; the named test lists a linked folder for recursive review.
        - Happy/Failure Path Difference: `test_render_policy_documents.py::test_rejects_invalid_policy_fields`
          Explanation: This test restricts recursive review to one selected subfolder; the named test rejects invalid YAML field values.
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
        `policy document renderer` lists linked applicable folders as the scope of recursive review.
        A policy names a linked folder whose target is inside the configured review roots.

        Verification Method: verify public function output

        Verification Detail:
        The document lists the linked path and instructs the agent to review it and all subfolders.

        Similar Coverage:
        - Scenario Difference: `test_render_policy_documents.py::test_all_expands_configured_roots`
          Explanation: This test lists a linked folder for recursive review; the named test expands all to every configured root.
        - Scenario Difference: `test_render_policy_documents.py::test_renders_policy_specific_folders`
          Explanation: This test lists a linked folder for recursive review; the named test restricts recursive review to one selected subfolder.
        - Happy/Failure Path Difference: `test_render_policy_documents.py::test_rejects_invalid_policy_fields`
          Explanation: This test lists a linked folder for recursive review; the named test rejects invalid YAML field values.
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

        Similar Coverage:
        - Happy/Failure Path Difference: `test_render_policy_documents.py::test_all_expands_configured_roots`
          Explanation: This test rejects invalid YAML field values; the named test expands all to every configured root.
        - Happy/Failure Path Difference: `test_render_policy_documents.py::test_renders_policy_specific_folders`
          Explanation: This test rejects invalid YAML field values; the named test restricts recursive review to one selected subfolder.
        - Happy/Failure Path Difference: `test_render_policy_documents.py::test_renders_linked_applicable_folders`
          Explanation: This test rejects invalid YAML field values; the named test lists a linked folder for recursive review.
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
                with self.assertRaises(ValueError):  # Input check
                    render_policy_documents(root=root)
                self.assertFalse((root / "policy/user-interface/back-navigation.md").exists())  # Input check

    def test_renders_policy_document(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy document renderer` generates policy documents from YAML using the provided Jinja template.
        Project files with template-like names do not replace the provided template.

        Verification Method: verify public function output

        Verification Detail:
        The document contains the YAML content, shared review instructions, and an empty review section despite unrelated project templates.

        Similar Coverage:
        - Scenario Difference: `test_render_policy_documents.py::test_resets_editable_attestation`
          Explanation: This test creates a document from YAML using the provided template; the named test clears the review after YAML changes while retaining exemptions.
        - Scenario Difference: `test_cli.py::test_render_resets_attestations_and_digest`
          Explanation: This test creates a document from YAML using the provided template; the named test clears completed reviews through the render command.
        - Scenario Difference: `test_policy_structure.py::test_enforces_policy_template_structure`
          Explanation: This test creates a document from YAML using the provided template; the named test verifies the shared policy document sections.
        """
        root = _renderer_fixture(self, policy_source=(
            "title: Back navigation policy\n"
            "objective: Keep navigation safe.\n"
            "policy_content: Use the shared back hook.\n"
        ))
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
        `policy document renderer` starts a fresh review after policy changes while retaining accepted exemptions.
        A policy change needs a fresh review while its accepted exceptions remain in place.

        Verification Method: verify public function output

        Verification Detail:
        Regeneration updates policy text, keeps accepted exceptions and their instructions, clears the review results.

        Similar Coverage:
        - Scenario Difference: `test_render_policy_documents.py::test_renders_policy_document`
          Explanation: This test clears the review after YAML changes while retaining exemptions; the named test creates a document from YAML using the provided template.
        - Happy/Failure Path Difference: `test_cli.py::test_reports_missing_policy_documents`
          Explanation: This test verifies that successful regeneration replaces an existing completed attestation with an empty attestation after the YAML source changes; the named test instead verifies that the failure-path verifier CLI instructs the caller to regenerate a missing policy document with empty attestations.
        - Scenario Difference: `test_cli.py::test_render_resets_attestations_and_digest`
          Explanation: This test clears the review after YAML changes while retaining exemptions; the named test clears completed reviews through the render command.
        - Scenario Difference: `test_cli.py::test_document_check_preserves_review_results`
          Explanation: This test clears the review after YAML changes while retaining exemptions; the named test preserves recorded findings during document checks.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_scope_changes_reset_attestations`
          Explanation: This test clears the review after YAML changes while retaining exemptions; the named test resets reviews after a root is added.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_removing_root_resets_attestations`
          Explanation: This test clears the review after YAML changes while retaining exemptions; the named test resets reviews after a root is removed.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_clears_data_type_attestations`
          Explanation: This test clears the review after YAML changes while retaining exemptions; the named test resets reviews after a tracked data-type file changes.
        """
        root = _renderer_fixture(self)
        source = root / "policy/user-interface/back-navigation.policy.yaml"
        exemption = "src/example.ts may retain its custom back handler until the navigation migration."
        source.write_text(source.read_text() + "exemptions: " + json.dumps(exemption) + "\n")
        render_policy_documents(root=root)
        output = root / "policy/user-interface/back-navigation.md"
        _complete(output, [])
        updated_source = source.read_text().replace("Keep navigation safe.", "Keep navigation consistent.")
        source.write_text(updated_source)
        render_policy_documents(root=root)
        regenerated = output.read_text()
        self.assertIn("Keep navigation consistent.", regenerated)
        self.assertIn("## Accepted exemptions", regenerated)
        self.assertIn(exemption, regenerated)
        self.assertLess(regenerated.index("## Accepted exemptions"), regenerated.index("# Attestation"))
        self.assertIn("Continue reviewing for other violations.", regenerated)
        self.assertTrue(regenerated.endswith("Noncompliant Files:\n"))
        self.assertNotIn("Noncompliant Files: NONE", regenerated.split("# Attestation", 1)[1])

    def test_rejects_manual_body_edits(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy document renderer` rejects policy text or accepted exceptions changed directly in generated Markdown.
        A developer edits the generated document instead of its YAML source.

        Verification Method: verify public function output

        Verification Detail:
        Editing either a policy rule or an accepted exception in Markdown raises an error requesting regeneration from YAML.

        Similar Coverage:
        - Scenario Difference: `test_cli.py::test_reports_missing_policy_documents`
          Explanation: This test rejects direct edits to generated policy text; the named test reports missing policy documents with generation instructions.
        - Happy/Failure Path Difference: `test_cli.py::test_document_check_preserves_review_results`
          Explanation: This test rejects direct edits to generated policy text; the named test preserves recorded findings during document checks.
        """
        edits = (
            ("Use the shared back hook.", "Use a custom back function."),
            ("Custom handler.", "All violations."),
        )
        for original, replacement in edits:
            with self.subTest(edited_text=original):
                root = _renderer_fixture(self)
                source = root / "policy/user-interface/back-navigation.policy.yaml"
                source.write_text(source.read_text() + (
                    "exemptions: |\n"
                    "  Custom handler. Retained in src/example.ts for the legacy API.\n"
                ))
                render_policy_documents(root=root)
                output = root / "policy/user-interface/back-navigation.md"
                before = output.read_text()
                self.assertIn(original, before)  # Input check
                output.write_text(before.replace(original, replacement))
                with self.assertRaisesRegex(ValueError, "Run agentic-devkit policy render to regenerate them with empty attestations"):
                    render_policy_documents(root=root, check=True)


if __name__ == "__main__":
    unittest.main()
