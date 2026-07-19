# consal: goals document for an opinionated tool for technically oriented research projects

## Context

consal is a Python tool for GitHub-driven autonomous development, built
on top of `dco`, a bash tool for launching sandboxed devcontainers to
run Claude Code. `dco` and consal are two components of one system,
cleanly separated by concern: `dco` owns container lifecycle, consal
owns everything about GitHub-driven autonomy on top of it. See
**Architecture** below.

## Architecture

- **`dco`** is a minimal, fully generic container-lifecycle tool: it
  creates a sandboxed devcontainer, keeps it alive, reattaches to it,
  and manages named sub-config profiles and persistent volumes. It has
  no built-in concept of "autonomous mode," GitHub, PATs, or labels.
- **consal** (this project) owns everything about GitHub-driven
  autonomy: the plan-then-decompose-then-autonomous-loop workflow,
  repo/PAT setup, guardrails, scheduling, and the hybrid
  interactive/async interaction model. It depends on `dco` the way
  `dco` depends on `docker`/`gh`/`devcontainer`, shelling out to it for
  container lifecycle via `dco`'s generic `--sub-config` mechanism,
  supplying its own custom profile/template rather than requiring `dco`
  to know anything about consal.

Keeping container-lifecycle concerns in `dco` and autonomy-specific
concerns in consal keeps the stable, generic part simple, and isolates
the complex, still-evolving part where Python's testing and
documentation tooling actually pays for itself.

## Prior art (why we're not adopting an existing tool)

The "run Claude Code in an isolated Docker container behind an egress
firewall" space already has multiple real implementations (`clawker`,
`ClaudeBox`, `sandclaude`, `codex-lockbox`, `agentbox`), so "container
isolation" alone isn't a differentiator. `clawker` is the most
sophisticated of these, a Go project that enforces its network
boundary via eBPF from a separate control-plane process outside the
container, a stronger enforcement point than `dco`'s own
passwordless-sudo-based in-container firewall. It's not adopted here:
it's an early-stage, considerably more complex dependency to take on
for a network-isolation improvement that isn't the primary safety
lever this system relies on (see "Isolation & safety goals" below),
when the equivalent container-lifecycle functionality `dco` already
provides is a few hundred lines of bash. `clawker` also doesn't touch
GitHub orchestration at all; it only occupies the container-isolation
niche, so it wouldn't overlap with consal's actual scope even if
adopted.

## Vision

**consal is an opinionated tool for managing technically oriented
research projects, using GitHub as the UI and Claude as the backend.**
A single-user tool built around the operator's own workflow, framed
around who that operator actually is.

**Target user:** a researcher running a technically oriented project
(computational research, a data pipeline, a research tool), not a
professional software developer. Real sophistication is expected:
someone capable of directing a technical project and judging whether
an explanation actually holds together, but code literacy isn't
assumed. GitHub literacy *is* assumed: navigating issues and PRs, and
reviewing a diff in the GitHub UI, is something the user can always do
and is expected to know how to do. The gap consal exists to close is
understanding the code, not operating GitHub. consal and Claude
translate technical work into plain language and provide coaching
where it's actually needed, without assuming the researcher already
knows how to run a software project.

Point it at a project idea, and it becomes a sandboxed AI collaborator
steered through GitHub's own developer-facing surface (issues, PRs,
comments), with an interactive channel always available as a direct
escape hatch, while a container boundary keeps the blast radius small
if it makes a mistake or is manipulated by adversarial content it
encounters while working autonomously. consal itself stays thin by
design: GitHub is the project-management UI, Claude Code is the
engineering capability, and consal is the orchestration layer making
those two things work together for a user who couldn't operate either
one directly for this purpose.

## Dual explanation as a design principle

Every unit of work consal dispatches (a plan, an issue, a PR) carries
two independent representations of the same task: a common-language
account of what it does and why, and the code itself. This is not just
a courtesy translation for a reader who doesn't read code, it's a
verification technique: a plain-language description is a claim about
the code, and checking the two against each other catches drift
between stated intent and actual implementation that neither
representation alone would surface.

