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

