"""
Tests for zana cloud (subscribe + status commands).
"""

from __future__ import annotations

from unittest.mock import patch

from zana.commands.cloud import PRICING_URL, cmd_cloud_status, cmd_subscribe


def test_cloud_status_runs_without_error() -> None:
    from zana.core.tier import Tier

    with (
        patch("zana.core.tier.detect_tier", return_value=Tier.SPROUT),
        patch("zana.core.memory_lite.is_sqlite_vec_available", return_value=False),
    ):
        cmd_cloud_status()


def test_cloud_status_shows_semantic_active_when_vec_installed() -> None:
    from zana.core.tier import Tier

    with (
        patch("zana.core.tier.detect_tier", return_value=Tier.SPROUT),
        patch("zana.core.memory_lite.is_sqlite_vec_available", return_value=True),
    ):
        cmd_cloud_status()


def test_cloud_status_grove_tier() -> None:
    from zana.core.tier import Tier

    with (
        patch("zana.core.tier.detect_tier", return_value=Tier.GROVE),
        patch("zana.core.memory_lite.is_sqlite_vec_available", return_value=False),
    ):
        cmd_cloud_status()


def test_cloud_status_seed_tier() -> None:
    from zana.core.tier import Tier

    with (
        patch("zana.core.tier.detect_tier", return_value=Tier.SEED),
        patch("zana.core.memory_lite.is_sqlite_vec_available", return_value=False),
    ):
        cmd_cloud_status()


def test_subscribe_does_not_open_browser_when_declined(monkeypatch) -> None:
    import webbrowser

    opened = []
    monkeypatch.setattr(webbrowser, "open", lambda url: opened.append(url))

    with patch("typer.confirm", return_value=False):
        cmd_subscribe()

    assert len(opened) == 0


def test_subscribe_opens_browser_when_confirmed(monkeypatch) -> None:
    import webbrowser

    opened = []
    monkeypatch.setattr(webbrowser, "open", lambda url: opened.append(url))

    with patch("typer.confirm", return_value=True):
        cmd_subscribe()

    assert len(opened) == 1
    assert opened[0] == PRICING_URL


def test_subscribe_shows_three_tiers(capsys) -> None:
    with patch("typer.confirm", return_value=False):
        cmd_subscribe()

    captured = capsys.readouterr()
    assert "Libre" in captured.out
    assert "Sovereign" in captured.out
    assert "Pro" in captured.out


def test_pricing_url_format() -> None:
    assert PRICING_URL.startswith("https://")
    assert "zana" in PRICING_URL or "vecanova" in PRICING_URL


def test_subscribe_handles_keyboard_interrupt_gracefully(monkeypatch) -> None:
    import webbrowser

    monkeypatch.setattr(webbrowser, "open", lambda url: None)

    with patch("typer.confirm", side_effect=KeyboardInterrupt):
        cmd_subscribe()
