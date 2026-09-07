from dspm.ai_security import models


def test_ai_security_module_imports() -> None:
    import dspm.ai_security.service as service

    assert models is not None
    assert service is not None
