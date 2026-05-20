"""
Tests for zana upgrade --grove (tier upgrade wizard).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from zana.commands.upgrade import cmd_grove_upgrade


def test_grove_upgrade_skips_when_already_installed() -> None:
    # Patch at source — is_sqlite_vec_available is locally imported inside cmd_grove_upgrade
    with patch("zana.core.memory_lite.is_sqlite_vec_available", return_value=True):
        cmd_grove_upgrade(no_interactive=True)


def test_grove_upgrade_installs_successfully() -> None:
    with (
        patch("zana.core.memory_lite.is_sqlite_vec_available", return_value=False),
        patch("zana.commands.upgrade._install_sqlite_vec", return_value=True),
        patch("zana.commands.upgrade._test_sqlite_vec", return_value=True),
    ):
        cmd_grove_upgrade(no_interactive=True)


def test_grove_upgrade_exits_on_install_failure() -> None:
    import typer

    with (
        patch("zana.core.memory_lite.is_sqlite_vec_available", return_value=False),
        patch("zana.commands.upgrade._install_sqlite_vec", return_value=False),
        pytest.raises(typer.Exit),
    ):
        cmd_grove_upgrade(no_interactive=True)


def test_grove_upgrade_exits_on_load_failure() -> None:
    import typer

    with (
        patch("zana.core.memory_lite.is_sqlite_vec_available", return_value=False),
        patch("zana.commands.upgrade._install_sqlite_vec", return_value=True),
        patch("zana.commands.upgrade._test_sqlite_vec", return_value=False),
        pytest.raises(typer.Exit),
    ):
        cmd_grove_upgrade(no_interactive=True)


def test_install_sqlite_vec_runs_pip(monkeypatch) -> None:
    import subprocess

    from zana.commands.upgrade import _install_sqlite_vec

    calls = []

    def fake_run(cmd, capture_output=False):
        calls.append(cmd)
        result = subprocess.CompletedProcess(cmd, returncode=0)
        return result

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = _install_sqlite_vec()
    assert result is True
    assert any("sqlite-vec" in str(c) for c in calls)


def test_test_sqlite_vec_returns_bool() -> None:
    from zana.commands.upgrade import _test_sqlite_vec

    # Should return True or False — never raise
    result = _test_sqlite_vec()
    assert isinstance(result, bool)
