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

## Add GitHub Actions

Follow the [GitHub Actions guide](../workflows/github-actions.md#policy-verification)
to check your committed policy attestations on pull requests.

## Review workflow

Use local reviews to create attestations, then CI to validate them.

### Local review

Run `$review-policy-attestations` after development or policy changes. The skill
reviews the configured folders, fixes minor violations, and records attestations.
Changes to reviewed code or root folders require a fresh review.

In each generated policy's `# Attestation` section, record either:

```text
Noncompliant Files: NONE
```

or the remaining violations:

```text
Noncompliant Files:
- src/example.py
```

Verification allows no more findings than the committed baseline; new policies
or invalid baseline attestations allow none. Commit the completed reviews with
your changes.

### CI verification

CI runs `agentic-devkit policy verify` against your committed code, policy documents,
and digests. It checks that attestations are current and finding counts stay within
the baseline. CI does not perform compliance reviews.

If the check fails, run `$review-policy-attestations` locally and commit the updated
code and review results. See the [GitHub Actions guide](../workflows/github-actions.md#policy-verification)
for CI setup.

## Policy Writing Contract

Store each policy at `policy/<field>/<policy-name>.policy.yaml`. Group related
policies by field and use lowercase kebab-case for folder and policy names,
for example `policy/naming/physical-lengths.policy.yaml`.

```yaml
title: Physical length naming
objective: Make the units of physical lengths explicit.
applicable_folders: all # All JSON roots (default), or a list such as [src/vehicles].
policy_content: |
  Parameters representing physical lengths in meters must end in _m.
  For example, use car_length_m and tree_height_m.
  Apply this rule based on what the parameter represents, not just its name.
  Counts and lengths measured in other units are outside this rule.
exemptions: | # Optional accepted violations; retained across review resets.
  src/legacy-car.py may retain car_length without the _m suffix
  until callers migrate to car_length_m.
```

Rendering inserts these values into the bundled `policy-template.md.j2`, which
supplies the shared review instructions and attestation structure. The generated
`<policy-name>.md` is stored beside its YAML source.

Edit policies in YAML, then run `$review-policy-attestations`. The tool generates
the Markdown; reviews update its `# Attestation` section.

## Review commands

After a successful review, run policy verification alongside your normal checks.
Use the skill when reviews need updating.

```bash
agentic-devkit policy verify
```

To regenerate documents with empty attestations, or check generated text without
changing files:

```bash
agentic-devkit policy render
agentic-devkit policy check-documents
```
