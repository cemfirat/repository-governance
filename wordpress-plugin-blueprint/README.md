# WordPress Plugin Blueprint

This directory defines the reusable blueprint for public WordPress plugins maintained under the Cem Firat GitHub account.

The blueprint is deliberately more than a GitHub template repository. A normal template is useful when creating a repository, but later changes to that template do not propagate to repositories that were already created.

The goal here is therefore a versioned system with four parts:

1. **Standard** — rules every plugin should satisfy.
2. **Profiles** — defaults for different plugin types.
3. **Managed components** — files or checks that can be synchronized safely.
4. **Compliance/sync tooling** — detects drift and proposes pull requests instead of overwriting repositories.

## Design principles

- No blind mass updates.
- No direct writes to protected `main` branches.
- Blueprint updates should result in reviewable pull requests.
- Plugin-owned code must never be overwritten by the blueprint.
- Shared workflow logic should be reused where practical instead of copied.
- Reusable workflow references should be pinned to a stable tag or commit SHA, not an unreviewed moving branch.
- CI is added only after the checks are deterministic and useful.
- Small plugins should stay small.
- Block plugins should use modern WordPress tooling rather than forcing a classic PHP architecture onto them.
- Existing plugins can adopt the blueprint incrementally.

## Profiles

Three initial profiles are planned:

### `simple`

Small utilities such as Doctype Inserter, At Head Tag and Widget Custom CSS Classes.

Typical characteristics:

- little or no dependency tooling
- one main PHP file plus focused includes when needed
- small regression suite
- deterministic release ZIP
- GitHub release/update flow where appropriate

### `application`

Larger plugins such as Calendar Booking or the CCF connector.

Typical characteristics:

- structured source directories
- deeper WordPress integration tests
- optional Composer/npm tooling
- explicit architecture/security documentation
- richer release qualification

### `block`

Plugins centered on the Block Editor.

The blueprint does not replace official modern block tooling. It adds the Cem Firat repository, governance, documentation, validation and release layer around the appropriate WordPress block scaffold.

## Ownership model

Every blueprint-controlled path belongs to one of three classes.

### Managed

The blueprint owns the whole file. Examples can include:

- `assets/logo.svg`
- narrowly scoped shared workflow caller files
- generated metadata files that contain no plugin-specific prose

Updates may replace these files, but only through a pull request.

### Structured

The blueprint owns only defined fields or sections. Examples:

- plugin header metadata
- README identity/requirements block
- `readme.txt` header metadata
- selected workflow inputs

Sync tooling must preserve plugin-specific content outside the managed fields.

### Plugin-owned

Never changed automatically by the blueprint:

- product PHP logic
- JavaScript application logic
- plugin-specific tests
- plugin-specific documentation
- migrations and data models
- custom UI/UX implementation

## Versioning

Each participating repository will eventually declare which blueprint profile and version it follows.

Example:

```yaml
schema: 1
blueprint:
  profile: simple
  version: 0.1.0
sync:
  mode: pull-request
```

The exact manifest filename and schema remain provisional until the research phase is complete.

## Update model

A future sync run should behave like this:

1. read each repository's manifest;
2. compare the pinned blueprint version to the current release;
3. inspect only files/fields allowed by the ownership model;
4. produce a human-readable drift report;
5. create a branch and pull request when a safe update exists;
6. run repository-specific tests;
7. merge only after review/checks succeed.

A failed or ambiguous migration must stop for review rather than guess.

## Current phase

The blueprint is currently in **research/specification**. No repository-wide synchronization is enabled yet.

See:

- [research/benchmark.md](research/benchmark.md)
- [sync-model.md](sync-model.md)
- [profiles/](profiles/)
- the shared repository standard in [../standards/wordpress-plugin.md](../standards/wordpress-plugin.md)
