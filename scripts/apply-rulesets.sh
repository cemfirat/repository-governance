#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/apply-rulesets.sh OWNER/REPO --profile public|private [--check "GITHUB ACTIONS JOB"]... [--dry-run]
Defaults: mandatory GitHub Actions check "test"; PR required; 0 reviewers; no bypass.
--check replaces the default and can be repeated for multiple real CI jobs.
Requires gh, jq and repository administration rights for live creation.
Existing rulesets are never overwritten. This command creates, not updates.
EOF
}

repo=""
profile=""
checks=()
dry_run=false
while (($#)); do
  case "$1" in
    --profile)
      [[ $# -ge 2 ]] || { echo "Missing --profile value" >&2; exit 2; }
      profile="$2"; shift 2 ;;
    --check)
      [[ $# -ge 2 && "$2" =~ [^[:space:]] ]] || { echo "Invalid --check" >&2; exit 2; }
      checks+=("$2"); shift 2 ;;
    --require-conversation-resolution)
      shift ;; # Deprecated flag; now enforced unconditionally.
    --dry-run) dry_run=true; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "Unknown flag: $1" >&2; exit 2 ;;
    *)
      [[ -z "$repo" ]] || { echo "One OWNER/REPO only" >&2; exit 2; }
      repo="$1"; shift ;;
  esac
done
[[ "$repo" =~ ^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$ ]] || { echo "Invalid OWNER/REPO" >&2; exit 2; }
[[ "$profile" == public || "$profile" == private ]] || { echo "Require --profile public|private" >&2; exit 2; }
command -v jq >/dev/null 2>&1 || { echo "jq is required" >&2; exit 1; }

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
hard="$root/rulesets/main-protection-hard-guardrails.json"
base="$root/rulesets/main-protection-merge-gates-base.json"
profile_file="$root/profiles/$profile.json"
[[ -f "$hard" && -f "$base" && -f "$profile_file" ]] || { echo "Missing policy templates" >&2; exit 1; }
jq -e --arg p "$profile" '.profile == $p and .visibility == $p and (.default_required_checks | type == "array" and length > 0)' "$profile_file" >/dev/null

if (( ${#checks[@]} == 0 )); then
  mapfile -t checks < <(jq -r '.default_required_checks[]' "$profile_file")
fi
checks_json="$(printf '%s\n' "${checks[@]}" |
  jq -R 'select(length > 0) | {context: ., integration_id: 15368}' |
  jq -s 'unique_by(.context)')"
jq -e 'length > 0' <<<"$checks_json" >/dev/null || { echo "A real required CI check is mandatory" >&2; exit 1; }

payload="$(mktemp)"
trap 'rm -f "$payload"' EXIT
jq --argjson checks "$checks_json" '
  .bypass_actors = [] |
  .rules |= map(
    if .type == "pull_request"
    then .parameters.required_approving_review_count = 0 |
         .parameters.required_review_thread_resolution = true |
         .parameters.require_extra_approval_for_unattributed_changes = false
    elif .type == "required_status_checks"
    then .parameters.required_status_checks = $checks |
         .parameters.strict_required_status_checks_policy = true
    else . end
  )
' "$base" > "$payload"
echo "Profile: $profile. Required GitHub Actions checks: $(jq -r '[.[].context] | join(", ")' <<<"$checks_json")"

if [[ "$dry_run" == true ]]; then
  echo "=== hard guardrails ==="; jq . "$hard"
  echo "=== merge gates ==="; jq . "$payload"
  exit 0
fi

command -v gh >/dev/null 2>&1 || { echo "gh CLI is required" >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "Run gh auth login first" >&2; exit 1; }
metadata="$(gh api "repos/$repo")"
[[ "$(jq -r '.visibility' <<<"$metadata")" == "$profile" ]] || { echo "Visibility mismatch; no changes" >&2; exit 1; }
[[ "$(jq -r '.default_branch' <<<"$metadata")" == main ]] || { echo "Default branch must be main" >&2; exit 1; }
gh api "repos/$repo/branches/main" >/dev/null
existing="$(gh api "repos/$repo/rulesets" --jq '.[].name')"
for name in "main protection - hard guardrails" "main protection - merge gates"; do
  if grep -Fxq "$name" <<<"$existing"; then
    echo "Ruleset already exists: $name. No changes made." >&2; exit 1
  fi
done

hard_response="$(gh api --method POST "repos/$repo/rulesets" --input "$hard")"
hard_id="$(jq -er '.id' <<<"$hard_response")"
if ! merge_response="$(gh api --method POST "repos/$repo/rulesets" --input "$payload")"; then
  echo "Merge gate failed. Hard guardrails $hard_id intentionally remain; inspect Settings." >&2
  exit 1
fi
merge_id="$(jq -er '.id' <<<"$merge_response")"
hard_actual="$(gh api "repos/$repo/rulesets/$hard_id")"
merge_actual="$(gh api "repos/$repo/rulesets/$merge_id")"
jq -e '.enforcement == "active" and .bypass_actors == [] and ([.rules[].type]|sort) == (["deletion","non_fast_forward"]|sort)' <<<"$hard_actual" >/dev/null
jq -e --argjson checks "$checks_json" '
  .enforcement == "active" and .bypass_actors == [] and
  ([.rules[] | select(.type=="pull_request") | .parameters |
    (.required_approving_review_count==0 and .required_review_thread_resolution==true)] == [true]) and
  ([.rules[] | select(.type=="required_status_checks") | .parameters |
    (.strict_required_status_checks_policy==true and
     ([.required_status_checks[]|{context,integration_id}]|sort_by(.context))==($checks|sort_by(.context)))] == [true])
' <<<"$merge_actual" >/dev/null || {
  echo "Verification failed: review GitHub rulesets manually" >&2; exit 1;
}
echo "Verified: https://github.com/$repo/settings/rules"
