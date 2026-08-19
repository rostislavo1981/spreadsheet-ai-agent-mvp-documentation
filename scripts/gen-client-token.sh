#!/usr/bin/env bash
# Generates a random pilot client token + its SHA-256 hash.
# The plaintext token goes to the Apps Script client (setClientToken).
# The hash goes to the backend's APP_CLIENT_TOKEN_HASHES env var.
set -euo pipefail

token=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
hash=$(python3 -c "import hashlib,sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest())" "$token")

echo "Client token (put in Apps Script via setClientToken):"
echo "  $token"
echo
echo "Token hash (put in backend .env as APP_CLIENT_TOKEN_HASHES):"
echo "  $hash"
