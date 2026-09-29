# WordPress Plugin Blueprint Architecture

## Principle

The blueprint is a governance and synchronization layer, not a framework that owns every plugin's application architecture.

A plugin remains independently testable, releasable, and reviewable. The blueprint supplies shared identity and quality rules and can propose updates through pull requests.

## Components

### 1. Manifest

`.ccf-wordpress-plugin.json` records the plugin identity and selected profile.

The manifest deliberately contains values that are expensive to infer safely:

- stable slug
- display name
- optional package root inside the repository
- main plugin file relative to that package root
- version
- text domain
- minimum WordPress/PHP versions
- explicit license mode and declared license metadata
- distribution channel
- update strategy (separate from `Update URI`)
- optional capabilities

This gives audit/sync tooling an explicit contract.

### Distribution and updates

Distribution and automatic update delivery are separate concerns.

A plugin may publish release ZIPs on GitHub while having no automatic WordPress update mechanism. The manifest therefore records both:

- `distribution.channel` — where releases are published;
- `distribution.updates` — how WordPress discovers/installs updates.

A GitHub `Update URI` header is validated as identity/protection metadata, but the blueprint must not treat it as proof that automatic GitHub updates are implemented.

### 2. Profile

Profiles define:

- repository-level required baseline files;
- package-level required files resolved below `plugin.root`;
- recommended repository files;
- exact-managed mappings with repository/package scope;
- optional license-mode conditions for managed content;
- profile-specific guidance.

A profile does not dictate internal PHP classes or folder structure beyond what the profile genuinely needs.

### 3. Exact-managed content

Exact-managed files are canonical and safe to replace byte-for-byte.

The initial set is intentionally small:

- shared repository-level `assets/logo.svg`;
- package-level GPL v2 license text only for manifests using `license_mode: managed-gpl`.

A manifest using `license_mode: declared` keeps licensing under plugin ownership. The blueprint validates the declaration but does not create, replace or reinterpret the license file.

More files can be added only when overwriting them cannot erase product-specific content.

### 4. Validation

The audit checks:

- repository-level and package-level required files;
- package-root path safety;
- exact-managed drift with scope-aware target resolution;
- canonical README banner;
- main plugin header versus manifest;
- plugin description length;
- GitHub update URI where applicable;
- package `readme.txt` metadata and declared license versus manifest;
- canonical GPL license presence/content only when `managed-gpl` is selected;
- changelog entry for the current version.

The audit uses the Python standard library only.

### 5. Sync

`sync-exact` has two modes:

- default: produce a plan only;
- `--write`: copy exact-managed files.

It must never modify validated or plugin-specific files.

### 6. Cross-repository propagation

Cross-repository automation is intentionally separated from local synchronization.

Future orchestrator responsibilities:

1. discover enrolled repositories;
2. read each manifest;
3. compare its `blueprint_version`;
4. create a short-lived branch;
5. apply exact-managed changes;
6. run the audit;
7. add only clearly generated/approved changes;
8. open a focused PR;
9. leave merge decisions to normal repository policy.

The orchestrator must not push directly to protected `main`.

## Repository root versus package root

The path given to the audit command is always the **repository root** containing `.ccf-wordpress-plugin.json`.

`plugin.root` identifies the installable WordPress package inside that repository and defaults to `.`. Package metadata such as the main PHP file, WordPress `readme.txt` and package-scoped managed files resolve below this path.

Repository presentation and governance files remain repository-scoped. This avoids forcing repositories such as connector projects to move their installable WordPress package to the repository root.

Both `plugin.root` and all profile-managed paths are validated as relative paths and may not escape the repository.

## Blueprint versioning

Use semantic versioning for the blueprint contract.

- **patch** — corrections that do not change required files or manifest semantics;
- **minor** — backward-compatible new checks/capabilities or optional managed content;
- **major** — manifest/profile changes that require plugin migration.

Until the first stable blueprint release, `0.x` changes may still evolve. Enrolled pilot plugins should therefore use PR review for every blueprint bump.

## Reusable workflow versioning

Reusable workflows should be published with the blueprint but consumed through an immutable SHA or reviewed version tag.

Do not reference `repository-governance@main` from a required merge check.

A major-version convenience tag may be introduced after the workflow contract is stable, but repositories with stricter reproducibility can continue pinning a full commit SHA.

## Failure model

The tool distinguishes:

- exit `0`: clean/success;
- exit `1`: valid plugin with blueprint drift;
- exit `2`: invalid manifest/profile/configuration.

This makes CI failures actionable rather than ambiguous.

## Security boundaries

- paths in the manifest/profile must remain relative and may not escape the repository;
- package-root resolution must remain inside the repository;
- sync writes only files explicitly listed as exact-managed and only in their declared scope;
- declared-license mode must never cause the blueprint to create or overwrite a license file;
- no credentials are stored in the blueprint;
- cross-repository writes require a separate authenticated mechanism and are not part of the local audit tool;
- required GitHub Actions should use least privilege and pinned third-party action revisions.

## Pilot

`wordpress-widget-custom-css-classes` is the first intended pilot because it is new, small, and has not accumulated release compatibility constraints yet.

The pilot should prove:

- manifest usability;
- audit accuracy;
- exact sync safety;
- README/readme/header consistency;
- profile fit;
- a clean PR-based blueprint update.

Only after that should the manifest be rolled out to older plugins.
