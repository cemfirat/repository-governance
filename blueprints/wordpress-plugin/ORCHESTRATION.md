# WordPress Blueprint PR Orchestration

The cross-repository orchestrator turns an explicitly safe blueprint migration into a reviewable pull request.

It is intentionally conservative and does not replace repository-specific CI or review.

## Safety model

Write mode is allowed only when all of the following are true:

- exactly one repository is targeted;
- the repository exists in the canonical fleet inventory;
- rollout is not marked `paused`;
- the upgrade planner classifies the migration as `safe-upgrade`;
- the source and target blueprint versions are listed in reviewed release metadata;
- only allow-listed blueprint control files would change;
- the target manifest has not changed since planning;
- the propagation branch does not already exist;
- an explicit write token is supplied.

The orchestrator never:

- writes directly to the default branch;
- merges a pull request;
- changes plugin feature code;
- changes README prose, changelogs, tests, packaging logic or product files;
- guesses a license mode when existing metadata is ambiguous;
- silently reuses `GITHUB_TOKEN` for cross-repository writes.

## Release metadata

Reviewed blueprint releases are registered in:

`blueprints/wordpress-plugin/releases.json`

A release entry defines:

- the immutable central audit-action commit SHA;
- which source blueprint versions may migrate to that release.

The first encoded migration is `0.1.0 -> 0.2.0`.

## Dry run

Dry run is the default:

```bash
python3 scripts/wordpress-plugin-pr-orchestrator.py \
  --repository cemfirat/example-plugin
```

JSON output:

```bash
python3 scripts/wordpress-plugin-pr-orchestrator.py \
  --repository cemfirat/example-plugin \
  --format json
```

Dry run reads the current manifest and blueprint workflow, applies only the reviewed migration in memory and reports the exact blueprint control files that would change.

## Write mode

Write mode requires an explicit token:

```bash
export CCF_BLUEPRINT_GITHUB_WRITE_TOKEN=...
python3 scripts/wordpress-plugin-pr-orchestrator.py \
  --repository cemfirat/example-plugin \
  --apply
```

The token should be least-privilege and scoped only to repositories that are intentionally managed by this process.

Write mode:

1. verifies the target repository and fleet state;
2. re-reads the current default-branch HEAD;
3. verifies the manifest still matches the planned state;
4. refuses an existing propagation branch;
5. creates a short-lived blueprint branch;
6. updates only the allow-listed blueprint control files;
7. opens a pull request;
8. stops.

The target repository's own checks and review process remain the merge gate.

## Current allow-list

The first implementation can modify only:

- `.ccf-wordpress-plugin.json`
- `.github/workflows/blueprint.yml`

Within the manifest it can set only:

- `blueprint_version`
- `plugin.root`
- `plugin.license_mode`

Any future expansion of this allow-list requires reviewed code and tests.

## Credentials

Read-only public inspection does not require authentication.

Optional private-repository reads use:

`CCF_FLEET_GITHUB_TOKEN`

Cross-repository writes require a separate explicit variable:

`CCF_BLUEPRINT_GITHUB_WRITE_TOKEN`

The write token is never stored in the repository.

## Failure behavior

Ambiguity stops the operation.

Examples:

- unknown blueprint migration;
- profile drift;
- ambiguous license metadata;
- missing blueprint workflow;
- workflow with no unique immutable central action pin;
- manifest changed after planning;
- pre-existing propagation branch.

These cases require review rather than an automatic fallback.
