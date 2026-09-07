"""Report-language guard tests."""

from __future__ import annotations

import pytest

from cost.language import assert_report_language, contains_banned, scrub_report_text


def test_scrub_replaces_banned_tokens():
    raw = "This compliance attestation is certified, secure, and guaranteed."
    cleaned = scrub_report_text(raw)
    assert contains_banned(cleaned) == []
    assert "framework reference" in cleaned
    assert "configuration reference" in cleaned


def test_assert_report_language_rejects_banned():
    with pytest.raises(ValueError, match="disallowed"):
        assert_report_language("This is a compliance report.")


def test_cost_observation_phrasing_ok():
    assert_report_language("Cloud Cost & Configuration Review with framework references.")
