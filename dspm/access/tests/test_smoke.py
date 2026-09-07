from dspm.access import models as _models  # noqa: F401


def test_access_module_imports() -> None:
    import dspm.access.service as service

    assert service is not None
