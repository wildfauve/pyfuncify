from pyfuncify import fn, chronos, monad

#
# fn.identity
#
def it_returns_identity():
    assert fn.identity(1) == 1

#
# fn.deep_get
#
def it_deep_gets():
    assert fn.deep_get({'a': {'b': 1}}, ['a', 'b']) == 1

#
# fn.compose_iter
#
def it_composes_piped_fns():
    add1 = lambda x: x + 1
    assert(fn.compose_iter([add1, add1], 10) == 12)


#
# fn.either_compose
#
def it_either_composes_fns():
    add1 = lambda x: monad.Right(x + 1)
    assert fn.either_compose([add1, add1], monad.Right(10)) == monad.Right(12)

def it_either_composes_until_a_left():
    add1 = lambda x: monad.Right(x + 1)
    failed = lambda x: monad.Left('boom!')
    assert fn.either_compose([add1, failed, add1], monad.Right(10)) == monad.Left('boom!')


#
# fn.find_by_filter
#
def it_finds_1_element_with_predicate_fn():
    predicate_fn = lambda x: x == 1
    res = fn.find_by_filter(predicate_fn, [1,2,3])

    assert res == 1

def it_returns_none_when_no_instances_found():
    predicate_fn = lambda x: x == 4
    res = fn.find_by_filter(predicate_fn, [1,2,3])

    assert not res

#
# Test Equality
#
def it_uses_the_equility_fn_to_find_in_list():
    result = fn.find(fn.equality('a', "equal"),([{'a': "equal"}]))

    assert result['a'] == 'equal'


#
# fn.remove_none
#
def it_removes_all_none_from_list():
    assert(fn.remove_none([1,2,None]) == [1,2])

#
# fn.remove
#
def it_removes_from_list_based_on_predicate():
    assert(fn.remove(lambda x: x == 1, [1,2,None]) == [2, None])

#
# fn.flatten
#
def it_flattens_an_n_dimensional_list():
    assert fn.flatten([[1], [2]]) == [1,2]
    
#
# fn.find_by_predicate(predicate_fn: Callable, iterable: List):
#
def it_finds_1st_element_using_predicate_and_returns_maybe():
    predicate_fn = lambda x: x == 1

    result = fn.find_by_predicate(predicate_fn, [1,2,3])

    assert result.is_just()
    assert result.value == 1

def it_fails_to_find_and_returns_nothing():
    predicate_fn = lambda x: x == 4

    result = fn.find_by_predicate(predicate_fn, [1,2,3])
    assert not result.value

