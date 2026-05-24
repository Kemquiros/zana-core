"""Global pytest fixtures — applied to all tests in cli/tests/."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def reset_zsm_session_context():
    """Clear _SESSION_CONTEXT before every test to prevent cross-test intent score contamination."""
    from zana.core.zsm_engine import _SESSION_CONTEXT

    _SESSION_CONTEXT.clear()
    yield
    _SESSION_CONTEXT.clear()
