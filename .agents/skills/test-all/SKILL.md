---
name: test-all
description: Use when the user wants to validate the repository before committing or releasing, or asks to test all, run all checks, or run all validation skills.
---

# Test All

Announce that you are using `$test-all` and run the validation workflows below
from the repository root. Preserve unrelated and concurrent changes. This skill
orchestrates the existing review skills; follow their instructions rather than
replacing agent reviews with command execution alone.

## 1. Check whether YAML reviews are needed

Compare all YAML file paths and raw bytes in these folders against local `main`,
including added, deleted, and untracked YAML files:

1. `tests/agentic_linter/fixtures/single_test_review/`
2. `tests/agentic_linter/fixtures/test_relationship_review/`

If all YAML files match `main` byte-for-byte, skip YAML reviews and preserve
existing review artifacts and reports. If any YAML file differs, run
[run-all-yaml-reviews](../run-all-yaml-reviews/SKILL.md) twice: first in
single-test mode, then in test-relationship mode. Complete both modes in full.
If `main` is unavailable, report the comparison as blocked.
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

## 5. Report results

Report each stage as passed, failed, blocked, skipped, or not applicable, with
counts or a brief reason. Note changed files and unresolved issues.
