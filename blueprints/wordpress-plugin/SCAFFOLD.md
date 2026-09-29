# WordPress Plugin Scaffolding

The scaffold generator creates a new repository baseline from the same WordPress plugin blueprint metadata used by audit, sync and fleet propagation.

It is intentionally conservative:

- it never creates a GitHub repository;
- it never pushes or publishes anything;
- it refuses a non-empty destination;
- it requires an explicit license mode;
- it requires an explicit distribution/update model;
- it generates only a minimal plugin entry point;
- it runs the existing blueprint audit before exposing the generated directory;
- block-plugin source scaffolding remains delegated to the official WordPress `@wordpress/create-block` toolchain.

## Simple plugin

Example:

```bash
python3 scripts/wordpress-plugin-scaffold.py \
  --destination ../wordpress-example-plugin \
  --profile simple \
  --slug wordpress-example-plugin \
  --name "WordPress Example Plugin" \
  --description "Adds a focused example capability to WordPress." \
  --license-mode managed-gpl \
  --distribution github-releases \
  --updates none \
  --repository cemfirat/wordpress-example-plugin
```

The generated plugin starts with `updates=none`. The scaffold does not claim or invent a GitHub release updater. Add and test an updater separately before changing that manifest field.

## Application plugin

The `application` profile uses the same safe baseline but signals that the repository is expected to grow deeper integration, security, privacy or operational documentation.

Example with a nested installable package:

```bash
python3 scripts/wordpress-plugin-scaffold.py \
  --destination ../example-application \
  --profile application \
  --slug example-application \
  --name "Example Application" \
  --description "Provides a larger WordPress integration for an external service." \
  --package-root wordpress \
  --license-mode managed-gpl \
  --distribution github-releases \
  --updates none \
  --repository cemfirat/example-application
```

Repository-level branding and governance files stay at the repository root while the WordPress package metadata and managed GPL license are generated below `wordpress/`.

## Declared license

The generator never guesses a non-GPL license.

A declared license must be supplied explicitly:

```bash
python3 scripts/wordpress-plugin-scaffold.py \
  --destination ../internal-plugin \
  --profile application \
  --slug internal-plugin \
  --name "Internal Plugin" \
  --description "Provides an internal WordPress integration." \
  --license-mode declared \
  --license "Proprietary / private project" \
  --distribution none \
  --updates none
```

In declared-license mode the blueprint does not create or overwrite a `LICENSE` file. Use `--license-header` only when the plugin should intentionally expose a matching WordPress plugin-header license value.

## Distribution rules

The initial scaffold supports these combinations:

| Distribution | Updates |
| --- | --- |
| `github-releases` | `none` |
| `wordpress.org` | `wordpress.org` |
| `none` | `none` |

For `github-releases`, `--repository owner/name` is required so the manifest and `Update URI` have a stable identity.

A fresh scaffold deliberately refuses `github-release-updater` because the generated source does not implement an updater.

## Generated baseline

For `simple` and `application`, the generator creates:

- `.ccf-wordpress-plugin.json`
- `.github/workflows/blueprint.yml` pinned to the reviewed blueprint action SHA
- `.gitignore`
- `README.md` with the shared brand banner
- `CHANGELOG.md`
- `assets/logo.svg`
- the main plugin PHP file
- WordPress `readme.txt`
- canonical package `LICENSE` only for `managed-gpl`

The generated PHP file contains only metadata and the direct-access guard. Product architecture is not invented by the scaffold.

## Block plugins

This generator intentionally refuses the `block` profile.

Use the official WordPress block scaffold for the product code:

```bash
npx @wordpress/create-block your-block-plugin
```

Then enroll the resulting repository in the shared blueprint. An automated governance-overlay path can be added separately once its interaction with the official scaffold is tested.

## Safety and validation

Generation happens in a temporary sibling directory. The requested destination is replaced only after the generated repository passes the existing blueprint audit.

If validation fails, the temporary output is removed and an existing destination remains untouched.

Related tracking issue: [#24](https://github.com/cemfirat/repository-governance/issues/24).
