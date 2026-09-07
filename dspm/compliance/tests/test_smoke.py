from dspm.compliance import models as _models  # noqa: F401


def test_compliance_module_imports() -> None:
    import dspm.compliance.service as service

    assert service is not None
