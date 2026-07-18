from pathlib import Path

import pytest

from consal.settings import (
    Settings,
    SettingsError,
    load_config_file,
    resolve_settings,
    write_config_file,
)


def test_load_config_file_returns_empty_dict_when_missing(tmp_path: Path) -> None:
    assert load_config_file(tmp_path) == {}


def test_load_config_file_parses_toml(tmp_path: Path) -> None:
    (tmp_path / ".consal").mkdir()
    (tmp_path / ".consal" / "config.toml").write_text(
        'project_id = "myproj"\nrepo = "owner/repo"\n'
    )
    assert load_config_file(tmp_path) == {"project_id": "myproj", "repo": "owner/repo"}


def test_resolve_settings_from_explicit_args(tmp_path: Path) -> None:
    settings = resolve_settings(
        workspace=tmp_path, project_id="myproj", repo="owner/repo", sub_config="custom"
    )
    assert settings == Settings(
        workspace=tmp_path.resolve(),
        project_id="myproj",
        repo="owner/repo",
        sub_config="custom",
    )


def test_resolve_settings_falls_back_to_config_file(tmp_path: Path) -> None:
    (tmp_path / ".consal").mkdir()
    (tmp_path / ".consal" / "config.toml").write_text(
        'project_id = "fromconfig"\nrepo = "owner/fromconfig"\nsub_config = "customsub"\n'
    )
    settings = resolve_settings(workspace=tmp_path)
    assert settings.project_id == "fromconfig"
    assert settings.repo == "owner/fromconfig"
    assert settings.sub_config == "customsub"


def test_resolve_settings_explicit_arg_overrides_config_file(tmp_path: Path) -> None:
    (tmp_path / ".consal").mkdir()
    (tmp_path / ".consal" / "config.toml").write_text(
        'project_id = "fromconfig"\nrepo = "owner/fromconfig"\n'
    )
    settings = resolve_settings(workspace=tmp_path, project_id="fromarg")
    assert settings.project_id == "fromarg"
    assert settings.repo == "owner/fromconfig"


def test_resolve_settings_sub_config_defaults_to_consal(tmp_path: Path) -> None:
    settings = resolve_settings(workspace=tmp_path, project_id="p", repo="o/r")
    assert settings.sub_config == "consal"


def test_resolve_settings_workspace_defaults_to_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    settings = resolve_settings(project_id="p", repo="o/r")
    assert settings.workspace == tmp_path.resolve()


def test_resolve_settings_raises_when_project_id_missing(tmp_path: Path) -> None:
    with pytest.raises(SettingsError, match="project-id"):
        resolve_settings(workspace=tmp_path, repo="o/r")


def test_resolve_settings_raises_when_repo_missing(tmp_path: Path) -> None:
    with pytest.raises(SettingsError, match="repo"):
        resolve_settings(workspace=tmp_path, project_id="p")


def test_resolve_settings_error_names_config_path(tmp_path: Path) -> None:
    with pytest.raises(SettingsError, match=r"\.consal/config\.toml"):
        resolve_settings(workspace=tmp_path)


def test_write_config_file_creates_file_and_parent_dir(tmp_path: Path) -> None:
    config_path = write_config_file(tmp_path, project_id="p", repo="o/r")
    assert config_path == tmp_path / ".consal" / "config.toml"
    assert load_config_file(tmp_path) == {"project_id": "p", "repo": "o/r"}


def test_write_config_file_merges_with_existing_values(tmp_path: Path) -> None:
    write_config_file(tmp_path, project_id="p", repo="o/r")
    write_config_file(tmp_path, sub_config="custom")
    assert load_config_file(tmp_path) == {
        "project_id": "p",
        "repo": "o/r",
        "sub_config": "custom",
    }


def test_write_config_file_overwrites_only_given_keys(tmp_path: Path) -> None:
    write_config_file(tmp_path, project_id="old", repo="o/r")
    write_config_file(tmp_path, project_id="new")
    assert load_config_file(tmp_path) == {"project_id": "new", "repo": "o/r"}


def test_write_config_file_round_trips_special_characters(tmp_path: Path) -> None:
    tricky = 'has "quotes" and \\backslashes'
    write_config_file(tmp_path, project_id=tricky)
    assert load_config_file(tmp_path) == {"project_id": tricky}
