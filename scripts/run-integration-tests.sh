#!/usr/bin/env bash
# Run Eigen's integration test tier (real gh/dco/devcontainer) and write
# the result to a file inside the repo. Run this on the host — this
# repo's own dev sandbox has no Docker access, so `dco`/`devcontainer`
# aren't reachable from in there. Since the sandbox bind-mounts this same
# repo directory, the output file is readable from inside it afterward.
set -euo pipefail
cd "$(dirname "$0")/.."

# CLAUDE_CODE_OAUTH_TOKEN is host-wide and personal, not eigen-specific,
# so it deliberately isn't auto-loaded into every shell (unlike
# EIGEN_GH_PAT, which lives in this repo's own gitignored .envrc via
# direnv) -- pulled in here, scoped to just running tests.
SECRETS_FILE="${EIGEN_SECRETS_FILE:-$HOME/.config/claude-code/secrets.env}"
if [[ -f "$SECRETS_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$SECRETS_FILE"
fi

mkdir -p .integration-results
out_file=".integration-results/latest.txt"
raw_file="$(mktemp)"
trap 'rm -f "$raw_file"' EXIT

{
  echo "=== eigen integration tests: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  uv run pytest -m integration -v --tb=short
} > "$raw_file" 2>&1 && status=0 || status=$?

echo "exit code: $status" >> "$raw_file"

# devcontainer's verbose `docker run` logging echoes every containerEnv
# value verbatim, including secrets passed via ${localEnv:...} -- a real
# CLAUDE_CODE_OAUTH_TOKEN leaked this way once already (into this file,
# then into an AI conversation reading it). Redact known secret env vars
# by literal string match (not regex, to avoid metacharacter issues)
# before this ever gets written to the file anything reads back.
python3 - "$raw_file" "$out_file" <<'PYEOF'
import os
import sys

raw_path, out_path = sys.argv[1], sys.argv[2]
content = open(raw_path, "r", errors="replace").read()

for var in ("CLAUDE_CODE_OAUTH_TOKEN", "EIGEN_GH_PAT"):
    value = os.environ.get(var)
    if value:
        content = content.replace(value, f"***REDACTED:{var}***")

with open(out_path, "w") as f:
    f.write(content)
PYEOF

echo "Integration test output written to $out_file (exit $status)"
exit "$status"