Concretely, this is what makes diff review meaningful for a user who
isn't fluent in code: they check the diff's scope and shape against
the plain-language claim (does it touch what it says it touches, does
the size look right, does anything look out of place), rather than
needing to evaluate code correctness line by line. It also gives
Claude itself a second representation of its own task to reconcile
against before work is considered done, not just a summary written for
a human after the fact.

Where exactly this lives in the workflow (issue bodies, PR
descriptions, the plan document's own structure, an explicit
reconciliation step before a PR opens) is not yet decided; this
section records the principle, not its implementation.

## The workflow

1. **Setup.** Create a container (via `dco`) and a GitHub repo for the
   project idea.
2. **Interactive planning.** A synchronous session (human + Claude,
   attached to the container, talking directly: the existing `dco
   --claude` interaction shape) produces a plan, written to the
   workspace as an actual file and version-controlled with git. The
   plan is a living artifact: not a rigid one-time spec, expected to
   evolve as the project develops, not something frozen after this
   first session.
3. **Autonomous operation.** The AI acts with real GitHub agency, not
   as a worker that only consumes issues someone else labeled: it
   decomposes the plan into issues (high-level idea → components →
   sub-components → issues, the ordinary way software gets broken
   down), monitors and responds to issues the human files, and starts
   work on issues, using GitHub the way a human developer on the team
   would.
4. **Human oversight, ongoing.** The human watches GitHub (issues,
   PRs, whatever project-management surface gets incorporated),
   reviews code, and responds to issues to steer direction. The human
   can also attach to the container directly at any time and talk to
   it. This channel never goes away once autonomous operation starts;
   it's a steering wheel, not just a bootstrap-phase tool.

Steps 2-4 are consal's behavior, built on containers `dco` provides;
step 1's container creation is literally just `dco`.

## Interaction model

Deliberately hybrid, not one mode or the other:

- **Async / GitHub-native** for steady-state work: the AI's primary
  interface for direction and review is issues and PRs, matching how a
  human collaborator would actually be managed on a real team.
- **Sync / interactive** for planning and for direct intervention: the
  human can attach and talk to the container any time, and whatever
  gets typed becomes the next turn in whatever's already running.

This hybrid is consal's behavior, not something `dco` itself needs to
know about. `dco` just keeps being able to launch/reattach to whatever
container/profile consal set up, exactly as it does for any project.

## Isolation & safety goals

The container's blast-radius containment has to hold against two
distinct threats, not just one:

- **Accidents.** The agent makes an ordinary mistake: bad code, an
  unintended destructive command, scope creep.
- **Adversarial hijacking.** The agent encounters adversarial content
  while operating autonomously (a malicious page during research, a
  poisoned dependency, injected instructions in an issue/PR comment)
  and is manipulated into acting against the user's interest.

Concretely, this means the following, all achieved by consal supplying
its own sub-config profile to `dco`, not by `dco` having built-in
knowledge of any of this. The primary lever is minimizing what's
inside the container and how far any one credential reaches, rather
than trying to build a perfect wall against an agent already inside
sending data out: a hijacked agent that has nothing valuable to steal
and no path to reach beyond its own sandboxed repo is a bounded
problem, regardless of what it attempts.

- A credential scoped to exactly the target repo, never the user's
  full personal access, so a hijacked agent's reach is bounded even if
  it tries to misuse its own credential. SSH and the PAT
  (`GH_TOKEN`/`CONSAL_GH_PAT`) are unrelated mechanisms: the PAT makes
  `gh` commands and HTTPS git operations work, but does nothing for an
  `ssh://`/`git@github.com:...` remote, which still needs a trusted
  host key and a private key regardless of any PAT. consal-managed
  projects therefore need **HTTPS remotes**, not SSH, for the
  scoped-credential isolation goal to actually cover `git push`, not
  just `gh` API calls.
  - **Open direction, not yet designed:** credential handling today is
    a single long-lived PAT/OAuth token per sub-config, sourced from a
    host env var. Since credential scope is the primary safety lever
    here (see above), a more sophisticated scheme, short-lived or
    rotating tokens, finer-grained scoping, a small credential-issuing
    helper, is worth exploring later. Still expected to stay on the
    order of a shell script or two, not a new subsystem.
