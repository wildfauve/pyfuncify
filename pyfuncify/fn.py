from pymonad.maybe import *
from pymonad.tools import curry
from pymonad.list import *
from typing import Dict, List, Any, Union, Callable
import re

"""
Common functions
"""

def identity(arg):
    return arg

def deep_get(dict: Dict, path: List[str], default: Any=None) -> Any:
    """
    Takes a Dict, a path into the Dict as a list, and a default if nothing found, and returns the item at the path.
    Note, only works for a nested Dict, no Lists are supported.
    Example:
        $ deep_get({'a': {'b': 1}}, ['a', 'b'], 0)
    """
    fst, rst = first(path), rest(path)
    if fst not in dict: return default
    if (fst in dict) and len(rst) == 0: return dict[fst]
    return deep_get(dict[fst], rst, default)

def rest(iterable):
    return iterable[1:]

def partial_first(iterable):
    return first(iterable)

def first(iterable, default=None, key=None):
    """
    Return first element of `iterable` that evaluates true, else return None
    (or an optional default value).
    >>> first([0, False, None, [], (), 42])
    42
    >>> first([0, False, None, [], ()]) is None
    True
    >>> first([0, False, None, [], ()], default='ohai')
    'ohai'
    >>> import re
    >>> m = first(re.match(regex, 'abc') for regex in ['b.*', 'a(.*)'])
    >>> m.group(1)
    'bc'
    The optional `key` argument specifies a one-argument predicate function
    like that used for `filter()`.  The `key` argument, if supplied, must be
    in keyword form.  For example:
    >>> first([1, 1, 3, 4, 5], key=lambda x: x % 2 == 0)
    4
    """
    if key is None:
        for el in iterable:
            if el:
                return el
    else:
        for el in iterable:
            if key(el):
                return el
    return default

def find_by_type(type, iterable):
    return partial_filter(type_predicate(type), iterable).then(partial_first)

def type_predicate(type):
    return lambda x: x['_type'] == type

def partial_filter(fn, iterable):
    return Just(list(filter(fn, iterable)))

def find_by_filter(fn, xs):
    return next(filter(fn, xs), None)

@curry(2)
def find(fn, xs):
    """
    fn.find(fn.equality(fn.at('a')), '1', [{'a': '1'}])
    """
    return next(select(fn, xs))

def select(fn: Callable, xs: List) -> filter:
    """
    returns all values from the list that are true when applying the fn to the item
    """
    return filter(fn, xs)
    # return iter([element for element in xs if fn(element)])

# + field_fn; the property to extract from the record.  Either a String or a Function which takes the record
# + test_value; the value which has == applied to determine equality
# + i; the record under test
# e.g. equality.(:a).("equal").({a: "equal"})
# e.g. equality.(test_fn).("equal").({a: "equal"})) ; where test_fn is -> x { x[:a] }
@curry(3)
def equality(field_or_fn, test_value, i):
    if callable(field_or_fn):
        return field_or_fn(i) == test_value
    else:
        return i[field_or_fn] == test_value


@curry(2)
def at(x, i):
    if x is None:
        return None
    elif x not in i:
        return None
    else:
        return i[x]

@curry(2)
def match(pattern, test_string):
    return re.match(pattern, test_string)

# Curryed fn that removes elements from a collection where f.(e) is true
@curry(2)
def remove(fn, xs):
    return list(filter(fn, xs))


def remove_none(xs):
    return remove(lambda x: x is not None, xs)

def not_empty(xs: List[Any]) -> bool:
    return len(xs) > 0

def only_one(xs: List[Any]) -> bool:
    return len(xs) == 1
