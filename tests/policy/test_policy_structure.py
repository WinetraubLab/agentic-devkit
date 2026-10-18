"""Tests in this file validate `policy template` located at `src/agentic_devkit/policies/policy-template.md.j2`.
`policy template` is responsible for the shared structure of generated field-policy documents.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest
from tests.policy.test_harness.fixtures import _fixture

class PolicyTests(unittest.TestCase):
    def test_enforces_policy_folder_layout(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy template` requires lowercase, hyphen-separated policy names and a YAML source for each Markdown policy.
        Standard usage: Related policies are grouped in named folders.

        Verification Method: verify public function output

        Verification Detail:
        Repository entries satisfy the root allowlist, field naming rules, policy naming rules, supported extensions, and YAML-source pairing.
        """
        root = _fixture(self)
        policy = root / "policy"
        allowed = {"README.md", "TODO-SECURITY.md", "policy-scope-digest.json"}
        kebab = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
        for entry in policy.iterdir():
            if entry.is_file():
                self.assertIn(entry.name, allowed)
                continue
            self.assertTrue(entry.is_dir())
            self.assertRegex(entry.name, kebab)
            for document in entry.iterdir():
                self.assertTrue(document.is_file())
                self.assertTrue(document.name.endswith((".md", ".policy.yaml")))
                name = document.name.removesuffix(".policy.yaml").removesuffix(".md")
                self.assertRegex(name, kebab)
                if document.suffix == ".md":
                    self.assertTrue(document.with_suffix(".policy.yaml").is_file())

    def test_enforces_policy_template_structure(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy template` includes policy text, review instructions, and one section for review results.
        Standard usage: Generated policies follow the shared document format.

        Verification Method: verify public function output

        Verification Detail:
        The provided template contains the policy fields and review instructions, followed by one attestation section without reviewer metadata.

        Similar Coverage:
        - Scenario Difference: `test_render_policy_documents.py::test_renders_policy_document`
          Explanation: This test verifies the shared policy document sections; the named test creates a document from YAML using the provided template.
        """
        root = _fixture(self)
        asset = Path(__file__).resolve().parents[2] / "src/agentic_devkit/policies/policy-template.md.j2"
        template = asset.read_text()
        for pattern in (r"^# \{\{ title \}\}", r"^## Objective$", r"^\{\{ objective \}\}$", r"^## Instructions$", r"^## Policy$", r"^\{\{ policy_content \}\}$", r"^# Attestation$", r"^Noncompliant Files:\s*$"):
            self.assertRegex(template, re.compile(pattern, re.MULTILINE))
        for pattern in (r"^Evidence:", r"^Reviewer:", r"^Decision:"):
            self.assertNotRegex(template, re.compile(pattern, re.MULTILINE))
        for path in (root / "policy").glob("*/*.md"):
            markdown = path.read_text()
            self.assertRegex(markdown, r"(?m)^# (?!Attestation\s*$).+")
            self.assertEqual(1, len(re.findall(r"^# Attestation[ \t]*$", markdown, re.MULTILINE)))
            self.assertRegex(markdown, r"(?m)^Noncompliant Files:(?: NONE)?$")
            self.assertNotRegex(markdown, r"(?m)^(?:Policy Scope Digest|Evidence|Reviewer|Decision):")


if __name__ == "__main__":
    unittest.main()
