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

The current inventory has five enrolled repositories. `wordpress-project-management` is intentionally `paused` until its license and distribution model are explicitly decided. The inventory file is authoritative for rollout state.

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

The guarded write-capable orchestrator consumes only explicitly safe proposals. It stages one repository at a time and separates branch creation from PR creation so branch CI can be verified first.

## Propagation model

The write-capable orchestrator preserves these boundaries:

1. calculate drift first;
2. show the exact proposed changes;
3. `--apply` creates a short-lived branch and updates only allow-listed governance files;
4. run that plugin's own branch CI;
5. `--open-pr` verifies the branch HEAD has CI/status signals and refuses while checks are pending or non-green;
6. open one focused PR only after green branch CI;
7. never merge automatically and never write directly to protected `main`.

## Current rollout model

Blueprint `0.2.0` introduces explicit package-root and license-mode support. The fleet target is therefore advanced to `0.2.0` only after the implementation is reviewed.

Blueprint contract changes must never be consumed silently. Enrolled repositories may temporarily appear as `version-drift` until each receives its own focused, tested upgrade.

Repositories marked `paused` stay outside automated writes. Nested-package and nonstandard-license repositories must use explicit metadata rather than being coerced into the root-level GPL baseline.
