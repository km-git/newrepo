from dspm.risk import models as _models  # noqa: F401


def test_risk_module_imports() -> None:
    import dspm.risk.service as service

    assert service is not None
