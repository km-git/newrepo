from dspm.encryption_check import models


def test_encryption_check_module_imports() -> None:
    import dspm.encryption_check.service as service

    assert models is not None
    assert service is not None
