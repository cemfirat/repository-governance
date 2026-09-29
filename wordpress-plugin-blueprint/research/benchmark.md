# WordPress Plugin Blueprint Research

This document records the first research pass before implementation of the reusable plugin blueprint.

## Research method

The blueprint should be based on three evidence layers, in this order:

1. **Official WordPress documentation and tooling**
2. **Official GitHub capabilities**
3. **Established real-world repositories**, used as implementation references rather than authorities

Popularity alone is not a selection criterion. An old or highly starred boilerplate can still encode obsolete assumptions.

## Official WordPress findings

### Plugin headers

WordPress requires only the plugin name at minimum, but officially supports fields including version, WordPress/PHP requirements, author, license, text domain, update URI and required plugins.

Reference:

- https://developer.wordpress.org/plugins/plugin-basics/header-requirements/

The blueprint should validate metadata consistency rather than add arbitrary fields.

### `readme.txt`

WordPress documents a separate plugin readme format. It is not the same artifact as GitHub's `README.md`.

Reference:

- https://developer.wordpress.org/plugins/wordpress-org/how-your-readme-txt-works/

Important current behavior: modern WordPress reads runtime requirements from the main plugin PHP header. The blueprint should still keep `readme.txt` coherent, but the plugin header is authoritative for WordPress/PHP requirements.

### Plugin Check

The official Plugin Check project supports static and runtime checks and is useful even when a plugin is not destined for the WordPress.org directory.

Reference repository:

- https://github.com/WordPress/plugin-check

Implication for the blueprint:

- Plugin Check should be an available validation layer.
- It should not automatically become a required merge gate for every plugin until compatibility and signal quality are verified for that profile.
- Runtime checks should run in isolated/test WordPress environments, not production.

### WordPress Playground

The Plugin Check repository demonstrates PR previews using WordPress Playground.

Potential blueprint use:

- optional PR preview for plugins where visual/admin/front-end review benefits from it;
- not mandatory for tiny non-visual utilities.

## Official GitHub findings

### Reusable workflows

GitHub supports reusable workflows with `workflow_call`.

References:

- https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows
- https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations

Implication:

Shared deterministic CI logic can live centrally, while each plugin keeps a small caller workflow.

Security/stability rule:

- prefer a reviewed release tag or commit SHA for shared workflow references;
- avoid silently consuming unreviewed changes from a moving branch.

GitHub explicitly notes that a commit SHA is the safest reference for stability/security.

### Template repositories

GitHub repository templates are useful for initial creation but are not a synchronization mechanism for repositories created earlier.

Implication:

The blueprint needs a separate drift/sync mechanism if improvements should reach existing plugins.

## Real-world repository findings

### `wp-cli/scaffold-command`

Repository:

- https://github.com/wp-cli/scaffold-command

Important current signal: the project itself states that `wp scaffold` plugin/theme scaffolding is no longer generally recommended for modern WordPress development, and points modern block development toward current WordPress tooling such as `@wordpress/create-block`.

Implication:

Do not build a single universal architecture that assumes every WordPress plugin should start from the same classic scaffold.

### `DevinVinson/WordPress-Plugin-Boilerplate`

Repository:

- https://github.com/DevinVinson/WordPress-Plugin-Boilerplate

Useful ideas:

- clear separation of concerns
- predictable file naming
- internationalization awareness
- repository/package distinction

What should not become mandatory:

- a fixed admin/public/includes object-oriented architecture for every plugin
- historical tooling or directory conventions merely because they are familiar

For a tiny utility plugin, such structure can create more maintenance overhead than value.

## Existing Cem Firat plugins

The current repositories already show two useful categories:

### Small utilities

- `wordpress-doctype-Inserter`
- `wordpress-at-head-tag`
- `wordpress-widget-custom-css-classes`

These benefit from a minimal structure, strong packaging/release checks and focused integration tests.

### Larger systems

- `wordpress-calendar-booking`
- `ccf-sites-ads-wordpress-connector`
- `wordpress-project-management`

These need deeper architecture/security/test documentation and should not be reduced to the small-plugin structure.

## Preliminary decisions

1. Build a **blueprint system**, not one giant boilerplate.
2. Use profile-based defaults: `simple`, `application`, `block`.
3. Keep repository identity/branding consistent across profiles.
4. Separate centrally managed, structured and plugin-owned content.
5. Prefer reusable workflows for deterministic shared logic.
6. Pin shared workflow versions.
7. Make updates to existing repositories via PRs.
8. Never overwrite ambiguous/plugin-owned content automatically.
9. Treat Plugin Check and Playground as optional capabilities that can become profile defaults only after practical validation.
10. Validate the blueprint first on `wordpress-widget-custom-css-classes` before broad rollout.

## Open research before generator implementation

- decide the manifest filename/schema;
- decide which checks are core vs profile-specific;
- test Plugin Check against at least one small and one complex existing plugin;
- compare packaging/update strategies already used by existing repositories;
- determine the minimum useful PHP/WordPress test matrix without creating noisy CI;
- decide whether shared workflows live in `repository-governance` or a dedicated automation repository;
- define a safe migration algorithm for structured files such as README/readme/plugin headers.
