# GitHub Actions

Use either workflow below, or both, alongside your existing test and coverage
checks. Install the tool in CI; complete agent reviews locally before pushing.

## TDD linting

Add TDD linting to your project's CI to check committed tests and manifest proof.
GitHub Actions verifies committed agent-review proof. See the
[TDD guide](../tdd/README.md#local-review) for the local review workflow.

Create `.github/workflows/agentic-tdd-linter.yml`:

```yaml
name: Agentic TDD Linter

on:
  pull_request:

jobs:
  lint-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uvx --from "git+https://github.com/WinetraubLab/agentic-devkit" agentic-devkit tdd lint
```

The command checks that every test has passing review proof matching its current
content. The default test directory is `tests/`; append `--test-root <directory>`
if yours differs. Use `--manifest <path>` in both local and CI commands if you
store the manifest elsewhere.

Commit your tests and `tests/agentic_review_manifest.jsonl`. Local `.agent.md`
review packets are not required in CI. Unchanged tests retain their reviews when
you update the linter or review rules.

If the check fails, run `$run-tdd-linter` locally, resolve the reported issues,
and commit the updated tests and manifest. CI does not perform reviews or
generate review packets.

## Policy verification

Add policy verification to check that your policy attestations match the reviewed
code and that reported violations do not exceed the baseline. First
[set up policy reviews](../policies/README.md#set-up-policy-reviews-to-your-project).

Create `.github/workflows/agentic-policy.yml`:

```yaml
name: Agentic Policy Verification

on:
  pull_request:

jobs:
  verify-policies:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@v5
      - run: uvx --from "git+https://github.com/WinetraubLab/agentic-devkit" agentic-devkit policy verify
```

Full Git history makes the pull request's base revision available for comparing
finding allowances. The verifier automatically uses that revision. Set
`POLICY_BASE_REVISION` to use another baseline.

The command checks reviewed root folders and digests, generated policy bodies,
and completed attestations. Commit your policy YAML, generated Markdown with
completed attestations, and `policy/policy-scope-digest.json` with your code changes.

If the check fails, run `$review-policy-attestations` locally, complete the
required reviews, and commit the updated results. CI verifies the saved results;
it does not perform the agent's compliance review.
