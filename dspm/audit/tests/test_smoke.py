from dspm.audit import models as _models  # noqa: F401


def test_audit_module_imports() -> None:
    import dspm.audit.service as service

    assert service is not None
