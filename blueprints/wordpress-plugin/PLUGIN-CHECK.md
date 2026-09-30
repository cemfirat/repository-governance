# WordPress Plugin Check policy

Status: **adopted as an optional shared blueprint capability**

Pilot: `cemfirat/wordpress-doctype-Inserter` PR #11.

## Decision

Mediated Plugin Check is useful, but its policy must match the plugin's actual distribution model.

The shared composite action is:

```text
blueprints/wordpress-plugin/plugin-check
```

It wraps the official `WordPress/plugin-check-action` at immutable reviewed commit:

```text
10857da14b6c2246d15402b3e69f777edcf8c12e
```

That commit corresponds to the reviewed v1.1.9 action used by the pilot.

## Required input

Consumers must pass the actual built/installable plugin directory:

```yaml
- uses: cemfirat/repository-governance/blueprints/wordpress-plugin/plugin-check@<pinned-governance-sha>
  with:
    build-dir: ${{ runner.temp }}/plugin-build/example-plugin
```

The repository must contain an enrolled `.ccf-wordpress-plugin.json` at its repository root.

## Distribution-aware categories

For `distribution.channel: wordpress.org`:

- general
- plugin_repo
- security
- performance
- accessibility

For `github-releases` or `none`:

- general
- security
- performance
- accessibility

The external-distribution policy deliberately excludes WordPress.org directory-only rules such as updater/directory submission policy while retaining cross-distribution quality checks.

## Safety rules

- package first, check the package second;
- do not run Plugin Check on a production WordPress site;
- use the canonical manifest plugin slug, not a GitHub repository name or build-folder name;
- do not globally ignore warning/error codes to force green CI;
- keep Plugin Check supplemental to plugin-specific regression/integration tests;
- keep the official action pinned to an immutable reviewed commit;
- review upstream action/plugin changes before updating that pin.

## Pilot evidence

The Doctype Inserter pilot exposed both genuine and contextual findings:

- a real missing `Tested up to` value was corrected;
- WordPress.org updater/trademark-style policy was inappropriate for intentional GitHub distribution;
- the action's slug override was necessary because the release-folder name is not the canonical plugin slug;
- two generic nonce recommendations were reviewed manually rather than changing read-only/core-driven behavior merely to silence a scanner.

After the policy was narrowed to the correct distribution categories, the official Plugin Check job and the existing regression/WordPress matrix were green on the merged pilot.

## Adoption rule

Plugin Check is not automatically required for every enrolled repository.

Adopt it when:

1. deterministic installable package contents exist;
2. the package can be built in CI;
3. initial findings have been reviewed;
4. branch CI is green;
5. only then may its stable check name become a merge gate.
