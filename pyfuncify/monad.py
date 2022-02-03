from pymonad.operators.either import Either
from typing import Any, TypeVar, Callable, Union, Any

from .logger import logger

M = TypeVar('M') # pylint: disable=invalid-name
S = TypeVar('S') # pylint: disable=invalid-name
T = TypeVar('T') # pylint: disable=invalid-name

class MEither(Either):
    def __or__(self, fns):
        """
        Acts as a Monadic OR, determining the function to execute based on the Either.
        Provide 2 terminating functions (failure_fn, success_fn)
        """
        return self.either(fns[0], fns[1])

    # Lifts the either; returning the wrapped value regardless of Left or Right
    def lift(self):
        return self.value if self.is_right() else self.monoid[0]

    def error(self):
        return self.monoid[0]


def Left(value: M) -> Either[M, Any]: # pylint: disable=invalid-name
    """ Creates a value of the first possible type in the Either monad. """
    return MEither(None, (value, False))


def Right(value: T) -> Either[Any, T]: # pylint: disable=invalid-name
    """ Creates a value of the second possible type in the Either monad. """
    return MEither(value, (None, True))

def maybe_value_ok(value: T) -> bool:
    return value.is_right()

def maybe_value_fail(value: T) -> bool:
    return value.is_left()

def monadic_try(name: str =None,
                status: int =None,
                exception_test_fn: Callable[[MEither], MEither]=None,
                error_cls: Any=None,
                error_result_fn: Callable=None):
    """
    Monadic Try Decorator.  Decorate any function which might return an exception.  When the function does not return an exception,
    the decorator wraps the result in a Right(), otherwise, it wraps the exception in a Left()

    Args:
        name: The name to be provided to the error object
        status: The status to be provided to the error object
        exception_test_fn: A function which takes the result.
                           When the result is Right, but the data may result in a Left.
                           The fn must return a value wrapped in an Either
        error_result_fn:   A function whose result will be returned in the exception flow.  It takes a built exception (either str or error_cls)

    The @monadic_try(name="step") is really syntax sugar for:
        $ monadic_try(name="x")(fn)(args)

        Hence the 3 nested functions
    """
    def inner(fn):
        def try_it(*args, **kwargs):
            try:
                result = Right(fn(*args, **kwargs))
                test_fn = kwargs.get('expectation_fn', exception_test_fn)
                return test_fn(result) if test_fn else result
            except Exception as e:
                error_result = Left(error_cls(message=str(e), name=(name or fn.__name__), code=status, klass=str(e.__class__))) if error_cls else Left(str(e))
                return_fn = kwargs.get('error_result_fn', error_result_fn)
                return return_fn(error_result) if return_fn else error_result

        return try_it
    return inner

def any_error(try_result: MEither) -> Union[str, None]:
    return try_result.either(lambda res: str(res.error()), lambda res: None)
