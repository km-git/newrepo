from dspm.compliance import models


def test_compliance_module_imports() -> None:
    import dspm.compliance.service as service

    assert models is not None
    assert service is not None
