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

`consal init --create` creates a brand-new GitHub repo (never a fork)
and pushes the sub-config to it in one step; plain `consal init` against
an existing project detects and adopts its `origin` remote. `consal
attach` wraps the interactive planning/intervention session, so `dco`
itself is never invoked directly by a user, only by consal.

Not yet built:
- **A scheduling/polling loop.** `consal run`/`consal plan` each perform
  exactly one tick. Running them repeatedly (cron, a shell loop,
  `watch`) is up to you for now, deliberately out of scope for
  `scheduler.py`.
- **Configurable oversight granularity.** A stated future goal, not V1
  scope. See `CONSAL_GOALS.md`'s "Configurability as a goal."

## Usage

Prerequisites, once per host (`consal doctor`, see below, checks all of
this at once): `dco` (with `--up-only` support — `dco --help` should
mention it), `@devcontainers/cli` (`devcontainer` on `PATH`), `gh`
authenticated as yourself (`gh auth status`), `CONSAL_GH_PAT` set (a PAT
scoped to exactly the target repo, never your full personal access — see
`CONSAL_GOALS.md`'s isolation goals), `CLAUDE_CODE_OAUTH_TOKEN` set (a
long-lived token from `claude setup-token`, so headless turns can
authenticate).

Per project, one of:

```sh
mkdir your-project && cd your-project
consal init --repo owner/name --create   # brand-new project: creates the
                                          # GitHub repo (never a fork) and
                                          # pushes the sub-config to it
```

```sh
cd your-existing-project                 # already a git repo with an
consal init                              # 'origin' remote: detected and
                                          # adopted automatically
```

Either way, this generates `.devcontainer/consal/` (the sandboxed
profile: firewall allowlist, guardrail hook, `containerEnv` wiring) and
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
consal doctor   # verify the setup is actually healthy, not just configured,
                # including that CONSAL_GH_PAT itself can push to the repo
consal attach   # interactive session: tell Claude the project idea, it
                # proposes PLAN.md, iterate on it together
consal plan     # decompose PLAN.md into GitHub issues (skips ones already
                # filed, via a marker in each issue's body)
consal run      # one autonomous tick: bring up the container, pick an
                # open issue, dispatch a real turn, record the result
```

Re-running `consal plan` after editing `PLAN.md` only files issues for
sections that don't already have one. `consal attach` is also the way to
intervene directly at any point once autonomous work has started — same
command, not a different one.

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
