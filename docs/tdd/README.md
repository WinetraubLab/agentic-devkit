# TDD linting

The TDD linting tool in `agentic-devkit` checks Python and TypeScript tests written during agent-assisted [test-driven development (TDD)](https://martinfowler.com/bliki/TestDrivenDevelopment.html).
It helps verify that tests written by coding agents are clear enough for humans to use when guiding implementation.

## Design Philosophy

Coding agents can generate implementation faster than humans can review it line by line. In agentic TDD, tests become the main review boundary: they define the intended behavior and constrain the generated code.
The TDD linter helps improve those tests before they become the specification. It does not replace human judgment, `pytest`, coverage tools, or code review.

## Development Pattern

The TDD linter supports an agentic TDD workflow built around the classic loop:

```text
Red -> Green -> Refactor
```

Follow this flow:

1. A human asks a coding agent to develop or modify a feature.
2. Red: test development, **with human review**.
   - The coding agent writes tests for the intended behavior.
   - The TDD linter checks whether the tests are understandable, focused, meaningful, connected to the change, and non-redundant.
   - The coding agent iterates on the tests until they are clear enough for human review.
   - The human reviews the tests as the primary specification of the intended behavior.
   - If the tests accurately capture the desired behavior, the human approves them.
3. Green: feature implementation, **without human review**.
   - The coding agent implements the feature until the approved tests pass.
   - The generated implementation is accepted based on the approved test suite, rather than line-by-line human review.
4. Refactor: implementation cleanup, **without human review**.
   - After the local project's full test suite passes, the coding agent invokes the installed `$simplify-implementation` skill to simplify its production and test-harness implementation while keeping the approved tests passing.
   - The refactored implementation is accepted based on the approved test suite.

Use the installed `$simplify-implementation` skill for the complete refactor-phase workflow in the local project.

The key assumption is that generated implementation code may be too large or complex for humans to review line by line. Instead, human review should focus on the tests, because the tests define the intended behavior. If the tests are clear, complete, and correct, then the generated implementation can be judged by whether it satisfies those tests.

## What It Checks

The TDD linter looks for tests that are:

- vague or hard to understand
- missing meaningful assertions
- missing required structured docstring fields
- using unsupported test path or verification method classifications
- mislabeled as private verification without calling a private function
- missing required visual inspection instructions or artifacts

The goal is to catch weak, vague, or bloated tests before they guide implementation.

## Set up TDD linting to your project

[Install the toolkit](../../README.md#installation) and the
[`run-tdd-linter` agent skill](../../README.md#agent-skills) in your project.

Keep your Python or TypeScript tests under `tests/`, for example
`tests/test_lengths.py` or `tests/lengths.test.ts`. Follow the
[Test Docstring Contract](#test-docstring-contract) when writing them. If your
tests live elsewhere, tell the agent which directory to use; the CLI supports
`--test-root <directory>`.

From your project root, ask your coding agent:

```text
Run the `$run-tdd-linter` skill.
```

A successful run leaves your tests with passing review proof in
`tests/agentic_review_manifest.jsonl`. Commit that manifest with your test changes.

## Add GitHub Actions

Follow the [GitHub Actions guide](../workflows/github-actions.md#tdd-linting) to check your
committed review proof on pull requests and pushes.

Each generated `.agent.md` file reviews one Python `test_...` function or TypeScript `test(...)` call. A source file with multiple tests produces one independent review artifact per test.

By default, both commands scan the test suite but process only tests without current passing manifest proof. Pass files or directories to limit the scope. Use `--fresh` to ignore previous review proof. For `create-agent-md`, this regenerates every packet in the selected scope, including the cross-test packet:

```bash
agentic-devkit tdd create-agent-md --fresh tests/test_example.py
agentic-devkit tdd lint --fresh tests/test_example.py
```

Without a path, `--fresh` applies to the complete test root. With a path, it refreshes
every test in that file or directory and rebuilds the cross-test packet from that
selected scope while leaving unrelated single-test packets alone. Without `--fresh`,
packet creation writes only the single-test packets that lack current passing proof.
It creates a cross-test packet only when at least one test is pending, and that packet
contains only relationships with a pending test on at least one side. Generated files
for selected tests that now have current proof are removed as obsolete.

Each single-test packet records the SHA256 of its extracted test content. Editing one
test therefore regenerates only that test's packet while preserving manifest proof for
other tests in the same file. Manifest proof records the linter version and review
contract as historical metadata. Reviews remain valid across linter-policy changes
and require renewal only when their reviewed test content changes.

## Install It On GitHub Actions On Your Project

Paste this prompt into your coding agent:

````text
Add `.github/workflows/agentic-tdd-linter.yml` to this project.

Use this workflow:

```yaml
name: Agentic TDD Linter

on:
  pull_request:
  push:

jobs:
  lint-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uvx --from "git+https://github.com/WinetraubLab/agentic-devkit" agentic-devkit tdd lint
```

Before committing, run `agentic-devkit tdd create-agent-md`, review any generated packets, and run `agentic-devkit tdd lint`. Commit the refreshed `tests/agentic_review_manifest.jsonl` with the test changes.
````

Full proof flow: [GitHub Actions Review Proof](../workflows/github-actions.md).

## Two Review Workflows

This project separates review creation from automated validation:

### Pre-commit review workflow

Contributors run this workflow before committing test changes:

1. Run `agentic-devkit tdd create-agent-md` to create `.agent.md` scorecards.
2. Complete every generated scorecard.
3. Run `lint` to record completed reviews in `tests/agentic_review_manifest.jsonl`.
4. Commit the updated tests and manifest.

This workflow creates `.agent.md` files and updates manifest proof.

### CI/CD validation workflow

CI/CD runs `agentic-devkit tdd lint` after the changes are committed. It validates
the committed tests and `tests/agentic_review_manifest.jsonl`. CI/CD does not create
`.agent.md` files, perform reviews, or record new manifest proof. Missing, stale,
failed, or version-incompatible proof causes CI/CD to fail and directs the contributor
to run the `$run-tdd-linter` skill.

## Test Docstring Contract

```text
Test naming:
Use at most five descriptive words. The Python `test_` prefix is not counted.

File docstring:
"""Tests in this file validate `parser` located at `src/parser.py`.
`parser` is responsible for converting text into structured values.

Terms:
- `manifest proof`: A stored agent-review result for one test source hash.
"""

Test Path: <exactly one of: happy path | failure path>

Requirement Tested:
<First sentence: state the general behavioral rule.>
<Second sentence: describe one concrete use case or scenario where the rule applies. Maximum 30 words across both sentences.>

Verification Method: <exactly one of: verify public function output | verify private function output | visual inspection by user>

Verification Detail:
<optional sentence explaining what the test checks; mention any mocking here>

Similar Coverage:
<optional list of related tests at higher or lower levels; put lower-level justification here>

Inspection Instructions:
<required for visual inspection tests; tell the user exactly what to verify in the image>
```

Instructions:
- Begin every test-file docstring with the exact module declaration and responsibility sentences shown above.
- Use a repository-relative path that identifies an existing module.
- Begin every first `Requirement Tested` sentence with the exact backticked module name declared by the file.
- Split tests into separate files when their requirements validate different modules.
- Put the corresponding file-level JSDoc before imports in a TypeScript `.test.ts` file.
- Use `happy path` when valid or supported inputs produce the expected successful result.
- Use `failure path` when invalid, unsafe, missing, or unsupported inputs are rejected with the expected error or guard behavior.
- Use `verify public function output` when the test calls a public function and asserts its returned output.
- Use `verify private function output` when the test calls a leading-underscore function and asserts its returned output, raised error, or state change.
- Use `visual inspection by user` when correctness is difficult to assert in code and the test writes a review artifact.
- Use the first `Requirement Tested` sentence to state what the system must do. Avoid generic wording such as `behaves as expected`.
- Use the second `Requirement Tested` sentence to state when, where, or for whom the rule applies.
- Define every backticked value used in `Requirement Tested` under the file docstring's `Terms:` section. Match the backticked spelling exactly.
- Use `Verification Detail` for the exact expected result or evidence.
- Use a separate `Similar Coverage` section for reciprocal higher/lower-level test references and lower-level justification.
- Keep the requirement, function inputs, and expected value close to the test body.
