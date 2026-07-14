# eigen-test sub-config

Fixture for `tests/integration/test_container.py` — exercises
`ensure_container_up`/`run_turn` against a real `dco`/`devcontainer`
container. Not the production "eigen" sub-config `config.generate_subconfig`
will eventually produce (that one still needs its own guardrail hook and PAT
injection); this one only needs to prove the container comes up and
`devcontainer exec ... -- claude -p` works.

Shares `../Dockerfile` (and therefore `../allowlist.txt`, and
`../init-firewall.sh`) with the default profile — see the comment at the
top of `../init-firewall.sh` for why a sub-config pointing `dockerfile` at
`../Dockerfile` can't have its own distinct allowlist without either
editing the shared one or using a non-shared Dockerfile. Fine here: the
shared allowlist is empty (firewall disabled), which is exactly what this
fixture wants.
