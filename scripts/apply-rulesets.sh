#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/apply-rulesets.sh OWNER/REPO [options]

Options:
  --check "CHECK NAME"              Add a required status check. Repeat as needed.
  --require-conversation-resolution Require all PR conversations to be resolved.
  --dry-run                         Print payloads without contacting GitHub.
  -h, --help                        Show this help.

Examples:
  bash scripts/apply-rulesets.sh OWNER/REPO --dry-run

  bash scripts/apply-rulesets.sh OWNER/REPO \
    --check "Build, typecheck and test" \
    --check "Smoke test"

Notes:
  - The target repository must already have a main branch.
  - Run CI at least once before adding required status checks so the check names are known.
  - The script refuses to continue if either standard ruleset name already exists.
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
      [[ -n "$2" ]] || { echo "--check must not be empty" >&2; exit 2; }
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
[[ "$repo" =~ ^[^/]+/[^/]+$ ]] || {
  echo "Repository must be in OWNER/REPO form." >&2
  exit 2
}

command -v jq >/dev/null 2>&1 || {
  echo "Required command not found: jq" >&2
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
      jq -R 'select(length > 0) | {context: .}' |
      jq -s 'unique_by(.context)'
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

command -v gh >/dev/null 2>&1 || {
  echo "Required command not found: gh" >&2
  exit 1
}

gh auth status >/dev/null 2>&1 || {
  echo "GitHub CLI is not authenticated. Run: gh auth login" >&2
  exit 1
}

echo "Checking target repository..."
gh api "repos/$repo" >/dev/null
gh api "repos/$repo/branches/main" >/dev/null

existing="$(
  gh api "repos/$repo/rulesets" --jq '.[].name'
)"

for expected in "main protection - hard guardrails" "main protection - merge gates"; do
  if grep -Fxq "$expected" <<<"$existing"; then
    echo "Ruleset already exists in $repo: $expected" >&2
    echo "No changes were made." >&2
    exit 1
  fi
done

echo "Creating hard guardrails in $repo..."
hard_response="$(
  gh api --method POST "repos/$repo/rulesets" --input "$hard_file"
)"
hard_id="$(jq -er '.id' <<<"$hard_response")"

echo "Creating merge gates in $repo..."
if ! gh api --method POST "repos/$repo/rulesets" --input "$merge_payload" >/dev/null; then
  echo "Merge-gates creation failed. Attempting to roll back hard guardrails..." >&2
  if gh api --method DELETE "repos/$repo/rulesets/$hard_id" >/dev/null 2>&1; then
    echo "Rollback succeeded." >&2
  else
    echo "Rollback failed. Review rulesets in $repo manually." >&2
  fi
  exit 1
fi

created="$(
  gh api "repos/$repo/rulesets" --jq '.[].name'
)"

for expected in "main protection - hard guardrails" "main protection - merge gates"; do
  if ! grep -Fxq "$expected" <<<"$created"; then
    echo "Verification failed: missing ruleset '$expected'." >&2
    exit 1
  fi
done

echo "Created and verified both rulesets in $repo."
echo "Review them in GitHub: Settings -> Rules -> Rulesets"
