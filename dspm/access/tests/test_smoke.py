from dspm.access import models


def test_access_module_imports() -> None:
    import dspm.access.service as service

    assert models is not None
    assert service is not None
