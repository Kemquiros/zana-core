"""Tests for S14-3: web search tool via DuckDuckGo."""

import builtins
import sys
import types
from unittest.mock import MagicMock, patch


def _inject_ddg_module():
    """Inject a fake duckduckgo_search module into sys.modules so patch() works."""
    if "duckduckgo_search" not in sys.modules:
        fake = types.ModuleType("duckduckgo_search")
        fake.DDGS = MagicMock  # placeholder
        sys.modules["duckduckgo_search"] = fake


def test_web_search_intent_detected():
    """'busca en internet Python' triggers web_search intent."""
    from zana.core.zsm import _detect_intent

    intent = _detect_intent("busca en internet Python tutorials")
    assert intent == "web_search"


def test_web_search_english_intent_detected():
    """'search the web for Python' triggers web_search intent."""
    from zana.core.zsm import _detect_intent

    intent = _detect_intent("search the web for Python tutorials")
    assert intent == "web_search"


def test_web_search_french_intent_detected():
    """French trigger 'recherche sur internet' triggers web_search intent."""
    from zana.core.zsm import _detect_intent

    intent = _detect_intent("recherche sur internet machine learning")
    assert intent == "web_search"


def test_web_search_returns_results():
    """DDGS.text with mocked results -> formatted output printed."""
    _inject_ddg_module()

    mock_results = [
        {
            "title": "Python Docs",
            "body": "Official Python documentation.",
            "href": "https://docs.python.org",
        },
        {
            "title": "Real Python",
            "body": "Learn Python programming.",
            "href": "https://realpython.com",
        },
    ]

    mock_ddgs = MagicMock()
    mock_ddgs.__enter__ = lambda s: s
    mock_ddgs.__exit__ = MagicMock(return_value=False)
    mock_ddgs.text = MagicMock(return_value=mock_results)

    with (
        patch("duckduckgo_search.DDGS", return_value=mock_ddgs),
        patch("zana.core.memory_lite.get_db") as mock_db,
    ):
        mock_db.return_value.add = MagicMock()
        mock_db.return_value.close = MagicMock()
        from zana.core.zsm import _exec_web_search

        _exec_web_search("busca en internet Python tutorials")

    mock_ddgs.text.assert_called_once_with("Python tutorials", max_results=5)


def test_web_search_ddg_not_installed(monkeypatch):
    """ImportError for duckduckgo_search -> graceful message, no crash."""
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "duckduckgo_search":
            raise ImportError("No module named 'duckduckgo_search'")
        return real_import(name, *args, **kwargs)

    # Remove from sys.modules to force re-import
    sys.modules.pop("duckduckgo_search", None)
    monkeypatch.setattr(builtins, "__import__", mock_import)

    from zana.core.zsm import _exec_web_search

    # Should not raise — graceful error message
    _exec_web_search("busca en internet Python")


def test_web_search_network_error():
    """Exception in DDGS.text -> graceful error, no crash."""
    _inject_ddg_module()

    mock_ddgs = MagicMock()
    mock_ddgs.__enter__ = lambda s: s
    mock_ddgs.__exit__ = MagicMock(return_value=False)
    mock_ddgs.text = MagicMock(side_effect=Exception("Network error"))

    with patch("duckduckgo_search.DDGS", return_value=mock_ddgs):
        from zana.core.zsm import _exec_web_search

        # Should not raise
        _exec_web_search("busca en internet Python")


def test_web_search_empty_query():
    """Empty query after stripping triggers -> helpful message, no search."""
    _inject_ddg_module()

    with patch("duckduckgo_search.DDGS") as mock_ddgs_class:
        from zana.core.zsm import _exec_web_search

        _exec_web_search("busca en internet")  # only trigger, no actual query
        # DDGS should not be instantiated
        mock_ddgs_class.assert_not_called()
