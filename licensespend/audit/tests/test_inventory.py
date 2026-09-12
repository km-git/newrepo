from licensespend.audit.service import inventory


def test_inventory_lists_modules_and_pygithub_leaf() -> None:
    data = inventory()
    dumped = data.model_dump()
    assert dumped["product"] == "licensespend"
    assert "m365" in dumped["modules"]
    assert dumped["tool_count"] >= 8
    pygithub = next(t for t in dumped["tools"] if t["package"] == "PyGithub")
    assert pygithub["license"].startswith("LGPL")
    assert dumped["gates"]["pygithub_vendored"] is False
    assert dumped["gates"]["metadata_only"] is True
