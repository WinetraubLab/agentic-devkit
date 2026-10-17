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

Record the result and every policy requiring review. Continue to Step 2 even when
the command fails or resets attestations.

## Step 2: Review attestations

Read `policy/README.md`, then follow the instructions in every policy requiring
review. Review the complete scope each policy names and fix definite minor
violations. Write `Noncompliant Files: NONE` on one line when none remain;
otherwise put sorted file bullets below `Noncompliant Files:`. Normalize every
reviewed policy to this format.

## Step 3: Run policy verification again

Run:

```bash
agentic-devkit policy verify
```

Use this second result as the final policy result. If it fails, report the exact
remaining policy failures and the attestations or files that still need work.
