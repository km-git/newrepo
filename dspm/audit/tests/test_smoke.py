from dspm.audit import models


def test_audit_module_imports() -> None:
    import dspm.audit.service as service

    assert models is not None
    assert service is not None
