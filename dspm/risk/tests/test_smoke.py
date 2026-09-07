from dspm.risk import models


def test_risk_module_imports() -> None:
    import dspm.risk.service as service

    assert models is not None
    assert service is not None
