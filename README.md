# agentic-devkit

Tools for developing your project with coding agents. Use TDD linting to review
Python and TypeScript tests, and policy tooling to review your code against your
project's rules.

## Installation

Requires Python 3.11 or newer and Git. Install in your project's Python environment:

```bash
python -m pip install git+https://github.com/WinetraubLab/agentic-devkit
```

## Choose a tool

- [TDD linting](docs/tdd/README.md): improve agent-written tests and record their reviews before implementation.
- [Policy tooling](docs/policies/README.md): define policies, generate review documents, and track compliance attestations.
- [GitHub Actions](docs/workflows/github-actions.md): check TDD review proof and policy attestations in your project's CI.

```bash
agentic-devkit tdd --help
agentic-devkit policy --help
```

## Agent skills

To use the guided agent workflows, copy the skill folders you need from
[shared skills](https://github.com/WinetraubLab/agentic-devkit/tree/main/.agents/skills/shared)
into `.agents/skills/` in your project:

- `run-tdd-linter`: review and improve your tests until TDD lint passes.
- `simplify-implementation`: simplify implementation after your test suite passes.
- `review-policy-attestations`: review your project's policies and complete attestations.

If your project already manages these skills through the `.agents/skills/shared`
Git submodule, update it instead:

```bash
git submodule update --init --remote .agents/skills/shared
```

The following guides use paths relative to your project's root.

## Repository Structure

Production code in this toolkit is grouped by responsibility:

```text
src/agentic_devkit/
    cli/main.py                  # Toolkit command routing
    version.py                   # Toolkit version
    tdd_lint/
        indexing_test_functions/ # Test discovery and extraction
        conventional_linter/     # Deterministic lint rules
        agentic_linter/          # Agent-review generation and proof
        cli/                     # TDD pipeline and reporting
    policies/                    # Policy rendering, scope digests, and attestations
```

Tests follow the same responsibilities and add integration and repository checks:

```text
tests/
    indexing_test_functions/     # Test discovery and extraction
    conventional_linter/         # Deterministic lint rules
    agentic_linter/              # Agent-review subsystem
    cli/                         # Toolkit CLI behavior
    policy/                      # Policy tooling
    integration_tests/           # End-to-end workflows
    repository_health/           # Fixture, manifest, and documentation checks
```

`integration_tests` and `repository_health` have no production-code counterparts:
they verify interactions and the repository itself rather than implement tool behavior.