- A human is the only one who can actually merge code into the
  project. The agent must never force-push, push directly to a
  protected branch, or touch branch/repo protection settings, enforced
  at two independent layers (a local guardrail as defense in depth,
  GitHub's own branch protection as the real backstop), with the local
  layer never treated as sufficient on its own.
- A network boundary during autonomous operation, as a secondary,
  defense-in-depth layer, not the primary safety mechanism:
  default-deny with an explicit, narrow allowlist, not "open and
  hope." This is worth having (the credential injected via
  `containerEnv` is readable by any process inside the container,
  including whatever Claude's own Bash tool runs, since Claude Code
  has no mechanism to expose an env var to its own process while
  hiding it from its own spawned subprocesses), but it's not where
  effort should concentrate: a tightly-scoped credential already
  bounds the damage even if egress control has a gap, so a simple
  allowlist is enough here, not a stronger enforcement architecture
  like `clawker`'s (see "Prior art" above).
  - **Scoped to consal sub-configs, not the default profile.** The
    *default* profile (this repo's own everyday dev sandbox,
    `.devcontainer/devcontainer.json`) stays unrestricted by design;
    only containers built from a consal sub-config get locked down.
    Every consal sub-config's `devcontainer.json` bind-mounts its own
    `allowlist.txt` over `/usr/local/etc/dco-allowlist.txt` at
    container-start, overriding the shared, empty top-level one *only*
    for containers built from that sub-config, without touching the
    shared `../Dockerfile` or the default profile at all.
    `templates/allowlist.txt` holds the minimal set `claude -p`
    actually needs: `api.anthropic.com` (required) plus Claude Code's
    own telemetry domains (`sentry.io`, `statsig.anthropic.com`,
    `statsig.com`, safe to drop since `init-firewall.sh` already
    skips, not fails on, any domain that doesn't resolve). GitHub is
    always allowed regardless, per `init-firewall.sh`'s existing
    behavior.
  - A per-sub-config Dockerfile (so `COPY allowlist.txt` could vary per
    profile) is deliberately not used: `init-firewall.sh`'s own
    top-of-file comment warns against a per-profile copy under
    `templates/<name>/`, since it would look editable but silently
    never be read, and duplicating ~75 lines of Dockerfile per
    sub-config to vary one file is worse than a one-line bind-mount
    override.
  - `config.generate_subconfig` substitutes a `__SUBCONFIG_NAME__`
    placeholder in the template's mount source (the mount needs to
    know its own sub-config directory name, which varies per call) and
    copies `allowlist.txt` alongside the guardrail hook;
    `config.validate_subconfig` checks it's present, same as the hook.

## Opinionated defaults, not a blank framework

consal is not neutral plumbing between GitHub and Claude. It encodes
real judgment about how to use Claude well on a technically oriented
research project: sophisticated usage patterns are available as
strong defaults, not left for the researcher to assemble from scratch.
The goal is that starting a project takes little effort and still gets
real leverage from Claude; every default stays configurable for a user
who wants to tune it (see "Configurability as a goal" below).

One default pattern: turn dispatch doesn't default to a single flat
prompt per issue. For non-trivial work, the default is an
orchestration pattern, one agent breaks the issue down, dispatches
parallel sub-agents at the pieces, has agents check each other's
output, then synthesizes a result before it becomes a PR. This doesn't
require consal to reimplement agent orchestration itself: Claude Code
already exposes its own multi-agent primitives (parallel sub-agent
dispatch, adversarial verification, synthesis) inside a single `claude
-p` session (see "SDK vs. CLI launcher" below). The sophistication
lives in how consal prompts and configures a turn to invoke that
pattern by default for suitable issues.

Which specific capabilities belong in the default set beyond this
(research-specific conventions: reproducibility checks, data
validation habits, documentation norms for research code) is
deliberately left open for a later refinement pass, not enumerated
here yet.

## Configurability as a goal

Oversight granularity is a tunable property of a project, not a fixed
global policy: PR-only review is fine for a project that's going well,
but the human should be able to dial in tighter, issue-level oversight
for a project where PRs start missing the target. Same for how direct
interactive intervention relates to whatever the agent is doing when
the human drops in: pause-and-redirect vs. leave-a-note-for-later are
both legitimate depending on the situation. Configurability also
covers which of consal's opinionated Claude-usage defaults (see
"Opinionated defaults, not a blank framework" above) are active for a
given project: comprehensive, sensible defaults with every one of them
configurable, not a fixed one-size-fits-all behavior.

