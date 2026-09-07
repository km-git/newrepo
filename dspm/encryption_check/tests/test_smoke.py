from dspm.encryption_check import models as _models  # noqa: F401


def test_encryption_check_module_imports() -> None:
    import dspm.encryption_check.service as service

    assert service is not None
