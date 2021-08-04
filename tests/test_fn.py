from pyfuncify import fn

def it_returns_identity():
    assert fn.identity(1) == 1


def it_deep_gets():
    assert fn.deep_get({'a': {'b': 1}}, ['a', 'b']) == 1
