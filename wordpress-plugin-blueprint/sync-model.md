# Blueprint Synchronization Model

The synchronization system exists to propagate improvements safely to existing plugin repositories.

It is explicitly **not** a mass-overwrite mechanism.

## Desired behavior

A blueprint release can be compared with every participating plugin.

The sync process should return one of four outcomes per repository:

- **up to date**
- **safe update available**
- **manual migration required**
- **not applicable**

Only a **safe update available** result may automatically produce a pull request.

## Ownership classes

### 1. Managed files

Exact-content synchronization is permitted.

Examples:

- shared logo
- generated caller workflows with no local customizations
- machine-generated baseline metadata

Safety requirements:

- compare the entire file before replacement;
- replace only paths explicitly declared managed;
- open a PR;
- never write directly to protected `main`.

### 2. Structured files

Only defined machine-readable fields or bounded sections may change.

Examples:

- plugin header fields
- `readme.txt` header fields
- a README requirements block
- workflow inputs

Safety requirements:

- parse the structure rather than using broad search/replace;
- preserve unknown/plugin-specific sections;
- if parsing is ambiguous, stop with **manual migration required**.

### 3. Plugin-owned files

The blueprint may audit them but may not modify them.

Examples:

- PHP feature implementation
- data migrations
- plugin-specific tests
- product documentation

## Proposed manifest

Provisional example:

```yaml
schema: 1

blueprint:
  profile: simple
  version: 0.1.0

repository:
  plugin_slug: wordpress-widget-custom-css-classes
  main_file: widget-css-classes.php

sync:
  mode: pull-request

managed:
  - assets/logo.svg

structured:
  - plugin-header
  - readme-header

capabilities:
  github-releases: false
  wordpress-plugin-check: false
  playground-preview: false
```

The schema is deliberately small. It should describe only information needed for validation/sync and must not become a duplicate of the plugin's own configuration.

## Version upgrade flow

Example: blueprint `0.1.0` → `0.2.0`.

1. Load the plugin manifest.
2. Validate that the repository still matches its declared current version.
3. Calculate migration steps between versions.
4. Apply changes only to declared managed/structured areas.
5. Run static validation.
6. Create a branch.
7. Commit with a deterministic message such as:
   `chore: sync WordPress plugin blueprint 0.2.0`
8. Open a PR explaining every changed component.
9. Let repository-specific CI run.
10. Merge only after successful checks/review.

## Drift handling

If a centrally managed file was changed locally, the sync tool must not silently erase the change.

Instead:

- show the local/expected difference;
- classify it as drift;
- require explicit reconciliation;
- optionally allow the repository to reclassify the file as structured or plugin-owned if justified.

## Shared workflows

Shared deterministic workflows should be centralized where it reduces duplication.

A caller repository should reference a stable version, for example a release tag or commit SHA.

Blueprint release notes must describe workflow changes so repository maintainers understand what will change before updating the pin.

## Rollout

The first rollout target is `wordpress-widget-custom-css-classes`.

Only after the model works there should it be applied to:

1. other simple plugins;
2. application-profile plugins;
3. block-profile plugins.

This order intentionally minimizes blast radius.
