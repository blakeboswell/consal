#!/usr/bin/env bash
# Run Eigen's integration test tier (real gh/dco/devcontainer) and write
# the result to a file inside the repo. Run this on the host — this
# repo's own dev sandbox has no Docker access, so `dco`/`devcontainer`
# aren't reachable from in there. Since the sandbox bind-mounts this same
# repo directory, the output file is readable from inside it afterward.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p .integration-results
out_file=".integration-results/latest.txt"

{
  echo "=== eigen integration tests: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  uv run pytest -m integration -v --tb=short
} > "$out_file" 2>&1 && status=0 || status=$?

echo "exit code: $status" >> "$out_file"
echo "Integration test output written to $out_file (exit $status)"
exit "$status"
