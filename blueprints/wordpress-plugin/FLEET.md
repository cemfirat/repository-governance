# WordPress Plugin Fleet

The fleet layer tracks which WordPress plugin repositories should follow which blueprint profile. It is intentionally separate from the per-plugin blueprint manifest.

## Inventory

The canonical inventory is [`inventory.json`](inventory.json).

It records only fleet-level intent:

- repository
- default branch
- desired blueprint profile
- rollout state

It does not contain credentials, release secrets, or inferred plugin configuration.

Current profiles:

- `simple`: Doctype Inserter, At Head Tag, Widget Custom CSS Classes
- `application`: CCF Sites & Ads WordPress Connector, WordPress Calendar Booking, WordPress Project Management

The widget plugin is the first enrolled pilot. The other repositories remain `planned` until each is migrated and verified independently.

## Read-only planner

Run:

```bash
python3 scripts/wordpress-plugin-fleet.py
```

JSON output:

```bash
python3 scripts/wordpress-plugin-fleet.py --format json
```

Inspect a single repository:

```bash
python3 scripts/wordpress-plugin-fleet.py \
  --repository cemfirat/wordpress-widget-custom-css-classes
```

The planner reads `.ccf-wordpress-plugin.json` from each repository's configured default branch and classifies it as:

- `current`
- `unenrolled`
- `version-drift`
- `profile-drift`
- `invalid-manifest`
- `fetch-error`

Planning never changes another repository.

## Authentication

All currently inventoried repositories are public, so the planner works without authentication.

For a future private repository, set an explicit cross-repository **read-only** token in:

```text
CCF_FLEET_GITHUB_TOKEN
```

The planner deliberately does not use GitHub Actions' repository-scoped `GITHUB_TOKEN` by default. A token must be supplied consciously when cross-repository private access is actually needed.

## Read-only upgrade proposals

After the fleet planner has identified version drift, use the upgrade proposal planner:

```bash
python3 scripts/wordpress-plugin-upgrade-plan.py
```

For JSON output:

```bash
python3 scripts/wordpress-plugin-upgrade-plan.py --format json
```

Limit the proposal to one repository:

```bash
python3 scripts/wordpress-plugin-upgrade-plan.py \
  --repository cemfirat/wordpress-calendar-booking
```

The proposal planner is deliberately conservative:

- it never writes another repository;
- it only marks migrations as `safe-upgrade` when that exact blueprint-version migration is encoded and tested;
- unknown migrations become `manual-review`;
- repositories without a manifest become `manual-enrollment`;
- repositories marked `paused` in the fleet inventory are not fetched or changed;
- license modes are never guessed when existing metadata is ambiguous.

A later write-capable orchestrator may consume these proposals, but it must still create a focused branch/PR per target repository and rerun that repository's own checks.

## Propagation model

The next layer may turn a plan into pull-request proposals, but it must preserve these boundaries:

1. calculate drift first;
2. show the exact proposed changes;
3. create a short-lived branch in the target plugin;
4. update exact-managed files and explicitly generated metadata only;
5. run that plugin's own CI;
6. open one focused PR;
7. never push directly to protected `main`.

A write-capable orchestrator is not part of the current fleet planner.

## Current rollout model

Blueprint `0.2.0` introduces explicit package-root and license-mode support. The fleet target is therefore advanced to `0.2.0` only after the implementation is reviewed.

Repositories already enrolled at `0.1.0` should then appear as `version-drift` until each receives its own focused upgrade PR. That drift is intentional: a blueprint contract change must never be consumed silently.

Planned repositories remain `unenrolled` until their baseline metadata has been reviewed. In particular, nested-package and nonstandard-license repositories must use the new explicit model rather than being coerced into the root-level GPL baseline.