This is a stated goal, not committed to for the first working version.
See v1 scope below.

## V1 scope (deliberately minimal, to get something working first)

This is the shipped baseline. The vision above extends beyond this
scope; this section records what v1 deliberately deferred, not the
current ceiling on ambition.

- **No issue-level gating.** The AI can file, comment on, and start any
  issue (self-created while decomposing the plan, or human-filed)
  without a "ready" label or other pre-approval step. The review
  checkpoint is the PR, full stop.
- **No special intervention orchestration.** Attaching and talking to
  the container directly *is* the intervention mechanism. Whatever's
  typed becomes the next conversational turn in whatever's already
  running, no pause/queue/redirect machinery to build. This is close
  to free: it's what a persistent, attachable session (via `dco`)
  already gives you.

Both of these are named as v1 simplifications of a stated goal, not
the goal itself. The configurability described above is real future
scope, not something being quietly dropped.

## Engineering principles

These are engineering constraints on consal, independent of language or
architecture:

1. Config that references other files (a build file pointing at a
   Dockerfile elsewhere, for instance) needs its *result* checked for
   self-consistency (every referenced path actually exists) before
   shipping, without needing a real container build to surface a gap.
2. Anything that asserts an external resource is reachable (a network
   allowlist entry, an API endpoint) needs an actual standing check
   that it resolves/responds, not a one-time assertion taken on faith.
3. Pasted secrets can be silently corrupted by terminal escape
   sequences; sanitization needs to be verified against actual byte
   sequences, not assumed correct because it looks reasonable.
4. A function's success/failure needs to be explicit and intentional,
   never an accidental side effect of whatever its last statement
   happens to return.
5. Retry logic is only correct paired with a way to independently
   verify the thing being retried can succeed at all. Otherwise "retry
   and skip" just quietly hides a permanent failure forever.
6. Mocked test infrastructure that never exercises the real underlying
   tool can rack up a high test count while missing exactly the bugs
   that matter. Test coverage needs to be evaluated against "would
   this have caught the last few real bugs," not against a passing
   count.
7. An autonomous agent doesn't act on its own instructions without an
   explicit first turn, and "reattach and see if it's working" is a
   bad way to discover whether it's actually running. Idle and working
   look identical from outside.

## Decided

