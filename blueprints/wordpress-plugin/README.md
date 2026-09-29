# WordPress Plugin Blueprint

The WordPress Plugin Blueprint is the shared source of truth for public WordPress plugin repositories maintained by Cem Firat.

It is deliberately **not** a single rigid PHP boilerplate. A small utility plugin, a large WordPress application, and a block plugin have different technical needs. The blueprint standardizes the parts that should be consistent across all of them: repository identity, branding, metadata, licensing, baseline validation, packaging/release policy, and controlled propagation of shared updates.

Current blueprint version: **0.1.0 (draft)**

## Goals

- make new WordPress plugin repositories start from a known-good baseline;
- keep existing plugins aligned without overwriting plugin-specific work;
- detect drift between plugin metadata, `readme.txt`, licensing, branding, and the blueprint manifest;
- allow centrally managed files to be synchronized safely;
- make blueprint changes flow to plugin repositories through reviewable pull requests;
- keep CI small and deterministic before it becomes a required merge gate.

## Profiles

The blueprint has three profiles:

- **simple** — focused PHP utilities with minimal dependencies;
- **application** — larger plugins with integrations, data flows, APIs, admin surfaces, or broader security/privacy requirements;
- **block** — block-oriented plugins whose scaffold should be based on the official `@wordpress/create-block` toolchain rather than a duplicated custom JavaScript stack.

Profiles share the same repository baseline but can require different files and validation depth.

## Ownership model

Files fall into three categories.

### Exact managed files

These are safe to synchronize byte-for-byte from `repository-governance`.

Initial examples:

- `assets/logo.svg`
- the full GPL v2 license text when the manifest declares `GPL-2.0-or-later`

`sync-exact` may update only these files.

### Validated files

These are plugin-specific and must never be blindly overwritten:

- `README.md`
- `readme.txt`
- `CHANGELOG.md`
- the main plugin PHP file
- packaging scripts
- test configuration

The blueprint validates their required structure and metadata consistency, but their product-specific content stays in the plugin repository.

### Plugin-specific files

Feature code, data models, integrations, migrations, plugin-specific tests, UI, and documentation remain entirely owned by each plugin.

## Manifest

Each enrolled plugin contains `.ccf-wordpress-plugin.json`.

Example:

```json
{
  "schema_version": 1,
  "blueprint": "wordpress-plugin",
  "blueprint_version": "0.1.0",
  "profile": "simple",
  "plugin": {
    "slug": "example-plugin",
    "name": "Example Plugin",
    "main_file": "example-plugin.php",
    "version": "1.0.0",
    "text_domain": "example-plugin",
    "minimum_wordpress": "6.5",
    "minimum_php": "8.0",
    "author": "Cem Firat",
    "license": "GPL-2.0-or-later",
    "license_header": "GPL-2.0-or-later"
  },
  "distribution": {
    "channel": "github-releases",
    "updates": "none",
    "update_uri": "https://github.com/cemfirat/example-plugin"
  },
  "features": {
    "block_plugin": false,
    "playground_preview": false
  }
}
```

The JSON Schema is in [`manifest.schema.json`](manifest.schema.json).

`Update URI` and update delivery are modeled separately. A non-WordPress.org `Update URI` protects an externally distributed plugin from accidental WordPress.org replacement, but it does not by itself implement GitHub update discovery or installation.

## Audit and sync

The baseline tool uses only the Python standard library:

```bash
python3 scripts/wordpress-plugin-blueprint.py \
  audit \
  --plugin-root /path/to/plugin
```

Plan exact managed-file changes without writing:

```bash
python3 scripts/wordpress-plugin-blueprint.py \
  sync-exact \
  --plugin-root /path/to/plugin
```

Apply only exact managed-file changes:

```bash
python3 scripts/wordpress-plugin-blueprint.py \
  sync-exact \
  --plugin-root /path/to/plugin \
  --write
```

`sync-exact --write` is intentionally narrow. It does not edit README prose, plugin source, changelogs, tests, or any other plugin-specific content.

## Fleet inventory and planning

The canonical repository inventory and read-only propagation plan are documented in [FLEET.md](FLEET.md).

The fleet planner detects enrollment/profile/version drift across WordPress plugin repositories without modifying them. Cross-repository write automation is deliberately a later layer.

## Update propagation

A blueprint change does **not** write directly to every plugin's `main` branch.

The intended propagation flow is:

1. change and validate the blueprint;
2. publish a reviewed blueprint revision;
3. discover enrolled plugin repositories and compare their manifest version;
4. calculate exact-managed changes and validation drift;
5. create one focused branch/pull request per affected plugin;
6. run that plugin's own checks;
7. merge only after the repository is green.

This keeps the blueprint central while preserving each plugin as an independent, reviewable product.

Cross-repository PR orchestration is intentionally a later phase. The first phase establishes deterministic local audit/sync behavior and a stable manifest before introducing credentials or write automation.

## Central GitHub Action

The blueprint audit is exposed as a composite GitHub Action from this directory. A plugin workflow only needs to check out its own source and call a pinned governance revision:

```yaml
- uses: actions/checkout@<pinned-actions-checkout-sha>
- uses: cemfirat/repository-governance/blueprints/wordpress-plugin@<pinned-governance-sha>
```

The action executes the audit code and profile files from the **same pinned governance revision**, so callers do not need a second governance checkout and cannot accidentally mix script/profile versions.

Consumers should pin a reviewed commit SHA or stable blueprint tag, never a moving `main` branch for a required check.

Plugin-specific test matrices remain in the plugin repository.

## New plugin methodology

Before a new plugin is scaffolded:

1. define the plugin purpose and distribution channel;
2. choose the smallest fitting profile;
3. finalize slug, plugin directory, main filename, text domain, and update identity before the first stable release;
4. scaffold only the profile-appropriate structure;
5. run the blueprint audit locally;
6. add focused behavior tests;
7. prove CI on a branch before making it a merge gate;
8. release only from reviewed/tested `main`.

For block plugins, use `@wordpress/create-block` as the underlying WordPress scaffold and layer this governance baseline on top.

## Repository layout

```text
blueprints/wordpress-plugin/
├── README.md
├── RESEARCH.md
├── ARCHITECTURE.md
├── manifest.schema.json
├── examples/
│   └── simple.manifest.json
├── managed/
│   └── gpl-2.0.txt
└── profiles/
    ├── simple.json
    ├── application.json
    └── block.json

scripts/
└── wordpress-plugin-blueprint.py

tests/
└── test_wordpress_plugin_blueprint.py
```

The general policy remains documented in [`../../standards/wordpress-plugin.md`](../../standards/wordpress-plugin.md).
