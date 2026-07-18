# Consal: goals document for a self-driving development system

## Context

This grew out of frustration with `dco`, a bash tool for launching sandboxed
devcontainers to run Claude Code (interactively, or unattended in an
"autonomous mode" driven by GitHub Issues/PRs). Building it out surfaced a
real pattern: bash-specific footguns (a `tr -c` pipe eating a newline into a
literal character, a `false`-as-return-value bug tripping `set -e`), plus a
test suite that was reactive (added after each live failure) and mocked away
exactly the integration points that mattered, so real bugs kept surfacing
only after multi-minute live Docker/GitHub cycles instead of before shipping.
Documentation had also collapsed into README bloat: every incremental fix
got a paragraph, instead of docstrings/commit messages/a real design doc at
their appropriate altitudes.

Rather than porting the bash 1:1 to Python, we stepped back to ask what the
actual goal is, independent of how the current tool happens to implement it.
This document is the result.

Along the way we evaluated whether to adopt an existing tool instead of
building anything (the "AI agent in a sandboxed container" space turned out
to be crowded — see **Prior art** below). We also considered a Claude
Agent-SDK-driven orchestrator vs. a thin CLI launcher as competing shapes
for a single project. The actual resolution turned out to be neither: **two
separate projects**, not one — see **Architecture** below. This is the
single biggest structural decision in this document.

This was originally produced as a plan-mode artifact inside the `dco` repo.
The new project was first named **Eigen** — a math term for the value
that scales a vector's magnitude without changing its direction, matching
the actual goal: multiplying one developer's output without taking over
their direction.

**Renamed to Consal (2026-07-18).** From *consilience* — the
leaping-together of otherwise-separate things into one coherent whole —
crossed with Latin *salire* ("to leap"), and evocative of "console."
Matches the tool's actual shape at least as well as Eigen did, arguably
better: Consal is, literally, forcing a convergence of genuinely separate
pieces — isolated agent sessions, devcontainer environments, the host
machine, GitHub's own developer-facing surface, and the human
collaborator — into one coherent, GitHub-native workflow. `dco` keeps its
own name; only this project's name was ever in question.

## Architecture: two projects, not one

- **`dco`** (existing, stays roughly as-is). Its job shrinks to exactly what
  it already does well and what the user already understands deeply:
  create a sandboxed devcontainer, keep it alive, reattach to it, manage
  named sub-config profiles and persistent volumes. It's **fully
  generic** — no built-in concept of "autonomous mode," GitHub, PATs, or
  labels. **Update since this doc was first drafted:** the follow-up work
  described below (stripping `--dsp`, the shipped `autonomous` profile,
  the guardrail hook, PAT/label logic out of `dco`) is done. `dco.in` went
  638 → 348 lines, its README 274 → ~90. `dco` today is exactly the
  container-lifecycle tool described here, nothing more.
- **Consal** (new, Python). Owns everything about
  GitHub-driven autonomy: the plan-then-decompose-then-autonomous-loop
  workflow, repo/PAT setup, the label taxonomy, guardrails, scheduling, and
  the hybrid interactive/async interaction model. It **depends on `dco`**
  the way `dco` depends on `docker`/`gh`/`devcontainer` — shelling out to
  it for container lifecycle, most likely via `dco`'s existing generic
  `--sub-config` mechanism, providing its own custom profile/template
  rather than relying on `dco` to know anything about it.

Why this split, not one project: nearly every bug from the bash build lived
in the autonomous-mode-specific logic, not in the container-lifecycle core.
Separating them means the stable, already-trusted, already-understood part
doesn't need a rewrite at all (bash's original "it's only N lines of code"
argument is valid again once the scope that made it fragile moves out), and
the part that actually needs Python's documentation/testing tooling is
exactly the part that's complex and still evolving.

## Prior art (why we're not adopting an existing tool)

