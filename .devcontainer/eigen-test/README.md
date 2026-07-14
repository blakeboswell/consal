# eigen-test sub-config

Fixture for `tests/integration/test_container.py` — exercises
`ensure_container_up`/`run_turn` against a real `dco`/`devcontainer`
container. Not the production "eigen" sub-config `config.generate_subconfig`
produces (this one has no PAT injection, and its own copy of
`guardrail-hook.sh` isn't wired up via `.claude/settings.json` — it's here
only to satisfy `validate_subconfig`'s check, not because this fixture
exercises hook enforcement); this fixture only needs to prove the
container comes up and `devcontainer exec ... -- claude -p` works.

Does carry `"ANTHROPIC_API_KEY": "${localEnv:ANTHROPIC_API_KEY}"` in
`containerEnv`, though — without it `claude -p` fails with "Not logged in"
regardless of everything else working (found via a real integration test
run, not designed upfront). Requires that env var actually set on the
host running the integration suite.

Shares `../Dockerfile` (and therefore `../allowlist.txt`, and
`../init-firewall.sh`) with the default profile — see the comment at the
top of `../init-firewall.sh` for why a sub-config pointing `dockerfile` at
`../Dockerfile` can't have its own distinct allowlist without either
editing the shared one or using a non-shared Dockerfile. Fine here: the
shared allowlist is empty (firewall disabled), which is exactly what this
fixture wants.
