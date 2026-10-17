"""Tests in this file validate `policy CLI` located at `src/agentic_devkit/policies/cli.py`.
`policy CLI` is responsible for exposing policy operations through agentic-devkit.
"""

import json
import unittest

from tests.policy.test_harness.fixtures import _fixture, _run_cli, _complete


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
        `policy CLI` verifies attestations using the caller's baseline revision.
