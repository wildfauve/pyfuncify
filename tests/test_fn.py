from pyfuncify import fn

def it_returns_identity():
    assert fn.identity(1) == 1


def it_deep_gets():
    assert fn.deep_get({'a': {'b': 1}}, ['a', 'b']) == 1


def it_composes_piped_fns():
    add1 = lambda x: x + 1
    assert(fn.compose_iter([add1, add1], 10) == 12)

def it_removes_all_none_from_list():
    assert(fn.remove_none([1,2,None]) == [1,2])

def it_removes_from_list_based_on_predicate():
    assert(fn.remove(lambda x: x == 1, [1,2,None]) == [2, None])

def it_flattens_an_n_dimensional_list():
    assert fn.flatten([[1], [2]]) == [1,2]