from dmarc.dkim_check import service


def test_module_imports():
    assert service.__doc__
