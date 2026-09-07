from dspm.discovery import models as _models  # noqa: F401


def test_discovery_module_imports() -> None:
    import dspm.discovery.service as service

    assert service is not None
