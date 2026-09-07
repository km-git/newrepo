from dspm.shadow import models as _models  # noqa: F401


def test_shadow_module_imports() -> None:
    import dspm.shadow.service as service

    assert service is not None
