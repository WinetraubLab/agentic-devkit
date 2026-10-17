# Policy tooling

The policy tool in `agentic-devkit` checks review attestations for your project's
policies. It helps keep agent-led policy reviews current and prevents the number
of reported violations from exceeding the committed baseline.

## Design Philosophy

Coding agents can generate implementation faster than humans can review it line by line. Project policies make shared expectations explicit: they define rules that should hold across features and changes.
The policy tool helps keep reviews of those rules current and prevents reported violations from increasing. It does not replace human judgment, tests, or code review.

