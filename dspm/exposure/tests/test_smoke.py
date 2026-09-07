from dspm.exposure import models


def test_exposure_module_imports() -> None:
    import dspm.exposure.service as service

    assert models is not None
    assert service is not None
