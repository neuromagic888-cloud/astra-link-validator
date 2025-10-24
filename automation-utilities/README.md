# Automation Utilities

This directory contains automation scripts for managing GitHub repository secrets and workflows.

## upsert_secrets_and_dispatch.py

A Python script to securely manage GitHub repository secrets and trigger workflows.

### Features

- **Fetch repository public key**: Retrieves the public key needed for secret encryption
- **Encrypt with PyNaCl sealed box**: Uses libsodium-based encryption for secure secret storage
- **Upsert secrets**: Creates or updates repository secrets
- **Verify secrets**: Confirms secrets were set correctly
- **Dispatch workflows**: Triggers the Quiet Link Validator workflow

### Requirements

```bash
pip install pynacl requests
```

### Usage

Set the required environment variables and run the script:

```bash
# Required
export GITHUB_TOKEN="ghp_your_token_here"

# Secrets to upsert
export NOTION_TOKEN="secret_notion_token"
export LINKCHECK_DB_ID="your_linkcheck_db_id"
export RADAR_DB_ID="your_radar_db_id"
export PROJECT_TRACKER_DB_ID="your_project_tracker_db_id"

# Optional - override repository (defaults to neuromagic888-cloud/astra-link-validator)
export GITHUB_REPOSITORY="owner/repo"

# Optional - skip workflow dispatch
export NO_DISPATCH=1

# Run the script
python automation-utilities/upsert_secrets_and_dispatch.py
```

### Security Notes

⚠️ **Important Security Considerations**

1. **Never commit secrets to version control**: Always use environment variables or secure secret management systems
2. **Token permissions**: The `GITHUB_TOKEN` must have:
   - `repo` scope (for reading/writing secrets)
   - `workflow` scope (for dispatching workflows)
3. **Use encrypted connections**: All API calls use HTTPS
4. **Secrets are encrypted**: All secrets are encrypted using PyNaCl sealed box before transmission
5. **Clean up tokens**: Rotate tokens regularly and revoke unused tokens
6. **Audit logs**: Review GitHub audit logs for secret access patterns
7. **Minimal permissions**: Use fine-grained personal access tokens when possible

### Safe Bash Fallback

If you prefer not to use Python, here's a safe bash script to upsert secrets using the GitHub CLI (`gh`):

```bash
#!/usr/bin/env bash
set -euo pipefail

# Exit on error, undefined variables, and pipe failures
# This ensures the script fails fast on any error

REPO="${GITHUB_REPOSITORY:-neuromagic888-cloud/astra-link-validator}"

echo "🔐 Upserting secrets to ${REPO}"

# Check required environment variables
: "${NOTION_TOKEN:?Error: NOTION_TOKEN is required}"
: "${LINKCHECK_DB_ID:?Error: LINKCHECK_DB_ID is required}"

# Upsert secrets using gh CLI
gh secret set NOTION_TOKEN --body "${NOTION_TOKEN}" --repo "${REPO}"
echo "✓ NOTION_TOKEN set"

gh secret set LINKCHECK_DB_ID --body "${LINKCHECK_DB_ID}" --repo "${REPO}"
echo "✓ LINKCHECK_DB_ID set"

# Optional secrets
if [[ -n "${RADAR_DB_ID:-}" ]]; then
  gh secret set RADAR_DB_ID --body "${RADAR_DB_ID}" --repo "${REPO}"
  echo "✓ RADAR_DB_ID set"
fi

if [[ -n "${PROJECT_TRACKER_DB_ID:-}" ]]; then
  gh secret set PROJECT_TRACKER_DB_ID --body "${PROJECT_TRACKER_DB_ID}" --repo "${REPO}"
  echo "✓ PROJECT_TRACKER_DB_ID set"
fi

# Verify secrets (list them - values are not shown)
echo ""
echo "📋 Verifying secrets..."
gh api "repos/${REPO}/actions/secrets" --jq '.secrets[].name' | while read -r secret_name; do
  echo "✓ ${secret_name}"
done

# Dispatch workflow (optional)
if [[ -z "${NO_DISPATCH:-}" ]]; then
  echo ""
  echo "🚀 Dispatching workflow..."
  gh workflow run quiet-link-validator.yml --repo "${REPO}"
  echo "✓ Workflow dispatched"
fi

echo ""
echo "✅ All operations completed successfully!"
```

### Using the Bash Fallback

```bash
# Make it executable
chmod +x upsert_secrets_fallback.sh

# Set environment variables and run
export NOTION_TOKEN="secret_notion_token"
export LINKCHECK_DB_ID="your_linkcheck_db_id"
./upsert_secrets_fallback.sh
```

### Troubleshooting

**Error: GITHUB_TOKEN not found**
- Ensure you've set the `GITHUB_TOKEN` environment variable
- Verify the token has correct permissions (repo, workflow)

**Error: Public key fetch failed**
- Check repository name is correct (format: `owner/repo`)
- Verify token has access to the repository

**Error: Secret verification failed**
- Wait a few seconds and retry - there may be a delay in secret propagation
- Check GitHub's status page for API issues

**Workflow dispatch failed**
- Ensure the workflow file exists: `.github/workflows/quiet-link-validator.yml`
- Verify the workflow has `workflow_dispatch` trigger enabled
- Check that the ref (branch/tag) exists

### Advanced Usage

**Upsert to a different branch:**

```bash
export WORKFLOW_REF="develop"
python automation-utilities/upsert_secrets_and_dispatch.py
```

**Only upsert secrets (skip workflow dispatch):**

```bash
export NO_DISPATCH=1
python automation-utilities/upsert_secrets_and_dispatch.py
```

### Exit Codes

- `0`: Success
- `1`: Error (missing token, API failure, verification failure, etc.)
