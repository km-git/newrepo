from dspm.classification import models as _models  # noqa: F401


def test_classification_module_imports() -> None:
    import dspm.classification.service as service

    assert service is not None