The "run Claude Code in an isolated Docker container behind an egress
firewall" space already has multiple real implementations (`clawker`,
`ClaudeBox`, `sandclaude`, `codex-lockbox`, `agentbox`), so "container
isolation" alone isn't a differentiator. We looked closely at `clawker`
specifically: a mature, actively-maintained Go project whose threat model
("you can't reliably stop an agent from being prompt-injected, so strip the
injection of any power to hurt you") matches this document's isolation
goals almost exactly, and whose enforcement architecture is arguably
*stronger* than `dco`'s — it uses eBPF to enforce the network boundary
**outside** the container via a separate control-plane process, so the
agent container has no path to its own firewall rules at all. `dco`'s
firewall runs *inside* the container via a passwordless-sudo script — a
real structural gap `clawker` closes. Decision: not adopting it (the user
isn't interested), but worth remembering as a concrete example of a
stronger enforcement model than `dco`'s current one, if `dco`'s firewall
approach ever gets revisited. Separately, `clawker` doesn't touch GitHub
orchestration at all — it only occupies the container-isolation niche, so
even if it had been adopted, it wouldn't have overlapped with Consal's
actual scope.

## Vision

A self-driving development system: point it at a project idea, and it
becomes a sandboxed AI collaborator you steer through GitHub's own
developer-facing surface (issues, PRs, comments) — with an interactive
channel always available as a direct escape hatch — while a container
boundary keeps the blast radius small if it makes a mistake or is
manipulated by adversarial content it encounters while working
autonomously.

## The workflow

1. **Setup.** Create a container (via `dco`) and a GitHub repo for the
   project idea.
2. **Interactive planning.** A synchronous session (human + Claude,
   attached to the container, talking directly — the existing `dco --claude`
   interaction shape) produces a plan, written to the workspace as an
   actual file and version-controlled with git. The plan is a living
   artifact: not a rigid one-time spec, expected to evolve as the project
   develops, not something frozen after this first session.
3. **Autonomous operation.** The AI now acts with real GitHub agency, not
   as a worker that only consumes issues someone else labeled: it
   decomposes the plan into issues (high-level idea → components →
   sub-components → issues, the ordinary way software gets broken down),
   monitors and responds to issues the human files, and starts work on
   issues — using GitHub the way a human developer on the team would.
4. **Human oversight, ongoing.** The human watches GitHub (issues, PRs,
   whatever project-management surface gets incorporated), reviews code,
   and responds to issues to steer direction. The human can also attach to
   the container directly at any time and talk to it — this channel never
   goes away once autonomous operation starts; it's a steering wheel, not
   just a bootstrap-phase tool.

Steps 2-4 are Consal's behavior, built on containers `dco`
provides; step 1's container creation is literally just `dco`.

## Interaction model

Deliberately hybrid, not one mode or the other:

- **Async / GitHub-native** for steady-state work: the AI's primary
  interface for direction and review is issues and PRs, matching how a
  human collaborator would actually be managed on a real team.
- **Sync / interactive** for planning and for direct intervention: the
  human can attach and talk to the container any time, and whatever gets
  typed becomes the next turn in whatever's already running.

This hybrid is Consal's behavior, not something `dco` itself
needs to know about — `dco` just keeps being able to launch/reattach to
whatever container/profile Consal set up, exactly as it does
for any project today.

## Isolation & safety goals

The container's blast-radius containment has to hold against two distinct
threats, not just one:

- **Accidents.** The agent makes an ordinary mistake — bad code, an
  unintended destructive command, scope creep.
- **Adversarial hijacking.** The agent encounters adversarial content while
  operating autonomously (a malicious page during research, a poisoned
  dependency, injected instructions in an issue/PR comment) and is
  manipulated into acting against the user's interest.

Concretely, this means (carried forward from what `dco` already got right,
restated as goals rather than implementation) — all achieved by Consal
supplying its own sub-config profile to `dco`, not by `dco` having
built-in knowledge of any of this:

- A real network boundary during autonomous operation: default-deny with an
  explicit, narrow allowlist, not "open and hope." **Correction
  (2026-07-18):** this was stated as a goal but not actually active —
  `.devcontainer/allowlist.txt` (the file the shared `../Dockerfile`
  bakes into every profile's image) was empty, which `init-firewall.sh`'s
  own documented behavior treats as "firewall fully disabled." Found by
  reasoning through a direct question: `CLAUDE_CODE_OAUTH_TOKEN` sits in
  every Consal sub-config's `containerEnv`, and any process inside the
  container — including whatever Claude's own Bash tool runs — can read
  it (verified: Claude Code has no mechanism to expose an env var to its
  own process while hiding it from its own spawned subprocesses; this is
  just how process environment inheritance works, not a bug). Nothing
  was actually stopping a hijacked agent from reading that token and
  sending it anywhere on the open internet.
  - **Scoped fix, not a global one.** The user deliberately did not want
    the *default* profile (this repo's own everyday dev sandbox,
    `.devcontainer/devcontainer.json`) locked down — that's a separate,
    later decision. Every Consal sub-config's `devcontainer.json` now
    bind-mounts its own `allowlist.txt` over
    `/usr/local/etc/dco-allowlist.txt` at container-start, overriding the
    shared, empty top-level one *only* for containers built from that
    sub-config — without touching the shared `../Dockerfile` or the
    default profile at all. `templates/allowlist.txt` holds the minimal
    set `claude -p` actually needs: `api.anthropic.com` (required) plus
    Claude Code's own telemetry domains (`sentry.io`,
    `statsig.anthropic.com`, `statsig.com` — safe to drop, since
    `init-firewall.sh` already skips, not fails on, any domain that
    doesn't resolve). GitHub is always allowed regardless, per
    `init-firewall.sh`'s existing behavior.
  - **Also considered and rejected:** an alternative that would give
    Consal sub-configs their own non-shared Dockerfile (so their
    `COPY allowlist.txt` step could differ from the default profile's).
    Rejected — `init-firewall.sh`'s own top-of-file comment already
    warns against exactly this ("don't add a per-profile copy under
    templates/<name>/: it would look editable/profile-specific but
    silently never be read... `dco --regen` is therefore sufficient to
    update this for every profile"), and duplicating ~75 lines of
    Dockerfile per sub-config to vary one file is worse than a one-line
    bind-mount override.
  - `config.generate_subconfig` now substitutes a `__SUBCONFIG_NAME__`
    placeholder in the template's mount source (the mount needs to know
    its own sub-config directory name, which varies per call) and copies
    `allowlist.txt` alongside the guardrail hook;
    `config.validate_subconfig` checks it's present, same as the hook.
- A credential scoped to exactly the target repo, never the user's full
  personal access — so a hijacked agent's reach is bounded even if it tries
  to misuse its own credential. **Note (2026-07-14):** SSH and the PAT
  (`GH_TOKEN`/`CONSAL_GH_PAT`) are unrelated mechanisms — the PAT makes
  `gh` commands and HTTPS git operations work, but does nothing for an
  `ssh://`/`git@github.com:...` remote, which still needs a trusted host
  key and a private key regardless of any PAT. Found by trying to push
  this very repo from inside its own dev sandbox, which has neither.
  Consal-managed projects need **HTTPS remotes**, not SSH, for the
  scoped-credential isolation goal to actually cover `git push`, not just
  `gh` API calls — relevant once `github.py`/`scheduler.py` exist and
  actually push branches from inside a container.
- A human is the only one who can actually merge code into the project.
  The agent must never force-push, push directly to a protected branch, or
  touch branch/repo protection settings — enforced at two independent
  layers (a local guardrail as defense in depth, GitHub's own branch
  protection as the real backstop), with the local layer never treated as
  sufficient on its own.

## Configurability as a goal

Oversight granularity should be a tunable property of a project, not a
fixed global policy: PR-only review is fine for a project that's going
well, but the human should be able to dial in tighter, issue-level
oversight for a project where PRs start missing the target. Same for how
direct interactive intervention relates to whatever the agent is doing
when the human drops in — pause-and-redirect vs. leave-a-note-for-later
are both legitimate depending on the situation.

This is a stated goal, explicitly **not** committed to for the first
working version — see v1 scope below.

## V1 scope (deliberately minimal, to get something working first)

- **No issue-level gating.** The AI can file, comment on, and start any
  issue — self-created while decomposing the plan, or human-filed —
  without a "ready" label or other pre-approval step. The review
  checkpoint is the PR, full stop.
- **No special intervention orchestration.** Attaching and talking to the
  container directly *is* the intervention mechanism. Whatever's typed
  becomes the next conversational turn in whatever's already running — no
  pause/queue/redirect machinery to build. This is close to free: it's
  what a persistent, attachable session (via `dco`) already gives you.

Both of these are explicitly named as v1 simplifications of a stated goal,
not the goal itself — the configurability described above is real future
scope, not something being quietly dropped.

## Lessons carried forward from the bash implementation

These held up as genuine engineering constraints independent of language or
architecture — they're requirements on *whatever* gets built next
(primarily Consal, since that's where the equivalent complexity
will live), not retrospective bash war stories:

1. Config that references other files (a build file pointing at a
   Dockerfile elsewhere, for instance) needs its *result* checked for
   self-consistency — every referenced path actually exists — before
   shipping, without needing a real container build to surface a gap.
2. Anything that asserts an external resource is reachable (a network
   allowlist entry, an API endpoint) needs an actual standing check that
   it resolves/responds, not a one-time assertion taken on faith.
3. Pasted secrets can be silently corrupted by terminal escape sequences;
   sanitization needs to be verified against actual byte sequences, not
   assumed correct because it looks reasonable.
4. A function's success/failure needs to be explicit and intentional,
   never an accidental side effect of whatever its last statement happens
   to return.
5. Retry logic is only correct paired with a way to independently verify
   the thing being retried can succeed at all — otherwise "retry and skip"
   just quietly hides a permanent failure forever.
6. Mocked test infrastructure that never exercises the real underlying
   tool can rack up a high test count while missing exactly the bugs that
   matter. Test coverage needs to be evaluated against "would this have
   caught the last few real bugs," not against a passing count.
7. An autonomous agent doesn't act on its own instructions without an
   explicit first turn, and "reattach and see if it's working" is a bad
   way to discover whether it's actually running — idle and working look
   identical from outside.

## Decided

- **SDK vs. CLI launcher (2026-07-14): CLI launcher.** Consal drives Claude
  by launching the `claude` CLI with a constructed prompt (e.g. "here's
  issue #42, implement it"), the same shape as `dco`'s old bash autonomous
  mode, and lets Claude Code's own agent loop handle the actual work — file
  edits, tests, git, all of it. Consal's own code is the orchestration layer
  around that: watch GitHub, decide what's next, hand off a prompt, repeat.
  Rejected alternative: the Claude Agent SDK, which would have Consal
  implement its own agent loop and tools in Python for full step-level
  programmatic control. Rejected because it's substantially more
  implementation effort to rebuild what Claude Code already provides, and
  nothing in v1 scope needs step-level control — the PR is already the
  review checkpoint. Revisit if the CLI approach's guardrails prove too
  coarse in practice (e.g. if enforcing the "lessons carried forward"
  constraints turns out to need hooks finer-grained than Claude Code's own
  permission/hook system exposes).

- **Consal/`dco` interface (2026-07-14): plain `dco` + `devcontainer exec`,
  never `--claude`, for autonomous turns.** `dco --claude`'s tmux/attach
  path is interactive-only by construction — a human at a TTY, no defined
  "done" signal — so it's reserved for step 2 (interactive planning) and
  direct human intervention (step 4), never for autonomous turns.
  - **Sub-config contents:** a directory, matching how `--sub-config`
    already works — `.devcontainer/consal/devcontainer.json` plus its own
    allowlist entries (referencing the shared `../Dockerfile` /
    `init-firewall.sh` `dco` already provides), plus the guardrail hook
    script. All checked into the project's own repo like any other
    sub-config, **except the PAT** — injected via `containerEnv` pointing
    at a host env var or gitignored secrets file, never committed.
    **Correction (2026-07-14):** the same applies to Claude's own
    credentials, found missing via a real integration test run — a fresh
    container's `claude-code-config-${DCO_PROJECT_ID}` volume has never
    logged in, so `claude -p` fails with "Not logged in" until
    authenticated some other way. `containerEnv` now also carries
    `"CLAUDE_CODE_OAUTH_TOKEN": "${localEnv:CLAUDE_CODE_OAUTH_TOKEN}"`,
    same pattern as the PAT — sourced from a host env var, never
    committed. Deliberately the subscription token (`claude setup-token`,
    a year-long OAuth token billed against the Pro/Max/Team plan's usage
    limits) rather than `ANTHROPIC_API_KEY` (separate, metered API
    billing) — draws against an existing monthly plan instead of
    incurring independent per-token charges. Named tradeoff: this shares
    its usage pool with the user's own interactive Claude Code sessions,
    unlike API-key billing, which never competes with personal usage but
    costs money independently. Requires that token to be generated once
    and set on any host actually running Consal-managed containers
    headlessly.
  - **Profile vs. runtime state split:** the profile above is static,
    checked-in config. Runtime state (active issue, loop status, logs) is
    churny and lives outside git, in a host-side `~/.consal/<project-id>/`
    directory or volume — mirroring how `dco` already keeps `~/.claude`
    out of the repo.
  - **Headless bring-up needed one small additive flag on `dco`:
    `--up-only`.** **Correction (2026-07-14):** the original version of
    this bullet assumed plain `dco --sub-config consal` (no `--claude`)
    already just ensures the container is up and returns. Reading `dco`'s
    actual source (`dco.in`) showed that's wrong — every path through
    `main()` ends by exec'ing an interactive shell or the `--claude` tmux
    session; there was no headless "bring it up, don't attach" mode at
    all. The real primitive `dco` uses internally is `devcontainer up
    --workspace-folder ... --config ...`, immediately followed by two
    things Consal would otherwise have had to reimplement to call that
    directly itself:
    - `DCO_PROJECT_ID`, a hash of workspace path + sub-config name
      (`project_id()` in `dco.in`) that `devcontainer.json`'s
      `${localEnv:DCO_PROJECT_ID:default}` mount sources consume **only
      at `devcontainer up` time**, never again by `devcontainer exec`.
      Reimplementing that hash in Python would create two copies with
      nothing enforcing they stay byte-for-byte identical forever — a
      drift silently forks every project's volumes (old data orphaned
      under the old hash). Exactly the silent-self-consistency failure
      lesson #1 warns about, and worse than most instances of it because
      it fails silently rather than loudly.
    - Git identity sync (`git config --global user.name`/`user.email`,
      read from the host) — `dco` already owns this; a second copy in
      Consal has to be kept in lockstep by hand.

    So instead of Consal reaching around `dco` to call `devcontainer up`
    directly, `dco` gets one small, additive flag: `--up-only` — runs
    everything `main()` already does up through git-identity sync
    (scaffold/self-heal, compute+export `DCO_PROJECT_ID`, `devcontainer
    up`, git config sync), then exits 0/1 instead of exec'ing a shell.
    Still squarely container-lifecycle, not autonomy-shaped surface, so
    it doesn't violate the reasoning that ruled out a `--exec`-style flag
    on `dco` (below). `ensure_container_up` becomes `dco <workspace_folder>
    --sub-config <name> --up-only` — the workspace path passed explicitly,
    matching `run_turn`'s `--workspace-folder`, rather than relying on the
    calling process's cwd matching dco's positional `[path]` argument
    implicitly. `DCO_PROJECT_ID` is consumed only at `devcontainer
    up` time, so Consal's per-turn `run_turn` needs no knowledge of it at
    all — the rest of this decision (per-turn `devcontainer exec ... --
    claude -p`, synchronous exit-code signal, container reuse) stands
    unchanged. Consal still drives each turn itself via `devcontainer exec
    --workspace-folder ... --config ... -- claude -p "$PROMPT"`, a public
    CLI Consal is free to call directly — growing `dco` a new `--exec`-style
    flag would re-add autonomy-shaped surface to the tool this project
    just spent effort stripping it out of. **Correction (2026-07-14):**
    `run_turn` initially omitted `--config`, matching only half of what
    `dco` itself always passes to every `devcontainer exec` call (see
    `dco.in`) — the CLI defaults to `.devcontainer/devcontainer.json`
    (the default profile) for matching which running container to attach
    to when `--config` is omitted, which doesn't match a container
    brought up via a named `--sub-config` and fails with "Dev container
    not found". Caught by the `consal_managed_project` integration test
    fixture (a disposable project with no pre-existing default-profile
    container to fall back onto by accident, unlike the long-lived real
    repo the earlier passing tests happened to run against).
  - **Success/failure signal comes free:** `devcontainer exec` is a
    synchronous foreground subprocess with a real exit code and captured
    stdout/stderr, so lesson #4 (explicit return value) is satisfied by
    construction — no idle-vs-working ambiguity, since Consal is the one
    blocking on the call.
  - **Container reuse, not fresh-per-task:** one container persists for
    the whole autonomous run, rebuilt only when the profile changes —
    keeps `dco`'s existing persistence (`~/.claude` volume, bash history)
    and avoids a container-build latency tax every loop turn. Named
    tradeoff, not a free win: fresh-per-issue would bound cross-issue state
    drift more tightly (a confused agent can't drag stale context from
    issue N into issue N+1). Default to reuse for v1; revisit if drift
    turns out to be a real problem.

  Net effect: `dco`'s interface to Consal is almost exactly what it is
  today, plus one small additive flag — `dco --sub-config <name>
  --up-only` for bring-up. Every per-turn call after that is Consal calling
  the public `devcontainer` CLI directly.

- **Distribution model (2026-07-14): a small package, stdlib + subprocess
  only.** This splits into two independent axes that the original framing
  ("stdlib-only single file vs. a proper package") bundled together:
  - **Dependency policy: stay stdlib + subprocess.** Consal already depends
    on `dco` by shelling out to it, the same way `dco` shells out to
    `docker`/`gh`/`devcontainer`. Continue that pattern one level up:
    Consal talks to GitHub by shelling out to `gh` (parsing its JSON output
    with stdlib `json`), not via `PyGithub`/`requests`. No third-party
    runtime dependencies. Preserves the same auditability property that
    motivated trimming `dco` itself down to ~350 lines — nothing to trust
    beyond stdlib and the CLIs already being shelled out to.
  - **File layout: a package (`src/consal/`), not one file.** Breaks from
    `dco`'s own single-file precedent, deliberately. The reason Consal is
    Python and not bash is that "the part that needs Python's
    testing/documentation tooling is exactly the part that's complex and
    evolving" — that only pays off with real module boundaries (GitHub
    polling, prompt construction, guardrail checks, and the scheduling
    loop are genuinely separate concerns). A single file fights the
    unit/integration test split below.
  - **No PyPI distribution needed** — single-user tool. `pipx install -e
    .` (or bare `python3 -m consal`) from the checkout is the whole story;
    skip packaging ceremony beyond what `pyproject.toml`/pytest need.

- **Testing strategy (2026-07-14): unit/integration split mapped directly
  to the "lessons carried forward" list**, not discovered incrementally:
  - Config self-consistency (referenced paths exist) → **unit**, tmp-dir
    fixtures, fast and deterministic.
  - Standing reachability check (allowlist/endpoints) → **unit-test the
    checker logic** against mocked good/bad hosts. The live check itself
    ships as a product feature (a `consal doctor` command), not a CI
    assertion — network state isn't CI's job to assert.
  - Secret sanitization vs. terminal escape sequences → **unit**, against
    real byte-sequence fixtures (actual ANSI/bracketed-paste bytes), never
    mocked away — lesson #6 is a direct warning against exactly that.
  - Explicit success/failure → convention + test pairing: every fallible
    function gets a positive *and* negative test, backed by a lint rule
    against bare `except`.
  - Retry paired with independent verification → **integration-ish**,
    simulate retry-with-a-fake-verifier and assert escalation on
    "unrecoverable" instead of infinite retry.
  - Mocked infra hiding real bugs (the meta-lesson) → a real **integration
    tier** that hits actual `gh`/`dco`/`devcontainer` against a disposable
    sandbox repo, not subprocess mocks.
  - Idle vs. working ambiguity → mostly solved by construction now that
    headless turns are synchronous `devcontainer exec` (see the `dco`
    interface decision above). **Update (2026-07-18):** covered by both a
    scheduler-dispatch unit test (mocked, given pending work does the loop
    actually issue the call) and a real integration test
    (`tests/integration/test_scheduler.py`) exercising the full chain —
    real container bring-up, real `list_open_issues`, real prompt
    construction, real state persistence — against the live GitHub repo.
    That test deliberately mocks only `container.run_turn` and
    `github.comment_on_issue`: letting an unscoped `claude -p` turn
    actually work a live issue would combine an uncontrollable
    model-judgment confound (the same reason the guardrail-enforcement
    test above stopped trusting live turns) with a real mutating GitHub
    write on every run.

  Mechanically: `pytest -m integration` as an opt-in marker, run
  separately from the fast default suite — fast tier runs on every save,
  the real-tools tier runs less often (pre-merge, not every commit),
  directly fixing "multi-minute live Docker/GitHub cycles surfacing bugs
  only after shipping." Coverage gets judged against "would this have
  caught the last few real bugs" (lesson #6), not against a passing count.

- **Guardrail hook ownership (2026-07-14): authored fresh in Consal, no
  Python-side reimplementation.** The local-guardrail layer from
  "Isolation & safety goals" (block `git push --force`, direct pushes to
  `main`/`master`, `gh pr merge`, branch-protection tampering, `gh secret
  set`) is a Claude Code `PreToolUse` hook — which has to be a shell
  command, since that's the interface Claude Code's hook system calls.
  There is no legitimate Python equivalent to build: a parallel policy
  checker in Consal's own code would never actually run in the enforcement
  path, since Consal (orchestrating from outside the container via
  `devcontainer exec`) has no visibility into individual Bash tool calls
  Claude Code makes mid-turn — it only ever sees a turn's aggregate exit
  code. Building one anyway would be dead code that could silently drift
  from what's real: the same failure shape as the `DCO_PROJECT_ID`
  mistake above, just one layer up.

  A `guardrails.py` module was scaffolded early on assuming otherwise and
  has been deleted. The policy itself is genuinely autonomy-specific (not
  something `dco` should know about, consistent with the whole
  architecture split), so it's authored and owned as a static template in
  Consal: `src/consal/templates/guardrail-hook.sh`, hand-written, ~10
  pattern checks, no generation from a Python policy DSL.
  `config.generate_subconfig` copies it into each managed project's
  `.devcontainer/<name>/` and writes a `.claude/settings.json` at the
  project root registering it as a `PreToolUse` hook;
  `config.validate_subconfig` checks the copy is actually present.
  Tested by shelling out to the real script with sample tool-call JSON on
  stdin (both block- and allow-cases) — lesson #6 directly on point: a
  Python reimplementation of the rules would test logic the real hook
  never runs.

  (An earlier version of this correction assumed there was an existing
  bash hook artifact in `dco`'s own tree to defer to, found in this
  repo's own `.devcontainer/autonomous-guardrail-hook.sh`. That file
  turned out to be stale content left over from before `dco`'s `--dsp`
  strip — not present in `dco`'s current tree at all — and has been
  deleted from here too. The policy was sound; the ownership conclusion
  it implied wasn't.)

- **CLI config (2026-07-18): CLI args are canonical, a checked-in
  `.consal/config.toml` just pre-fills them.** Standard layered-config
  pattern — precedence is explicit `--flag` > config file value >
  built-in default, not two parallel ways to configure the tool.
  `project_id`/`repo` get no built-in default (guessing wrong here could
  point the scheduler at the wrong GitHub repo, or collide two projects'
  `~/.consal/<project_id>/` state directories) — `resolve_settings`
  raises a clear error naming exactly what's missing and where it could
  come from, rather than silently picking something. `sub_config`
  defaults to `"consal"`; `workspace` defaults to cwd, matching `dco`'s
  own convention for its positional `[path]`. The config file is static,
  checked-in project config — like the sub-config profile itself — not
  runtime state, so it lives in the project's own repo, not
  `~/.consal/<project_id>/`. Parsed via stdlib `tomllib` (Python 3.11+,
  already required) — no new dependency.

- **`consal doctor` (2026-07-18): three check categories, directly off
  lessons #1/#2 and the testing-strategy decision that named this
  command.** Distinct from the test suite, which checks code logic
  against mocks and never the real machine it runs on:
  - Environment prerequisites (`dco`/`devcontainer` on PATH, `gh`
    authenticated, `CONSAL_GH_PAT`/`CLAUDE_CODE_OAUTH_TOKEN` set) — the
    same category `tests/integration/test_environment.py` checks, but as
    a real command a human runs against their own machine.
  - Sub-config self-consistency (lesson #1) via the existing
    `config.validate_subconfig`.
  - Standing allowlist reachability (lesson #2): a real
    `socket.getaddrinfo` per domain in the sub-config's `allowlist.txt`,
    not a one-time assertion that the list is correct because it's
    written down.

- **`consal init` (2026-07-18): the missing piece, found while writing
  usage docs.** `config.generate_subconfig` had no CLI entry point —
  before this, the only way to set up a new project was calling it
  directly from a Python REPL/script, which meant the README's usage
  section had no honest one-line answer to "how do I set up a new
  project." `consal init` wraps it and optionally merges
  `project_id`/`repo`/`sub_config` into `.consal/config.toml`, whichever
  were given. Unlike `doctor`/`run`, nothing is required — generating the
  sub-config itself needs neither `project_id` nor `repo`
  (`generate_subconfig`'s own signature takes only a workspace and a
  sub-config name). Re-running `init` merges into the existing config
  file rather than clobbering it, so recording `project_id` later doesn't
  lose a `repo` set earlier.

- **Documentation structure (2026-07-18): decided, matching the direction
  already agreed.** Docstrings carry API-level detail (already the
  practice throughout `src/consal/` — every module has a substantive
  top-of-file docstring). `README.md` is quickstart/usage only, split
  into a "Status" section naming what's real vs. not yet built and a
  "Usage" section walking prerequisites → `consal init` →
  `.consal/config.toml` → `consal doctor` → `consal run`. `CONSAL_GOALS.md`
  (this file) is the separate design doc for the "why." Incremental fixes
  stay in commit messages, not accreted into the README — already the
  practice all session; no new artifact (changelog, docs/ directory, doc
  generator) needed for a single-user CLI tool.

## Non-goals

- Reimplementing GitHub's own issue/PR primitives.
- `dco` reimplementing anything about GitHub, autonomy, or Claude Code's
  own agentic-loop/scheduling primitives — that entire domain now belongs
  to Consal, not `dco`, by design.
