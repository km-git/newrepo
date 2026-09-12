from dspm.loop.watch import classify_item, url_hash


def test_url_hash_dedupes():
    h1 = url_hash("https://example.com/a")
    h2 = url_hash("https://example.com/a")
    assert h1 == h2


def test_classify_dspm_keyword_scores_high():
    item = classify_item(
        {"title": "Best DSPM vendors: Cyera vs Presidio", "summary": "data security posture", "url": "http://x"},
        dspm_context="dspm/classification",
    )
    assert item["verdict"] in {"discover", "watch"}
    assert item["score"] >= 5
