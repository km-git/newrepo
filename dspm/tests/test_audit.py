from pathlib import Path

from dspm.audit.service import build_inventory


def test_inventory_lists_modules():
    inv = build_inventory()
    assert inv["module_count"] == 20
    assert len(inv["modules"]) >= 12
    assert inv["oss_tool_count"] == 11


def test_inventory_json_written(tmp_path: Path):
    from dspm.audit.service import write_inventory_json

    out = tmp_path / "inv.json"
    data = write_inventory_json(out)
    assert out.exists()
    assert data["oss_tools"][0]["name"] == "presidio-analyzer"
