# GitHub Ruleset templates

## Recommended storage

Create a small private repository, for example:

`cemfirat/repository-governance`

Store these files under:

`rulesets/main-protection-hard-guardrails.json`
`rulesets/main-protection-merge-gates-base.json`

That keeps repository protection policy separate from product code and gives you one central source for future repositories.

## Template 1: hard guardrails

`main-protection-hard-guardrails.json`

Use unchanged for repositories whose protected branch is `main`.

It:
- targets `main`
- blocks branch deletion
- blocks force pushes
- has no bypass actors

## Template 2: merge gates base

`main-protection-merge-gates-base.json`

It:
- targets `main`
- requires pull requests
- allows both Maintain and Repository admin to bypass the merge gates
- intentionally does NOT contain repository-specific required status checks

After importing it into a repository, add the repository's actual required CI checks under:
`Require status checks to pass`

This avoids accidentally importing check names from another repository.

## Optional policy choices

Conversation resolution is intentionally OFF in the generic merge-gates template because most of the repositories currently use that setting. If a repository should require all PR conversations to be resolved before merge, enable:
`Require conversation resolution before merging`

If you want this enabled everywhere, create a second merge-gates template with that option enabled.

## Suggested workflow for a new repository

1. Create/push the repository and make sure `main` exists.
2. Add a CI workflow and let it run at least once so GitHub knows the check names.
3. Import `main-protection-hard-guardrails.json`.
4. Import `main-protection-merge-gates-base.json`.
5. Add the repository-specific required status checks.
6. Verify both rulesets are Active and target only `main`.