- **SDK vs. CLI launcher: CLI launcher.** consal drives Claude by
  launching the `claude` CLI with a constructed prompt (e.g. "here's
  issue #42, implement it") and lets Claude Code's own agent loop
  handle the actual work: file edits, tests, git, all of it. consal's
  own code is the orchestration layer around that: watch GitHub,
  decide what's next, hand off a prompt, repeat. The alternative, the
  Claude Agent SDK (consal implementing its own agent loop and tools in
  Python for full step-level programmatic control), is substantially
  more implementation effort to rebuild what Claude Code already
  provides, and nothing in v1 scope needs step-level control: the PR
  is already the review checkpoint. Worth revisiting only if the CLI
  approach's guardrails prove too coarse in practice, e.g. if
  enforcing the engineering principles above turns out to need hooks
  finer-grained than Claude Code's own permission/hook system exposes.

- **consal/`dco` interface: plain `dco` + `devcontainer exec`, never
  `--claude`, for autonomous turns.** `dco --claude`'s tmux/attach path
  is interactive-only by construction (a human at a TTY, no defined
  "done" signal), so it's reserved for step 2 (interactive planning)
  and direct human intervention (step 4), never for autonomous turns.
  - **Sub-config contents:** a directory, matching how `--sub-config`
    already works: `.devcontainer/consal/devcontainer.json` plus its
    own allowlist entries (referencing the shared `../Dockerfile` /
    `init-firewall.sh` `dco` already provides), plus the guardrail hook
    script. All checked into the project's own repo like any other
    sub-config, **except credentials**: both the PAT and Claude's own
    OAuth token are injected via `containerEnv`
    (`"CLAUDE_CODE_OAUTH_TOKEN": "${localEnv:CLAUDE_CODE_OAUTH_TOKEN}"`,
    same pattern as the PAT), sourced from a host env var, never
    committed. A fresh container's
    `claude-code-config-${DCO_PROJECT_ID}` volume starts logged out, so
    `claude -p` needs this to authenticate headlessly. Deliberately the
    subscription token (`claude setup-token`, a year-long OAuth token
    billed against the Pro/Max/Team plan's usage limits) rather than
    `ANTHROPIC_API_KEY` (separate, metered API billing), drawing
    against an existing monthly plan instead of incurring independent
    per-token charges. Named tradeoff: this shares its usage pool with
    the user's own interactive Claude Code sessions, unlike API-key
    billing, which never competes with personal usage but costs money
    independently. Requires that token to be generated once and set on
    any host actually running consal-managed containers headlessly.
  - **Profile vs. runtime state split:** the profile above is static,
    checked-in config. Runtime state (active issue, loop status, logs)
    is churny and lives outside git, in a host-side
    `~/.consal/<project-id>/` directory or volume, mirroring how `dco`
    already keeps `~/.claude` out of the repo.
  - **Headless bring-up: `dco --sub-config <name> --up-only`.** Plain
    `dco` has no headless "bring it up, don't attach" mode: every path
    through its `main()` ends by exec'ing an interactive shell or the
    `--claude` tmux session. The real primitive `dco` uses internally
    is `devcontainer up --workspace-folder ... --config ...`, but
    calling that directly from consal would mean reimplementing two
    things `dco` already owns:
    - `DCO_PROJECT_ID`, a hash of workspace path + sub-config name
      that `devcontainer.json`'s `${localEnv:DCO_PROJECT_ID:default}`
      mount sources consume only at `devcontainer up` time, never
      again by `devcontainer exec`. A second implementation of that
      hash in Python would have nothing enforcing it stays
      byte-for-byte identical to `dco`'s own forever; drift would
      silently fork every project's volumes (old data orphaned under
      the old hash), exactly the silent-self-consistency failure
      principle #1 warns about.
    - Git identity sync (`git config --global user.name`/`user.email`,
      read from the host): `dco` already owns this; a second copy in
      consal would have to be kept in lockstep by hand.

    So `dco` has one small, additive flag: `--up-only` runs everything
    `main()` already does up through git-identity sync (scaffold/
    self-heal, compute+export `DCO_PROJECT_ID`, `devcontainer up`, git
    config sync), then exits 0/1 instead of exec'ing a shell. Still
    squarely container-lifecycle, not autonomy-shaped surface.
    `ensure_container_up` calls `dco <workspace_folder> --sub-config
    <name> --up-only`, the workspace path passed explicitly (matching
    `run_turn`'s `--workspace-folder`) rather than relying on the
    calling process's cwd matching `dco`'s positional `[path]` argument
    implicitly. `DCO_PROJECT_ID` is consumed only at `devcontainer up`
    time, so consal's per-turn `run_turn` needs no knowledge of it at
    all. Every per-turn call after bring-up is consal calling the
    public `devcontainer` CLI directly: `devcontainer exec
    --workspace-folder ... --config ... -- claude -p "$PROMPT"`,
    always passing both `--workspace-folder` and `--config` (omitting
    `--config` makes the CLI default to matching against the default
    profile's container, which fails with "Dev container not found"
    against a named sub-config). Growing `dco` a new `--exec`-style
    flag instead would re-add autonomy-shaped surface to a tool that's
    deliberately kept generic.
  - **Success/failure signal comes free:** `devcontainer exec` is a
    synchronous foreground subprocess with a real exit code and
    captured stdout/stderr, so principle #4 (explicit return value) is
    satisfied by construction. No idle-vs-working ambiguity, since
    consal is the one blocking on the call.
  - **Container reuse, not fresh-per-task:** one container persists for
    the whole autonomous run, rebuilt only when the profile changes.
    Keeps `dco`'s existing persistence (`~/.claude` volume, bash
    history) and avoids a container-build latency tax every loop turn.
    Named tradeoff, not a free win: fresh-per-issue would bound
    cross-issue state drift more tightly (a confused agent can't drag
    stale context from issue N into issue N+1). Default to reuse for
    v1; revisit if drift turns out to be a real problem.

  Net effect: `dco` gains one small additive flag for consal's
  benefit, `--up-only` for headless bring-up. Every per-turn call
  after that is consal calling the public `devcontainer` CLI directly.

- **Distribution model: a small package, stdlib + subprocess only.**
  This splits into two independent axes:
  - **Dependency policy: stay stdlib + subprocess.** consal already
    depends on `dco` by shelling out to it, the same way `dco` shells
    out to `docker`/`gh`/`devcontainer`. Continue that pattern one
    level up: consal talks to GitHub by shelling out to `gh` (parsing
    its JSON output with stdlib `json`), not via `PyGithub`/`requests`.
    No third-party runtime dependencies. Preserves the same
    auditability property that motivated trimming `dco` itself down to
    ~350 lines. Nothing to trust beyond stdlib and the CLIs already
    being shelled out to.
  - **File layout: a package (`src/consal/`), not one file.** Breaks
    from `dco`'s own single-file precedent, deliberately. The reason
    consal is Python and not bash is that the part that needs Python's
    testing/documentation tooling is exactly the part that's complex
    and evolving. That only pays off with real module boundaries
    (GitHub polling, prompt construction, guardrail checks, and the
    scheduling loop are genuinely separate concerns). A single file
    fights the unit/integration test split below.
  - **No PyPI distribution needed**, single-user tool. `pipx install
    -e .` (or bare `python3 -m consal`) from the checkout is the whole
    story; skip packaging ceremony beyond what `pyproject.toml`/pytest
    need.

- **Testing strategy: unit/integration split mapped directly to the
  engineering principles above:**
  - Config self-consistency (referenced paths exist) → **unit**,
    tmp-dir fixtures, fast and deterministic.
  - Standing reachability check (allowlist/endpoints) → **unit-test
    the checker logic** against mocked good/bad hosts. The live check
    itself ships as a product feature (a `consal doctor` command), not
    a CI assertion; network state isn't CI's job to assert.
  - Secret sanitization vs. terminal escape sequences → **unit**,
    against real byte-sequence fixtures (actual ANSI/bracketed-paste
    bytes), never mocked away. Principle #6 is a direct warning
    against exactly that.
  - Explicit success/failure → convention + test pairing: every
    fallible function gets a positive *and* negative test, backed by a
    lint rule against bare `except`.
  - Retry paired with independent verification → **integration-ish**,
    simulate retry-with-a-fake-verifier and assert escalation on
    "unrecoverable" instead of infinite retry.
  - Mocked infra hiding real bugs (the meta-principle) → a real
    **integration tier** that hits actual `gh`/`dco`/`devcontainer`
    against a disposable sandbox repo, not subprocess mocks.
  - Idle vs. working ambiguity → solved by construction, since
    headless turns are synchronous `devcontainer exec` (see the `dco`
    interface decision above), and covered by both a scheduler-dispatch
    unit test (mocked, checking that pending work makes the loop
    actually issue the call) and a real integration test
    (`tests/integration/test_scheduler.py`) exercising the full chain:
    real container bring-up, real `list_open_issues`, real prompt
    construction, real state persistence, against the live GitHub repo.
    That test deliberately mocks only `container.run_turn` and
    `github.comment_on_issue`: letting an unscoped `claude -p` turn
    actually work a live issue would combine an uncontrollable
    model-judgment confound (the same reason the guardrail-enforcement
    tests invoke the hook script directly instead of a live `claude -p`
    turn) with a real mutating GitHub write on every run.

  Mechanically: `pytest -m integration` as an opt-in marker, run
  separately from the fast default suite. Fast tier runs on every
  save; the real-tools tier runs less often (pre-merge, not every
  commit). Coverage gets judged against "would this have caught the
  last few real bugs" (principle #6), not against a passing count.

- **Guardrail hook ownership: authored fresh in consal, no Python-side
  reimplementation.** The local-guardrail layer from "Isolation &
  safety goals" (block `git push --force`, direct pushes to
  `main`/`master`, `gh pr merge`, branch-protection tampering, `gh
  secret set`) is a Claude Code `PreToolUse` hook, which has to be a
  shell command, since that's the interface Claude Code's hook system
  calls. There is no legitimate Python equivalent to build: a parallel
  policy checker in consal's own code would never actually run in the
  enforcement path, since consal (orchestrating from outside the
  container via `devcontainer exec`) has no visibility into individual
  Bash tool calls Claude Code makes mid-turn, it only ever sees a
  turn's aggregate exit code. Building one anyway would be dead code
  that could silently drift from what the real hook actually enforces.

  The policy itself is genuinely autonomy-specific (not something
  `dco` should know about, consistent with the whole architecture
  split), so it's authored and owned as a static template in consal:
  `src/consal/templates/guardrail-hook.sh`, hand-written, ~10 pattern
  checks, no generation from a Python policy DSL.
  `config.generate_subconfig` copies it into each managed project's
  `.devcontainer/<name>/` and writes a `.claude/settings.json` at the
  project root registering it as a `PreToolUse` hook;
  `config.validate_subconfig` checks the copy is actually present.
  Tested by shelling out to the real script with sample tool-call JSON
  on stdin (both block- and allow-cases): a Python reimplementation of
  the rules would test logic the real hook never runs.

