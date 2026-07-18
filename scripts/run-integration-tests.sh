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

# devcontainer's verbose `docker run` logging echoes every containerEnv
# value verbatim, including secrets passed via ${localEnv:...} -- a real
# CLAUDE_CODE_OAUTH_TOKEN leaked this way once already (into this file,
# then into an AI conversation reading it). Redact known secret env vars
# by literal string match (not regex, to avoid metacharacter issues) by
# streaming pytest's combined output through this filter *before* any of
# it touches disk, rather than writing raw output to a file first and
# redacting afterward -- that earlier approach left a window, however
# brief, where an unredacted copy existed on disk. Streaming means no
# unredacted copy is ever written anywhere, not even transiently.
#
# Uses `python3 -c` (script as an argument), not `python3 - <<PYEOF`
# (script piped via heredoc-stdin) -- verified by hand that the heredoc
# form is a real bug here: `python3 -` reads the *program itself* from
# stdin, which consumes the same stdin the piped pytest output needs to
# land on, so the redaction loop below would silently never see any
# data. `-c` leaves stdin free for the actual pipe.
REDACT_PY='
import os
import sys

secrets = []
for var in ("CLAUDE_CODE_OAUTH_TOKEN", "EIGEN_GH_PAT"):
    value = os.environ.get(var)
    if value:
        secrets.append((var, value))

for line in sys.stdin:
    for var, value in secrets:
        line = line.replace(value, f"***REDACTED:{var}***")
    sys.stdout.write(line)
    sys.stdout.flush()
'

# set +e / capture PIPESTATUS / set -e, not `pipeline || true`: verified
# by hand that appending `|| true` clobbers PIPESTATUS back to 0 (it
# counts as its own trivial pipeline), while omitting it entirely lets
# `set -e` kill the script the instant the pipeline's exit status is
# nonzero, before this script can even read it. Toggling -e off only
# around the pipeline is the pattern that actually preserves both the
# real exit code and forward progress.
set +e
{
  echo "=== eigen integration tests: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  uv run pytest -m integration -v --tb=short
} 2>&1 | python3 -c "$REDACT_PY" > "$out_file"
status="${PIPESTATUS[0]}"
set -e

echo "exit code: $status" >> "$out_file"
echo "Integration test output written to $out_file (exit $status)"
exit "$status"
