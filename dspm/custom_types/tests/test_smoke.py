from dspm.custom_types import models as _models  # noqa: F401


def test_custom_types_module_imports() -> None:
    import dspm.custom_types.service as service

    assert service is not None
