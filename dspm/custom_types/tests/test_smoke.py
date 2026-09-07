from dspm.custom_types import models


def test_custom_types_module_imports() -> None:
    import dspm.custom_types.service as service

    assert models is not None
    assert service is not None
