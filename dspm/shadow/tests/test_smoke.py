from dspm.shadow import models


def test_shadow_module_imports() -> None:
    import dspm.shadow.service as service

    assert models is not None
    assert service is not None
