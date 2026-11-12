#!/usr/bin/env bash
# Ask for the Anthropic API key (hidden input) and save it to the project's .env.
set -euo pipefail
cd "$(dirname "$0")/.."

printf "Paste your Anthropic API key and press Enter (it will not be shown): "
read -rs key
echo
key="$(printf '%s' "$key" | tr -d '[:space:]"'"'")"

if [[ "$key" != sk-ant-api* && "$key" != sk-ant-usr* ]]; then
  echo "That doesn't look like an Anthropic key (keys start with sk-ant-api or sk-ant-usr, from console.anthropic.com/settings/keys). Nothing was saved."
  exit 1
fi

cat > .env <<EOF
# Anthropic API key for run_llm_links.py. Listed in .gitignore; never commit it.
ANTHROPIC_API_KEY=$key
EOF
chmod 600 .env
echo "Saved to .env (key ending in ...${key: -4}). You can close this tab."
