"""Tests in this file validate `policy template` located at `src/agentic_devkit/policies/policy-template.md.j2`.
`policy template` is responsible for the shared structure of generated field-policy documents.
"""

from __future__ import annotations

from pathlib import Path
import re
import unittest
from jinja2 import Environment, StrictUndefined

class PolicyTests(unittest.TestCase):

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
        asset = Path(__file__).resolve().parents[2] / "src/agentic_devkit/policies/policy-template.md.j2"
        template = Environment(undefined=StrictUndefined, autoescape=False).from_string(asset.read_text())
        markdown = template.render(
            title="Physical length naming", objective="Make physical units explicit.",
            policy_content="Use the _m suffix for lengths in meters.",
            applicable_folders=["src"], scope_directories=["src"], exemptions="",
        )
        sections = [
            "# Physical length naming", "## Objective", "Make physical units explicit.",
            "## Instructions", "## Policy", "Use the _m suffix for lengths in meters.",
            "# Attestation",
        ]
        positions = [markdown.index(section) for section in sections]
        self.assertEqual(sorted(positions), positions)
        self.assertEqual(1, len(re.findall(r"^# Attestation[ \t]*$", markdown, re.MULTILINE)))
        self.assertEqual("Noncompliant Files:", markdown.split("# Attestation", 1)[1].strip())


if __name__ == "__main__":
    unittest.main()
