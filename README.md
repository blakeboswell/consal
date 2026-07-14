# Eigen

A self-driving development system: point it at a project idea and it
decomposes a plan into GitHub issues, then works them autonomously inside
a `dco`-managed container, with GitHub itself (issues/PRs) as the
steering interface.

See [`EIGEN_GOALS.md`](./EIGEN_GOALS.md) for the full design rationale
and the decisions this repo's structure follows.

## Status

Early scaffolding — not yet functional.

## Development

```sh
uv sync                # install deps into .venv
uv run pytest          # fast unit tests only
uv run pytest -m integration   # real gh/dco/devcontainer integration tests
uv run eigen doctor    # self-consistency / reachability checks (stub)
```
