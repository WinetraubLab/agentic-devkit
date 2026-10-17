# Policy tooling

The policy tool in `agentic-devkit` checks review attestations for your project's
policies. It helps keep agent-led policy reviews current and prevents the number
of reported violations from exceeding the committed baseline.

## Design Philosophy

Coding agents can generate implementation faster than humans can review it line by line. Project policies make shared expectations explicit: they define rules that should hold across features and changes.
The policy tool helps keep reviews of those rules current and prevents reported violations from increasing. It does not replace human judgment, tests, or code review.

## Development Pattern

Policies capture rules that require semantic understanding, such as naming physical
lengths in meters with `_m`: `car_length_m`, `tree_height_m`. A conventional linter
cannot reliably infer which parameters represent physical lengths, and an agent
may forget the rule as a coding session grows.

Define the policy once so it persists across coding sessions. After development,
the agent reviews the code against it, fixes mistakes, and records an attestation.

```text
Development -> Attestation
```

Use the installed `$review-policy-attestations` skill for this review workflow.

## What It Checks

- Reviews are current for the code being checked.
- Policy documents and attestations are valid.
- Reported violations do not exceed the committed baseline.

## Set up policy reviews to your project

[Install the toolkit](../../README.md#installation) and the
[`review-policy-attestations` agent skill](../../README.md#agent-skills) in your project.

Create your policies using the [Policy Writing Contract](#policy-writing-contract),
for example `policy/naming/physical-lengths.policy.yaml`. Your project will contain:

```text
policy/
├── policy-scope-digest.json     # Reviewed root folders and generated digests
└── <field>/
    ├── <policy-name>.policy.yaml # Policy content supplied to the template
    └── <policy-name>.md         # Generated policy and editable attestation
```

Specify the root folders to review under your policies in
`policy/policy-scope-digest.json`:

```json
{
  "digests": [
    {
      "root_folder": "src",
      "digest": null
    }
  ]
}
```

Add an entry for each root folder. Set `digest` to `null` for new entries; the
tool generates and updates it during review. Folder paths are relative to your
project root.

From your project root, ask your coding agent:

```text
Run the `$review-policy-attestations` skill.
```

A successful run leaves generated policies with completed attestations and a
current `policy/policy-scope-digest.json`. Commit these with your policy YAML
and code changes.

