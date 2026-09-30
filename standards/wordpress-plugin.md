# WordPress Plugin Repository Standard

This document defines the shared repository baseline for public WordPress plugins maintained under the Cem Firat GitHub account.

The goal is consistency in presentation, metadata, licensing, releases and repository hygiene without forcing unrelated plugins into the same internal architecture.

## 1. Shared presentation

Every public WordPress plugin repository should use the shared repository banner at the top of `README.md`:

```html
<p align="center">
  <img src="https://raw.githubusercontent.com/cemfirat/repository-governance/main/assets/brand-banner.webp" alt="Cem Firat creative consultancy artwork" width="900" />
</p>
```

Repositories should also contain the shared `assets/logo.svg` from this governance repository.

The shared artwork establishes a recognizable family identity. Product-specific screenshots or diagrams can be added below it when useful.

## 2. README baseline

The README should normally contain:

1. shared brand banner
2. plugin title
3. concise one-paragraph purpose
4. author, license and runtime requirements
5. current release/development status when relevant
6. feature or behavior overview
7. installation/update instructions
8. important compatibility or security notes
9. development/release information when the repository is intended for contributors
10. license statement

Documentation should describe only behavior that is implemented and verified. Planned functionality belongs in issues or roadmap documentation rather than being presented as current capability.

## 3. WordPress metadata

The main plugin header and `readme.txt` must agree on:

- plugin name
- version / stable tag
- minimum WordPress version
- minimum PHP version
- license
- text domain where applicable

Public plugins should normally include:

- `Plugin URI`
- `Author`
- `Author URI`
- explicit and internally consistent license metadata
- an explicit `Update URI` when GitHub is the intended update source

GPL-licensed plugins should normally use `GPL-2.0-or-later` plus the matching GPL license URI. A repository that deliberately uses another licensing model must declare that model explicitly; the shared blueprint must not silently convert it to GPL.

Requirements should reflect the code actually used, not arbitrary version preferences.

## 4. Repository and package files

The repository-level baseline is normally:

- `README.md`
- `CHANGELOG.md`
- `.gitignore`
- `assets/logo.svg`
- `.github/` when CI, release automation or repository-specific templates are used

The installable WordPress package normally includes:

- the main plugin PHP file
- `readme.txt`
- `LICENSE` when the declared licensing model requires a distributed license file

For most plugins the package root is the repository root. Repositories that deliberately keep the installable plugin under a subdirectory may declare that package root in the blueprint manifest rather than duplicating or moving repository-level documentation.

Additional files such as `SECURITY.md`, `CONTRIBUTING.md`, `docs/`, `tests/`, `scripts/`, Composer metadata or npm metadata are added when justified by the plugin.

## 5. Language and naming

Repository prose should be internally consistent. Public technical metadata and reusable repository documentation should generally use English unless a plugin is deliberately product- or audience-specific.

The repository slug, plugin directory, main plugin filename, text domain, release ZIP name and updater identity should be decided before the first stable release. Renaming any of these after public update distribution begins can break update or installation continuity.

## 6. Licensing

Licensing is never inferred from another plugin and is never changed merely to satisfy the blueprint.

For `GPL-2.0-or-later` plugins managed by the shared blueprint, the installable package must contain the complete GPL v2 license text in `LICENSE`, and the plugin header/readme metadata must remain consistent.

Plugins with an intentionally different license may use the blueprint's declared-license mode. In that mode the blueprint validates the declared metadata but does not create, replace or reinterpret a license file.

Do not publish a package with contradictory or misleading license metadata.

## 7. Packaging

Release ZIP creation should be deterministic and explicit.

A package script should define exactly which files enter the ZIP and should exclude development-only content such as:

- `.git/`
- local build output not required at runtime
- test fixtures that do not belong in production
- credentials or environment files
- editor/OS artifacts

The resulting plugin directory name inside the ZIP must remain stable across releases.

## 8. Testing and CI

CI is not added merely for appearance.

Before a workflow becomes a required merge gate:

1. its checks must have a clear purpose;
2. equivalent local or static checks should be understood;
3. the workflow must run and pass on the feature branch before a pull request is opened;
4. its check names should be stable;
5. unnecessary matrix combinations should be avoided.

**Repository rule:** no pull request is opened before the relevant branch CI is green.

At minimum, public PHP plugins should have syntax validation. Behavior-changing code should gain focused regression coverage where practical.

Real WordPress integration or HTTP tests are preferred for behavior that depends on WordPress lifecycle hooks, installation/update behavior or generated frontend output.

The official WordPress Plugin Check is an optional shared quality layer once deterministic installable package contents exist. Run it against those package contents, not against a production site. For external/GitHub distribution, use cross-distribution categories (general, security, performance, accessibility) and do not apply WordPress.org-directory-only policy accidentally. For WordPress.org distribution, include the directory-policy category. Do not hide findings through blanket suppressions; review exceptions individually.

## 9. Releases and updates

For plugins distributed through GitHub Releases:

- a release is created only from reviewed/tested `main`;
- the release tag must correspond to the plugin version;
- release notes should come from the matching changelog section;
- the release ZIP should be built from the tested source;
- existing published releases must not be silently overwritten;
- WordPress update discovery and installation should be tested when the plugin provides self-updates.

The exact tag naming scheme may differ between repositories if an established updater already depends on it. New repositories should choose one convention before their first stable release and keep it stable.

## 10. Main-branch governance

Public plugin repositories should use the common repository-governance approach where supported:

- protect `main` from deletion;
- prevent force-pushes;
- use focused branches and pull requests;
- make reliable CI checks required only after those checks are proven stable.

Emergency/admin merge bypass must not also grant destructive branch bypass.

## 11. Plugin-specific differences

Consistency does not mean identical architecture.

A simple one-file utility and a large booking system should share repository presentation, metadata and release hygiene while keeping different:

- test depth
- dependency management
- file structure
- UI architecture
- integration coverage
- security documentation
- release qualification

Technical differences are acceptable when they are deliberate and documented.

## 12. New-plugin checklist

Before the first stable release:

- [ ] shared README banner added
- [ ] shared `assets/logo.svg` added
- [ ] plugin header finalized
- [ ] repository/directory/main-file/text-domain identity finalized
- [ ] WordPress and PHP minimum versions verified
- [ ] license mode and metadata are explicit and internally consistent
- [ ] managed GPL packages contain the complete canonical `LICENSE`
- [ ] `readme.txt` matches plugin metadata
- [ ] `CHANGELOG.md` created
- [ ] packaging contents defined
- [ ] PHP syntax validation passes
- [ ] focused behavior tests added where needed
- [ ] release/update flow verified if used
- [ ] main-branch protection configured appropriately

Related tracking issue: [#8](https://github.com/cemfirat/repository-governance/issues/8).