- **CLI config: CLI args are canonical, a checked-in
  `.consal/config.toml` just pre-fills them.** Standard layered-config
  pattern: precedence is explicit `--flag` > config file value >
  built-in default, not two parallel ways to configure the tool.
  `project_id`/`repo` get no built-in default (guessing wrong here
  could point the scheduler at the wrong GitHub repo, or collide two
  projects' `~/.consal/<project_id>/` state directories).
  `resolve_settings` raises a clear error naming exactly what's
  missing and where it could come from, rather than silently picking
  something. `sub_config` defaults to `"consal"`; `workspace` defaults
  to cwd, matching `dco`'s own convention for its positional `[path]`.
  The config file is static, checked-in project config, like the
  sub-config profile itself, not runtime state, so it lives in the
  project's own repo, not `~/.consal/<project_id>/`. Parsed via stdlib
  `tomllib` (Python 3.11+, already required), no new dependency.

- **`consal doctor`: three check categories, directly off principles
  #1/#2 and the testing-strategy decision that named this command.**
  Distinct from the test suite, which checks code logic against mocks
  and never the real machine it runs on:
  - Environment prerequisites (`dco`/`devcontainer` on PATH, `gh`
    authenticated, `CONSAL_GH_PAT`/`CLAUDE_CODE_OAUTH_TOKEN` set): the
    same category `tests/integration/test_environment.py` checks, but
    as a real command a human runs against their own machine.
  - Sub-config self-consistency (principle #1) via the existing
    `config.validate_subconfig`.
  - Standing allowlist reachability (principle #2): a real
    `socket.getaddrinfo` per domain in the sub-config's
    `allowlist.txt`, not a one-time assertion that the list is correct
    because it's written down.

- **`consal init`: the CLI entry point for `config.generate_subconfig`.**
  `consal init` wraps it and optionally merges
  `project_id`/`repo`/`sub_config` into `.consal/config.toml`,
  whichever were given. Unlike `doctor`/`run`, nothing is required:
  generating the sub-config itself needs neither `project_id` nor
  `repo` (`generate_subconfig`'s own signature takes only a workspace
  and a sub-config name). Re-running `init` merges into the existing
  config file rather than clobbering it, so recording `project_id`
  later doesn't lose a `repo` set earlier.

- **Documentation structure.** Docstrings carry API-level detail
  (every module in `src/consal/` has a substantive top-of-file
  docstring). `README.md` is quickstart/usage only, split into a
  "Status" section naming what's real vs. not yet built and a "Usage"
  section walking prerequisites → `consal init` → `.consal/config.toml`
  → `consal doctor` → `consal run`. `CONSAL_GOALS.md` (this file) is
  the separate design doc for the "why." Incremental fixes stay in
  commit messages, not accreted into the README; no new artifact
  (changelog, docs/ directory, doc generator) needed for a single-user
  CLI tool.

## Non-goals

- Reimplementing GitHub's own issue/PR primitives.
- `dco` reimplementing anything about GitHub, autonomy, or Claude
  Code's own agentic-loop/scheduling primitives: that entire domain
  now belongs to consal, not `dco`, by design.
