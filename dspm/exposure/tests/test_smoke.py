from dspm.exposure import models as _models  # noqa: F401


def test_exposure_module_imports() -> None:
    import dspm.exposure.service as service

    assert service is not None
