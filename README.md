# consal

A self-driving development system: point it at a project idea and it
decomposes a plan into GitHub issues, then works them autonomously inside
a `dco`-managed container, with GitHub itself (issues/PRs) as the
steering interface.

See [`CONSAL_GOALS.md`](./CONSAL_GOALS.md) for the full design rationale
and the decisions this repo's structure follows.

## Status

The core loop works end to end: given a project with open GitHub issues,
`consal run` picks one, dispatches a real `claude -p` turn inside a
sandboxed, network-locked-down container, and records the result,
verified against a live GitHub repo and a live container, not just mocks.
`consal plan` decomposes a `PLAN.md` into GitHub issues the same way,
one dispatched turn, idempotent via a marker in each issue's body (see
`CONSAL_GOALS.md`'s "Plan decomposition" decision).

Not yet built:
- **Wrapping the interactive attach flow.** The interactive planning
  session itself (step 2 of the workflow in `CONSAL_GOALS.md`) is just
  `dco --claude` directly; no consal command wraps it yet, the one place
  a user still has to know `dco`'s name.
- **A scheduling/polling loop.** `consal run`/`consal plan` each perform
  exactly one tick. Running them repeatedly (cron, a shell loop,
  `watch`) is up to you for now, deliberately out of scope for
  `scheduler.py`.
- **Configurable oversight granularity.** A stated future goal, not V1
  scope. See `CONSAL_GOALS.md`'s "Configurability as a goal."

## Usage

Prerequisites, once per host:

- [`dco`](https://github.com/blakeboswell/dco) installed, with `--up-only`
  support (`dco --help` should mention it)
- [`@devcontainers/cli`](https://github.com/devcontainers/cli) installed
  (`devcontainer` on `PATH`)
- `gh` installed and authenticated (`gh auth status`)
- `CONSAL_GH_PAT` set: a PAT scoped to exactly the target repo, never
  your full personal access (see `CONSAL_GOALS.md`'s isolation goals)
- `CLAUDE_CODE_OAUTH_TOKEN` set: a long-lived token from
  `claude setup-token`, so headless turns can authenticate

Run `consal doctor` (see below) to check all of this at once.

Per project, a git repo with at least one commit (`dco`'s git-identity
sync and the guardrail hook's branch-detection logic both expect a real
repo):

```sh
cd your-project
consal init --repo owner/name
```

Generates `.devcontainer/consal/` (the sandboxed profile: firewall
allowlist, guardrail hook, `containerEnv` wiring) and
`.consal/config.toml`:

```toml
sub_config = "consal"
repo = "owner/name"
```

`project_id` (namespaces runtime state under `~/.consal/<project_id>/`)
isn't set automatically. Add it yourself, or pass `--project-id` on
every `doctor`/`run` call. CLI flags always take precedence over this
file; `consal init` merges new values into it rather than overwriting,
so re-running `init` to add one setting doesn't lose another.

Then:

```sh
consal doctor   # verify the setup is actually healthy, not just configured
consal plan     # decompose PLAN.md into GitHub issues (skips ones already
                # filed, via a marker in each issue's body)
consal run      # one autonomous tick: bring up the container, pick an
                # open issue, dispatch a real turn, record the result
```

`consal plan` reads `PLAN.md` at the workspace root, the file the
interactive planning session (step 2 of the workflow in
`CONSAL_GOALS.md`) produces. Re-running it after editing the plan only
files issues for sections that don't already have one.

## Development

```sh
uv sync                # install deps into .venv
uv run pytest          # fast unit tests only
uv run consal doctor   # self-consistency / reachability checks
```

The integration tier (`pytest -m integration`) hits real `gh`/`dco`/
`devcontainer` and can't run inside this repo's own dev sandbox: no
Docker there. Run it on the host instead:

```sh
./scripts/run-integration-tests.sh
```

Writes to `.integration-results/latest.txt` (gitignored), readable from
inside the sandbox too, since it bind-mounts this same repo directory.
