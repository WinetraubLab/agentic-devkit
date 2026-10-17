# Developer Policies

## TDD Lint Skill Routing

When the user asks to "make sure code passes tdd" or
equivalently ensure TDD lint passes, invoke the `run-tdd-linter` skill at
`.agents/skills/shared/run-tdd-linter/SKILL.md` and follow its workflow.

## Language-Agnostic Conventional Linting

Conventional linter implementations shall be language-agnostic. Language-specific
behavior belongs in test indexing and extraction. Every conventional lint rule shall
apply to every supported language, with equivalent behavior covered by tests.
