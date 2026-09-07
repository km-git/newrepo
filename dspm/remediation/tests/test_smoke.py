from dspm.remediation import models as _models  # noqa: F401


def test_remediation_module_imports() -> None:
    import dspm.remediation.service as service

    assert service is not None
