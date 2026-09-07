from dspm.ai_security import models as _models  # noqa: F401


def test_ai_security_module_imports() -> None:
    import dspm.ai_security.service as service

    assert service is not None
