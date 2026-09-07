from licensespend.loop.service import classify_finding, is_mechanical_issue, skip_commercial


def test_classify_abstains_unknown_sku() -> None:
    result = classify_finding(sku="not-a-sku", idle_days=120, user_id_hash="abc" * 10)
    assert result.abstain is True
    assert result.reclaim_aud is None


def test_classify_rejects_raw_email() -> None:
    try:
        classify_finding(sku="m365-e3", idle_days=120, user_id_hash="alex@contoso.example")
    except ValueError as exc:
        assert "unhashed" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_skip_commercial_and_issue_gates() -> None:
    assert skip_commercial("Zylo vs Productiv comparison")
    assert not skip_commercial("msgraph-sdk 1.0 release")
    denied = is_mechanical_issue("update Graph permissions", "", ["good first issue"])
    assert denied["eligible"] is False
    price = is_mechanical_issue("bump pricebook AUD", "", ["good first issue"])
    assert price["eligible"] is False
    ok = is_mechanical_issue("typo in README", "", ["good first issue"])
    assert ok["eligible"] is True
