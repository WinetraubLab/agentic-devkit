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
