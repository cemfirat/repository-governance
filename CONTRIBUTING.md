# Contributing

Thanks for considering an improvement to this repository.

## Scope

Good contributions are small and focused, for example:

- correcting a GitHub ruleset field
- improving safety checks in the helper script
- improving documentation
- adding validation that catches a real configuration mistake

Please avoid adding organization-specific secrets, internal repository names, credentials, customer data, or private operational details.

## Pull requests

1. Create a branch from `main`.
2. Keep the change focused.
3. Run the local checks where possible:

   ```bash
   jq empty rulesets/*.json
   bash -n scripts/apply-rulesets.sh
   bash scripts/apply-rulesets.sh example/repository --dry-run >/dev/null
   ```

4. Open a pull request and explain the policy or behavior change.
5. Wait for the repository validation workflow to pass.

Changes to bypass behavior, deletion protection, force-push protection, required approvals, or required status checks should be called out explicitly in the pull request description.
