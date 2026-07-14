"""Integration tests: hit real `gh`/`dco`/`devcontainer` against a
disposable sandbox repo, per EIGEN_GOALS.md's testing strategy. Excluded
from the default run (see `addopts` in pyproject.toml); run explicitly
with `pytest -m integration`.
"""

import pytest

pytestmark = pytest.mark.integration


def test_placeholder() -> None:
    pytest.skip("no integration tests yet — real gh/dco/devcontainer plumbing isn't built")
