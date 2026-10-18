---
name: test-all
description: Use when the user wants to validate the repository before committing or releasing, or asks to test all, run all checks, or run all validation skills.
---

# Test All

Announce that you are using `$test-all` and run the validation workflows below
from the repository root. Preserve unrelated and concurrent changes. This skill
orchestrates the existing review skills; follow their instructions rather than
replacing agent reviews with command execution alone.

## 1. Review all YAML examples

Use [run-all-yaml-reviews](../run-all-yaml-reviews/SKILL.md) twice:

1. Single-test reviews.
2. Test-relationship reviews.

Invoking `$test-all` requests both catalogs. Complete each catalog separately,
including its isolated reviews, expectation comparisons, and required reporting.
Do not change YAML expectations or review criteria to make comparisons pass.

## 2. Run TDD lint

Use [run-tdd-linter](../shared/run-tdd-linter/SKILL.md), including its correction
cycles, packet reviews, and final verification. Use its default inputs unless
the user supplies different values.

## 3. Review policies

If the repository has `policy/**/*.policy.yaml`, use
[review-policy-attestations](../shared/review-policy-attestations/SKILL.md).
Complete every required policy review, then verify the attestations again.
If the repository has no policy sources, report this stage as not applicable;
do not create policies just to run it. Policy tooling tests still run below.

## 4. Run all tests

Run the complete suite using the repository's virtual environment:

```bash
.venv/bin/python -m unittest discover -s tests
```

Use the configured project interpreter if the environment has a different path.
Include policy tests and YAML runner tests; do not silently exclude failing tests.
Record the test count and command exit status.

## 5. Confirm the final state

Continue independent stages after failures and collect their results. Follow each
child skill's limits on corrections; report unresolved failures without weakening
requirements or fabricating review proof.

If a later stage changes files reviewed earlier, rerun the affected tests and
refresh invalidated TDD or policy reviews using their skills. Repeat a YAML
catalog only when its fixtures, criteria, or runner implementation changed.
Do not repeat completed, unaffected reviews. If checks still fail after the child
skill's correction cycle, report the remaining failures instead of starting an
unbounded retry loop.

End with a table covering single-test YAML reviews, test-relationship YAML reviews,
TDD lint, policy attestations, and the full test suite. Mark each as passed,
failed, blocked, or not applicable, with counts or a concrete reason. Identify
changed files and unresolved issues. Claim overall success only when every
applicable check passes for the final working tree.
