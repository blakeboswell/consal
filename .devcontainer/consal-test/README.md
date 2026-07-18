# consal-test sub-config

Fixture for `tests/integration/test_container.py`, exercising
`ensure_container_up`/`run_turn` against a real `dco`/`devcontainer`
container. Not the production "consal" sub-config `config.generate_subconfig`
produces (this one has no PAT injection, and its own copy of
`guardrail-hook.sh` isn't wired up via `.claude/settings.json`; it's here
only to satisfy `validate_subconfig`'s check, not because this fixture
exercises hook enforcement). This fixture only needs to prove the
container comes up and `devcontainer exec ... -- claude -p` works.

Does carry `"CLAUDE_CODE_OAUTH_TOKEN": "${localEnv:CLAUDE_CODE_OAUTH_TOKEN}"`
in `containerEnv`, though. Without it `claude -p` fails with "Not logged
in" regardless of everything else working (found via a real integration
test run, not designed upfront). Subscription token (`claude
setup-token`), not `ANTHROPIC_API_KEY`: draws against the Pro/Max/Team
plan's usage limits rather than separate metered billing. Requires that
env var actually set on the host running the integration suite.

Shares `../Dockerfile` (and therefore `../allowlist.txt`, and
`../init-firewall.sh`) with the default profile. See the comment at the
top of `../init-firewall.sh` for why a sub-config pointing `dockerfile` at
`../Dockerfile` can't have its own distinct allowlist without either
editing the shared one or using a non-shared Dockerfile. Fine here: the
shared allowlist is empty (firewall disabled), which is exactly what this
fixture wants.
