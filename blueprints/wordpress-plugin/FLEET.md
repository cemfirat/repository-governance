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

## Expected initial state

At the time the inventory was introduced:

- `wordpress-widget-custom-css-classes` is enrolled at blueprint `0.1.0` with profile `simple`;
- the other five inventoried repositories do not yet contain a blueprint manifest and should therefore plan as `unenrolled`.

This state was verified against GitHub before enabling fleet rollout work.
