# WordPress Plugin Blueprint Research

Research date: 2026-09-29.

This note records the external and internal findings used to design the blueprint. The purpose is to avoid turning historical habits or a single third-party boilerplate into an unquestioned standard.

## Primary WordPress findings

### Plugin headers are the runtime source of plugin requirements

WordPress documents the main plugin header and its supported fields, including `Requires at least`, `Requires PHP`, `Update URI`, `Text Domain`, and `Requires Plugins`.

Source: https://developer.wordpress.org/plugins/plugin-basics/header-requirements/

Implication:

- the main PHP file is authoritative for runtime plugin metadata;
- the blueprint must compare manifest values to the plugin header;
- minimum versions should be chosen from actual code requirements, not copied from another plugin.

### `Update URI` is not an external updater

WordPress introduced the `Update URI` header so externally distributed plugins can avoid being accidentally overwritten by a similarly named WordPress.org plugin. A non-WordPress.org URI causes the normal WordPress.org update lookup to ignore the plugin unless code handles the dynamic external update filter.

Source: https://make.wordpress.org/core/2021/06/29/introducing-update-uri-plugin-header-in-wordpress-5-8/

Implication:

- record the `Update URI` independently from the actual update strategy;
- never claim that a GitHub URL in the header enables GitHub updates;
- require an explicit updater implementation and tests before a plugin manifest declares automatic GitHub release updates.

### `readme.txt` is a separate distribution/documentation surface

WordPress documents the plugin directory readme format separately. Since WordPress 5.8, runtime requirements are no longer taken from `readme.txt`; they come from the main plugin file.

Source: https://developer.wordpress.org/plugins/wordpress-org/how-your-readme-txt-works/

Implication:

- keep `readme.txt` because it remains useful and may become the WordPress.org surface;
- validate that its visible metadata does not contradict the plugin header;
- do not treat it as the runtime authority.

### Plugin Check should be part of the quality model

The official `WordPress/plugin-check` project performs both static and runtime checks and can analyze installed plugins as well as plugin paths/archives.

Source: https://github.com/WordPress/plugin-check

Implication:

- Plugin Check belongs in the planned validation stack;
- it should supplement, not replace, plugin-specific regression tests;
- it should be introduced only after the base packaging/install path is deterministic.

### Traditional WP-CLI plugin scaffolding is not the modern universal answer

`wp-cli/scaffold-command` now explicitly notes that scaffolding plugins/themes with `wp scaffold` is no longer recommended as the general approach for modern WordPress development.

Source: https://github.com/wp-cli/scaffold-command

Implication:

- do not base the Cem Firat blueprint on a legacy universal scaffold;
- use a profile model instead.

### Block plugins should build on `@wordpress/create-block`

WordPress documents `@wordpress/create-block` as the officially supported tool for scaffolding block plugins. It supports external templates, custom namespaces/text domains, and optional `wp-env` setup.

Source: https://developer.wordpress.org/block-editor/reference-guides/packages/packages-create-block/

Implication:

- the block profile should layer governance on top of `create-block`;
- do not clone and freeze WordPress's JavaScript build stack inside our own blueprint.

### WordPress Playground is useful for review, not mandatory for every plugin

WordPress Playground documents GitHub Action based pull-request previews and browser-based test environments.

Source: https://developer.wordpress.org/playground/handbook/guides/github-action-pr-preview/

Implication:

- make Playground preview an opt-in capability;
- prefer it for UI/admin/front-end behavior where a browser preview materially improves review;
- do not force it on tiny non-visual utilities.

## GitHub findings

### Template repositories bootstrap; they do not provide ongoing synchronization

GitHub template repositories create a new repository with the template's files and directory structure, but the new repository has unrelated history.

Source: https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template

Implication:

- a GitHub template may help create new repositories;
- it cannot be the update mechanism for existing plugins;
- ongoing alignment needs a manifest, audit/sync tooling, and PR-based propagation.

### Reusable workflows are the right tool for shared deterministic CI logic

GitHub supports reusable workflows through `workflow_call`.

Source: https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows

GitHub also recommends stable references; a full commit SHA is the safest immutable reference, while version tags are useful for maintained compatible releases.

Source: https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations

Implication:

- share baseline CI logic instead of copying large workflow files;
- pin required consumers to reviewed versions rather than `@main`;
- keep plugin-specific test jobs local.

## Third-party boilerplate benchmark

The long-running `DevinVinson/WordPress-Plugin-Boilerplate` is useful as an architectural reference but intentionally imposes an admin/public/includes class structure.

Source: https://github.com/DevinVinson/WordPress-Plugin-Boilerplate

Implication:

- do not make that architecture mandatory;
- a one-file utility should remain small;
- larger plugins can use classes/namespaces/dependency containers when their complexity justifies them.

## Internal repository audit

Repositories reviewed:

- `cemfirat/wordpress-doctype-Inserter`
- `cemfirat/wordpress-at-head-tag`
- `cemfirat/wordpress-calendar-booking`
- `cemfirat/wordpress-project-management`
- `cemfirat/ccf-sites-ads-wordpress-connector`
- `cemfirat/wordpress-widget-custom-css-classes`

Existing common strengths:

- shared brand banner is already widely used;
- the shared `assets/logo.svg` is already established;
- the stronger public plugins already use `LICENSE`, `readme.txt`, changelogs, tests, and release automation;
- several repositories already distinguish small utilities from complex applications in practice.

Observed inconsistency:

- some repositories are missing a full license or WordPress-style readme;
- CI/release depth differs substantially;
- repository identity/version/update conventions are not yet encoded in a machine-readable manifest;
- common files are copied, so there is no reliable drift detection.

## Resulting blueprint decisions

1. Use a **core standard plus profiles**, not a monolithic boilerplate.
2. Add a **machine-readable manifest** to enrolled plugins.
3. Split shared content into **exact-managed**, **validated**, and **plugin-specific** ownership.
4. Use **PR-based propagation** rather than direct cross-repository writes.
5. Treat GitHub template repositories as optional bootstrapping only.
6. Use **reusable workflows** for stable common CI logic after the baseline is proven.
7. Delegate block scaffolding to **`@wordpress/create-block`**.
8. Add Plugin Check and Playground only where they provide concrete value.
9. Do not make a check required until it has been proven stable on a branch.
