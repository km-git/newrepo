"""Smoke tests for sspm.oauth_grants."""

from __future__ import annotations

from sspm.oauth_grants import models, service


def test_module_imports() -> None:
    assert service is not None
    assert models is not None
