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

The widget plugin was the first enrolled pilot. The current 0.2.0 rollout is now established across the reviewed fleet:

- `wordpress-widget-custom-css-classes` — enrolled, simple profile;
- `wordpress-doctype-Inserter` — enrolled, simple profile;
- `wordpress-at-head-tag` — enrolled, simple profile;
- `wordpress-calendar-booking` — enrolled, application profile;
- `ccf-sites-ads-wordpress-connector` — enrolled, application profile with nested package root and declared-license model;
- `wordpress-project-management` — intentionally paused until license/distribution metadata is explicitly decided.

Enrollment means the repository has an explicit manifest and consumes the reviewed shared blueprint. Optional quality gates such as Plugin Check remain repository-specific and must be proven before becoming required.

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

The guarded write-capable orchestrator can consume reviewed proposals one repository at a time. It defaults to dry-run, creates a focused branch rather than writing to protected `main`, never auto-merges, and leaves the target repository's own branch/PR CI as merge authority.

## Propagation model

The guarded PR orchestrator is implemented, but it preserves these boundaries:

1. calculate drift first;
2. show the exact proposed changes;
3. create a short-lived branch in the target plugin;
4. update exact-managed files and explicitly generated metadata only;
5. run that plugin's own branch CI;
6. open one focused PR only after branch CI is green;
7. require PR CI/review before merge;
8. never push directly to protected `main`;
9. never auto-merge.

The account-wide working rule is explicit: **no PR before green branch CI**.

## Current rollout model

Blueprint `0.2.0` is the active fleet target. All reviewed repositories except the explicitly paused Project Management plugin are enrolled at that version.

The rollout remains intentionally profile- and repository-aware:

- simple plugins may use the shared distribution-aware official WordPress Plugin Check once deterministic package contents are proven;
- application plugins may use a lighter branch-readiness gate when running their entire integration matrix on every branch push would be wasteful;
- `wordpress-calendar-booking` keeps its comprehensive CI on PR/`main` and uses focused pre-PR branch readiness; Plugin Check remediation is tracked separately in its issue #219 after the first packaged pilot exposed existing findings;
- the CCF Sites & Ads connector keeps its explicit declared/proprietary license model and does not silently inherit GPL- or WordPress.org-specific assumptions;
- `wordpress-project-management` stays paused until license and distribution metadata are decided explicitly.

A future blueprint version must again appear as reviewable fleet drift. Contract changes are never consumed silently.
