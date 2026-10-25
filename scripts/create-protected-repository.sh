#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/create-protected-repository.sh OWNER/REPO --profile public|private \
    --template OWNER/PROJECT-TEMPLATE [--check "REAL CI JOB"]... [--dry-run]

Creates a new GitHub repository from a real project template and immediately
applies mandatory CI/PR rulesets. Does not copy GitHub settings from a template.
Default required GitHub Actions check: test. Use --check if your CI job differs.
EOF
}
repo=""; profile=""; template=""; checks=(); dry_run=false
while (($#)); do
  case "$1" in
    --profile)
      [[ $# -ge 2 ]] || { echo "Missing profile" >&2; exit 2; }
      profile="$2"; shift 2 ;;
    --template)
      [[ $# -ge 2 ]] || { echo "Missing template" >&2; exit 2; }
      template="$2"; shift 2 ;;
    --check)
      [[ $# -ge 2 && "$2" =~ [^[:space:]] ]] || { echo "Invalid check" >&2; exit 2; }
      checks+=("$2"); shift 2 ;;
    --dry-run) dry_run=true; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "Unknown option $1" >&2; exit 2 ;;
    *)
      [[ -z "$repo" ]] || { echo "One target repository only" >&2; exit 2; }
      repo="$1"; shift ;;
  esac
done

for name in "$repo" "$template"; do
  [[ "$name" =~ ^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$ ]] || { echo "Invalid OWNER/REPO or template" >&2; exit 2; }
done
[[ "$profile" == public || "$profile" == private ]] || { echo "Require --profile public|private" >&2; exit 2; }
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
args=("$repo" --profile "$profile")
for check in "${checks[@]}"; do args+=(--check "$check"); done

if [[ "$dry_run" == true ]]; then
  printf "Would create: "; printf '%q ' gh repo create "$repo" "--$profile" --template "$template"; echo
  bash "$root/scripts/apply-rulesets.sh" "${args[@]}" --dry-run
  exit 0
fi
command -v gh >/dev/null 2>&1 || { echo "gh CLI required" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "jq required" >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "Run gh auth login first" >&2; exit 1; }
if gh api "repos/$repo" >/dev/null 2>&1; then
  echo "$repo already exists; refusing to overwrite" >&2; exit 1
fi
template_info="$(gh api "repos/$template")"
[[ "$(jq -r '.is_template // false' <<<"$template_info")" == true ]] || {
  echo "$template is not marked as a GitHub template repository" >&2; exit 1;
}
[[ "$(jq -r '.default_branch' <<<"$template_info")" == main ]] || {
  echo "Project template must use main" >&2; exit 1;
}
gh api "repos/$template/contents/.github/workflows" >/dev/null 2>&1 || {
  echo "Template needs an actual .github/workflows CI workflow first" >&2; exit 1;
}

gh repo create "$repo" "--$profile" --template "$template"
if ! bash "$root/scripts/apply-rulesets.sh" "${args[@]}"; then
  echo "WARNING: repository was created but protection is NOT fully verified." >&2
  echo "Do not merge until the new repository's Rulesets are fixed." >&2
  exit 1
fi
echo "Protected: https://github.com/$repo"
echo "Next: verify a real PR actually emits the selected checks; no fake tests."
