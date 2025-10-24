#!/usr/bin/env python3
"""
Upsert GitHub repository secrets and dispatch workflow.

This script:
1. Fetches the repository's public key for secret encryption
2. Encrypts secrets using PyNaCl sealed box (libsodium)
3. Upserts secrets to the GitHub repository
4. Verifies secrets were set correctly
5. Dispatches the Quiet Link Validator workflow

Requirements:
- PyNaCl (pip install pynacl)
- requests (pip install requests)
- GITHUB_TOKEN environment variable with repo and workflow permissions
"""

import os
import sys
import json
import base64
from typing import Dict, Optional
import requests
from nacl import encoding, public


def get_repo_public_key(repo: str, token: str) -> tuple[str, str]:
    """
    Fetch the repository's public key for secret encryption.
    
    Args:
        repo: Repository in format 'owner/repo'
        token: GitHub personal access token
        
    Returns:
        Tuple of (key_id, public_key_base64)
    """
    url = f"https://api.github.com/repos/{repo}/actions/secrets/public-key"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "astra-link-validator-automation"
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    return data["key_id"], data["key"]


def encrypt_secret(public_key_base64: str, secret_value: str) -> str:
    """
    Encrypt a secret using PyNaCl sealed box.
    
    Args:
        public_key_base64: Base64-encoded public key from GitHub
        secret_value: The secret value to encrypt
        
    Returns:
        Base64-encoded encrypted secret
    """
    public_key = public.PublicKey(public_key_base64.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def upsert_secret(repo: str, token: str, secret_name: str, encrypted_value: str, key_id: str) -> None:
    """
    Create or update a repository secret.
    
    Args:
        repo: Repository in format 'owner/repo'
        token: GitHub personal access token
        secret_name: Name of the secret
        encrypted_value: Base64-encoded encrypted secret value
        key_id: ID of the public key used for encryption
    """
    url = f"https://api.github.com/repos/{repo}/actions/secrets/{secret_name}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "astra-link-validator-automation"
    }
    
    payload = {
        "encrypted_value": encrypted_value,
        "key_id": key_id
    }
    
    response = requests.put(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    print(f"✓ Secret '{secret_name}' upserted successfully")


def verify_secret_exists(repo: str, token: str, secret_name: str) -> bool:
    """
    Verify that a secret exists in the repository.
    
    Args:
        repo: Repository in format 'owner/repo'
        token: GitHub personal access token
        secret_name: Name of the secret to verify
        
    Returns:
        True if secret exists, False otherwise
    """
    url = f"https://api.github.com/repos/{repo}/actions/secrets/{secret_name}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "astra-link-validator-automation"
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    return response.status_code == 200


def dispatch_workflow(repo: str, token: str, workflow_id: str = "quiet-link-validator.yml", ref: str = "main") -> None:
    """
    Dispatch a workflow run.
    
    Args:
        repo: Repository in format 'owner/repo'
        token: GitHub personal access token
        workflow_id: Workflow file name or ID
        ref: Git ref (branch, tag, or SHA)
    """
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/dispatches"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "astra-link-validator-automation"
    }
    
    payload = {
        "ref": ref
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    print(f"✓ Workflow '{workflow_id}' dispatched on ref '{ref}'")


def main():
    """Main execution function."""
    # Get required environment variables
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("❌ Error: GITHUB_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    # Repository (can be overridden via env var)
    repo = os.getenv("GITHUB_REPOSITORY", "neuromagic888-cloud/astra-link-validator")
    
    # Secrets to upsert (read from environment)
    secrets_to_upsert = {
        "NOTION_TOKEN": os.getenv("NOTION_TOKEN"),
        "LINKCHECK_DB_ID": os.getenv("LINKCHECK_DB_ID"),
        "RADAR_DB_ID": os.getenv("RADAR_DB_ID"),
        "PROJECT_TRACKER_DB_ID": os.getenv("PROJECT_TRACKER_DB_ID")
    }
    
    # Filter out None values
    secrets_to_upsert = {k: v for k, v in secrets_to_upsert.items() if v is not None}
    
    if not secrets_to_upsert:
        print("⚠️  Warning: No secrets provided via environment variables", file=sys.stderr)
        print("Expected: NOTION_TOKEN, LINKCHECK_DB_ID, RADAR_DB_ID, PROJECT_TRACKER_DB_ID")
        sys.exit(1)
    
    print(f"🔐 Upserting {len(secrets_to_upsert)} secret(s) to {repo}")
    
    try:
        # Step 1: Get repository public key
        print("\n1️⃣ Fetching repository public key...")
        key_id, public_key = get_repo_public_key(repo, github_token)
        print(f"✓ Public key retrieved (ID: {key_id})")
        
        # Step 2: Encrypt and upsert each secret
        print("\n2️⃣ Encrypting and upserting secrets...")
        for secret_name, secret_value in secrets_to_upsert.items():
            encrypted_value = encrypt_secret(public_key, secret_value)
            upsert_secret(repo, github_token, secret_name, encrypted_value, key_id)
        
        # Step 3: Verify secrets
        print("\n3️⃣ Verifying secrets...")
        all_verified = True
        for secret_name in secrets_to_upsert.keys():
            exists = verify_secret_exists(repo, github_token, secret_name)
            if exists:
                print(f"✓ Secret '{secret_name}' verified")
            else:
                print(f"❌ Secret '{secret_name}' not found", file=sys.stderr)
                all_verified = False
        
        if not all_verified:
            print("\n❌ Some secrets could not be verified", file=sys.stderr)
            sys.exit(1)
        
        # Step 4: Dispatch workflow (optional, can be disabled via NO_DISPATCH env var)
        if not os.getenv("NO_DISPATCH"):
            print("\n4️⃣ Dispatching Quiet Link Validator workflow...")
            ref = os.getenv("WORKFLOW_REF", "main")
            dispatch_workflow(repo, github_token, "quiet-link-validator.yml", ref)
        else:
            print("\n4️⃣ Skipping workflow dispatch (NO_DISPATCH is set)")
        
        print("\n✅ All operations completed successfully!")
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ HTTP Error: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
