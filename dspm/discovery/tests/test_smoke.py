from dspm.discovery import models


def test_discovery_module_imports() -> None:
    import dspm.discovery.service as service

    assert models is not None
    assert service is not None
