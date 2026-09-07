from dspm.classification import models


def test_classification_module_imports() -> None:
    import dspm.classification.service as service

    assert models is not None
    assert service is not None
