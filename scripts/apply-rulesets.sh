#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/apply-rulesets.sh OWNER/REPO [options]

Options:
  --check "CHECK NAME"              Add a required status check. Repeat as needed.
  --require-conversation-resolution Require all PR conversations to be resolved.
  --dry-run                         Print the payloads without changing GitHub.
  -h, --help                        Show this help.

Examples:
  scripts/apply-rulesets.sh cemfirat/example

  scripts/apply-rulesets.sh cemfirat/example \
    --check "Build, typecheck and test" \
    --check "Smoke test"

Notes:
  - The repository must already have a main branch.
  - Run CI at least once before adding required status checks so the check names are known.
  - The script stops if either standard ruleset name already exists, preventing duplicates.
EOF
}

repo=""
checks=()
require_conversation_resolution=false
dry_run=false

while (($#)); do
  case "$1" in
    --check)
      [[ $# -ge 2 ]] || { echo "Missing value for --check" >&2; exit 2; }
      checks+=("$2")
      shift 2
      ;;
    --require-conversation-resolution)
      require_conversation_resolution=true
      shift
      ;;
    --dry-run)
      dry_run=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      if [[ -n "$repo" ]]; then
        echo "Only one OWNER/REPO argument is allowed." >&2
        exit 2
      fi
      repo="$1"
      shift
      ;;
  esac
done

[[ -n "$repo" ]] || { usage >&2; exit 2; }
[[ "$repo" == */* ]] || { echo "Repository must be in OWNER/REPO form." >&2; exit 2; }

for cmd in gh jq; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "Required command not found: $cmd" >&2
    exit 1
  }
done

gh auth status >/dev/null 2>&1 || {
  echo "GitHub CLI is not authenticated. Run: gh auth login" >&2
  exit 1
}

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
hard_file="$root/rulesets/main-protection-hard-guardrails.json"
merge_file="$root/rulesets/main-protection-merge-gates-base.json"

[[ -f "$hard_file" && -f "$merge_file" ]] || {
  echo "Ruleset templates are missing." >&2
  exit 1
}

merge_payload="$(mktemp)"
trap 'rm -f "$merge_payload"' EXIT

resolution_json=false
if [[ "$require_conversation_resolution" == true ]]; then
  resolution_json=true
fi

jq --argjson resolution "$resolution_json" '
  .rules |= map(
    if .type == "pull_request"
    then .parameters.required_review_thread_resolution = $resolution
    else .
    end
  )
' "$merge_file" > "$merge_payload"

if ((${#checks[@]})); then
  checks_json="$(
    printf '%s\n' "${checks[@]}" |
      jq -R '{context: .}' |
      jq -s '.'
  )"

  tmp="$(mktemp)"
  jq --argjson checks "$checks_json" '
    .rules += [{
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "do_not_enforce_on_create": false,
        "required_status_checks": $checks
      }
    }]
  ' "$merge_payload" > "$tmp"
  mv "$tmp" "$merge_payload"
fi

if [[ "$dry_run" == true ]]; then
  echo "=== hard guardrails ==="
  jq . "$hard_file"
  echo
  echo "=== merge gates ==="
  jq . "$merge_payload"
  exit 0
fi

existing="$(
  gh api "repos/$repo/rulesets"     --jq '.[].name' 2>/dev/null || true
)"

for expected in "main protection - hard guardrails" "main protection - merge gates"; do
  if grep -Fxq "$expected" <<<"$existing"; then
    echo "Ruleset already exists in $repo: $expected" >&2
    echo "No changes were made." >&2
    exit 1
  fi
done

echo "Creating hard guardrails in $repo..."
gh api --method POST "repos/$repo/rulesets" --input "$hard_file" >/dev/null

echo "Creating merge gates in $repo..."
gh api --method POST "repos/$repo/rulesets" --input "$merge_payload" >/dev/null

echo "Created both rulesets in $repo."
echo "Verify them in GitHub: Settings -> Rules -> Rulesets"
