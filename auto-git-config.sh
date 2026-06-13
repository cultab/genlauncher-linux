#!/usr/bin/env bash
# auto-git-config.sh
# Run this before committing to set the correct author identity.
# The model name and email are updated automatically each time a new
# model revision runs in this workspace.
#
# Usage (from the genlauncher_tui repo):
#   source ../auto-git-config.sh
# or
#   eval "$(cat ../auto-git-config.sh)"

MODEL_NAME="big-pickle"
MODEL_EMAIL="big-pickle@opencode.ai"

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "Not inside a git repository" >&2
    exit 1
}

cd "$REPO_ROOT" || exit 1
git config user.name "$MODEL_NAME"
git config user.email "$MODEL_EMAIL"
echo "git config set: $MODEL_NAME <$MODEL_EMAIL>"
