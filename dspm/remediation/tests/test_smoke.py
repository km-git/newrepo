from dspm.remediation import models


def test_remediation_module_imports() -> None:
    import dspm.remediation.service as service

    assert models is not None
    assert service is not None
