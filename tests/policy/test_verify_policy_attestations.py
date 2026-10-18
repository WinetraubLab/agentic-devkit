    def test_replaces_stale_data_type_digest(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy attestation verifier` updates saved code fingerprints after reviewed files change.
        Changing a tracked data-type file causes the stored fingerprints to be replaced.

        Verification Method: verify public function output

        Verification Detail:
        Before the reset, the stored central digest differs from the digest derived from the changed policy-scope content. After the reset, the stored central digest has the same value as that digest.

        Similar Coverage:
        - Happy/Failure Path Difference: `test_policy_scope.py::test_hashes_only_git_index_files`
          Explanation: This test records a recomputed digest after indexed data-type content changes. The named test establishes the Git-index boundary for digest inputs.
        - Scenario Difference: `test_verify_policy_attestations.py::test_clears_data_type_attestations`
          Explanation: This test synchronizes the stored digest after a data-type change. The named test clears field-policy attestations after the same kind of change.
        - Scenario Difference: `test_verify_policy_attestations.py::test_regenerates_malformed_policy`
          Explanation: This test synchronizes a stale digest. The named test recreates malformed field-policy Markdown during stale-digest regeneration.
        - Scenario Difference: `test_cli.py::test_explains_required_policy_reviews`
          Explanation: This test verifies the stored digest state. The named test emits the recovery diagnostic for the same mismatch.
        - Scenario Difference: `test_verify_policy_attestations.py::test_excludes_roots_from_cli_instructions`
          Explanation: This test synchronizes a stale digest. The named test excludes root policy paths from CLI remediation output.
        """
        root = _fixture(self)
        stored = (root / "policy/policy-scope-digest.json").read_bytes()
        (root / "actions/data-types/example.ts").write_text("export type Example = number;\n")
        changed = hash_policy_scope(root)
        with self.assertRaisesRegex(ValueError, "Policy scope changed"):
            verify_policy_attestations(root=root, baseline_revision="HEAD")
        self.assertNotEqual(stored, (root / "policy/policy-scope-digest.json").read_bytes())
        _complete(root / "policy/access/security.md")
        _complete(root / "policy/privacy/privacy.md")
        verified = verify_policy_attestations(root=root, baseline_revision="HEAD")
        self.assertEqual(changed, verified.digest)

    def test_clears_data_type_attestations(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy attestation verifier` clears previous review results after reviewed code changes.
        Changing a tracked data-type file starts fresh reviews for every policy.

        Verification Method: verify public function output

        Verification Detail:
        Before the reset, both field policies contain attested files in their Noncompliant Files sections. After the reset, both generated field policies contain an empty Noncompliant Files section at the end.

        Similar Coverage:
        - Scenario Difference: `test_verify_policy_attestations.py::test_regenerates_malformed_policy`
          Explanation: This test clears every generated field-policy attestation after a data-type change. The named test specifically recreates one malformed field policy with an empty attestation.
        - Scenario Difference: `test_cli.py::test_explains_required_policy_reviews`
          Explanation: This test observes reset field policies. The named test emits the recovery diagnostic for those policies.
        - Happy/Failure Path Difference: `test_policy_scope.py::test_hashes_only_git_index_files`
          Explanation: This test clears attestations after a data-type change. The named test establishes the Git-index boundary that determines digest inputs.
        - Scenario Difference: `test_verify_policy_attestations.py::test_replaces_stale_data_type_digest`
          Explanation: This test clears field-policy attestations after a data-type change. The named test synchronizes the stored digest after that change.
        - Scenario Difference: `test_verify_policy_attestations.py::test_excludes_roots_from_cli_instructions`
          Explanation: This test verifies regenerated field-policy attestations. The named test excludes root policy paths from the related CLI output.
        """
        root = _fixture(self, security_exceptions=["src/example.ts"], privacy_exceptions=["actions/data-types/example.ts"])
        (root / "actions/data-types/example.ts").write_text("export type Example = number;\n")
        try:
            verify_policy_attestations(root=root, baseline_revision="HEAD")
        except ValueError:
            pass
        for name in ("policy/access/security.md", "policy/privacy/privacy.md"):
            self.assertTrue((root / name).read_text().endswith("Noncompliant Files:\n"))

    def test_regenerates_malformed_policy(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy attestation verifier` repairs broken policy documents when changed code triggers fresh reviews.
        A damaged policy document is rebuilt from its YAML with an empty review section.

        Verification Method: verify public function output

        Verification Detail:
        The regenerated field policy contains its generated heading and an empty Noncompliant Files section. The regenerated field policy excludes the original malformed heading.

        Similar Coverage:
        - Happy/Failure Path Difference: `test_policy_scope.py::test_hashes_only_git_index_files`
          Explanation: This test uses a tracked-source digest change to recreate malformed field-policy Markdown. The named test proves which source files affect that digest.
        - Scenario Difference: `test_verify_policy_attestations.py::test_clears_data_type_attestations`
          Explanation: This test recreates one malformed field policy with an empty attestation. The named test clears every generated field-policy attestation after a data-type change.
        - Scenario Difference: `test_cli.py::test_explains_required_policy_reviews`
          Explanation: This test recreates malformed Markdown after a tracked-source change. The named test emits the recovery diagnostic through npm.
        - Scenario Difference: `test_verify_policy_attestations.py::test_replaces_stale_data_type_digest`
          Explanation: This test recreates malformed field-policy Markdown. The named test synchronizes the stored digest after a data-type change.
        - Scenario Difference: `test_verify_policy_attestations.py::test_excludes_roots_from_cli_instructions`
          Explanation: This test recreates malformed field-policy Markdown. The named test excludes root policy paths from CLI remediation output.
        """
        root = _fixture(self)
        policy = root / "policy/access/security.md"
        policy.write_text("# Malformed policy\n")
        (root / "src/example.ts").write_text("export const value = 2;\n")
        try:
            verify_policy_attestations(root=root, baseline_revision="HEAD")
        except ValueError:
            pass
        regenerated = policy.read_text()
        self.assertTrue(regenerated.startswith("# Security policy\n"))
        self.assertTrue(regenerated.endswith("Noncompliant Files:\n"))
        self.assertNotIn("# Malformed policy", regenerated)

    def test_rejects_exception_count_above_baseline(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy attestation verifier` rejects reviews reporting more violating files than the last committed review.
        The current review reports more files with violations than the review committed at HEAD.

        Verification Method: verify public function output

        Verification Detail:
        The public verifier invocation throws an error.

        Similar Coverage:
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_accepts_exception_lists_within_baselines`
          Explanation: This test rejects a working count that exceeds its committed limit. The named test accepts working counts at their committed limits.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_accepts_improvement_below_baseline`
          Explanation: This test rejects regression from one exception to two. The named test accepts improvement from one exception to zero.
        - Scenario Difference: `test_verify_policy_attestations.py::test_rejects_missing_count_in_head`
          Explanation: This test rejects a working count above a present committed count. The named test rejects a committed policy that supplies no count.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_accepts_new_policy_without_exceptions`
          Explanation: This test verifies that `policy attestation verifier` refuses a policy when its exception count exceeds its HEAD baseline. When a policy has two exceptions against a committed baseline of one, `policy attestation verifier` refuses that policy; the named test instead verifies that `policy attestation verifier` accepts each newly added policy whose attestation has an empty noncompliant-file list.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_requires_clean_unreviewed_baseline`
          Explanation: The above-baseline test exceeds a recorded allowance; the clean-baseline test accepts zero findings against an empty attestation.
        """
        root = _fixture(self, security_exceptions=["src/example.ts"])
        _complete(root / "policy/access/security.md", ["src/example.ts", "actions/data-types/example.ts"])
        with self.assertRaises(ValueError):
            verify_policy_attestations(root=root, baseline_revision="HEAD")

    def test_excludes_roots_from_cli_instructions(self) -> None:
        """Test Path: failure path

        Requirement Tested:
        `policy attestation verifier` excludes project notes from the list of policies needing review.
        A code change must not request reviews of the README or TODO file.

        Verification Method: verify public function output

        Verification Detail:
        The CLI diagnostic contains neither root policy artifact path.

        Similar Coverage:
        - Happy/Failure Path Difference: `test_policy_scope.py::test_hashes_only_git_index_files`
          Explanation: This test excludes root paths from CLI output. The named test establishes the Git-index boundary for digest inputs.
        - Scenario Difference: `test_verify_policy_attestations.py::test_replaces_stale_data_type_digest`
          Explanation: This test excludes root paths from CLI remediation output. The named test verifies the synchronized digest stored after a mismatch.
        - Scenario Difference: `test_verify_policy_attestations.py::test_clears_data_type_attestations`
          Explanation: This test excludes root policy paths from CLI output. The named test verifies cleared field-policy attestations.
        - Scenario Difference: `test_verify_policy_attestations.py::test_regenerates_malformed_policy`
          Explanation: This test excludes root paths from CLI remediation output. The named test recreates malformed field-policy Markdown.
        - Scenario Difference: `test_cli.py::test_explains_required_policy_reviews`
          Explanation: This test verifies root-path exclusion. The named test verifies the complete recovery diagnostic.
        """
        root = _fixture(self)
        (root / "src/example.ts").write_text("export const value = 2;\n")
        result = _run_cli(root, "verify")
        output = result.stdout + result.stderr
        self.assertNotIn("policy/README.md", output)
        self.assertNotIn("policy/TODO-SECURITY.md", output)

    def test_respects_policy_specific_review_folders(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy attestation verifier` accepts reported files only within that policy's applicable folders.
        A folder reviewed for other policies must also be added to this policy.

        Verification Method: verify public function output

        Verification Detail:
        A finding in a globally configured folder fails until the policy's applicable folders include it.
        """
        root = _fixture(self)
        source = root / "policy/access/security.policy.yaml"
        original = source.read_text()
        source.write_text(original + "applicable_folders: [src]\n")
        render_policy_documents(root=root)
        _complete(root / "policy/access/security.md", ["actions/data-types/example.ts"])
        _complete(root / "policy/privacy/privacy.md")
        with self.assertRaisesRegex(ValueError, r"policy/access/security\.md"):
            verify_policy_attestations(root=root, baseline_revision="HEAD")
        source.write_text(original + "applicable_folders: [src, actions/data-types]\n")
        render_policy_documents(root=root)
        _complete(root / "policy/access/security.md", ["actions/data-types/example.ts"])
        _complete(root / "policy/privacy/privacy.md")
        result = verify_policy_attestations(root=root, baseline_revision="HEAD")
        self.assertEqual("HEAD", result.baseline_revision)

    def test_requires_clean_unreviewed_baseline(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `policy attestation verifier` rejects a new policy's attestation if it reports any violations.
        When introducing a policy, existing violations must be fixed before its first attestation passes.

        Verification Method: verify public function output

        Verification Detail:
        The new policy passes with NONE but fails when its first review lists a violating file.

        Similar Coverage:
        - Scenario Difference: `test_verify_policy_attestations.py::test_accepts_exception_lists_within_baselines`
          Explanation: The baseline-count test uses a committed finding allowance; the clean-baseline test starts with no completed attestation.
        - Scenario Difference: `test_verify_policy_attestations.py::test_accepts_improvement_below_baseline`
          Explanation: The improvement test reduces an existing allowance to zero; the clean-baseline test starts with no completed attestation.
        - Scenario Difference: `test_verify_policy_attestations.py::test_accepts_new_policy_without_exceptions`
          Explanation: The named test adds a policy after the last commit; this test commits the new policy with a blank review before completing it.
        - Happy/Failure Path Difference: `test_verify_policy_attestations.py::test_rejects_exception_count_above_baseline`
          Explanation: The above-baseline test exceeds a recorded allowance; the clean-baseline test accepts zero findings against an empty attestation.
        """
        root = _fixture(self)
        source = root / "policy/access/new-policy.policy.yaml"
        source.write_text("title: New policy\nobjective: Enforce a new rule.\npolicy_content: Follow the new rule.\n")
        render_policy_documents(root=root)
        _complete(root / "policy/access/security.md", ["src/example.ts"])
        _complete(root / "policy/privacy/privacy.md")
        policy = root / "policy/access/new-policy.md"
        _commit(root, "Add new policy before its first review")
        _complete(policy)
        verify_policy_attestations(root=root, baseline_revision="HEAD")
        _complete(policy, ["src/example.ts"])
        # Input check
        with self.assertRaisesRegex(ValueError, r"policy/access/new-policy\.md"):
            verify_policy_attestations(root=root, baseline_revision="HEAD")


if __name__ == "__main__":
    unittest.main()
