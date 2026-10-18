---
name: review-policy-attestations
description: Use when the user asks to check a repository against its policies, complete policy attestations, or resolve a policy verification failure.
---

# Review Policy Attestations

## Step 1: Run policy verification

Run:

```bash
agentic-devkit policy verify
```

Record the result and every policy requiring review. If generated policy documents
are missing or stale after YAML changes, run `agentic-devkit policy render`, then
verify again. Continue to Step 2 when verification requests review or resets
attestations. Resolve configuration errors before reviewing.

## Step 2: Review attestations

Follow the instructions in every policy requiring review. Review the complete
scope each policy names and fix definite minor violations. Write
`Noncompliant Files: NONE` on one line when none remain; otherwise put sorted
file bullets below `Noncompliant Files:`. Normalize every reviewed policy to
this format.

## Step 3: Run policy verification again

Run:

```bash
agentic-devkit policy verify
```

Use this second result as the final policy result. If it fails, report the exact
remaining policy failures and the attestations or files that still need work.
